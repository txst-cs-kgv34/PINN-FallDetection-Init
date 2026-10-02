"""Compare data-only and physics-informed CoM networks under identical A13 folds."""

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_phase_baseline import write_csv
from phase_annotations import read_json, validate_phase_notes
from pinn_torch import GRAVITY_M_S2, LossWeights, evaluate_model, train_model
from run_pinn_pilot import (
    AXES,
    AXIS_LABELS,
    error_metrics,
    make_training_records,
    prepare_trial,
    standardize_conditions,
    training_mean_prediction,
)
from skeleton_model import segment_model


def gravity_only_prediction(time_s, initial_velocity):
    gravity = np.array([0.0, -GRAVITY_M_S2, 0.0])
    return initial_velocity * time_s[:, None] + 0.5 * gravity * time_s[:, None] ** 2


def parse_list(value, cast):
    parsed = [cast(item.strip()) for item in value.split(",") if item.strip()]
    if not parsed:
        raise argparse.ArgumentTypeError("provide at least one comma-separated value")
    return parsed


def weight_label(value):
    return f"{value:g}"


def plot_rmse_sweep(metrics, output_path):
    weights = sorted({float(row["physics_weight"]) for row in metrics})
    groups = {
        weight: [
            float(row["model_rmse_3d_m"])
            for row in metrics
            if float(row["physics_weight"]) == weight
        ]
        for weight in weights
    }
    x = np.arange(len(weights))
    means = [np.mean(groups[weight]) for weight in weights]
    stds = [np.std(groups[weight]) for weight in weights]
    figure, axis = plt.subplots(figsize=(7.2, 4.6))
    axis.errorbar(
        x,
        means,
        yerr=stds,
        marker="o",
        capsize=4,
        color="#176d8a",
        linewidth=2,
        label="network mean ± SD",
    )
    axis.axhline(
        np.mean([float(row["baseline_rmse_3d_m"]) for row in metrics]),
        color="#d07326",
        linestyle="--",
        label="training-mean baseline",
    )
    axis.set_xticks(x, [weight_label(weight) for weight in weights])
    axis.set_xlabel("Physics-loss weight λphysics (0 = data-only)")
    axis.set_ylabel("Held-out 3D CoM RMSE (m)")
    axis.set_title("S43 A13 physics-weight sensitivity")
    axis.grid(alpha=0.22)
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(output_path, dpi=170)
    plt.close(figure)


def plot_fold_comparison(metrics, best_weight, output_path):
    trials = sorted({row["held_out_trial"] for row in metrics})
    data_only = []
    best_pinn = []
    baseline = []
    for trial in trials:
        trial_rows = [row for row in metrics if row["held_out_trial"] == trial]
        data_only.append(
            np.mean(
                [
                    float(row["model_rmse_3d_m"])
                    for row in trial_rows
                    if float(row["physics_weight"]) == 0
                ]
            )
        )
        best_pinn.append(
            np.mean(
                [
                    float(row["model_rmse_3d_m"])
                    for row in trial_rows
                    if float(row["physics_weight"]) == best_weight
                ]
            )
        )
        baseline.append(float(trial_rows[0]["baseline_rmse_3d_m"]))
    x = np.arange(len(trials))
    width = 0.24
    figure, axis = plt.subplots(figsize=(8.0, 4.8))
    axis.bar(x - width, baseline, width, label="training mean", color="#d07326")
    axis.bar(x, data_only, width, label="data-only", color="#6b7a8f")
    axis.bar(
        x + width,
        best_pinn,
        width,
        label=f"PINN λ={weight_label(best_weight)}",
        color="#176d8a",
    )
    axis.set_xticks(x, [trial.replace("S43A13", "") for trial in trials])
    axis.set_xlabel("Held-out trial")
    axis.set_ylabel("3D CoM RMSE (m)")
    axis.set_title("Whole-trial leave-one-out comparison")
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False, ncol=3)
    figure.tight_layout()
    figure.savefig(output_path, dpi=170)
    plt.close(figure)


