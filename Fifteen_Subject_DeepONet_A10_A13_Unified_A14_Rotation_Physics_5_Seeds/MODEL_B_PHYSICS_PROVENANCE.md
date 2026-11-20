# Model B physics provenance

The planar residual is the delayed CartPole residual used by `Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds`. Its implementation is in `operator_core.py` under `physics_residual_components` and `controller_force_from_delayed_state`.

For angle `theta`, direction-aligned CoM displacement `x`, delayed state index `d`, and inferred gains `[Kp_theta, Kd_theta, Kp_x, Kd_x]`, the controller force is

```text
gate  = sigmoid(sharpness * (abs(theta[d]) - Pi))
force = Kp_theta*gate*theta[d] + Kd_theta*theta_dot[d]
        + Kp_x*x[d] + Kd_x*x_dot[d]
```

The normalized residuals are

```text
r_theta = (M11*theta_ddot + M12*x_ddot
           - 0.5*m*g*l*sin(theta)) / M11

r_x = (M12*theta_ddot + (m+m0)*x_ddot
       - 0.5*m*l*theta_dot^2*sin(theta) - force) / (m+m0)
```

where `M11=(1/3)*m*l^2` and `M12=0.5*m*l*cos(theta)`. Constants remain `m=0.0138 kg`, `m0=1 kg`, `l=0.57 m`, `g=9.81 m/s^2`, `tau=0.23 s`, `Pi=0.0635 rad`, and dead-zone sharpness 50. The CartPole loss weight remains 0.01.

For A14 only, the model retains this same CartPole residual for `theta/x` and adds

```text
r_yaw = yaw_ddot - (Kp_yaw*yaw[d] + Kd_yaw*yaw_dot[d]) / I_yaw
I_yaw = 0.08 * subject_mass * subject_height^2
```

The yaw residual is also weighted 0.01. The no-physics baseline retains the same architecture and inferred controller pathway but sets both residual weights to zero.

