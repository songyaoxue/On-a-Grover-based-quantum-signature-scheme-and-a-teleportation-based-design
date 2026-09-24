# Supplementary Materials

This package contains the code, data, figures, and reproducibility documentation supporting the numerical simulations and circuit-level evaluations.

## Package structure

- `code/qiskit_simulation/`: protocol-batch simulation, local circuit references, resource accounting, and validation.
- `code/ibm_aer_simulation/`: ideal IBM Aer circuit generation and comparison workflows.
- `code/ibm_hardware/`: offline processing of the included IBM Quantum results. Hardware connection and submission are not enabled by the standard offline workflow.
- `code/Supplementary material--Figure_6_Full_Code.docx`: complete Qiskit simulation Python source collected in one Word document.
- `code/Supplementary material--Figure_7_Full_Code.docx`: complete IBM Aer, IBM hardware, and offline-processing Python source collected in one Word document.
- `data/numerical_experiments/`: numerical source tables and fixed-seed reproducibility records.
- `data/local_reference/`: local simulator and resource-reference outputs.
- `data/ibm_hardware_existing/`: existing IBM Quantum counts, job metadata, and result tables. These files are preserved without numerical modification.
- `figures/main_manuscript_candidates/`: Figure 6 and Figure 7 in PDF and PNG formats.
- `figures/supplementary/`: supporting numerical figures in PDF and PNG formats.
- `documentation/`: methods, scope, reproducibility instructions, and figure-code-data mapping.
- `Supplementary_Data_Tables.xlsx`: reader-facing data tables.
- `requirements.txt`: Python dependency ranges.
- `CHECKSUMS.sha256`: SHA256 checksums for all package files except the checksum file itself.

## Protocol-batch scope

One protocol execution uses `2*lambda+1` physical `p1` copies, `lambda` `p2` copies, and `lambda` `p3` copies. S5 and S7 select test copies uniformly without replacement after the relevant copies and records have arrived. Fresh QOTP key blocks are allocated independently and consumed once for each encrypted physical object.

The included IBM Quantum results concern a direct `m=1` composed circuit-level candidate. They are not a direct hardware execution of the complete physical-copy batch. The offline workflows do not connect to IBM Quantum or submit hardware jobs.

## Local validation

Install the dependencies listed in `requirements.txt`, then run from `code/qiskit_simulation/`:

```bash
python -m pytest -q verification_experiment_validation.py
```

All stochastic numerical workflows use the fixed seeds recorded in `data/numerical_experiments/run_metadata.json`.
