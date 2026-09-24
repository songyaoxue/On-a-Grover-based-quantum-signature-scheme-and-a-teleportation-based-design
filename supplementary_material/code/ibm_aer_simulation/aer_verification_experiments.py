"""Aer-specific entry point for the organized verification experiment suite.

The numerical implementation is imported from the shared Qiskit simulation module so
that the Aer wrapper does not duplicate or alter the validated computational logic.
Running this module writes only to the explicitly supplied data directory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


QISKIT_MODULE_DIR = Path(__file__).resolve().parents[1] / "qiskit_simulation"
if str(QISKIT_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(QISKIT_MODULE_DIR))

from verification_experiment_suite import qiskit_aer_local_reference


def run_aer_verification_experiments(repo_root: Path, data_dir: Path) -> None:
    """Run the existing local BasicSimulator/Aer reference workflow."""
    qiskit_aer_local_reference(repo_root.resolve(), data_dir.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run local Qiskit Aer verification experiments.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    arguments = parser.parse_args()
    run_aer_verification_experiments(arguments.repo_root, arguments.data_dir)
