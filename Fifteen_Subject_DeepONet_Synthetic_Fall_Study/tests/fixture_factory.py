from __future__ import annotations

import json
from pathlib import Path


SUBJECTS = [f"S{index:02d}" for index in range(1, 16)]
SCORES = {1: 0.30, 2: 0.10, 3: 0.20, 4: 0.50, 5: 0.40}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def create_results_fixture(root: Path) -> Path:
    results = root / "results" / "full"
    for seed_index in range(1, 6):
        base_seed = 20261100 + seed_index
        for fold in range(1, 6):
            start = 3 * (fold - 1)
            test = SUBJECTS[start : start + 3]
            validation = SUBJECTS[(start + 3) % len(SUBJECTS)]
            train = [
                subject
                for subject in SUBJECTS
                if subject not in set(test) | {validation}
            ]
            folder = (
                results
                / f"seed_{seed_index:02d}_{base_seed}"
                / f"fold_{fold:02d}"
            )
            write_json(
                folder / "training_selection.json",
                {
                    "best_epoch": 10 + fold + seed_index,
                    "best_validation_value": SCORES[seed_index] + 0.01 * fold,
                    "selection_metric": "real validation-subject forecast normalized MSE",
                    "test_subject_used_for_selection": False,
                    "training_regime": "direct_physics",
                },
            )
            write_json(
                folder / "summary.json",
                {
                    "fold": fold,
                    "seed_index": seed_index,
                    "base_optimization_seed": base_seed,
                    "effective_fold_seed": base_seed + fold,
                    "validation_subject": validation,
                    "train_subjects": train,
                    "test_subjects": test,
                    "checkpoint_selected_only_on_real_validation_subject": True,
                    "physics_loss_enabled": True,
                    "test_pooled_metrics": {
                        "normalized_mse": 1000.0 - 100.0 * seed_index
                    },
                },
            )
            (folder / "final_best_model_state.pt").write_bytes(
                f"fixture fold={fold} seed={seed_index}\n".encode("utf-8")
            )
    return results
