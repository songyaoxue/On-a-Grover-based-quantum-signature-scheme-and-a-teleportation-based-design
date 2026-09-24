# Reproducibility

## Execution environment

- Protocol-batch execution environment: Python 3.12.5, Qiskit 2.0.0, qiskit-aer 0.17.0, NumPy 2.1.1, pandas 3.0.2, Matplotlib 3.10.1.
- Primary seed: 20260903.
- Repeated Swap-Test trials: 50,000 per point.
- Protocol trials: 4,000 per point.
- Explicit Aer Swap-Test shots: 16,384 per point.
- Composed-candidate local shots: 4,096 per circuit-level reference.

## Validation result

All organized Python modules pass syntax compilation and import smoke checks. The physical-copy regression suite passes 93 of 93 tests, with no failures or skipped tests. Two complete same-seed executions produced byte-identical protocol, resource, sampling, fresh-key, and PNG outputs; PDF byte hashes may differ because PDF metadata embeds generation timestamps.

## Offline operation

Local analytical, Monte Carlo, BasicSimulator, and ideal Aer workflows do not require an IBM account. Existing IBM counts and metadata can be processed entirely offline from `data/ibm_hardware_existing/`. IBM Runtime connection and hardware submission are opt-in operations and are not triggered by the default validation workflow.

## Data lineage

The main numerical tables are in `data/numerical_experiments/`. Local circuit-consistency tables are in `data/local_reference/`. Existing hardware records are preserved in `data/ibm_hardware_existing/`. `Supplementary_Data_Tables.xlsx` consolidates the main CSV tables without replacing the machine-readable source files.

The sampling and key-allocation trace files omit raw key bits and provide machine-readable cardinality, single-consumption, and deterministic-seed checks. The protocol workflow never requires an IBM account.
