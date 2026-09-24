# Qiskit Simulation

This directory contains the main local experiment suite, circuit references, physical-copy resource ledger, and validation suite. The protocol-level simulation represents one batch with `2*lambda+1` independent `p1` arrays, `lambda` `p2` arrays, and `lambda` `p3` arrays. Trent and Bob sample their S5 and S7 test subsets uniformly without replacement after all relevant states and records are committed.

Each selected physical pair is compared separately. The phenomenological state-level model `F_eff=(1-noise)F+noise/2` is applied separately to each comparison and is not an Aer or hardware noise model. Fresh key blocks are allocated per encrypted physical object and consumed once. The resource table is generated from the protocol-step and encrypted-object ledgers.

The generic repeated Swap-Test analysis retains `m` as the number of independent comparisons and uses the fidelity-dependent product model. Circuit files implementing the three-Bell-pair composed candidate support the included direct `m=1` circuit-level evidence; they are not the physical-copy batch implementation.

Inputs are defined in the modules and in the included CSV files. Outputs are written only when the corresponding command is explicitly invoked with an output directory. No IBM account is required, and these modules do not submit hardware jobs.

Validation:

```bash
python -m pytest -q verification_experiment_validation.py
```
