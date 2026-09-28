"""Compatibility imports for older external scripts; new code uses task modules."""

from audit_data import analyze, dump, write_csv
from plot_evidence import make_plots
from skeleton_model import (
    NAMES,
    PARENTS,
    LIMBS,
    LEFT,
    RIGHT,
    COLORS,
    SOURCES,
    segment_model,
    com_proxy,
    sensitivity,
)
