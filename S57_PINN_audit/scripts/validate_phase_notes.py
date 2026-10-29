"""Validate manually exported phase notes and write trial windows."""

from pathlib import Path
import argparse
import csv
import json

from phase_annotations import validate_phase_notes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notes", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    config = json.loads((args.run / "config.json").read_text(encoding="utf-8"))
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    _, windows = validate_phase_notes(args.notes, args.run, config, selection)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(windows, indent=2) + "\n", encoding="utf-8")
        csv_path = args.output.with_suffix(".csv")
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(windows[0]))
            writer.writeheader()
            writer.writerows(windows)
    print(f"PASS: {len(windows)} complete, ordered phase-marked trials")


if __name__ == "__main__":
    main()
