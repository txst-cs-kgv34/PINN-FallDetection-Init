# S58 A11 manual phase status

Manual phase notes were received for **5** trial(s). Strict validation: **fail**.

**Manual observation:** All A11 trials were marked, but real rows stop immediately before true ground contact. The marked apparent-contact frames are pre-contact proxies, and subsequent rows are repaired rather than observed contact/post-fall motion.

**Camera-axis interpretation:** `camera_x`.

**Modeling decision:** `exclude_primary_training_and_generalization` — Do not use S58 for primary full-trajectory training, contact/post-fall supervision, or headline generalization metrics. It may be retained only for an explicitly labeled exploratory pre-contact or censored-data analysis with repaired frames masked.

## Phase/repair intersection

| Trial | Phase order | Onset-contact repaired | Contact repaired | Post-fall repaired |
|:---|:---:|---:|:---:|:---:|
| S58A11T01 | pass | 0/35 (0.0%) | no | yes |
| S58A11T02 | pass | 0/57 (0.0%) | no | yes |
| S58A11T03 | fail | 1/32 (3.1%) | no | no |
| S58A11T04 | fail | 1/36 (2.8%) | no | no |
| S58A11T05 | pass | 0/30 (0.0%) | no | yes |

## Explicit exclusions or limitations

- All A11 trials: exclude from primary full-trajectory training and primary generalization metrics because true contact and post-contact motion are not observed.
- S58A11T03 and S58A11T04: apparent_contact and post_fall use the same frame, so strict ordered phase validation fails.

The contact label is an apparent skeleton-based contact observation, not force-plate-confirmed contact. Automatic suggestions are superseded by the manual notes.
