"""Read and audit recordings; preserve source bytes and export derived measurements."""

from pathlib import Path
import csv
import hashlib
import io
import json
import re
import zipfile
import numpy as np
from skeleton_model import NAMES, LIMBS, SOURCES, segment_model, com_proxy, sensitivity


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def write_csv(path, rows):
    if not rows:
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def analyze(input_path, cfg, root):
    rawdir = root / "raw"
    out = root / "results"
    plots = out / "plots"
    comdir = out / "com"
    for d in [rawdir, out, plots, comdir]:
        d.mkdir(parents=True, exist_ok=True)
    mass = cfg["mass_lb"] * 0.45359237
    height = cfg["height_in"] * 0.0254
    fps = cfg["fps"]
    segments = segment_model(cfg["sex"])
    assert np.isclose(sum(s["mass_fraction"] for s in segments), 1, atol=1e-12)
    for s in segments:
        s["mass_kg"] = mass * s["mass_fraction"]
    dump(
        root / "segment_model.json",
        {
            "status": "Approximate segment-mass CoM proxy, not validated anatomical CoM",
            "mass_kg": mass,
            "height_m": height,
            "source": SOURCES,
            "segments": segments,
            "sex": cfg["sex"],
            "model_id": "visual3d_deleva_sdk_proxy_v2_" + cfg["sex"],
            "reported_mass_fraction_sum": sum(
                s["reported_mass_fraction"] for s in segments
            ),
            "mass_normalization": "Female source fractions divided by their sum (0.9999); male fractions unchanged.",
            "height_use": "Reported stature is retained for diagnostic ratios only. No eye-to-foot or per-frame rescaling.",
            "parameter_note": (
                "Male shank 0.4395; 0.4459 sensitivity variant."
                if cfg["sex"] == "male"
                else "Female shank 0.4352; male-specific shank sensitivity is omitted."
            ),
        },
    )
    write_csv(
        out / "segment_mass_model.csv",
        [
            {
                **s,
                "a": ",".join(NAMES[j] for j in s["a"]),
                "b": ",".join(NAMES[j] for j in s["b"]),
            }
            for s in segments
        ],
    )
    manifest = []
    stats = []
    bone_stats = []
    events = []
    frames = []
    dataset = {}
    coms = {}
    lengths = {}
    scales = {}
    sens = []
    pattern = re.compile(
        r"(?P<subject>S\d+)(?P<activity>A\d+)(?P<trial>T\d+)\.csv", re.I
    )
    if input_path.is_dir():
        entries = [
            (str(p.relative_to(input_path)), p.read_bytes())
            for p in sorted(input_path.rglob("*.csv"))
        ]
    else:
        with zipfile.ZipFile(input_path) as z:
            entries = [
                (i.filename, z.read(i))
                for i in z.infolist()
                if not i.is_dir() and i.filename.lower().endswith(".csv")
            ]
    seen = set()
    ignored = []
    for member, raw in sorted(entries, key=lambda item: Path(item[0]).name):
        name = Path(member).name
        match = pattern.fullmatch(name)
        if (
            "__MACOSX" in Path(member).parts
            or not match
            or match["subject"].upper() != cfg["subject_id"]
        ):
            ignored.append(member)
            continue
        name = name.upper().replace(".CSV", ".csv")
        if name in seen:
            raise ValueError("Duplicate trial filename: " + name)
        seen.add(name)
        trial = Path(name).stem
        act = match["activity"].upper()
        cfg["activities"].setdefault(act, act)
        (rawdir / name).write_bytes(raw)
        meta = {
            "trial": trial,
            "activity": act,
            "description": cfg["activities"][act],
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_member": member,
            "status": "empty" if not raw.strip() else "numeric",
        }
        manifest.append(meta)
        if meta["status"] == "empty":
            stats.append({**meta, "frames": 0, "first_to_last_s": None})
            continue
        try:
            a = np.loadtxt(io.BytesIO(raw), delimiter=",", ndmin=2)
            if a.shape[1] != 96 or len(a) < 2:
                raise ValueError(
                    f"Expected at least two frames and 96 columns, got {a.shape}"
                )
            if not np.isfinite(a).all():
                raise ValueError(
                    "Nonfinite values: entire trial withheld, raw retained"
                )
            check = a.reshape(-1, 32, 3)
            if any(
                np.any(np.linalg.norm(check[:, i] - check[:, j], axis=1) <= 0)
                for i, j in LIMBS.values()
            ):
                raise ValueError(
                    "Zero-length limb: scale diagnostics undefined, raw retained"
                )
            if np.any(
                np.linalg.norm(check[:, 26] - check[:, [20, 24]].mean(1), axis=1) == 0
            ):
                raise ValueError(
                    "Zero head-to-ankle vector: orientation undefined, raw retained"
                )
        except ValueError as error:
            meta.update(status="invalid", error=str(error))
            stats.append({**meta, "frames": 0})
            continue
        x = a.reshape(-1, 32, 3) * {"mm": 0.001, "m": 1.0}[cfg["coordinate_units"]]
        n = len(x)
        dataset[trial] = x
        t = np.arange(n) / fps
        c, segment_positions = com_proxy(x, segments)
        coms[trial] = c
        le = np.stack(
            [np.linalg.norm(x[:, a] - x[:, b], axis=1) for a, b in LIMBS.values()], 1
        )
        ratios = le / np.median(le, axis=0)
        scale = np.median(ratios, axis=1)
        lengths[trial] = le
        scales[trial] = scale
        d = np.linalg.norm(np.diff(x, axis=0), axis=2)
        dc = np.linalg.norm(np.diff(c, axis=0), axis=1)
        scale_step = np.r_[np.nan, np.abs(np.diff(scale) / scale[:-1])]
        joint_step = np.r_[np.nan, d.max(1)]
        flagged = (joint_step > cfg["screening"]["joint_step_m"]) | (
            scale_step > cfg["screening"]["frame_scale_change_fraction"]
        )
        head_ankle = x[:, 26] - (x[:, 20] + x[:, 24]) / 2
        angle = np.degrees(
            np.arccos(
                np.clip(-head_ankle[:, 1] / np.linalg.norm(head_ankle, axis=1), -1, 1)
            )
        )
        # Euclidean eye-to-foot spans are pose-dependent and omit head/sole offsets.
        eyes = x[:, [28, 30]].mean(1)
        eyefoot = np.stack(
            [np.linalg.norm(eyes - x[:, j], axis=1) for j in [21, 25]], 1
        ).max(1)
        eq = x.mean(1)
        eqdiff = np.linalg.norm(c - eq, axis=1)
        corr = (
            float(np.corrcoef(le.T)[np.triu_indices(8, 1)].min())
            if np.all(le.std(0) > 1e-12)
            else None
        )
        largest = np.unravel_index(d.argmax(), d.shape)
        stat = {
            **meta,
            "frames": n,
            "columns": 96,
            "first_to_last_s": (n - 1) / fps,
            "n_over_fps_s": n / fps,
            "nonfinite_values": int((~np.isfinite(a)).sum()),
            "zero_values": int((a == 0).sum()),
            "exact_duplicate_rows": n - len(np.unique(a, axis=0)),
            "max_joint_step_m": float(d.max()),
            "max_joint_step_joint": NAMES[largest[1]],
            "max_step_from_frame0": int(largest[0]),
            "max_step_to_frame0": int(largest[0] + 1),
            "max_pelvis_step_m": float(d[:, 0].max()),
            "max_com_step_m": float(dc.max()),
            "steps_any_joint_over_threshold": int(
                (d.max(1) > cfg["screening"]["joint_step_m"]).sum()
            ),
            "flagged_destination_frames": int(flagged.sum()),
            "limb_scale_range_pct": float(100 * (scale.max() / scale.min() - 1)),
            "max_limb_cv_pct": float((100 * le.std(0) / le.mean(0)).max()),
            "min_limb_correlation": corr,
            "max_normalized_limb_spread": float(np.ptp(ratios, axis=1).max()),
            "head_ankle_angle_to_camera_minus_y_start_deg": float(angle[0]),
            "head_ankle_angle_to_camera_minus_y_end_deg": float(angle[-1]),
            "head_ankle_angle_min_deg": float(angle.min()),
            "eye_foot_distance_start_m": float(eyefoot[0]),
            "eye_foot_distance_max_m": float(eyefoot.max()),
            "max_eye_foot_over_reported_stature": float(eyefoot.max() / height),
            "com_minus_equal_joint_centroid_median_m": float(np.median(eqdiff)),
            "com_minus_equal_joint_centroid_max_m": float(eqdiff.max()),
            "com_camera_x_range_m": float(np.ptp(c[:, 0])),
            "com_camera_y_range_m": float(np.ptp(c[:, 1])),
            "com_camera_z_range_m": float(np.ptp(c[:, 2])),
            "com_camera_minus_y_change_end_m": float(-(c[-1, 1] - c[0, 1])),
        }
        stats.append(stat)
        sens.append({"trial": trial, **sensitivity(x, segments, c, cfg["sex"])})
        for j, name in enumerate(LIMBS):
            v = le[:, j]
            bone_stats.append(
                {
                    "trial": trial,
                    "segment": name,
                    "median_m": float(np.median(v)),
                    "min_m": float(v.min()),
                    "max_m": float(v.max()),
                    "cv_pct": float(100 * v.std() / v.mean()),
                }
            )
        cr = []
        for k in range(n):
            rr = {
                "trial": trial,
                "activity": act,
                "frame0": k,
                "time_from_clip_start_nominal_s": k / fps,
                "com_proxy_camera_x_m": float(c[k, 0]),
                "com_proxy_camera_y_m": float(c[k, 1]),
                "com_proxy_camera_z_m": float(c[k, 2]),
                "delta_camera_x_m": float(c[k, 0] - c[0, 0]),
                "delta_camera_minus_y_m": float(-c[k, 1] + c[0, 1]),
                "delta_camera_z_m": float(c[k, 2] - c[0, 2]),
                "absolute_height_above_floor_m": None,
                "true_horizontal_1_m": None,
                "true_horizontal_2_m": None,
                "equal_joint_centroid_x_m": float(eq[k, 0]),
                "equal_joint_centroid_y_m": float(eq[k, 1]),
                "equal_joint_centroid_z_m": float(eq[k, 2]),
                "median_normalized_limb_scale": float(scale[k]),
                "max_joint_step_from_previous_m": (
                    None if k == 0 else float(joint_step[k])
                ),
                "review_flag": bool(flagged[k]),
                "head_ankle_angle_to_camera_minus_y_deg": float(angle[k]),
                "eye_to_furthest_foot_m": float(eyefoot[k]),
            }
            cr.append(rr)
            frames.append(rr)
            if flagged[k]:
                j = int(d[k - 1].argmax())
                events.append(
                    {
                        "trial": trial,
                        "from_frame0": k - 1,
                        "to_frame0": k,
                        "max_joint": NAMES[j],
                        "max_joint_step_m": float(joint_step[k]),
                        "com_step_m": float(dc[k - 1]),
                        "limb_scale_step_fraction": float(scale_step[k]),
                        "reason": f"joint step >{cfg['screening']['joint_step_m']}m and/or scale change >{100*cfg['screening']['frame_scale_change_fraction']}%; review only",
                    }
                )
        write_csv(comdir / (trial + "_com_proxy.csv"), cr)
    for act, trials in cfg.get("expected_trials", {}).items():
        for tr in trials:
            trial = cfg["subject_id"] + act + tr
            if trial + ".csv" not in seen:
                meta = {
                    "trial": trial,
                    "activity": act,
                    "description": cfg["activities"].get(act, act),
                    "status": "missing",
                    "bytes": None,
                    "sha256": None,
                }
                manifest.append(meta)
                stats.append({**meta, "frames": 0})
    dump(out / "ignored_members.json", ignored)
    cross = []
    names = list(dataset)
    for i, a in enumerate(names):
        aa = {r.tobytes() for r in dataset[a]}
        for b in names[i + 1 :]:
            shared = len(aa & {r.tobytes() for r in dataset[b]})
            if shared:
                cross.append(
                    {"trial_a": a, "trial_b": b, "exact_shared_frames": shared}
                )
    for name, rows in [
        ("trial_summary", stats),
        ("manifest", manifest),
        ("segment_lengths", bone_stats),
        ("review_events", events),
        ("com_proxy_all_frames", frames),
        ("landmark_sensitivity", sens),
    ]:
        write_csv(out / (name + ".csv"), rows)
        dump(out / (name + ".json"), rows)
    dump(out / "cross_trial_duplicates.json", cross)
    valid = [r for r in stats if r["frames"]]
    class_summary = []
    for act, label in cfg["activities"].items():
        vs = [r for r in valid if r["activity"] == act]
        class_summary.append(
            {
                "activity": act,
                "description": label,
                "expected": len(cfg.get("expected_trials", {}).get(act, [])) or None,
                "nonempty": len(vs),
                "unavailable_trials": [
                    r["trial"]
                    for r in stats
                    if r["activity"] == act and not r["frames"]
                ],
                "frames": sum(r["frames"] for r in vs),
                "min_span_s": min((r["first_to_last_s"] for r in vs), default=None),
                "max_span_s": max((r["first_to_last_s"] for r in vs), default=None),
                "max_scale_range_pct": max(
                    (r["limb_scale_range_pct"] for r in vs), default=None
                ),
            }
        )
    dump(out / "class_summary.json", class_summary)
    write_csv(out / "class_summary.csv", class_summary)
    summary = {
        "subject": cfg,
        "mass_kg": mass,
        "height_m": height,
        "archive_sha256": (
            hashlib.sha256(input_path.read_bytes()).hexdigest()
            if input_path.is_file()
            else None
        ),
        "expected_files": sum(map(len, cfg.get("expected_trials", {}).values()))
        or None,
        "nonempty_files": len(valid),
        "empty_files": sum(r["status"] == "empty" for r in manifest),
        "invalid_files": sum(r["status"] == "invalid" for r in manifest),
        "missing_files": sum(r["status"] == "missing" for r in manifest),
        "total_frames": len(frames),
        "first_to_last_span_min_s": min(
            (r["first_to_last_s"] for r in valid if r["first_to_last_s"] is not None),
            default=None,
        ),
        "first_to_last_span_max_s": max(
            (r["first_to_last_s"] for r in valid if r["first_to_last_s"] is not None),
            default=None,
        ),
        "clips_under_one_second": sum(
            r["first_to_last_s"] < cfg["screening"]["short_clip_seconds"] for r in valid
        ),
        "clips_start_angle_over_60deg": sum(
            r["head_ankle_angle_to_camera_minus_y_start_deg"] > 60 for r in valid
        ),
        "clips_with_review_flags": sum(
            r["flagged_destination_frames"] > 0 for r in valid
        ),
        "total_review_flagged_destination_frames": sum(
            r["flagged_destination_frames"] for r in valid
        ),
        "global_limb_scale_range_pct_min": min(
            (
                r["limb_scale_range_pct"]
                for r in valid
                if r["limb_scale_range_pct"] is not None
            ),
            default=None,
        ),
        "global_limb_scale_range_pct_max": max(
            (
                r["limb_scale_range_pct"]
                for r in valid
                if r["limb_scale_range_pct"] is not None
            ),
            default=None,
        ),
        "global_max_joint_step_m": max(
            (r["max_joint_step_m"] for r in valid if r["max_joint_step_m"] is not None),
            default=None,
        ),
        "global_min_limb_correlation": min(
            (
                r["min_limb_correlation"]
                for r in valid
                if r["min_limb_correlation"] is not None
            ),
            default=None,
        ),
        "nonfinite_values": sum(r["nonfinite_values"] for r in valid),
        "duplicate_rows_within": sum(r["exact_duplicate_rows"] for r in valid),
        "cross_trial_duplicate_pairs": cross,
        "equal_joint_centroid_difference_median_m": (
            float(
                np.median(
                    np.concatenate(
                        [
                            np.linalg.norm(coms[k] - dataset[k].mean(1), axis=1)
                            for k in names
                        ]
                    )
                )
            )
            if names
            else None
        ),
        "anatomical_com_status": "Approximate segment-mass proxy only; landmark and tracking errors uncalibrated.",
        "floor_height_status": "Unavailable. Camera axes and displacement proxies are exported instead.",
        "training_status": "No PINN trained, no synthetic falls generated. All files inspected for quality only.",
        "sources": SOURCES,
    }
    dump(out / "study_summary.json", summary)
    dump(root / "config.json", cfg)
    return summary
