#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Subject-B inverse + forward conditional PINN.

Workflow
--------
STAGE 1
    Fit a differentiable conditional trajectory PINN to real Subject-B data.

STAGE 2
    Freeze the trajectory network and identify:
        kp_theta
        kd_theta
        kp_x
        kd_x
        Pi

    tau is fixed at 0.23 s.

STAGE 3
    Freeze the identified controller and refine the same conditional network
    over random initial conditions using nonlinear physics.

STAGE 4
    Generate and save synthetic Subject-B trajectories.

Dependencies
------------
tensorflow
numpy
resampy
matplotlib
tqdm
"""
from __future__ import annotations
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import resampy
import tensorflow as tf
from numpy import genfromtxt
from tqdm import tqdm
tf.keras.backend.set_floatx('float32')
SEED = 1234
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

@dataclass
class Config:
    data_folder: str = '/home/qdj17/SAFE-POSE/pole_balancing/Pole_balancing_data/SubjectB'
    file_pattern: str = 'SubjectB_*.tsv'
    number_of_trials: int = 14
    original_rate_hz: int = 250
    processed_rate_hz: int = 100
    start_index_raw: int = 1024
    output_folder: str = 'subject_b_inverse_forward_results'
    stick_mass_kg: float = 0.0138
    stick_length_m: float = 0.57
    gravity_m_s2: float = 9.81
    effective_cart_mass_kg: float = 1.0
    tau_s: float = 0.23
    fall_angle_deg: float = 20.0
    prefall_margin_s: float = 0.08
    minimum_trial_seconds: float = 2.0
    derivative_fit_samples: int = 11
    width: int = 128
    depth: int = 4
    fourier_modes: int = 16
    theta_output_scale_rad: float = math.radians(25.0)
    x_output_scale_m: float = 0.25
    stage1_epochs: int = 7000
    stage1_batch_size: int = 2048
    stage1_learning_rate: float = 0.0008
    stage1_data_warmup_epochs: int = 1500
    stage1_physics_weight: float = 0.02
    stage1_history_weight: float = 2.0
    stage2_epochs: int = 5000
    stage2_batch_size: int = 4096
    stage2_gain_learning_rate: float = 0.001
    stage2_pi_learning_rate: float = 0.0001
    stage2_pi_freeze_epochs: int = 1500
    initial_kp_theta: float = 150.0
    initial_kd_theta: float = 20.0
    initial_kp_x: float = 10.0
    initial_kd_x: float = 20.0
    initial_pi_deg: float = 3.0
    pi_min_deg: float = 0.5
    pi_max_deg: float = 8.0
    deadzone_sharpness: float = 50.0
    stage3_epochs: int = 5000
    stage3_batch_size: int = 4096
    stage3_learning_rate: float = 0.0001
    stage3_data_weight: float = 2.0
    stage3_physics_weight: float = 1.0
    stage3_history_weight: float = 5.0
    generation_horizon_s: float = 30.0
    generation_sample_rate_hz: int = 100
    number_generated_trajectories: int = 100
    number_plotted_trajectories: int = 12
    generated_theta0_min_deg: float = -3.0
    generated_theta0_max_deg: float = 3.0
    print_every: int = 250
CFG = Config()

# Functionality: Read one Subject-B TSV trial, compute pole angle and fingertip position, remove the raw warm-up, resample to 100 Hz, center x, and return float32 arrays.
def read_tsv(tsv, start_index=CFG.start_index_raw, end_index=None):
    """
    Read one Subject-B TSV trial.

    Returns
    -------
    theta_rad : shape [N]
        Pole angle in radians.

    x_m : shape [N]
        Fingertip/lower-marker x coordinate in metres, centered near t=0.

    Data format
    -----------
    Six columns:

        marker 1: x1, y1, z1
        marker 2: x2, y2, z2

    The basic structure follows the original pipeline.
    """
    dat = genfromtxt(tsv, delimiter='\t')
    if dat.ndim == 1:
        dat = dat.reshape(-1, 1)
    if dat.shape[1] < 6:
        raise ValueError(f'File {tsv} has fewer than six columns.')
    dat = dat[:, :6]
    x1, y1, z1, x2, y2, z2 = np.hsplit(dat, 6)
    ell = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2) + 1e-10
    angle_argument = (x1 - x2) / ell
    angle_argument = np.clip(angle_argument, -1.0, 1.0)
    theta_rad = np.arcsin(angle_argument).reshape(-1)
    x_mm = x2.reshape(-1)
    theta_rad = theta_rad[start_index:end_index]
    x_mm = x_mm[start_index:end_index]
    theta_rad = resampy.resample(theta_rad, sr_orig=CFG.original_rate_hz, sr_new=CFG.processed_rate_hz)
    x_mm = resampy.resample(x_mm, sr_orig=CFG.original_rate_hz, sr_new=CFG.processed_rate_hz)
    x_m = x_mm * 0.001
    baseline_count = min(len(x_m), int(0.5 * CFG.processed_rate_hz))
    x_m = x_m - np.median(x_m[:baseline_count])
    theta_rad = theta_rad.astype(np.float32)
    x_m = x_m.astype(np.float32)
    assert theta_rad.ndim == 1
    assert x_m.ndim == 1
    assert len(theta_rad) == len(x_m)
    return (theta_rad, x_m)

@dataclass
class Trial:
    name: str
    t: np.ndarray
    theta: np.ndarray
    x: np.ndarray
    theta0: float
    x0: float
    theta_dot0: float
    x_dot0: float
    duration: float

# Functionality: Estimate the initial derivative of a signal by fitting a straight line to the first few samples.
def estimate_initial_derivative(t, signal, number_of_samples):
    count = min(number_of_samples, len(signal))
    if count < 3:
        return 0.0
    coefficients = np.polyfit(t[:count], signal[:count], deg=1)
    return float(coefficients[0])

# Functionality: Find the usable end of a balancing trial by locating the first fall-angle threshold crossing and removing the configured pre-fall margin.
def find_balancing_end(theta_rad):
    threshold = math.radians(CFG.fall_angle_deg)
    crossings = np.flatnonzero(np.abs(theta_rad) >= threshold)
    if len(crossings) == 0:
        return len(theta_rad)
    margin = int(round(CFG.prefall_margin_s * CFG.processed_rate_hz))
    return max(1, int(crossings[0]) - margin)

# Functionality: Load all configured Subject-B TSV files, preprocess each trial, estimate initial conditions, reject trials that are too short, and return Trial objects.
def load_trials():
    folder = Path(CFG.data_folder)
    files = sorted(folder.glob(CFG.file_pattern))
    if len(files) == 0:
        raise FileNotFoundError(f'No files found in {folder}')
    files = files[:CFG.number_of_trials]
    print(f'Loading {len(files)} Subject-B trials...')
    trials = []
    for path in files:
        theta, x = read_tsv(path)
        usable_end = find_balancing_end(theta)
        theta = theta[:usable_end]
        x = x[:usable_end]
        t = np.arange(len(theta), dtype=np.float32) / CFG.processed_rate_hz
        duration = float(t[-1]) if len(t) else 0.0
        if duration < CFG.minimum_trial_seconds:
            print(f'  skipped {path.name}: {duration:.2f}s')
            continue
        theta0 = float(theta[0])
        x0 = float(x[0])
        theta_dot0 = estimate_initial_derivative(t, theta, CFG.derivative_fit_samples)
        x_dot0 = estimate_initial_derivative(t, x, CFG.derivative_fit_samples)
        trial = Trial(name=path.name, t=t[:, None], theta=theta[:, None], x=x[:, None], theta0=theta0, x0=x0, theta_dot0=theta_dot0, x_dot0=x_dot0, duration=duration)
        trials.append(trial)
        print(f'  {path.name}: {len(t)} samples, {duration:.2f} s, theta0={math.degrees(theta0):+.3f} deg')
    if len(trials) == 0:
        raise RuntimeError('No valid trials remain.')
    return trials

# Functionality: Concatenate all Trial objects into one dictionary of sample-wise arrays for PINN training.
def concatenate_trials(trials):
    data = {'t': [], 'theta': [], 'x': [], 'theta0': [], 'x0': [], 'theta_dot0': [], 'x_dot0': [], 'duration': []}
    for trial in trials:
        n = len(trial.t)
        data['t'].append(trial.t)
        data['theta'].append(trial.theta)
        data['x'].append(trial.x)
        data['theta0'].append(np.full((n, 1), trial.theta0, dtype=np.float32))
        data['x0'].append(np.full((n, 1), trial.x0, dtype=np.float32))
        data['theta_dot0'].append(np.full((n, 1), trial.theta_dot0, dtype=np.float32))
        data['x_dot0'].append(np.full((n, 1), trial.x_dot0, dtype=np.float32))
        data['duration'].append(np.full((n, 1), trial.duration, dtype=np.float32))
    return {key: np.concatenate(value, axis=0) for key, value in data.items()}

class ControllerParameters(tf.Module):

    # Functionality: Initialize the class and create its TensorFlow variables/layers.
    def __init__(self):
        super().__init__()
        self.kp_theta = tf.Variable(CFG.initial_kp_theta, dtype=tf.float32, trainable=True, name='kp_theta')
        self.kd_theta = tf.Variable(CFG.initial_kd_theta, dtype=tf.float32, trainable=True, name='kd_theta')
        self.kp_x = tf.Variable(CFG.initial_kp_x, dtype=tf.float32, trainable=True, name='kp_x')
        self.kd_x = tf.Variable(CFG.initial_kd_x, dtype=tf.float32, trainable=True, name='kd_x')
        self.pi_min_rad = tf.constant(math.radians(CFG.pi_min_deg), dtype=tf.float32)
        self.pi_max_rad = tf.constant(math.radians(CFG.pi_max_deg), dtype=tf.float32)
        initial_pi_rad = math.radians(CFG.initial_pi_deg)
        pi_min = math.radians(CFG.pi_min_deg)
        pi_max = math.radians(CFG.pi_max_deg)
        fraction = (initial_pi_rad - pi_min) / (pi_max - pi_min)
        fraction = np.clip(fraction, 1e-05, 1.0 - 1e-05)
        raw_initial = math.log(fraction / (1.0 - fraction))
        self.raw_pi = tf.Variable(raw_initial, dtype=tf.float32, trainable=True, name='raw_pi')

    @property
    # Functionality: Convert the unconstrained raw Pi variable through a sigmoid mapping into the configured physical dead-zone bounds.
    def pi_rad(self):
        fraction = tf.sigmoid(self.raw_pi)
        return self.pi_min_rad + fraction * (self.pi_max_rad - self.pi_min_rad)

    @property
    # Functionality: Return the controller variables that are allowed to be optimized.
    def trainable_variables(self):
        return [self.kp_theta, self.kd_theta, self.kp_x, self.kd_x, self.raw_pi]

class FourierFeatures(tf.keras.layers.Layer):

    # Functionality: Initialize the class and create its TensorFlow variables/layers.
    def __init__(self, number_of_modes):
        super().__init__()
        frequencies = 2.0 * math.pi * tf.range(1, number_of_modes + 1, dtype=tf.float32)
        self.frequencies = tf.reshape(frequencies, [1, -1])

    # Functionality: Execute the layer/model forward pass for the supplied inputs.
    def call(self, normalized_time):
        projection = normalized_time * self.frequencies
        return tf.concat([normalized_time, tf.sin(projection), tf.cos(projection)], axis=1)

class ConditionalPolePINN(tf.keras.Model):

    # Functionality: Initialize the class and create its TensorFlow variables/layers.
    def __init__(self):
        super().__init__()
        self.time_scale = tf.constant(CFG.generation_horizon_s, dtype=tf.float32)
        self.fourier = FourierFeatures(CFG.fourier_modes)
        self.hidden_layers = []
        for _ in range(CFG.depth):
            self.hidden_layers.append(tf.keras.layers.Dense(CFG.width, activation='tanh', kernel_initializer='glorot_normal'))
        self.output_layer = tf.keras.layers.Dense(2, activation=None)

    # Functionality: Execute the layer/model forward pass for the supplied inputs.
    def call(self, inputs, training=False):
        inputs = tf.convert_to_tensor(inputs, dtype=tf.float32)
        time = inputs[:, 0:1]
        theta0 = inputs[:, 1:2]
        x0 = inputs[:, 2:3]
        theta_dot0 = inputs[:, 3:4]
        x_dot0 = inputs[:, 4:5]
        normalized_time = time / self.time_scale
        time_features = self.fourier(normalized_time)
        condition_features = tf.concat([theta0 / CFG.theta_output_scale_rad, x0 / CFG.x_output_scale_m, theta_dot0, x_dot0], axis=1)
        hidden = tf.concat([time_features, condition_features], axis=1)
        for layer in self.hidden_layers:
            hidden = layer(hidden, training=training)
        raw = self.output_layer(hidden, training=training)
        theta = theta0 + theta_dot0 * time + time ** 2 * CFG.theta_output_scale_rad * raw[:, 0:1]
        x = x0 + x_dot0 * time + time ** 2 * CFG.x_output_scale_m * raw[:, 1:2]
        return tf.concat([theta, x], axis=1)

# Functionality: Combine time and the four initial-condition variables into the five-column conditional PINN input tensor.
def build_inputs(time, theta0, x0, theta_dot0, x_dot0):
    return tf.concat([time, theta0, x0, theta_dot0, x_dot0], axis=1)

# Functionality: Evaluate the PINN and use nested automatic-differentiation tapes to obtain theta, x, and their first and second time derivatives.
def trajectory_derivatives(model, time, theta0, x0, theta_dot0, x_dot0, training):
    with tf.GradientTape(persistent=True) as second_tape:
        second_tape.watch(time)
        with tf.GradientTape(persistent=True) as first_tape:
            first_tape.watch(time)
            inputs = build_inputs(time, theta0, x0, theta_dot0, x_dot0)
            prediction = model(inputs, training=training)
            theta = prediction[:, 0:1]
            x = prediction[:, 1:2]
        theta_dot = first_tape.gradient(theta, time)
        x_dot = first_tape.gradient(x, time)
    theta_ddot = second_tape.gradient(theta_dot, time)
    x_ddot = second_tape.gradient(x_dot, time)
    del first_tape
    del second_tape
    if theta_dot is None:
        raise RuntimeError('theta_dot is None.')
    if x_dot is None:
        raise RuntimeError('x_dot is None.')
    if theta_ddot is None:
        raise RuntimeError('theta_ddot is None.')
    if x_ddot is None:
        raise RuntimeError('x_ddot is None.')
    return (theta, x, theta_dot, x_dot, theta_ddot, x_ddot)

# Functionality: Evaluate the PINN at t - tau and differentiate the delayed outputs to obtain delayed position and velocity states.
def delayed_state(model, time, theta0, x0, theta_dot0, x_dot0, training):
    delayed_time = time - tf.cast(CFG.tau_s, dtype=time.dtype)
    with tf.GradientTape(persistent=True) as tape:
        tape.watch(delayed_time)
        delayed_inputs = build_inputs(delayed_time, theta0, x0, theta_dot0, x_dot0)
        prediction = model(delayed_inputs, training=training)
        theta_delayed = prediction[:, 0:1]
        x_delayed = prediction[:, 1:2]
    theta_dot_delayed = tape.gradient(theta_delayed, delayed_time)
    x_dot_delayed = tape.gradient(x_delayed, delayed_time)
    del tape
    if theta_dot_delayed is None:
        raise RuntimeError('theta_dot_delayed is None.')
    if x_dot_delayed is None:
        raise RuntimeError('x_dot_delayed is None.')
    return (theta_delayed, x_delayed, theta_dot_delayed, x_dot_delayed)

# Functionality: Apply a differentiable sigmoid approximation of the sensory dead zone to the delayed pole angle.
def smooth_deadzone(theta_delayed, controller):
    gate = tf.sigmoid(CFG.deadzone_sharpness * (tf.abs(theta_delayed) - controller.pi_rad))
    theta_perceived = gate * theta_delayed
    return (theta_perceived, gate)

# Functionality: Construct the delayed feedback force and return the two nonlinear pendulum-cart equation residuals together with diagnostic states.
def physics_residuals(model, controller, time, theta0, x0, theta_dot0, x_dot0, training):
    theta, x, theta_dot, x_dot, theta_ddot, x_ddot = trajectory_derivatives(model, time, theta0, x0, theta_dot0, x_dot0, training)
    theta_delayed, x_delayed, theta_dot_delayed, x_dot_delayed = delayed_state(model, time, theta0, x0, theta_dot0, x_dot0, training)
    theta_perceived, deadzone_gate = smooth_deadzone(theta_delayed, controller)
    force = controller.kp_theta * theta_perceived + controller.kd_theta * theta_dot_delayed + controller.kp_x * x_delayed + controller.kd_x * x_dot_delayed
    m = CFG.stick_mass_kg
    m0 = CFG.effective_cart_mass_kg
    length = CFG.stick_length_m
    gravity = CFG.gravity_m_s2
    mass_11 = 1.0 / 3.0 * m * length ** 2
    mass_cross = 0.5 * m * length * tf.cos(theta)
    mass_22 = m + m0
    residual_1 = mass_11 * theta_ddot + mass_cross * x_ddot - 0.5 * m * gravity * length * tf.sin(theta)
    residual_2 = mass_cross * theta_ddot + mass_22 * x_ddot - 0.5 * m * length * theta_dot ** 2 * tf.sin(theta) - force
    residual_1 = residual_1 / mass_11
    residual_2 = residual_2 / mass_22
    diagnostics = {'theta': theta, 'x': x, 'theta_dot': theta_dot, 'x_dot': x_dot, 'theta_ddot': theta_ddot, 'x_ddot': x_ddot, 'theta_delayed': theta_delayed, 'x_delayed': x_delayed, 'theta_dot_delayed': theta_dot_delayed, 'x_dot_delayed': x_dot_delayed, 'theta_perceived': theta_perceived, 'deadzone_gate': deadzone_gate, 'force': force}
    return (residual_1, residual_2, diagnostics)

# Functionality: Generate random row indices for mini-batch sampling.
def random_indices(length, batch_size):
    return np.random.randint(0, length, size=batch_size)

# Functionality: Select indexed rows from a NumPy array and convert them to a float32 TensorFlow tensor.
def tensor_from_rows(array, indices):
    return tf.convert_to_tensor(array[indices], dtype=tf.float32)

# Functionality: Randomly sample a mini-batch from the concatenated real Subject-B data.
def sample_real_batch(real_data, batch_size):
    indices = random_indices(len(real_data['t']), batch_size)
    return {key: tensor_from_rows(value, indices) for key, value in real_data.items()}

# Functionality: Sample physics-collocation times from real trial durations while preserving each selected trial's initial conditions.
def sample_physics_batch_from_real(trials, batch_size):
    trial_indices = np.random.randint(0, len(trials), size=batch_size)
    time = np.zeros((batch_size, 1), dtype=np.float32)
    theta0 = np.zeros_like(time)
    x0 = np.zeros_like(time)
    theta_dot0 = np.zeros_like(time)
    x_dot0 = np.zeros_like(time)
    for row, trial_index in enumerate(trial_indices):
        trial = trials[trial_index]
        lower = CFG.tau_s
        upper = max(lower + 0.0001, trial.duration)
        time[row, 0] = np.random.uniform(lower, upper)
        theta0[row, 0] = trial.theta0
        x0[row, 0] = trial.x0
        theta_dot0[row, 0] = trial.theta_dot0
        x_dot0[row, 0] = trial.x_dot0
    return tuple((tf.convert_to_tensor(array, dtype=tf.float32) for array in (time, theta0, x0, theta_dot0, x_dot0)))

# Functionality: Sample random times and initial conditions used to refine the forward conditional trajectory family.
def sample_random_forward_family(batch_size):
    time = np.random.uniform(CFG.tau_s, CFG.generation_horizon_s, size=(batch_size, 1)).astype(np.float32)
    theta0 = np.radians(np.random.uniform(CFG.generated_theta0_min_deg, CFG.generated_theta0_max_deg, size=(batch_size, 1))).astype(np.float32)
    x0 = np.random.uniform(-0.01, 0.01, size=(batch_size, 1)).astype(np.float32)
    theta_dot0 = np.random.normal(0.0, 0.04, size=(batch_size, 1)).astype(np.float32)
    x_dot0 = np.random.normal(0.0, 0.02, size=(batch_size, 1)).astype(np.float32)
    return tuple((tf.convert_to_tensor(array, dtype=tf.float32) for array in (time, theta0, x0, theta_dot0, x_dot0)))

# Functionality: Sample negative-time history points over [-tau, 0] and construct linear history targets from the initial states.
def sample_history_batch(theta0, x0, theta_dot0, x_dot0):
    batch_size = tf.shape(theta0)[0]
    history_time = tf.random.uniform(shape=(batch_size, 1), minval=-CFG.tau_s, maxval=0.0, dtype=tf.float32)
    target_theta = theta0 + theta_dot0 * history_time
    target_x = x0 + x_dot0 * history_time
    return (history_time, target_theta, target_x)

# Functionality: Compute normalized mean-squared reconstruction error between PINN predictions and measured theta/x data.
def data_loss(model, batch, training):
    inputs = build_inputs(batch['t'], batch['theta0'], batch['x0'], batch['theta_dot0'], batch['x_dot0'])
    prediction = model(inputs, training=training)
    theta_prediction = prediction[:, 0:1]
    x_prediction = prediction[:, 1:2]
    theta_error = (theta_prediction - batch['theta']) / CFG.theta_output_scale_rad
    x_error = (x_prediction - batch['x']) / CFG.x_output_scale_m
    return tf.reduce_mean(theta_error ** 2) + tf.reduce_mean(x_error ** 2)

# Functionality: Compute normalized mean-squared error enforcing the prescribed pre-zero state history.
def history_loss(model, theta0, x0, theta_dot0, x_dot0, training):
    history_time, target_theta, target_x = sample_history_batch(theta0, x0, theta_dot0, x_dot0)
    inputs = build_inputs(history_time, theta0, x0, theta_dot0, x_dot0)
    prediction = model(inputs, training=training)
    theta_error = (prediction[:, 0:1] - target_theta) / CFG.theta_output_scale_rad
    x_error = (prediction[:, 1:2] - target_x) / CFG.x_output_scale_m
    return tf.reduce_mean(theta_error ** 2) + tf.reduce_mean(x_error ** 2)

# Functionality: Train the trajectory PINN on real data, history consistency, and gradually introduced first-equation physics, while saving the best weights.
def train_stage_1(model, controller, trials, real_data):
    optimizer = tf.keras.optimizers.Adam(learning_rate=CFG.stage1_learning_rate)
    history = []
    best_loss = float('inf')
    output_folder = Path(CFG.output_folder)
    print('\n' + '=' * 78)
    print('STAGE 1 — TRAJECTORY PINN FITTING')
    print('=' * 78)
    print(f'Warmup epochs      : {CFG.stage1_data_warmup_epochs}')
    print(f'Maximum r1 weight  : {CFG.stage1_physics_weight}')
    for epoch in range(CFG.stage1_epochs):
        real_batch = sample_real_batch(real_data, CFG.stage1_batch_size)
        t_physics, theta0, x0, theta_dot0, x_dot0 = sample_physics_batch_from_real(trials, CFG.stage1_batch_size)
        if epoch < CFG.stage1_data_warmup_epochs:
            physics_weight = 0.0
        else:
            denominator = max(1, CFG.stage1_epochs - CFG.stage1_data_warmup_epochs)
            progress = (epoch - CFG.stage1_data_warmup_epochs) / denominator
            progress = np.clip(progress, 0.0, 1.0)
            physics_weight = CFG.stage1_physics_weight * progress
        with tf.GradientTape() as tape:
            loss_data_value = data_loss(model, real_batch, training=True)
            residual_1, _, _ = physics_residuals(model=model, controller=controller, time=t_physics, theta0=theta0, x0=x0, theta_dot0=theta_dot0, x_dot0=x_dot0, training=True)
            loss_physics_1 = tf.reduce_mean(residual_1 ** 2)
            loss_history_value = history_loss(model=model, theta0=theta0, x0=x0, theta_dot0=theta_dot0, x_dot0=x_dot0, training=True)
            total_loss = loss_data_value + physics_weight * loss_physics_1 + CFG.stage1_history_weight * loss_history_value
        gradients = tape.gradient(total_loss, model.trainable_variables)
        pairs = [(gradient, variable) for gradient, variable in zip(gradients, model.trainable_variables) if gradient is not None]
        if pairs:
            valid_gradients = [item[0] for item in pairs]
            valid_variables = [item[1] for item in pairs]
            valid_gradients, _ = tf.clip_by_global_norm(valid_gradients, 20.0)
            optimizer.apply_gradients(zip(valid_gradients, valid_variables))
        loss_number = float(total_loss.numpy())
        history.append(loss_number)
        if loss_number < best_loss:
            best_loss = loss_number
            model.save_weights(output_folder / 'stage1_best.weights.h5')
        if epoch % CFG.print_every == 0 or epoch == CFG.stage1_epochs - 1:
            print(f'Stage 1 epoch {epoch:5d} | total={loss_number:.4e} | data={float(loss_data_value.numpy()):.4e} | r1={float(loss_physics_1.numpy()):.4e} | hist={float(loss_history_value.numpy()):.4e} | lambda_r1={physics_weight:.5f}')
    model.load_weights(output_folder / 'stage1_best.weights.h5')
    print(f'\nStage 1 complete. Best objective = {best_loss:.6e}')
    return history

# Functionality: Freeze the trajectory PINN and identify controller gains plus the sensory dead-zone threshold from the second physics residual.
def train_stage_2(model, controller, trials):
    model.trainable = False
    gain_optimizer = tf.keras.optimizers.Adam(learning_rate=CFG.stage2_gain_learning_rate)
    pi_optimizer = tf.keras.optimizers.Adam(learning_rate=CFG.stage2_pi_learning_rate)
    gain_variables = [controller.kp_theta, controller.kd_theta, controller.kp_x, controller.kd_x]
    history = []
    best_loss = float('inf')
    best_values = None
    print('\n' + '=' * 78)
    print('STAGE 2 — INVERSE CONTROLLER IDENTIFICATION')
    print('=' * 78)
    print(f'Pi frozen for first {CFG.stage2_pi_freeze_epochs} epochs.')
    print(f'Pi bounds: {CFG.pi_min_deg:.2f}° to {CFG.pi_max_deg:.2f}°')
    for epoch in range(CFG.stage2_epochs):
        time, theta0, x0, theta_dot0, x_dot0 = sample_physics_batch_from_real(trials, CFG.stage2_batch_size)
        with tf.GradientTape(persistent=True) as tape:
            _, residual_2, diagnostics = physics_residuals(model=model, controller=controller, time=time, theta0=theta0, x0=x0, theta_dot0=theta_dot0, x_dot0=x_dot0, training=False)
            absolute_residual = tf.abs(residual_2)
            huber_delta = tf.constant(1.0, dtype=tf.float32)
            quadratic = tf.minimum(absolute_residual, huber_delta)
            linear = absolute_residual - quadratic
            residual_loss = 0.5 * quadratic ** 2 + huber_delta * linear
            loss_value = tf.reduce_mean(residual_loss)
        gain_gradients = tape.gradient(loss_value, gain_variables)
        gain_pairs = [(gradient, variable) for gradient, variable in zip(gain_gradients, gain_variables) if gradient is not None]
        if gain_pairs:
            gradients_valid = [item[0] for item in gain_pairs]
            variables_valid = [item[1] for item in gain_pairs]
            gradients_valid, _ = tf.clip_by_global_norm(gradients_valid, 20.0)
            gain_optimizer.apply_gradients(zip(gradients_valid, variables_valid))
        if epoch >= CFG.stage2_pi_freeze_epochs:
            pi_gradients = tape.gradient(loss_value, [controller.raw_pi])
            if pi_gradients[0] is not None:
                pi_gradients, _ = tf.clip_by_global_norm(pi_gradients, 2.0)
                pi_optimizer.apply_gradients(zip(pi_gradients, [controller.raw_pi]))
        del tape
        controller.kp_theta.assign(tf.clip_by_value(controller.kp_theta, 0.0, 600.0))
        controller.kd_theta.assign(tf.clip_by_value(controller.kd_theta, 0.0, 120.0))
        controller.kp_x.assign(tf.clip_by_value(controller.kp_x, -100.0, 100.0))
        controller.kd_x.assign(tf.clip_by_value(controller.kd_x, -100.0, 120.0))
        loss_number = float(loss_value.numpy())
        history.append(loss_number)
        if loss_number < best_loss:
            best_loss = loss_number
            best_values = {'kp_theta': float(controller.kp_theta.numpy()), 'kd_theta': float(controller.kd_theta.numpy()), 'kp_x': float(controller.kp_x.numpy()), 'kd_x': float(controller.kd_x.numpy()), 'raw_pi': float(controller.raw_pi.numpy())}
        if epoch % CFG.print_every == 0 or epoch == CFG.stage2_epochs - 1:
            if epoch < CFG.stage2_pi_freeze_epochs:
                pi_status = 'FROZEN'
            else:
                pi_status = 'TRAIN'
            gate = diagnostics['deadzone_gate']
            gate_mean = float(tf.reduce_mean(gate).numpy())
            gate_active = float(tf.reduce_mean(tf.cast(gate > 0.5, tf.float32)).numpy())
            print(f'Stage 2 epoch {epoch:5d} | r2={loss_number:.4e} | kp_th={float(controller.kp_theta.numpy()):.3f} | kd_th={float(controller.kd_theta.numpy()):.3f} | kp_x={float(controller.kp_x.numpy()):.3f} | kd_x={float(controller.kd_x.numpy()):.3f} | Pi={math.degrees(float(controller.pi_rad.numpy())):.3f}° | {pi_status} | gate_mean={gate_mean:.3f} | gate_active={100.0 * gate_active:.1f}%')
    if best_values is not None:
        controller.kp_theta.assign(best_values['kp_theta'])
        controller.kd_theta.assign(best_values['kd_theta'])
        controller.kp_x.assign(best_values['kp_x'])
        controller.kd_x.assign(best_values['kd_x'])
        controller.raw_pi.assign(best_values['raw_pi'])
    print('\nStage 2 complete.')
    print(f'Best inverse objective = {best_loss:.6e}')
    return history

# Functionality: Print the identified Subject-B controller parameters beside the reference values used in the paper.
def print_identified_parameters(controller):
    print('\n' + '=' * 86)
    print('IDENTIFIED SUBJECT-B EFFECTIVE CONTROL PARAMETERS')
    print('=' * 86)
    print(f"{'Parameter':<15}{'Predicted':>15}{'Paper reference':>20}")
    print('-' * 55)
    print(f"{'kp_theta':<15}{float(controller.kp_theta.numpy()):>15.4f}{240.0:>20.4f}")
    print(f"{'kd_theta':<15}{float(controller.kd_theta.numpy()):>15.4f}{30.0:>20.4f}")
    print(f"{'kp_x':<15}{float(controller.kp_x.numpy()):>15.4f}{13.0:>20.4f}")
    print(f"{'kd_x':<15}{float(controller.kd_x.numpy()):>15.4f}{30.0:>20.4f}")
    print(f"{'Pi [deg]':<15}{math.degrees(float(controller.pi_rad.numpy())):>15.4f}{3.0:>20.4f}")
    print(f"{'tau [s]':<15}{CFG.tau_s:>15.4f}{0.23:>20.4f}")
    print('=' * 86)

# Functionality: Save the identified controller and physical parameters to identified_parameters.json.
def save_parameters(controller):
    output_folder = Path(CFG.output_folder)
    data = {'subject': 'B', 'tau_s': CFG.tau_s, 'pi_rad': float(controller.pi_rad.numpy()), 'pi_deg': math.degrees(float(controller.pi_rad.numpy())), 'kp_theta': float(controller.kp_theta.numpy()), 'kd_theta': float(controller.kd_theta.numpy()), 'kp_x': float(controller.kp_x.numpy()), 'kd_x': float(controller.kd_x.numpy()), 'feedback_model': 'reduced_delayed_state_feedback', 'predictor_integral_included': False, 'physical_parameters': {'m_kg': CFG.stick_mass_kg, 'm0_kg': CFG.effective_cart_mass_kg, 'l_m': CFG.stick_length_m, 'g_m_s2': CFG.gravity_m_s2}}
    with (output_folder / 'identified_parameters.json').open('w') as handle:
        json.dump(data, handle, indent=2)

# Functionality: Freeze the identified controller and refine the trajectory PINN over random initial conditions using physics, real-data, and history losses.
def train_stage_3(model, controller, real_data):
    model.trainable = True
    optimizer = tf.keras.optimizers.Adam(learning_rate=CFG.stage3_learning_rate)
    history = []
    best_loss = float('inf')
    output_folder = Path(CFG.output_folder)
    print('\n' + '=' * 78)
    print('STAGE 3 — FORWARD-FAMILY PHYSICS REFINEMENT')
    print('=' * 78)
    print('Controller parameters are frozen.')
    for epoch in range(CFG.stage3_epochs):
        real_batch = sample_real_batch(real_data, CFG.stage3_batch_size)
        time, theta0, x0, theta_dot0, x_dot0 = sample_random_forward_family(CFG.stage3_batch_size)
        with tf.GradientTape() as tape:
            residual_1, residual_2, _ = physics_residuals(model=model, controller=controller, time=time, theta0=theta0, x0=x0, theta_dot0=theta_dot0, x_dot0=x_dot0, training=True)
            physics_loss_value = tf.reduce_mean(residual_1 ** 2) + tf.reduce_mean(residual_2 ** 2)
            data_loss_value = data_loss(model, real_batch, training=True)
            history_loss_value = history_loss(model=model, theta0=theta0, x0=x0, theta_dot0=theta_dot0, x_dot0=x_dot0, training=True)
            total_loss = CFG.stage3_physics_weight * physics_loss_value + CFG.stage3_data_weight * data_loss_value + CFG.stage3_history_weight * history_loss_value
        gradients = tape.gradient(total_loss, model.trainable_variables)
        pairs = [(gradient, variable) for gradient, variable in zip(gradients, model.trainable_variables) if gradient is not None]
        gradient_norm_value = float('nan')
        if pairs:
            valid_gradients = [item[0] for item in pairs]
            valid_variables = [item[1] for item in pairs]
            valid_gradients, gradient_norm = tf.clip_by_global_norm(valid_gradients, 10.0)
            gradient_norm_value = float(gradient_norm.numpy())
            optimizer.apply_gradients(zip(valid_gradients, valid_variables))
        loss_number = float(total_loss.numpy())
        history.append(loss_number)
        if loss_number < best_loss:
            best_loss = loss_number
            model.save_weights(output_folder / 'stage3_best.weights.h5')
        if epoch % CFG.print_every == 0 or epoch == CFG.stage3_epochs - 1:
            print(f'Stage 3 epoch {epoch:5d} | total={loss_number:.4e} | physics={float(physics_loss_value.numpy()):.4e} | data={float(data_loss_value.numpy()):.4e} | history={float(history_loss_value.numpy()):.4e} | |grad|={gradient_norm_value:.3e}')
    model.load_weights(output_folder / 'stage3_best.weights.h5')
    print(f'\nStage 3 complete. Best objective = {best_loss:.6e}')
    return history

# Functionality: Plot the Stage 1, Stage 2, and Stage 3 loss histories on a shared logarithmic loss axis and save the figure.
def save_loss_plot(stage1_history, stage2_history, stage3_history):
    output_folder = Path(CFG.output_folder)
    fig, ax = plt.subplots(figsize=(11, 6))
    x1 = np.arange(len(stage1_history))
    x2 = np.arange(len(stage2_history)) + len(stage1_history)
    x3 = np.arange(len(stage3_history)) + len(stage1_history) + len(stage2_history)
    ax.plot(x1, stage1_history, label='Stage 1')
    ax.plot(x2, stage2_history, label='Stage 2')
    ax.plot(x3, stage3_history, label='Stage 3')
    ax.set_yscale('log')
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Loss')
    ax.set_title('Inverse + Forward PINN Training')
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_folder / 'training_losses.png', dpi=180)
    plt.close(fig)

# Functionality: Build conditional inputs for one real trial and return the PINN-predicted theta and x trajectories.
def predict_trial(model, trial):
    n = len(trial.t)
    inputs = np.column_stack([trial.t[:, 0], np.full(n, trial.theta0), np.full(n, trial.x0), np.full(n, trial.theta_dot0), np.full(n, trial.x_dot0)]).astype(np.float32)
    prediction = model(inputs, training=False).numpy()
    return (prediction[:, 0], prediction[:, 1])

# Functionality: Compare measured and PINN-reconstructed trajectories for up to four real trials and save the figure.
def save_real_reconstruction_plot(model, trials):
    output_folder = Path(CFG.output_folder)
    selected = trials[:min(4, len(trials))]
    fig, axes = plt.subplots(len(selected), 2, figsize=(13, 3.2 * len(selected)), squeeze=False)
    for i, trial in enumerate(selected):
        theta_prediction, x_prediction = predict_trial(model, trial)
        time = trial.t[:, 0]
        axes[i, 0].plot(time, np.degrees(trial.theta[:, 0]), label='Real', lw=1.2)
        axes[i, 0].plot(time, np.degrees(theta_prediction), '--', label='PINN', lw=1.2)
        axes[i, 0].set_ylabel('θ [deg]')
        axes[i, 0].set_title(trial.name)
        axes[i, 0].grid(True, alpha=0.3)
        axes[i, 0].legend()
        axes[i, 1].plot(time, 100.0 * trial.x[:, 0], label='Real', lw=1.2)
        axes[i, 1].plot(time, 100.0 * x_prediction, '--', label='PINN', lw=1.2)
        axes[i, 1].set_ylabel('x [cm]')
        axes[i, 1].grid(True, alpha=0.3)
        axes[i, 1].legend()
    axes[-1, 0].set_xlabel('Time [s]')
    axes[-1, 1].set_xlabel('Time [s]')
    fig.suptitle('Real Subject-B Trials vs PINN Reconstruction')
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(output_folder / 'real_vs_pinn_reconstruction.png', dpi=180)
    plt.close(fig)

# Functionality: Generate synthetic Subject-B trajectories over random initial pole angles and save each trajectory as a NumPy file.
def generate_trajectories(model):
    output_folder = Path(CFG.output_folder) / 'synthetic_subjectB_PINN'
    output_folder.mkdir(parents=True, exist_ok=True)
    number_samples = int(round(CFG.generation_horizon_s * CFG.generation_sample_rate_hz)) + 1
    time = np.linspace(0.0, CFG.generation_horizon_s, number_samples, dtype=np.float32)
    theta0_samples_deg = np.random.uniform(CFG.generated_theta0_min_deg, CFG.generated_theta0_max_deg, CFG.number_generated_trajectories)
    trajectories = []
    print(f'\nGenerating {CFG.number_generated_trajectories} conditional PINN trajectories...')
    for i in tqdm(range(CFG.number_generated_trajectories), desc='Generating trajectories'):
        theta0_rad = math.radians(float(theta0_samples_deg[i]))
        n = len(time)
        inputs = np.column_stack([time, np.full(n, theta0_rad), np.zeros(n), np.zeros(n), np.zeros(n)]).astype(np.float32)
        prediction = model(inputs, training=False).numpy()
        theta_rad = prediction[:, 0]
        theta_deg = np.degrees(theta_rad)
        x_m = prediction[:, 1]
        data = np.column_stack([time, theta_rad, theta_deg, x_m])
        np.save(output_folder / f'synth_B_{i:04d}.npy', data)
        trajectories.append({'time': time, 'theta_rad': theta_rad, 'theta_deg': theta_deg, 'x_m': x_m, 'theta0_deg': theta0_samples_deg[i]})
    print(f'Saved {len(trajectories)} trajectories to {output_folder}')
    return trajectories

# Functionality: Plot a subset of generated theta and fingertip-position trajectories and save generated_samples.png.
def save_generated_plot(trajectories):
    output_folder = Path(CFG.output_folder)
    selected = trajectories[:min(CFG.number_plotted_trajectories, len(trajectories))]
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for trajectory in selected:
        label = f"{trajectory['theta0_deg']:+.2f}°"
        axes[0].plot(trajectory['time'], trajectory['theta_deg'], lw=1.0, label=label)
        axes[1].plot(trajectory['time'], 100.0 * trajectory['x_m'], lw=1.0)
    axes[0].set_ylabel('θ [deg]')
    axes[0].set_title('Generated Subject-B PINN Trajectories')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=7, ncol=3, title='θ₀')
    axes[1].set_ylabel('x [cm]')
    axes[1].set_xlabel('Time [s]')
    axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_folder / 'generated_samples.png', dpi=180)
    plt.close(fig)

# Functionality: Save the final conditional PINN weights and the full configuration JSON file.
def save_final_model(model):
    output_folder = Path(CFG.output_folder)
    model.save_weights(output_folder / 'conditional_forward_pinn.weights.h5')
    with (output_folder / 'configuration.json').open('w') as handle:
        json.dump(asdict(CFG), handle, indent=2)

# Functionality: Run the complete inverse-plus-forward PINN workflow: load data, train all stages, report parameters, save diagnostics, and generate synthetic trajectories.
def main():
    output_folder = Path(CFG.output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    print('=' * 78)
    print('SUBJECT-B INVERSE + FORWARD CONDITIONAL PINN')
    print('=' * 78)
    print(f'Input folder : {Path(CFG.data_folder).resolve()}')
    print(f'Output folder: {output_folder.resolve()}')
    print(f'TensorFlow devices: {tf.config.list_physical_devices()}')
    print(f'Delay        : {CFG.tau_s:.3f} s')
    print(f'Pi bounds    : {CFG.pi_min_deg:.1f}° to {CFG.pi_max_deg:.1f}°')
    print('Controller   : reduced delayed-state feedback')
    trials = load_trials()
    real_data = concatenate_trials(trials)
    print(f"\nPrepared {len(real_data['t'])} real samples from {len(trials)} trials.")
    model = ConditionalPolePINN()
    controller = ControllerParameters()
    dummy_input = tf.zeros((1, 5), dtype=tf.float32)
    _ = model(dummy_input)
    stage1_history = train_stage_1(model=model, controller=controller, trials=trials, real_data=real_data)
    stage2_history = train_stage_2(model=model, controller=controller, trials=trials)
    print_identified_parameters(controller)
    save_parameters(controller)
    stage3_history = train_stage_3(model=model, controller=controller, real_data=real_data)
    print('\nController used for synthetic generation:')
    print_identified_parameters(controller)
    save_final_model(model)
    save_loss_plot(stage1_history, stage2_history, stage3_history)
    save_real_reconstruction_plot(model, trials)
    trajectories = generate_trajectories(model)
    save_generated_plot(trajectories)
    print('\n' + '=' * 78)
    print('FINISHED SUCCESSFULLY')
    print('=' * 78)
    print('\nSaved:')
    print(output_folder / 'identified_parameters.json')
    print(output_folder / 'conditional_forward_pinn.weights.h5')
    print(output_folder / 'configuration.json')
    print(output_folder / 'training_losses.png')
    print(output_folder / 'real_vs_pinn_reconstruction.png')
    print(output_folder / 'generated_samples.png')
    print(output_folder / 'synthetic_subjectB_PINN')
if __name__ == '__main__':
    main()
