# Ten-subject PINN audit batch summary

| Subject | Numeric | Empty | Missing | Invalid | Frames | Repaired frames | Gaps | A11 available | A11 >=20% repaired |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S59 | 21 | 0 | 4 | 0 | 4181 | 9 | 4 | 5 | 0 |
| S58 | 24 | 0 | 1 | 0 | 4281 | 2087 | 57 | 5 | 5 |
| S56 | 24 | 1 | 0 | 0 | 4337 | 391 | 50 | 5 | 3 |
| S49 | 23 | 0 | 2 | 0 | 3027 | 55 | 14 | 4 | 1 |
| S48 | 24 | 0 | 0 | 1 | 3463 | 329 | 40 | 5 | 3 |
| S46 | 24 | 0 | 1 | 0 | 5381 | 0 | 0 | 5 | 0 |
| S45 | 25 | 0 | 0 | 0 | 8413 | 0 | 0 | 5 | 0 |
| S44 | 25 | 0 | 0 | 0 | 7322 | 0 | 0 | 5 | 0 |
| S34 | 21 | 0 | 4 | 0 | 5990 | 0 | 0 | 5 | 0 |
| S32 | 21 | 0 | 4 | 0 | 5527 | 0 | 0 | 5 | 0 |

Entire missing or empty trials were not synthesized. The original numeric audit preceded the manual A11 phase-note update documented below.

## Manual A11 phase-note update (November 6, 2026)

| Subject | Marked A11 trials | Strict phase order | Camera fall direction | Modeling decision |
|:---|---:|:---:|:---|:---|
| S59 | 5 | pass | X | usable |
| S58 | 5 | fail | X | exclude from primary training/generalization; exploratory censored pre-contact analysis only |
| S56 | 5 | pass | X | usable with repair-mask sensitivity analysis |
| S49 | 3 | pass | X | use T02, T04, T05; exclude incomplete T01 and absent T03 |
| S48 | 5 | pass | X | use onset through apparent contact; mask repaired post-contact frames |
| S46 | 5 | pass | X | usable |
| S45 | 5 | pass | X | usable |
| S44 | 5 | pass | X with Z tilt | usable after subject-centric horizontal-axis alignment |
| S34 | 5 | pass | Z | usable after mapping Z fall progression to the model progression coordinate |
| S32 | 5 | pass | Z | usable after mapping Z fall progression to the model progression coordinate |

S58A11T03 and S58A11T04 assign apparent contact and post-fall to the same frame, and all S58 A11 recordings end before observed true contact/post-contact motion.
