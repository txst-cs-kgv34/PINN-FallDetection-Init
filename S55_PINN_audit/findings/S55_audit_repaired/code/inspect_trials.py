"""Prepare selected audited trials for offline playback and foot-geometry inspection."""

from pathlib import Path
import argparse
import hashlib
import json
import platform
import shutil

import numpy as np

from audit_data import dump, write_csv
from build_viewer import build_viewer
from filter_motion import filter_motion
from foot_geometry import compute_foot_geometry
from skeleton_model import NAMES, PARENTS, com_proxy


def prepare_inspection(
    run, selection_path, output, metadata_path=None, cutoff_hz=None, order=6
):
    """Validate selection, preserve raw timing, calculate geometry and build the player."""
    # 1. Resolve the existing audit and an explicit, subject-matched selection.
    config = json.loads((run / "config.json").read_text())
    selection = json.loads(selection_path.read_text())
    if selection["subject_id"] != config["subject_id"]:
        raise ValueError("Selection subject does not match the audit")
    model = json.loads((run / "segment_model.json").read_text())
    manifest = json.loads((run / "results/manifest.json").read_text())
    available = {row["trial"]: row for row in manifest if row["status"] == "numeric"}
    candidates = selection["remaining_candidate_trials"]
    excluded = selection.get("excluded_trials", {})
    if not candidates or len(set(candidates)) != len(candidates):
        raise ValueError("Provide a nonempty, unique candidate list")
    if set(candidates) & set(excluded):
        raise ValueError("A selected trial is also excluded")
    if set(candidates) - set(available):
        raise ValueError("A selected trial is absent or failed the audit input checks")
    confirmations = json.loads(metadata_path.read_text()) if metadata_path else {}
    fps = config["fps"]
    audit_frames = json.loads((run / "results/com_proxy_all_frames.json").read_text())
    flags = {
        trial: [r["review_flag"] for r in audit_frames if r["trial"] == trial]
        for trial in candidates
    }
    if cutoff_hz is not None:
        # Validate settings and SciPy availability before creating a new output folder.
        filter_motion(np.ones((40, 32, 3)), fps, cutoff_hz, order)
    output.mkdir(parents=True, exist_ok=False)
    geometry_dir = output / "geometry"
    geometry_dir.mkdir()

    # 2. Read verified raw coordinates; calculate raw and optional filtered views.
    trials = []
    summaries = []
    for trial in sorted(candidates):
        path = run / "raw" / (trial + ".csv")
        if hashlib.sha256(path.read_bytes()).hexdigest() != available[trial]["sha256"]:
            raise ValueError(f"Raw input changed since audit: {trial}")
        pose = np.loadtxt(path, delimiter=",", ndmin=2).reshape(-1, 32, 3)
        pose = pose * {"mm": 0.001, "m": 1.0}[config["coordinate_units"]]
        raw_com = com_proxy(pose, model["segments"])[0]
        repeated = np.r_[False, np.all(pose[1:] == pose[:-1], axis=(1, 2))]
        modes = {"raw": pose}
        filter_settings = {"status": "not_requested"}
        if cutoff_hz is not None:
            filtered, filter_settings = filter_motion(pose, fps, cutoff_hz, order)
            if filtered is not None:
                modes["filtered"] = filtered
        if len(flags[trial]) != len(pose):
            raise ValueError(f"Frame flag count mismatch: {trial}")
        item = {
            "trial": trial,
            "frames": len(pose),
            "raw_review_flags": flags[trial],
            "raw_repeated_previous": repeated.tolist(),
            "filter": filter_settings,
            "modes": {},
        }
        export_rows = []
        filtered_change = None
        for mode, positions in modes.items():
            com = com_proxy(positions, model["segments"])[0]
            geometry = compute_foot_geometry(positions, com)
            item["modes"][mode] = {
                "pose": positions.tolist(),
                "com": com.tolist(),
                **{key: value.tolist() for key, value in geometry.items()},
            }
            if mode == "filtered":
                filtered_change = float(np.linalg.norm(com - raw_com, axis=1).max())
            for frame in range(len(pose)):
                row = {
                    "trial": trial,
                    "mode": mode,
                    "frame0": frame,
                    "nominal_time_s": frame / fps,
                    "raw_review_flag": flags[trial][frame],
                    "raw_repeated_previous": bool(repeated[frame]),
                    "foot_separation_camera_xz_m": float(
                        geometry["foot_separation_camera_xz"][frame]
                    ),
                    "foot_separation_camera_x_m": float(
                        geometry["foot_separation_camera_x"][frame]
                    ),
                }
                for axis, label in enumerate("xyz"):
                    row[f"com_camera_{label}_m"] = float(com[frame, axis])
                    row[f"foot_midpoint_camera_{label}_m"] = float(
                        geometry["foot_midpoint"][frame, axis]
                    )
                    row[f"com_relative_to_foot_midpoint_camera_{label}_m"] = float(
                        geometry["com_relative_to_foot_midpoint"][frame, axis]
                    )
                export_rows.append(row)
        write_csv(geometry_dir / (trial + ".csv"), export_rows)
        trials.append(item)
        summaries.append(
            {
                "trial": trial,
                "frames": len(pose),
                "raw_flagged_frames": sum(flags[trial]),
                "raw_repeat_transitions": int(repeated.sum()),
                "filter_status": filter_settings["status"],
                "max_filtered_com_change_m": filtered_change,
            }
        )

    # 3. Save explicit inputs/settings, a portable player and reproducible source snapshots.
    payload = {
        "subject": config,
        "confirmations": confirmations,
        "selection": selection,
        "fps": fps,
        "joint_names": NAMES,
        "parents": PARENTS,
        "trials": trials,
    }
    (output / "inspection_data.json").write_text(
        json.dumps(payload, separators=(",", ":"), allow_nan=False) + "\n"
    )
    dump(output / "selection.json", selection)
    dump(output / "metadata_confirmations.json", confirmations)
    dump(output / "segment_model.json", model)
    write_csv(output / "inspection_summary.csv", summaries)
    dump(output / "inspection_summary.json", summaries)
    build_viewer(output / "inspection_data.json", output / "INSPECT.html")
    source = Path(__file__).resolve().parent
    shutil.copytree(
        source, output / "scripts", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copytree(source.parent / "viewer", output / "viewer")
    code_files = list((output / "scripts").glob("*.py")) + list(
        (output / "viewer").glob("*")
    )
    provenance = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "audit_run": str(run.resolve()),
        "audit_config_sha256": hashlib.sha256(
            (run / "config.json").read_bytes()
        ).hexdigest(),
        "raw_sha256": {trial: available[trial]["sha256"] for trial in candidates},
        "cutoff_hz": cutoff_hz,
        "order_per_pass": order,
        "source_sha256": {
            str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in code_files
        },
    }
    if cutoff_hz is not None:
        import scipy

        provenance["scipy"] = scipy.__version__
    dump(output / "provenance.json", provenance)
    print(
        f"Inspection ready: {len(trials)} trials, {sum(t['frames'] for t in trials)} frames → {output / 'INSPECT.html'}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run", type=Path, required=True, help="Completed audit directory"
    )
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, required=True, help="New inspection directory"
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        help="Latest collection confirmations; audit remains historical",
    )
    parser.add_argument(
        "--cutoff-hz",
        type=float,
        help="Optional offline low-pass comparison; raw is always retained",
    )
    parser.add_argument("--filter-order", type=int, default=6)
    args = parser.parse_args()
    prepare_inspection(
        args.run,
        args.selection,
        args.output,
        args.metadata,
        args.cutoff_hz,
        args.filter_order,
    )


if __name__ == "__main__":
    main()
