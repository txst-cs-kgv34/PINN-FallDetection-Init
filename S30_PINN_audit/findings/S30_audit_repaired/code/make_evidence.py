"""Regenerate every evidence PNG using saved raw data and run configuration."""

from pathlib import Path
import argparse
import json
import numpy as np
from plot_evidence import make_plots
from skeleton_model import com_proxy


def regenerate(run):
    cfg = json.loads((run / "config.json").read_text())
    rows = json.loads((run / "results/trial_summary.json").read_text())
    segments = json.loads((run / "segment_model.json").read_text())["segments"]
    data = {}
    coms = {}
    scales = {}
    frames = json.loads((run / "results/com_proxy_all_frames.json").read_text())
    for row in rows:
        if not row["frames"]:
            continue
        name = row["trial"]
        data[name] = (
            np.loadtxt(run / "raw" / (name + ".csv"), delimiter=",", ndmin=2).reshape(
                -1, 32, 3
            )
            * {"mm": 0.001, "m": 1}[cfg["coordinate_units"]]
        )
        coms[name] = com_proxy(data[name], segments)[0]
        scales[name] = np.array(
            [f["median_normalized_limb_scale"] for f in frames if f["trial"] == name]
        )
    from temporal_diagnostics import audit_temporal

    audit_temporal(run)
    if data:
        make_plots(cfg, data, coms, scales, rows, run / "results/plots")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    regenerate(p.parse_args().run)


if __name__ == "__main__":
    main()
