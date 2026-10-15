"""Merge phase-note exports while enforcing explicit trial eligibility decisions."""

import argparse
import json
from pathlib import Path

from phase_annotations import read_json


def merge_phase_notes(base_path, supplement_path, eligibility_path):
    base = read_json(base_path)
    supplement = read_json(supplement_path)
    eligibility = read_json(eligibility_path)
    if (
        base["subject"] != supplement["subject"]
        or base["subject"] != eligibility["subject_id"]
    ):
        raise ValueError("subject identifiers do not match")
    if float(base["nominal_fps"]) != float(supplement["nominal_fps"]):
        raise ValueError("nominal FPS values do not match")

    decisions = eligibility["trial_decisions"]
    merged = {(note["trial"], note["phase"]): note for note in base["notes"]}
    excluded_notes = []
    for note in supplement["notes"]:
        trial = note["trial"]
        if trial not in decisions:
            raise ValueError(
                f"supplemental trial lacks an eligibility decision: {trial}"
            )
        if decisions[trial]["onset_to_contact_eligible"]:
            merged[(trial, note["phase"])] = note
        else:
            excluded_notes.append(note)

    return {
        "subject": base["subject"],
        "nominal_fps": base["nominal_fps"],
        "notes": sorted(
            merged.values(), key=lambda note: (note["trial"], note["frame0"])
        ),
        "merge_provenance": {
            "base_file": Path(base_path).name,
            "supplement_file": Path(supplement_path).name,
            "eligibility_file": Path(eligibility_path).name,
            "excluded_supplemental_notes": excluded_notes,
            "trial_decisions": decisions,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--supplement", required=True, type=Path)
    parser.add_argument("--eligibility", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    result = merge_phase_notes(args.base, args.supplement, args.eligibility)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "subject": result["subject"],
                "included_notes": len(result["notes"]),
                "excluded_supplemental_notes": len(
                    result["merge_provenance"]["excluded_supplemental_notes"]
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
