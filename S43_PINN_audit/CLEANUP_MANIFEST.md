# S43 codebase cleanup manifest

This directory was created from the archived project as a new allowlisted copy.
The original archive was not modified.

## Retained

- Complete S43 audit run, raw files, findings, and provenance snapshot
- S43 inspection package and viewer used for manual phase marking
- Reviewed S43 phase annotations and eligibility configurations
- Phase-aligned baseline and activity comparison
- Framework-aligned A11 and A13 Stage 1 experiments
- Independent Stage 1 checkpoint export and the 16 retained frozen checkpoints
- Revised gradient-based Stage 2 and its synthetic recovery validation
- Fixed-delay profile diagnostic
- Stage 3A assumption-based sensitivity specification
- Active scripts, configs, requirements, and phase-specific verifiers

## Removed from the active codebase

- S06 and S50 data, configurations, findings, and outputs
- General subject templates and non-S43 audit verifier
- Initial pilot PINNs and non-framework reconstruction/physics-weight branches
- Stage 1.5 experiments
- Simulated Stage 2A branches
- Real-effective-torque and nuisance-torque identification branches
- Earlier full-PID bounded least-squares Stage 2
- Torque-limit and torque-saturation fitting
- Obsolete top-level `core.py`
- Duplicate source snapshots inside the generated inspection package; the
  active inspection source remains in top-level `scripts/` and `viewer/`
- macOS metadata (`.DS_Store`, AppleDouble `._*`) and `__MACOSX`

The old audit code under `findings/S43_audit/code/` remains only because it is
part of the completed audit's provenance record. It is not used by the active
workflow.

## Dependency repair made during cleanup

The revised Stage 2 previously imported frozen-network evaluation helpers from
the superseded full-PID module. Those neutral functions now live in
`scripts/frozen_stage1.py`. A new `scripts/export_stage1_checkpoints.py` creates
the checkpoint ensemble directly from the retained Stage 1 workflow, so no
active phase depends on removed Stage 2 code.
