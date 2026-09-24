"""Analysis entry point for existing IBM hardware result files.

This module has no IBM account connection and no job-submission function. It delegates
the existing CSV classification, Wilson-interval calculation, and Figure 7 rendering
logic to the shared verification suite. Output generation is guarded by an explicit
command-line flag to prevent accidental replacement of reviewed artifacts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


QISKIT_MODULE_DIR = Path(__file__).resolve().parents[1] / "qiskit_simulation"
if str(QISKIT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(QISKIT_MODULE_DIR))

from verification_experiment_suite import plot_figure6, wilson


def analyze_existing_hardware_results(repo_root: Path, data_dir: Path, figure_dir: Path) -> None:
    """Process included CSV files only; no IBM service call is made."""
    plot_figure6(repo_root.resolve(), data_dir.resolve(), figure_dir.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze existing IBM hardware result CSV files.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--figure-dir", type=Path, required=True)
    parser.add_argument(
        "--write-derived-output",
        action="store_true",
        help="Required guard for writing classifications, confidence intervals, and Figure 7 files.",
    )
    arguments = parser.parse_args()
    if not arguments.write_derived_output:
        parser.error("no output written: pass --write-derived-output after selecting non-original target directories")
    analyze_existing_hardware_results(arguments.repo_root, arguments.data_dir, arguments.figure_dir)
