"""Run the fixed-delay identifiability diagnostic for revised Stage 2."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_phase_baseline import write_csv
from phase_annotations import read_json, validate_phase_notes
from run_stage2_gradient_pid import prepare_trial
from skeleton_model import segment_model
from stage2_gradient_pid import (
    GRAVITY_M_S2,
    ParameterBounds,
    build_synthetic_records,
    identify_fixed_delay_gains,
    load_frozen_stage1,
    prepare_frozen_records,
)


def _bounds(settings):
    raw = settings["bounds"]
    return ParameterBounds(
        alpha_kp=tuple(raw["alpha_kp"]),
        beta_kd=tuple(raw["beta_kd"]),
        kappa_ki=tuple(raw["kappa_ki"]),
        delay_s=(0.0, 1.0),
    )


def _prepare_trials(config, run_dir, subject, selection):
    segments = segment_model(subject["sex"])
    activity_trials = {}
    for specification in config["activities"]:
        _, windows = validate_phase_notes(
            Path(specification["phase_notes"]), run_dir, subject, selection
        )
        windows = [
            item for item in windows
            if item["activity"] == specification["activity"]
        ]
        activity_trials[specification["activity"]] = [
            prepare_trial(
                run_dir,
                subject,
                window,
                segments,
                config["preprocessing"],
                specification["horizontal_axis"],
            )
            for window in windows
        ]
    return activity_trials


def _fit_checkpoint(job):
    checkpoint, trials, mass_kg, source, diagnostic = job
    stage1 = source["stage1"]
    stage2 = source["stage2"]
    delays = diagnostic["fixed_delay_s"]
    optimizer = diagnostic["gain_optimizer"]
    model = load_frozen_stage1(checkpoint, stage1["architecture"])
    mean = np.asarray(checkpoint["condition_mean"])
    scale = np.asarray(checkpoint["condition_scale"])
    local_trials = []
    for original in trials:
        trial = dict(original)
        trial["condition_scaled"] = (trial["condition_raw"] - mean) / scale
        trial["torque_scale"] = mass_kg * GRAVITY_M_S2 * trial["length_m"]
        local_trials.append(trial)
    by_name = {trial["trial"]: trial for trial in local_trials}
    training = [by_name[name] for name in checkpoint["training_trials"]]
    reference_length = float(np.median([trial["length_m"] for trial in training]))
    records = prepare_frozen_records(
        model,
        training,
        mass_kg,
        stage1["damping_nms"],
        checkpoint["time_scale_s"],
        stage2["controller_collocation_points"],
        max(delays),
    )
    selected_rows, start_rows = [], []
    for fixed_delay in delays:
        best, profiles = identify_fixed_delay_gains(
            records=records,
            fixed_delay_s=fixed_delay,
            mass_kg=mass_kg,
            reference_length_m=reference_length,
            bounds=_bounds(stage2),
            starts=optimizer["starts"],
            lbfgs_max_iter=optimizer["lbfgs_max_iter"],
            integral_time_reference_s=stage2["integral_time_reference_s"],
        )
        identity = {
            "activity": checkpoint["activity"],
            "held_out_trial": checkpoint["held_out_trial"],
            "training_trials": ";".join(checkpoint["training_trials"]),
            "seed": checkpoint["seed"],
        }
        selected_rows.append({**identity, **best})
        start_rows.extend({**identity, **profile} for profile in profiles)
    return selected_rows, start_rows


def _synthetic_profile(source, diagnostic):
    settings = source["synthetic_validation"]
    stage2 = source["stage2"]
    mass = settings["mass_kg"]
    length = settings["length_m"]
    torque_reference = mass * GRAVITY_M_S2 * length
    inertia_reference = mass * length**2
    derivative_reference = np.sqrt(inertia_reference * torque_reference)
    true_fit = {
        "kp_nm_per_rad": settings["true_alpha_kp"] * torque_reference,
        "kd_nms_per_rad": settings["true_beta_kd"] * derivative_reference,
        "ki_nm_per_rad_s": settings["true_kappa_ki"] * torque_reference
        / stage2["integral_time_reference_s"],
        "delay_s": settings["true_delay_s"],
    }
    records = build_synthetic_records(
        mass,
        length,
        settings["damping_nms"],
        true_fit,
        settings["initial_states"],
        settings["duration_s"],
        settings["internal_hz"],
        max(diagnostic["fixed_delay_s"]),
    )
    rows = []
    for delay in diagnostic["fixed_delay_s"]:
        best, _ = identify_fixed_delay_gains(
            records=records,
            fixed_delay_s=delay,
            mass_kg=mass,
            reference_length_m=length,
            bounds=_bounds(stage2),
            starts=diagnostic["gain_optimizer"]["starts"],
            lbfgs_max_iter=diagnostic["gain_optimizer"]["lbfgs_max_iter"],
            integral_time_reference_s=stage2["integral_time_reference_s"],
        )
        rows.append(best)
    best = min(rows, key=lambda row: row["training_physics_loss"])
    return rows, {
        "true_delay_s": settings["true_delay_s"],
        "best_profile_delay_s": best["delay_s"],
        "absolute_error_s": abs(best["delay_s"] - settings["true_delay_s"]),
        "profile_minimum_loss": best["training_physics_loss"],
    }


def _group(rows, fields):
    grouped = {}
    for row in rows:
        key = tuple(row[field] for field in fields)
        grouped.setdefault(key, []).append(row)
    return grouped


def _diagnostic_decision(rows, delays):
    groups = _group(rows, ("activity", "held_out_trial", "seed"))
    profiles = []
    for key, local in sorted(groups.items()):
        local.sort(key=lambda row: row["delay_s"])
        losses = np.asarray([row["training_physics_loss"] for row in local])
        best_index = int(np.argmin(losses))
        best_delay = float(local[best_index]["delay_s"])
        tolerance = max(1e-12, 1e-8 * float(np.max(losses)))
        profiles.append({
            "activity": key[0],
            "held_out_trial": key[1],
            "seed": int(key[2]),
            "best_delay_s": best_delay,
            "best_loss": float(losses[best_index]),
            "lower_boundary_minimum": best_index == 0,
            "upper_boundary_minimum": best_index == len(local) - 1,
            "interior_minimum": 0 < best_index < len(local) - 1,
            "monotone_nonincreasing": bool(np.all(np.diff(losses) <= tolerance)),
            "loss_at_0_05_s": float(losses[0]),
            "loss_at_0_30_s": float(losses[-1]),
            "relative_loss_drop_0_05_to_0_30": float((losses[0] - losses[-1]) / losses[0]),
        })
    best_delays = np.asarray([item["best_delay_s"] for item in profiles])
    interior_count = sum(item["interior_minimum"] for item in profiles)
    upper_count = sum(item["upper_boundary_minimum"] for item in profiles)
    lower_count = sum(item["lower_boundary_minimum"] for item in profiles)
    delay_span = float(best_delays.max() - best_delays.min())
    consistent = interior_count >= 12 and delay_span <= 0.05 + 1e-12
    return profiles, {
        "tested_delay_s": delays,
        "fold_seed_profiles": len(profiles),
        "interior_minima": interior_count,
        "lower_boundary_minima": lower_count,
        "upper_boundary_minima": upper_count,
        "monotone_nonincreasing_profiles": sum(
            item["monotone_nonincreasing"] for item in profiles
        ),
        "best_delay_min_s": float(best_delays.min()),
        "best_delay_max_s": float(best_delays.max()),
        "best_delay_span_s": delay_span,
        "consistent_delay_identification_gate": "pass" if consistent else "fail",
        "decision": (
            "Delay has a consistent interior profile minimum."
            if consistent
            else "Delay is not consistently identifiable across the frozen Stage-1 folds and seeds."
        ),
    }


def _plot_profiles(output, rows, synthetic_rows):
    plot_dir = output / "plots"
    plot_dir.mkdir()
    groups = _group(rows, ("activity", "held_out_trial"))
    for (activity, trial), local in sorted(groups.items()):
        fig, axis = plt.subplots(figsize=(7, 4.5))
        for seed, seed_rows in sorted(_group(local, ("seed",)).items()):
            seed_rows.sort(key=lambda row: row["delay_s"])
            axis.plot(
                [1000 * row["delay_s"] for row in seed_rows],
                [row["training_physics_loss"] for row in seed_rows],
                marker="o",
                linewidth=2,
                label=f"Seed {seed[0]}",
            )
        axis.set(
            xlabel="Fixed delay (ms)",
            ylabel="Training physics loss",
            title=f"{trial} fixed-delay profile",
        )
        axis.grid(alpha=0.25)
        axis.legend()
        fig.tight_layout()
        fig.savefig(plot_dir / f"{trial}_fixed_delay_profile.png", dpi=180)
        plt.close(fig)

    for activity, local in sorted(_group(rows, ("activity",)).items()):
        fig, axis = plt.subplots(figsize=(8, 5))
        for key, curve in sorted(_group(local, ("held_out_trial", "seed")).items()):
            curve.sort(key=lambda row: row["delay_s"])
            loss = np.asarray([row["training_physics_loss"] for row in curve])
            axis.plot(
                [1000 * row["delay_s"] for row in curve],
                loss / loss.min(),
                alpha=0.55,
                linewidth=1.5,
                label=f"{key[0]} s{key[1]}",
            )
        axis.axhline(1.0, color="#555555", linewidth=1)
        axis.set(
            xlabel="Fixed delay (ms)",
            ylabel="Loss / profile minimum",
            title=f"{activity[0]} normalized fixed-delay profiles",
        )
        axis.grid(alpha=0.25)
        axis.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(plot_dir / f"{activity[0]}_fixed_delay_profiles.png", dpi=180)
        plt.close(fig)

    fig, axis = plt.subplots(figsize=(7, 4.5))
    axis.plot(
        [1000 * row["delay_s"] for row in synthetic_rows],
        [row["training_physics_loss"] for row in synthetic_rows],
        marker="o",
        linewidth=2,
    )
    axis.axvline(100.0, color="#b83280", linestyle="--", label="True delay")
    axis.set(
        xlabel="Fixed delay (ms)",
        ylabel="Training physics loss",
        title="Synthetic known-delay profile",
    )
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "synthetic_fixed_delay_profile.png", dpi=180)
    plt.close(fig)


def _summary(decision, profile_decisions, synthetic):
    lines = [
        "# S43 fixed-delay profile diagnostic",
        "",
        "At each of 11 fixed delays from 0.05 to 0.30 s, only Kp, Kd and Ki were optimized by exact automatic gradients with bounded L-BFGS-B. All delays use the same Stage-1 collocation times at or after 0.30 s. Stage-1 weights remain frozen; perturbation torque is zero; no nuisance torque, effective-torque target, saturation or torque limit is used.",
        "",
        "## Synthetic control",
        "",
        f"The known synthetic delay is {synthetic['true_delay_s']:.3f} s. The profile minimum is {synthetic['best_profile_delay_s']:.3f} s (absolute error {1000*synthetic['absolute_error_s']:.1f} ms).",
        "",
        "## Real-data decision",
        "",
        f"- Interior minima: {decision['interior_minima']}/{decision['fold_seed_profiles']}",
        f"- Upper-bound minima at 0.30 s: {decision['upper_boundary_minima']}/{decision['fold_seed_profiles']}",
        f"- Lower-bound minima at 0.05 s: {decision['lower_boundary_minima']}/{decision['fold_seed_profiles']}",
        f"- Monotone non-increasing profiles: {decision['monotone_nonincreasing_profiles']}/{decision['fold_seed_profiles']}",
        f"- Best-delay range: {decision['best_delay_min_s']:.3f}--{decision['best_delay_max_s']:.3f} s",
        f"- Consistent delay-identification gate: **{decision['consistent_delay_identification_gate'].upper()}**",
        "",
        decision["decision"],
        "",
        "## Fold/seed minima",
        "",
        "| Activity | Held-out trial | Seed | Best delay | Interior | Upper boundary |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item in profile_decisions:
        lines.append(
            f"| {item['activity']} | {item['held_out_trial']} | {item['seed']} | {item['best_delay_s']:.3f} s | {item['interior_minimum']} | {item['upper_boundary_minimum']} |"
        )
    lines += [
        "",
        "The diagnostic evaluates structural identifiability under the current zero-perturbation, fixed-link model. It does not turn the selected delay or gains into physiological measurements.",
        "",
    ]
    return "\n".join(lines)


def run(diagnostic_path, run_dir, subject_path, selection_path, output, workers):
    diagnostic = json.loads(diagnostic_path.read_text())
    source_path = Path(diagnostic["source_stage2_config"])
    source = json.loads(source_path.read_text())
    subject = read_json(subject_path)
    selection = read_json(selection_path)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    mass_kg = float(subject["mass_lb"]) * 0.45359237
    activity_trials = _prepare_trials(source, run_dir, subject, selection)
    checkpoints = json.loads(Path(source["stage1"]["checkpoint_file"]).read_text())
    jobs = [
        (checkpoint, activity_trials[checkpoint["activity"]], mass_kg, source, diagnostic)
        for checkpoint in checkpoints
    ]
    selected_rows, start_rows = [], []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        for index, (selected, starts) in enumerate(executor.map(_fit_checkpoint, jobs), 1):
            selected_rows.extend(selected)
            start_rows.extend(starts)
            print(f"[{index}/{len(jobs)}] fixed-delay fold/seed profile", flush=True)
    selected_rows.sort(
        key=lambda row: (row["activity"], row["held_out_trial"], row["seed"], row["delay_s"])
    )
    start_rows.sort(
        key=lambda row: (
            row["activity"], row["held_out_trial"], row["seed"],
            row["delay_s"], row["start_index"],
        )
    )
    synthetic_rows, synthetic_decision = _synthetic_profile(source, diagnostic)
    profile_decisions, decision = _diagnostic_decision(
        selected_rows, diagnostic["fixed_delay_s"]
    )
    write_csv(output / "fixed_delay_profiles.csv", selected_rows)
    write_csv(output / "fixed_delay_start_profiles.csv", start_rows)
    write_csv(output / "fold_seed_minima.csv", profile_decisions)
    write_csv(output / "synthetic_fixed_delay_profile.csv", synthetic_rows)
    (output / "DECISION.json").write_text(
        json.dumps({"synthetic": synthetic_decision, "real_data": decision}, indent=2) + "\n"
    )
    (output / "experiment_config.json").write_text(
        json.dumps({"diagnostic": diagnostic, "source_stage2": source}, indent=2) + "\n"
    )
    _plot_profiles(output, selected_rows, synthetic_rows)
    (output / "SUMMARY.md").write_text(
        _summary(decision, profile_decisions, synthetic_decision) + "\n"
    )
    print(json.dumps(decision, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path,
        default=Path("configs/S43_stage2_fixed_delay_profile.json"),
    )
    parser.add_argument("--run", type=Path, default=Path("findings/S43_audit"))
    parser.add_argument("--subject-config", type=Path, default=Path("configs/S43.json"))
    parser.add_argument(
        "--selection", type=Path,
        default=Path("configs/S43_modeling_selection.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("analyses/S43_stage2_fixed_delay_profile"),
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    run(
        args.config, args.run, args.subject_config, args.selection,
        args.output, args.workers,
    )


if __name__ == "__main__":
    main()
