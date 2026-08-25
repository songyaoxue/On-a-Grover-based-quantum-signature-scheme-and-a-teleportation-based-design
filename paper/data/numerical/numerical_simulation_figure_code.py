"""Rebuild the manuscript numerical figure from the canonical pipeline data."""
from __future__ import annotations

import argparse
from pathlib import Path

from Numerical_Simulation_Full_Pipeline import generate_complete_numerical_figure


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    generate_complete_numerical_figure(args.data_dir, args.data_dir / "combined_numerical_simulations")
