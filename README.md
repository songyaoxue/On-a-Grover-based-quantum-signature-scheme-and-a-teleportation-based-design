# On a Grover-Based Quantum Signature Scheme and a Teleportation-Based Design

This repository contains the current local author manuscript and the code, data, and figures accompanying its numerical and circuit-level evaluations.

## Current materials

- [Author manuscript (PDF)](paper/current/Entropygroveralgorithmsignaturev8.pdf) and [LaTeX source](paper/current/Entropygroveralgorithmsignaturev8.tex). The PDF is compiled from the local author source with the current Figure 6 and Figure 7; it is **not** the publisher's version of record. The MDPI template prints a placeholder DOI, so cite the publisher's article page instead.
- [Supplementary materials](supplementary_material/README.md), including [Qiskit code](supplementary_material/code/qiskit_simulation/), [Aer code](supplementary_material/code/ibm_aer_simulation/), [IBM hardware/offline analysis code](supplementary_material/code/ibm_hardware/), [source data](supplementary_material/data/), and [figures](supplementary_material/figures/).
- [Reproducibility notes](supplementary_material/documentation/REPRODUCIBILITY.md) and [dependency requirements](supplementary_material/requirements.txt).

The numerical protocol-batch implementation uses `2*lambda+1` physical `p1` copies and `lambda` copies each of `p2` and `p3`. The S5 and S7 test positions are sampled without replacement after receipt of the corresponding copies and records. Each protected physical object receives an independently allocated, single-use QOTP key block. The resource ledger reports `(5*lambda+3)*n` Bell pairs for an `n`-qubit message.

The preserved IBM Quantum measurements evaluate selected circuit-level operations and a direct `m=1` composed candidate. They are **not** a hardware execution of the full physical-copy batch or a proof of protocol security. The included hardware counts and job metadata are existing results; reproducing the local numerical analyses does not require a new IBM job.

## Historical repository materials

The pre-existing [`experiments/`](experiments/) and [`paper/manuscript/`](paper/manuscript/) directories are retained for provenance. They describe an earlier manuscript and experimental organization and should not be mistaken for the current supplementary workflow. New readers should start with `paper/current/` and `supplementary_material/`.

## Build and verification

The manuscript source can be compiled from `paper/current/` with `latexmk -pdf Entropygroveralgorithmsignaturev8.tex`. For local numerical validation, install `supplementary_material/requirements.txt` in an isolated Python environment and follow its reproducibility notes. Hardware submission is unnecessary and must be explicitly enabled in scripts that support it; never commit IBM or GitHub credentials.
