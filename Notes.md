Subject 51's front fall; it does not seem complete.
Subject 50 to 54 has many missing rows in the samples
Subject 62's samples has different camera orientation. The fall displacement is mainly along camera (Z) instead of camera (X) as the forward displacement.
Subject 39 - No A14 samples
Subject 38 - No A10 samples
Subject 37 - No A11 samples
Subject 36 - No A10, A12 samples
Subject 35 - No A12 samples
Subject 34 - No. of A14 samples - 1
Subject 32 - No. of A14 samples - 1
S32 front fall motion is facing towards the camera i.e Z axis, unlike others with X axis.
S34 front fall motion is facing towards the camera i.e Z axis, unlike others with X axis.
S44 front fall motion is slightly tilted towards the camera i.e Z axis, unlike others with X axis.
S58 - All A11 trails has gap rows after the apparent contact. But the real rows are stopped just before the contact with the ground. Let Exclude this subject from training.

Participant#,Gender,Weight(lb),Height(ft),(inch)
S43,Female,130,5,4
S55,Male,145,5,5
S57,Male,180,5,8
S62,Male,155,5,4
S63,Male,180,5,6

S59,Male,220,6,0
S56,Male,165,5,10
S49,Female,165,4,11
S48,Male,188,5,8
S46,Male,160,5,8
S45,Male,170,5,11
S44,Male,180,6,1
S34,Female,125,5,6
S32,Male,160,5,10
S30,Female,190,5,6

Total Available Subjects:
S43, S55, S57, S62, S63, S59, S56, S49, S48, S46, S45, S44, S34, S32, S30

Complete DeepONet information flow
flowchart TD
    A["First 0.40 s: θ, x, θ̇, ẋ"] --> B["Four context windows"]
    B --> C["Context encoder"]
    D["Mass and height"] --> C
    C --> E["Four latent/controller coordinates"]
    E --> F["Forward operator branch"]
    G["Initial state and auxiliary values"] --> F
    H["Future query time"] --> I["Time trunk"]
    F --> J["Branch–trunk combination"]
    I --> J
    J --> K["Predicted future θ and x"]
    K --> L["Compare with measured future"]

We model the human body as a reduced-order cart-pole/inverted-pendulum system. Human CoM trajectories provide the angular and horizontal motion variables, and the physics residual enforces the corresponding biomechanical balance equations.

Model B (Real-data training with physics) uses an explicit reduced-order human biomechanics residual derived from the cart-pole representation of human CoM motion.

Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics/results/full/fold_##/test_predictions/<trial>.npz
file contains:
| Array | Meaning |
|---|---|
| `time_s` | Forecast timestamps starting at 0.40 s |
| `target_theta_rad` | Real held-out theta trajectory |
| `target_x_m` | Real held-out forward CoM trajectory |
| `predicted_theta_rad` | Model-generated theta trajectory |
| `predicted_x_m` | Model-generated forward CoM trajectory |
| `inferred_controller` | Four context-inferred effective controls |
| `controller_semantics` | Identifies the controls as physical-gain parameters |