"""Create a derived CSV set with explicit repairs for fully blank skeleton rows.

Short gaps are forward-filled. Longer internal gaps are linearly interpolated.
Boundary gaps without two valid endpoints are filled from the nearest valid row.
Original files are never modified, and every repaired row is recorded.
"""

from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import re
import zipfile

import numpy as np


PATTERN = re.compile(r"(?P<subject>S\d+)(?P<activity>A\d+)(?P<trial>T\d+)\.csv", re.I)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def entries(source):
    if source.is_dir():
        return [(str(path.relative_to(source)), path.read_bytes()) for path in sorted(source.rglob("*.csv"))]
    with zipfile.ZipFile(source) as archive:
        return [
            (item.filename, archive.read(item))
            for item in archive.infolist()
            if not item.is_dir() and item.filename.lower().endswith(".csv")
        ]


def blank_runs(mask):
    indices = np.flatnonzero(mask)
    if not len(indices):
        return []
    runs = []
    start = previous = int(indices[0])
    for index in indices[1:]:
        index = int(index)
        if index == previous + 1:
            previous = index
        else:
            runs.append((start, previous))
            start = previous = index
    runs.append((start, previous))
    return runs


def repair_rows(raw, short_gap_max):
    text = raw.decode("utf-8-sig", errors="strict")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise ValueError("empty recording")
    if any(len(row) != 96 for row in rows):
        raise ValueError("every CSV row must contain exactly 96 fields")
    blank = np.array([all(not value.strip() for value in row) for row in rows], dtype=bool)
    partial = [index for index, row in enumerate(rows) if any(not value.strip() for value in row) and not blank[index]]
    if partial:
        raise ValueError(f"partially blank rows are not repaired: {[i + 1 for i in partial]}")
    values = np.full((len(rows), 96), np.nan, dtype=float)
    for index, row in enumerate(rows):
        if not blank[index]:
            values[index] = np.asarray(row, dtype=float)
    if not np.isfinite(values[~blank]).all():
        raise ValueError("nonfinite nonblank values are not repaired")
    if blank.all():
        raise ValueError("recording contains no valid coordinate row")

    repairs = []
    for start, end in blank_runs(blank):
        count = end - start + 1
        before = start - 1 if start > 0 and np.isfinite(values[start - 1]).all() else None
        after = end + 1 if end + 1 < len(values) and np.isfinite(values[end + 1]).all() else None
        if count <= short_gap_max and before is not None:
            values[start : end + 1] = values[before]
            method = "forward_fill_short_gap"
        elif before is not None and after is not None:
            for offset, index in enumerate(range(start, end + 1), start=1):
                alpha = offset / (count + 1)
                values[index] = (1.0 - alpha) * values[before] + alpha * values[after]
            method = "linear_interpolation_long_gap"
        elif before is not None:
            values[start : end + 1] = values[before]
            method = "forward_fill_trailing_boundary"
        elif after is not None:
            values[start : end + 1] = values[after]
            method = "backward_fill_leading_boundary"
        else:
            raise ValueError("gap has no valid boundary frame")
        repairs.append(
            {
                "start_row1": start + 1,
                "end_row1": end + 1,
                "frame_count": count,
                "method": method,
                "previous_valid_row1": before + 1 if before is not None else None,
                "next_valid_row1": after + 1 if after is not None else None,
            }
        )
    if not np.isfinite(values).all():
        raise ValueError("repair left nonfinite values")
    stream = io.StringIO()
    np.savetxt(stream, values, delimiter=",", fmt="%.10f")
    return stream.getvalue().encode("utf-8"), repairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--short-gap-max", type=int, default=3)
    args = parser.parse_args()
    if args.short_gap_max < 1:
        parser.error("--short-gap-max must be positive")
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    args.output.mkdir(parents=True)

    manifest = []
    frame_mask = []
    seen = set()
    for member, raw in sorted(entries(args.input), key=lambda item: Path(item[0]).name):
        name = Path(member).name
        match = PATTERN.fullmatch(name)
        if "__MACOSX" in Path(member).parts or not match or match["subject"].upper() != args.subject.upper():
            continue
        if name.upper() in seen:
            raise ValueError(f"duplicate trial filename: {name}")
        seen.add(name.upper())
        repaired, gaps = repair_rows(raw, args.short_gap_max)
        destination = args.output / name
        destination.write_bytes(repaired)
        trial = destination.stem
        for gap in gaps:
            manifest.append({"trial": trial, **gap})
            for row1 in range(gap["start_row1"], gap["end_row1"] + 1):
                frame_mask.append({"trial": trial, "row1": row1, "frame0": row1 - 1, "method": gap["method"]})
        row_count = sum(1 for line in repaired.splitlines() if line.strip())
        (args.output / f"{trial}.repair.json").write_text(
            json.dumps(
                {
                    "trial": trial,
                    "source_member": member,
                    "source_sha256": sha256(raw),
                    "repaired_sha256": sha256(repaired),
                    "rows": row_count,
                    "repaired_rows": sum(gap["frame_count"] for gap in gaps),
                    "gaps": gaps,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    write_csv(args.output / "repair_manifest.csv", manifest)
    write_csv(args.output / "repaired_frames.csv", frame_mask)
    (args.output / "repair_manifest.json").write_text(
        json.dumps(
            {
                "subject": args.subject.upper(),
                "policy": {
                    "short_gap_max_frames": args.short_gap_max,
                    "short_gap_method": "forward fill from previous valid frame",
                    "long_internal_gap_method": "per-coordinate linear interpolation between valid boundary frames",
                    "boundary_gap_method": "nearest valid frame carry because two-sided interpolation is impossible",
                    "original_files_modified": False,
                },
                "trial_count": len(seen),
                "repaired_gap_count": len(manifest),
                "repaired_frame_count": len(frame_mask),
                "gaps": manifest,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"trials": len(seen), "gaps": len(manifest), "repaired_frames": len(frame_mask)}, indent=2))


if __name__ == "__main__":
    main()
