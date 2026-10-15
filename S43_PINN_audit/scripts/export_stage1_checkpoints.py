"""Export the selected Stage-1 fold/seed models for frozen Stage 2 use.

This is intentionally separate from Stage 2. It repeats only the retained
Stage-1 training setup at the preselected nonzero physics weight and writes the
network weights plus fold-specific normalization constants needed downstream.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from inverted_pendulum_pinn import LossWeights, train_model
from phase_annotations import read_json, validate_phase_notes
from run_stage1_inverted_pendulum import (
    make_training_records,
    prepare_trial,
    standardize_conditions,
)
from skeleton_model import segment_model


ROOT = Path(__file__).resolve().parents[1]


def rooted(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def export_checkpoints(
    export_config_path,
    run_dir,
    subject_config_path,
    selection_path,
    output_path=None,
    smoke=False,
):
    export_config = read_json(export_config_path)
    subject = read_json(subject_config_path)
    selection = read_json(selection_path)
    if export_config["subject"] != subject["subject_id"]:
        raise ValueError("checkpoint and subject configurations disagree")

    output = rooted(output_path or export_config["output"])
    if output.exists():
        raise FileExistsError(
            f"output already exists: {output}; choose a new --output path"
        )

    run_dir = rooted(run_dir)
    segments = segment_model(subject["sex"])
    height_m = float(subject["height_in"]) * 0.0254
    mass_kg = float(subject["mass_lb"]) * 0.45359237
    selected_weight = float(export_config["selected_physics_weight"])
    checkpoints = []

    activity_specs = export_config["activities"][:1] if smoke else export_config["activities"]
    for activity_spec in activity_specs:
        activity = activity_spec["activity"]
        experiment = read_json(rooted(activity_spec["experiment_config"]))
        settings = experiment["settings"]
        configured_weight = float(experiment["selected_best_nonzero_physics_weight"])
        if abs(configured_weight - selected_weight) > 1e-12:
            raise ValueError(
                f"{activity} selected weight {configured_weight:g} does not match "
                f"checkpoint-export weight {selected_weight:g}"
            )

        _, windows = validate_phase_notes(
            rooted(activity_spec["phase_notes"]), run_dir, subject, selection
        )
        windows = [window for window in windows if window["activity"] == activity]
        if len(windows) != 4:
            raise ValueError(f"expected four eligible {activity} trials, found {len(windows)}")
        trials = [
            prepare_trial(run_dir, subject, window, segments, settings)
            for window in windows
        ]

        held_out_trials = trials[:1] if smoke else trials
        seeds = settings["seeds"][:1] if smoke else settings["seeds"]
        epochs = 1 if smoke else int(settings["epochs"])
        history_interval = 1 if smoke else int(settings["history_interval"])
        damping_nms = float(settings["damping_nms"])

        for fold_index, original_held_out in enumerate(held_out_trials):
            training = [
                item.copy()
                for item in trials
                if item["trial"] != original_held_out["trial"]
            ]
            held_out = original_held_out.copy()
            condition_mean, condition_scale = standardize_conditions(
                training, held_out
            )
            time_scale_s = max(item["duration_s"] for item in training)
            records = make_training_records(
                training,
                height_m,
                mass_kg,
                damping_nms,
                int(settings["collocation_points"]),
            )
            weights = LossWeights(
                physics=selected_weight,
                rigid_length=selected_weight * float(settings["rigid_length_ratio"]),
                effective_torque_l2=float(settings["effective_torque_l2"]),
                effective_torque_rate=float(settings["effective_torque_rate"]),
            )
            for seed in seeds:
                training_seed = int(seed) + fold_index
                model, history = train_model(
                    records,
                    condition_size=len(condition_mean),
                    time_scale_s=time_scale_s,
                    architecture=settings["architecture"],
                    epochs=epochs,
                    learning_rate=float(settings["learning_rate"]),
                    loss_weights=weights,
                    seed=training_seed,
                    history_interval=history_interval,
                )
                checkpoints.append(
                    {
                        "activity": activity,
                        "held_out_trial": held_out["trial"],
                        "seed": int(seed),
                        "training_trials": [item["trial"] for item in training],
                        "condition_mean": condition_mean.tolist(),
                        "condition_scale": condition_scale.tolist(),
                        "time_scale_s": float(time_scale_s),
                        "training_seed": training_seed,
                        "state_dict": {
                            name: value.detach().cpu().numpy().tolist()
                            for name, value in model.state_dict().items()
                        },
                        "history": history,
                    }
                )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(checkpoints, indent=2) + "\n", encoding="utf-8")
    return {
        "output": str(output),
        "checkpoints": len(checkpoints),
        "smoke": smoke,
        "selected_physics_weight": selected_weight,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "S43_stage1_checkpoints.json",
    )
    parser.add_argument(
        "--run", type=Path, default=ROOT / "findings" / "S43_audit"
    )
    parser.add_argument(
        "--subject-config", type=Path, default=ROOT / "configs" / "S43.json"
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "configs" / "S43_modeling_selection.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="train one epoch for one A11 fold/seed to test the export path",
    )
    args = parser.parse_args()
    result = export_checkpoints(
        args.config,
        args.run,
        args.subject_config,
        args.selection,
        args.output,
        args.smoke,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
