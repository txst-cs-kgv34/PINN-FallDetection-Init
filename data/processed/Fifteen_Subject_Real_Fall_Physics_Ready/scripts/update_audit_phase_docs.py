#!/usr/bin/env python3
"""Add the consolidated multi-activity phase review to each subject audit."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path


START = "<!-- MULTIACTIVITY_PHASE_UPDATE_START -->"
END = "<!-- MULTIACTIVITY_PHASE_UPDATE_END -->"


def replace_block(path: Path, block: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if START in text and END in text:
        before = text.split(START, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip()
        text = before + "\n\n" + block + ("\n\n" + after if after else "\n")
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def b(value: str) -> bool:
    return value == "True"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audits-root", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--remaining-notes-root", type=Path, required=True)
    args = parser.parse_args()

    with (args.package / "manifests" / "trial_manifest.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    subjects = sorted({r["subject"] for r in rows}, key=lambda s: int(s[1:]))
    for subject in subjects:
        audit = args.audits_root / f"{subject}_PINN_audit"
        srows = [r for r in rows if r["subject"] == subject]
        analysis = audit / "analysis_inputs"
        analysis.mkdir(exist_ok=True)
        shutil.copy2(args.package / "subjects" / subject / "trial_manifest.csv", analysis / f"{subject}_real_fall_trial_manifest.csv")
        shutil.copy2(args.package / "subjects" / subject / "phase_annotations.json", analysis / f"{subject}_all_fall_phase_annotations.json")
        for activity in ["A10", "A12", "A13", "A14"]:
            candidates = list(args.remaining_notes_root.rglob(f"{subject}_{activity}_phase_notes.json"))
            if candidates:
                shutil.copy2(candidates[0], analysis / candidates[0].name)

        table = [
            "| Activity | Numeric | Detection-ready | Manual exclusions | Unavailable |",
            "|:--|--:|--:|--:|--:|",
        ]
        for activity in ["A10", "A11", "A12", "A13", "A14"]:
            arows = [r for r in srows if r["activity"] == activity]
            table.append(
                f"| {activity} | {sum(b(r['source_available']) for r in arows)} | "
                f"{sum(b(r['include_detection_training']) for r in arows)} | "
                f"{sum(r['dataset_status'] == 'manual_exclusion' for r in arows)} | "
                f"{sum(r['dataset_status'] == 'source_unavailable' for r in arows)} |"
            )
        exceptions = [r for r in srows if not b(r["include_detection_training"])]
        exception_lines = [f"- `{r['trial']}` — {r['decision_reason']}" for r in exceptions]
        axis_lines = []
        for r in srows:
            if r["camera_axis_manual_note"] and r["camera_axis_manual_note"] not in axis_lines:
                axis_lines.append(r["camera_axis_manual_note"])

        block = "\n".join([
            START,
            "## Multi-activity manual phase update",
            "",
            "A10, A12, A13, and A14 manual phase notes were reconciled with this audit; the previously reviewed A11 annotations were retained. The trial manifest separates manual fall validity from repair quality and preserves unavailable or incomplete trials as explicit exclusions.",
            "",
            *table,
            "",
            f"Machine-readable files: `analysis_inputs/{subject}_real_fall_trial_manifest.csv` and `analysis_inputs/{subject}_all_fall_phase_annotations.json`.",
            "",
            "A14 may end on either camera side after rotation. Use the per-trial X–Z fall direction rather than an activity-wide sign. Apparent contact remains skeleton-observed.",
            *( ["", "Manual camera-axis note(s): " + ", ".join(axis_lines) + "."] if axis_lines else [] ),
            *( ["", "### Excluded or unavailable trial slots", "", *exception_lines] if exception_lines else [] ),
            END,
        ])
        replace_block(audit / "README.md", block)

        finding_candidates = list(audit.glob(f"findings/{subject}_audit_repaired/FINDINGS.md"))
        if not finding_candidates:
            finding_candidates = list(audit.glob(f"findings/{subject}_audit/FINDINGS.md"))
        if finding_candidates:
            strict_planar = sum(b(r["include_planar_physics_primary"]) for r in srows)
            strict_rotation = sum(b(r["include_rotation_physics_primary"]) for r in srows)
            fblock = "\n".join([
                START,
                "## Multi-activity phase findings",
                "",
                f"Manual review yields **{sum(b(r['include_detection_training']) for r in srows)} detection-ready falls**, "
                f"**{strict_planar} strict planar-physics trials**, and **{strict_rotation} strict rotation-physics trials** for {subject}.",
                "",
                *table,
                "",
                "Repair-sensitive valid trials remain available with masks; they are not silently promoted into the strict physics subset. Incomplete falls and missing/empty sources are not represented as training examples.",
                END,
            ])
            replace_block(finding_candidates[0], fblock)

    summary = list(csv.DictReader((args.package / "manifests" / "activity_summary.csv").open(encoding="utf-8")))
    root_readme = """# Fifteen-subject PINN audit folders — multi-activity phase update

This archive contains the original subject audit packages plus the reconciled manual phase notes for A10–A14. Each subject now has an updated README, an updated audit FINDINGS file, a 25-slot real-fall trial manifest, and normalized all-activity annotations under `analysis_inputs/`.

The per-subject manifests are the authoritative inclusion records. Missing, empty, and manually incomplete falls remain explicit exclusions. Repaired-but-manually-valid trials retain their repair-quality tier so primary and sensitivity analyses can be separated.

Across the 15 subjects there are 375 expected slots, 358 numeric audit sources, and 322 manually validated detection-ready falls. Use subject-grouped splits and do not assume camera X is the fall direction.
"""
    (args.audits_root / "README.md").write_text(root_readme, encoding="utf-8")
    root_findings = [
        "# Consolidated findings",
        "",
        "| Activity | Numeric | Detection-ready | Planar primary | Rotation primary | Manual exclusions | Unavailable |",
        "|:--|--:|--:|--:|--:|--:|--:|",
    ]
    for r in summary:
        root_findings.append(
            f"| {r['activity']} {r['activity_name']} | {r['numeric_sources']} | {r['detection_ready']} | "
            f"{r['planar_physics_primary']} | {r['rotation_physics_primary']} | {r['manual_exclusions']} | {r['source_unavailable']} |"
        )
    root_findings += [
        "",
        "A10 for S30, S32, S34, and S62 and A14 for S62 use a camera-Z/−Y review plane. A14 fall direction varies by trial. S44 A14 is retained for detection/sensitivity work but withheld from primary rotate-physics fitting because it appears front-fall-like and may omit the turn-around.",
    ]
    (args.audits_root / "FINDINGS.md").write_text("\n".join(root_findings) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
