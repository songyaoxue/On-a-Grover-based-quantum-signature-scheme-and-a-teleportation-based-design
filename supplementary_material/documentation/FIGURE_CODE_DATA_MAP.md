# Figure Code Data Map

| Figure | Source data | Responsible code | Scope |
|---|---|---|---|
| Figure 6 protocol batch | `data/numerical_experiments/figure6_source_data/panel_a_swap_test.csv`; `panel_b_protocol_acceptance.csv`; `panel_c_alice_repudiation.csv`; `panel_d_resource_scaling.csv` | `code/qiskit_simulation/verification_experiment_suite.py`; `resource_operation_ledger.py` | Panel (b) uses one physical-copy batch; panel (d) uses the step-derived batch ledger |
| Figure 7 hardware scope | `data/numerical_experiments/figure7_confidence_intervals.csv`; `data/ibm_hardware_existing/*.csv`; `raw_counts.json` | `code/qiskit_simulation/verification_experiment_suite.py`; `code/ibm_hardware/ibm_hardware_result_analysis.py`; `ibm_offline_analysis.py` | Circuit-level evidence, direct composed candidate `m=1`; not the full physical-copy batch |
| Repeated Swap-Test detection | `data/numerical_experiments/swap_test_detection.csv` | `code/qiskit_simulation/verification_experiment_suite.py` | Analytical and Monte Carlo results for six fidelities |
| High-fidelity Swap-Test detection | `data/numerical_experiments/swap_test_detection.csv` | `code/qiskit_simulation/verification_experiment_suite.py` | Diagnostic for `F=0.9` and `F=0.99` |
| Bob attack detection versus fidelity | `data/numerical_experiments/bob_attack_fidelity_detection.csv` | `code/qiskit_simulation/verification_experiment_suite.py` | State-level fidelity diagnostic |