def plot_selected_trajectory(
    trial,
    time_s,
    actual,
    data_only,
    pinn,
    baseline,
    best_weight,
    output_path,
):
    figure, axes = plt.subplots(3, 1, figsize=(7.5, 7.5), sharex=True)
    for index, axis in enumerate(axes):
        axis.plot(time_s, actual[:, index], color="#202733", linewidth=2.4, label="held-out")
        axis.plot(time_s, baseline[:, index], color="#d07326", linestyle="--", label="training mean")
        axis.plot(time_s, data_only[:, index], color="#6b7a8f", linestyle=":", linewidth=1.8, label="data-only")
        axis.plot(time_s, pinn[:, index], color="#176d8a", linestyle="--", linewidth=1.9, label=f"PINN λ={weight_label(best_weight)}")
        axis.axhline(0, color="#888888", linewidth=0.7)
        axis.grid(alpha=0.2)
        axis.set_ylabel(f"{AXIS_LABELS[index]}\nΔCoM (m)")
    axes[0].legend(frameon=False, fontsize=7.5, ncol=2)
    axes[-1].set_xlabel("Physical time from marked fall onset (s)")
    figure.suptitle(f"Controlled network comparison — held out {trial}", fontsize=12)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    figure.savefig(output_path, dpi=170)
    plt.close(figure)


def aggregate_weight(metrics, weight):
    rows = [row for row in metrics if float(row["physics_weight"]) == weight]
    return {
        "rmse": float(np.mean([float(row["model_rmse_3d_m"]) for row in rows])),
        "residual": float(
            np.mean([float(row["physics_residual_rms_m_s2"]) for row in rows])
        ),
    }


