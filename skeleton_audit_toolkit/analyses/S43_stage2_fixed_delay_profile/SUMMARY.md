# S43 fixed-delay profile diagnostic

At each of 11 fixed delays from 0.05 to 0.30 s, only Kp, Kd and Ki were optimized by exact automatic gradients with bounded L-BFGS-B. All delays use the same Stage-1 collocation times at or after 0.30 s. Stage-1 weights remain frozen; perturbation torque is zero; no nuisance torque, effective-torque target, saturation or torque limit is used.

## Synthetic control

The known synthetic delay is 0.100 s. The profile minimum is 0.100 s (absolute error 0.0 ms).

## Real-data decision

- Interior minima: 0/16
- Upper-bound minima at 0.30 s: 16/16
- Lower-bound minima at 0.05 s: 0/16
- Monotone non-increasing profiles: 16/16
- Best-delay range: 0.300--0.300 s
- Consistent delay-identification gate: **FAIL**

Delay is not consistently identifiable across the frozen Stage-1 folds and seeds.

## Fold/seed minima

| Activity | Held-out trial | Seed | Best delay | Interior | Upper boundary |
|---|---|---:|---:|---:|---:|
| A11 | S43A11T02 | 43013 | 0.300 s | False | True |
| A11 | S43A11T02 | 43014 | 0.300 s | False | True |
| A11 | S43A11T03 | 43013 | 0.300 s | False | True |
| A11 | S43A11T03 | 43014 | 0.300 s | False | True |
| A11 | S43A11T04 | 43013 | 0.300 s | False | True |
| A11 | S43A11T04 | 43014 | 0.300 s | False | True |
| A11 | S43A11T05 | 43013 | 0.300 s | False | True |
| A11 | S43A11T05 | 43014 | 0.300 s | False | True |
| A13 | S43A13T01 | 43013 | 0.300 s | False | True |
| A13 | S43A13T01 | 43014 | 0.300 s | False | True |
| A13 | S43A13T02 | 43013 | 0.300 s | False | True |
| A13 | S43A13T02 | 43014 | 0.300 s | False | True |
| A13 | S43A13T03 | 43013 | 0.300 s | False | True |
| A13 | S43A13T03 | 43014 | 0.300 s | False | True |
| A13 | S43A13T05 | 43013 | 0.300 s | False | True |
| A13 | S43A13T05 | 43014 | 0.300 s | False | True |

The diagnostic evaluates structural identifiability under the current zero-perturbation, fixed-link model. It does not turn the selected delay or gains into physiological measurements.

