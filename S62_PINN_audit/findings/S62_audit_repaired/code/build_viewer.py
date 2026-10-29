"""Build a self-contained offline inspection player from prepared trial data."""

from pathlib import Path
import argparse
import json


def build_viewer(data_path, output_path):
    """Embed reviewed local assets and JSON; the resulting HTML needs no server."""
    assets = Path(__file__).resolve().parents[1] / "viewer"
    data = json.loads(data_path.read_text())
    encoded = json.dumps(data, separators=(",", ":"), allow_nan=False).replace(
        "<", "\\u003c"
    )
    template = (assets / "inspection.html").read_text()
    html = template.replace(
        "/* INLINE_STYLE */", (assets / "inspection.css").read_text()
    )
    html = html.replace("/* INLINE_SCRIPT */", (assets / "inspection.js").read_text())
    html = html.replace("DATA_PLACEHOLDER", encoded)
    output_path.write_text(html)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_viewer(args.data, args.output)


if __name__ == "__main__":
    main()