def build_summary(output_dir, metrics, physics_weights, best_weight, seeds):
    data_only = aggregate_weight(metrics, 0.0)
    best = aggregate_weight(metrics, best_weight)
    baseline = np.mean([float(row["baseline_rmse_3d_m"]) for row in metrics])
    gravity = np.mean([float(row["gravity_rmse_3d_m"]) for row in metrics])
    relative = 100 * (data_only["rmse"] - best["rmse"]) / data_only["rmse"]
    baseline_gap = 100 * (best["rmse"] - baseline) / baseline
    matched = {}
    for row in metrics:
        key = (row["held_out_trial"], int(row["seed"]))
        matched.setdefault(key, {})[float(row["physics_weight"])] = float(
            row["model_rmse_3d_m"]
        )
    paired_wins = sum(
        values[best_weight] < values[0.0]
        for values in matched.values()
        if best_weight in values and 0.0 in values
    )
    baseline_wins = sum(
        float(row["model_rmse_3d_m"]) < float(row["baseline_rmse_3d_m"])
        for row in metrics
        if float(row["physics_weight"]) == best_weight
    )
    best_rows = [
        row for row in metrics if float(row["physics_weight"]) == best_weight
    ]
    hardest = max(best_rows, key=lambda row: float(row["model_rmse_3d_m"]))
    outcome = (
        "The best tested nonzero physics weight improved on the matched data-only network."
        if relative > 0
        else "No tested nonzero physics weight improved on the matched data-only network."
    )
    lines = [
        "# S43 A13 controlled physics-weight experiment",
        "",
        "## Outcome",
        "",
        outcome,
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Data-only mean held-out 3D RMSE | {data_only['rmse']:.4f} m |",
        f"| Best tested PINN weight | {weight_label(best_weight)} |",
        f"| Best PINN mean held-out 3D RMSE | {best['rmse']:.4f} m |",
        f"| PINN RMSE reduction relative to data-only | {relative:.1f}% |",
        f"| Matched fold/seed runs improved over data-only | {paired_wins} / {len(matched)} |",
        f"| Training-mean baseline RMSE | {baseline:.4f} m |",
        f"| Best PINN RMSE above training mean | {baseline_gap:.1f}% |",
        f"| Best PINN runs beating training mean | {baseline_wins} / {len(best_rows)} |",
        f"| Gravity-only sanity-check RMSE | {gravity:.4f} m |",
        f"| Best PINN physics residual RMS | {best['residual']:.4f} m/s² |",
        f"| Whole-trial folds | 4 |",
        f"| Seeds per fold and weight | {len(seeds)} |",
        "",
        "## Design",
        "",
        "The data-only and PINN models use the same trajectory network, hard onset position/velocity constraints, physical-time inputs, trial conditions, folds, seeds, optimizer and epochs. Only the physics-loss weight changes. Condition normalization uses the three training trials in each fold. The untrained gravity-only curve is a sanity check rather than a realistic supported-body model.",
        "",
        f"Tested physics weights: {', '.join(weight_label(value) for value in physics_weights)}.",
        "",
        f"The largest remaining error is {hardest['held_out_trial']} at {float(hardest['model_rmse_3d_m']):.4f} m for seed {hardest['seed']}; this trial is {float(hardest['held_out_max_abs_condition_z']):.1f} training standard deviations outside at least one training-condition range.",
        "",
        "## Interpretation gate",
        "",
        "This is an exploratory four-trial, single-subject, single-activity comparison. Selecting the best weight from the same four folds is model selection, not independent validation. The learned effective acceleration still combines support, voluntary control, contact, measurement/model error and any true perturbation; it is not a recovered external force.",
        "",
        "Synthetic generation remains gated on consistent improvement over the data-only and training-mean baselines, acceptable residual behavior, and later validation on additional real trials or activities.",
        "",
    ]
    (output_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def run_experiment(
    run_dir,
    config_path,
    selection_path,
    notes_path,
    output_dir,
    activity,
    settings,
):
    run_dir = Path(run_dir)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"output already exists: {output_dir}")
    config = read_json(config_path)
    selection = read_json(selection_path)
    _, windows = validate_phase_notes(notes_path, run_dir, config, selection)
    windows = [window for window in windows if window["activity"] == activity]
    if len(windows) != 4:
        raise ValueError(f"this experiment expects four eligible {activity} trials")
    segments = segment_model(config["sex"])
    trials = [
        prepare_trial(
            run_dir,
            config,
            window,
            segments,
            settings["standing_radius"],
            settings["velocity_window_frames"],
        )
        for window in windows
    ]
    for trial in trials:
        trial["condition_raw"] = np.concatenate(
            [trial["condition_raw"], [trial["duration_s"]]]
        )
    output_dir.mkdir(parents=True)
    (output_dir / "plots").mkdir()
    height_m = float(config["height_in"]) * 0.0254
    mass_kg = float(config["mass_lb"]) * 0.45359237
    metrics = []
    predictions = []
    histories = []

    for fold_index, original_held_out in enumerate(trials):
        training = [
            item.copy()
            for item in trials
            if item["trial"] != original_held_out["trial"]
        ]
        held_out = original_held_out.copy()
        condition_mean, condition_scale = standardize_conditions(training, held_out)
        time_scale_s = max(item["duration_s"] for item in training)
        records = make_training_records(
            training, height_m, settings["collocation_points"]
        )
        baseline = training_mean_prediction(
            training, held_out["time_s"], held_out["duration_s"]
        )
        gravity = gravity_only_prediction(
            held_out["time_s"], held_out["initial_velocity"]
        )
        baseline_metrics = error_metrics(held_out["position"], baseline)
        gravity_metrics = error_metrics(held_out["position"], gravity)
        condition = np.tile(
            held_out["condition_scaled"], (len(held_out["time_s"]), 1)
        )
        velocity = np.tile(
            held_out["initial_velocity"], (len(held_out["time_s"]), 1)
        )
        for physics_weight in settings["physics_weights"]:
            for seed_index, seed in enumerate(settings["seeds"]):
                is_data_only = physics_weight == 0
                loss_weights = LossWeights(
                    physics=physics_weight,
                    effective_acceleration_l2=(
                        0.0
                        if is_data_only
                        else settings["effective_acceleration_l2"]
                    ),
                    effective_acceleration_jerk=(
                        0.0
                        if is_data_only
                        else settings["effective_acceleration_jerk"]
                    ),
                )
                model, history = train_model(
                    records,
                    condition_size=len(condition_mean),
                    time_scale_s=time_scale_s,
                    architecture=settings["architecture"],
                    epochs=settings["epochs"],
                    learning_rate=settings["learning_rate"],
                    loss_weights=loss_weights,
                    seed=seed + fold_index,
                    history_interval=settings["history_interval"],
                )
                evaluation = evaluate_model(
                    model,
                    held_out["time_s"],
                    condition,
                    velocity,
                    time_scale_s,
                )
                model_metrics = error_metrics(
                    held_out["position"], evaluation["position"]
                )
                physics_rms = float(
                    np.sqrt(
                        np.mean(
                            np.sum(evaluation["physics_residual"] ** 2, axis=1)
                        )
                    )
                )
                effective_force_rms = float(
                    mass_kg
                    * np.sqrt(
                        np.mean(
                            np.sum(
                                evaluation["effective_acceleration"] ** 2, axis=1
                            )
                        )
                    )
                )
                metrics.append(
                    {
                        "held_out_trial": held_out["trial"],
                        "training_trials": ";".join(
                            item["trial"] for item in training
                        ),
                        "physics_weight": physics_weight,
                        "seed": seed,
                        **{f"model_{key}": value for key, value in model_metrics.items()},
                        **{
                            f"baseline_{key}": value
                            for key, value in baseline_metrics.items()
                        },
                        **{
                            f"gravity_{key}": value
                            for key, value in gravity_metrics.items()
                        },
                        "physics_residual_rms_m_s2": physics_rms,
                        "effective_force_rms_n": effective_force_rms,
                        "held_out_duration_s": held_out["duration_s"],
                        "training_time_scale_s": time_scale_s,
                        "held_out_max_abs_condition_z": float(
                            np.max(np.abs(held_out["condition_scaled"]))
                        ),
                        "final_training_total_loss": history[-1]["total_loss"],
                        "final_training_data_loss": history[-1]["data"],
                        "final_training_physics_loss": history[-1]["physics"],
                    }
                )
                histories.extend(
                    {
                        "held_out_trial": held_out["trial"],
                        "physics_weight": physics_weight,
                        "seed": seed,
                        **row,
                    }
                    for row in history
                )
                for index, time_s in enumerate(held_out["time_s"]):
                    row = {
                        "held_out_trial": held_out["trial"],
                        "physics_weight": physics_weight,
                        "seed": seed,
                        "time_s": time_s,
                    }
                    for axis_index, axis in enumerate(AXES):
                        row[f"actual_{axis}_m"] = held_out["position"][index, axis_index]
                        row[f"model_{axis}_m"] = evaluation["position"][index, axis_index]
                        row[f"baseline_{axis}_m"] = baseline[index, axis_index]
                        row[f"gravity_{axis}_m"] = gravity[index, axis_index]
                        row[f"effective_acceleration_{axis}_m_s2"] = evaluation[
                            "effective_acceleration"
                        ][index, axis_index]
                        row[f"physics_residual_{axis}_m_s2"] = evaluation[
                            "physics_residual"
                        ][index, axis_index]
                    predictions.append(row)

    nonzero_weights = [value for value in settings["physics_weights"] if value > 0]
    if not nonzero_weights:
        raise ValueError("include at least one nonzero physics weight")
    best_weight = min(
        nonzero_weights,
        key=lambda value: aggregate_weight(metrics, value)["rmse"],
    )
    write_csv(output_dir / "fold_metrics.csv", metrics)
    write_csv(output_dir / "fold_predictions.csv", predictions)
    write_csv(output_dir / "training_history.csv", histories)
    plot_rmse_sweep(metrics, output_dir / "plots" / "rmse_vs_physics_weight.png")
    plot_fold_comparison(
        metrics, best_weight, output_dir / "plots" / "fold_rmse_comparison.png"
    )

    representative_seed = settings["seeds"][0]
    for trial in sorted({row["held_out_trial"] for row in predictions}):
        rows = [
            row
            for row in predictions
            if row["held_out_trial"] == trial
            and int(row["seed"]) == representative_seed
        ]
        data_rows = sorted(
            [row for row in rows if float(row["physics_weight"]) == 0],
            key=lambda row: float(row["time_s"]),
        )
        pinn_rows = sorted(
            [row for row in rows if float(row["physics_weight"]) == best_weight],
            key=lambda row: float(row["time_s"]),
        )
        actual = np.array(
            [[float(row[f"actual_{axis}_m"]) for axis in AXES] for row in data_rows]
        )
        data_prediction = np.array(
            [[float(row[f"model_{axis}_m"]) for axis in AXES] for row in data_rows]
        )
        pinn_prediction = np.array(
            [[float(row[f"model_{axis}_m"]) for axis in AXES] for row in pinn_rows]
        )
        baseline = np.array(
            [[float(row[f"baseline_{axis}_m"]) for axis in AXES] for row in data_rows]
        )
        plot_selected_trajectory(
            trial,
            np.array([float(row["time_s"]) for row in data_rows]),
            actual,
            data_prediction,
            pinn_prediction,
            baseline,
            best_weight,
            output_dir / "plots" / f"{trial}_selected_comparison.png",
        )

    experiment_config = {
        "activity": activity,
        "settings": settings,
        "seed_policy": "training seed = listed base seed + zero-based fold index",
        "selected_best_nonzero_physics_weight": best_weight,
        "selection_note": "Exploratory minimum mean held-out RMSE across the same four folds; not independent validation.",
        "condition_order": [
            "initial_velocity_lateral",
            "initial_velocity_vertical",
            "initial_velocity_forward",
            "onset_relative_com_lateral",
            "onset_relative_com_vertical",
            "onset_relative_com_forward",
            "onset_foot_separation_m",
            "marked_onset_to_contact_duration_s",
        ],
        "gravity_proxy_m_s2": [0.0, -GRAVITY_M_S2, 0.0],
        "mass_kg": mass_kg,
        "height_m": height_m,
    }
    (output_dir / "experiment_config.json").write_text(
        json.dumps(experiment_config, indent=2) + "\n", encoding="utf-8"
    )
    build_summary(
        output_dir,
        metrics,
        settings["physics_weights"],
        best_weight,
        settings["seeds"],
    )
    return {
        "activity": activity,
        "folds": 4,
        "weights": settings["physics_weights"],
        "seeds": settings["seeds"],
        "best_nonzero_physics_weight": best_weight,
        "output": str(output_dir),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--phase-notes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--activity", default="A13")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--collocation-points", type=int, default=24)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--physics-weights", default="0,0.01,0.1,1,10")
    parser.add_argument("--seeds", default="43013,43014")
    args = parser.parse_args()
    physics_weights = parse_list(args.physics_weights, float)
    seeds = parse_list(args.seeds, int)
    if 0.0 not in physics_weights:
        raise ValueError("physics weights must include 0 for the data-only control")
    settings = {
        "epochs": args.epochs,
        "collocation_points": args.collocation_points,
        "learning_rate": args.learning_rate,
        "physics_weights": physics_weights,
        "seeds": seeds,
        "history_interval": 50,
        "standing_radius": 2,
        "velocity_window_frames": 5,
        "effective_acceleration_l2": 0.0001,
        "effective_acceleration_jerk": 0.001,
        "architecture": {
            "trajectory_hidden_size": 32,
            "trajectory_hidden_layers": 3,
            "residual_hidden_size": 16,
            "residual_hidden_layers": 2,
        },
    }
    result = run_experiment(
        args.run,
        args.config,
        args.selection,
        args.phase_notes,
        args.output,
        args.activity,
        settings,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
