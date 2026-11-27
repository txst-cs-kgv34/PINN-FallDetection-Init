#!/usr/bin/env python3
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


HERE=Path(__file__).resolve().parent


def main() -> None:
    parser=argparse.ArgumentParser(description="Package detector results without checkpoints by default."); parser.add_argument("--include-models",action="store_true"); parser.add_argument("--output",type=Path,default=HERE/"Fifteen_Subject_A10_A14_CoM_Transformer_Physics_Augmentation_Ratios_5_Seeds_Results.zip"); args=parser.parse_args()
    comparison=HERE/"outputs/comparison/comparison_summary.json"
    if not comparison.is_file(): raise FileNotFoundError("Run all three conditions and compare before packaging")
    with zipfile.ZipFile(args.output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in ("README.md","FINDINGS.md","config.json"):
            archive.write(HERE/name,name)
        for path in sorted((HERE/"outputs").rglob("*")):
            if path.is_file() and (args.include_models or path.suffix!=".pt"): archive.write(path,path.relative_to(HERE))
    print(args.output)


if __name__=="__main__": main()
