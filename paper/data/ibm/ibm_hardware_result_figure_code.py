"""Generate the four-panel IBM hardware result figure from recorded result files."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent


def generate_ibm_hardware_figure() -> None:
    # The CSV files contain previously completed IBM jobs; this script submits nothing.
    teleportation = pd.read_csv(ROOT / "teleportation_hardware.csv")
    qotp = pd.read_csv(ROOT / "qotp_hardware.csv")
    swap = pd.read_csv(ROOT / "swap_test_hardware.csv")
    aer = pd.read_csv(ROOT / "composed_candidate_aer.csv").iloc[0]
    pilot = pd.read_csv(ROOT / "composed_candidate_pilot.csv").iloc[0]
    final = pd.read_csv(ROOT / "composed_candidate_final.csv").iloc[0]

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.4))
    ax = axes.ravel()

    state_labels = ["0", "1", "+", "-"]
    tele = teleportation.set_index("input_state").loc[state_labels]
    ax[0].bar(state_labels, tele["correct_output_probability"], color=[".2", ".35", ".5", ".65"])
    ax[0].set(title="(a) Quantum teleportation", ylabel="Correct-output probability", ylim=(0, 1.05))

    key_values = sorted(qotp["key"].unique())[:4]
    width = 0.18
    positions = np.arange(4)
    for index, key in enumerate(key_values):
        part = qotp[qotp["key"] == key].set_index("input_state").reindex(state_labels)
        ax[1].bar(
            positions + (index - 1.5) * width,
            part["correct_output_probability"], width, label=f"K={int(key):04d}",
        )
    ax[1].set_xticks(positions, state_labels)
    ax[1].set(title="(b) Strengthened-QOTP roundtrip", ylabel="Correct-output probability", ylim=(0.94, 1.005))
    ax[1].legend(fontsize=8)

    cases = ["identical_0_0", "identical_plus_plus", "orthogonal_0_1", "orthogonal_plus_minus", "fixed_overlap_F_0.25"]
    selected = swap[(swap["execution"] == "Final") & (swap["lambda"] == 1)].set_index("case").loc[cases]
    ideal = (1 - selected["fidelity"].to_numpy()) / 2
    ax[2].bar(np.arange(5) - 0.18, ideal, 0.36, label="Ideal", color=".8", edgecolor="black")
    ax[2].bar(np.arange(5) + 0.18, selected["single_test_detection_probability"], 0.36, label="IBM hardware", color=".25")
    ax[2].set_xticks(range(5), ["0/0", "+/+", "0/1", "+/-", "F=.25"])
    ax[2].set(title="(c) Swap-test verification", ylabel="Single-test detection probability", ylim=(0, 0.65))
    ax[2].legend(fontsize=8)

    values = [aer["success_probability"], pilot["success_probability"], final["success_probability"]]
    lower = [0, pilot["success_probability"] - pilot["wilson_95_low"], final["success_probability"] - final["wilson_95_low"]]
    upper = [0, pilot["wilson_95_high"] - pilot["success_probability"], final["wilson_95_high"] - final["success_probability"]]
    ax[3].bar(["Aer ideal", "Pilot", "Final"], values, color=[".75", ".45", ".15"])
    ax[3].errorbar(range(3), values, yerr=[lower, upper], fmt="none", color="black", capsize=4)
    ax[3].set(
        title="(d) Composed staged-emulation candidate",
        ylabel="Combined correct-output probability", ylim=(0, 1.05),
    )

    fig.suptitle("Recorded IBM hardware results and Aer reference", fontsize=16)
    fig.tight_layout()
    for extension in ("pdf", "png", "eps"):
        fig.savefig(ROOT / f"combined_ibm_hardware_results.{extension}", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    generate_ibm_hardware_figure()
