# Code Guide

The code is organized by execution environment. The numerical protocol workflow uses one physical-copy batch with `2*lambda+1` `p1` copies, `lambda` `p2` copies, and `lambda` `p3` copies. Package-local path handling allows the existing IBM data to be read from `data/ibm_hardware_existing/` without access to the manuscript repository.

Complete Word compilations of the Python source are provided as `Supplementary material--Figure_6_Full_Code.docx` and `Supplementary material--Figure_7_Full_Code.docx`. The Figure 7 document combines the complete IBM Aer and IBM hardware source. Each document preserves the complete text and indentation of every included `.py` file.

## Qiskit simulation

- `qiskit_simulation/verification_experiment_suite.py`: main analytical, Monte Carlo, local circuit, data, and figure workflow.
- `qiskit_simulation/verification_experiment_validation.py`: physical-copy, sampling, fresh-key, circuit, and resource regression suite.
- `qiskit_simulation/qiskit_circuit_library.py`: circuit construction utilities.
- `qiskit_simulation/qiskit_protocol_reference.py`: organized protocol and composed-candidate reference.
- `qiskit_simulation/resource_operation_ledger.py`: step-derived resource ledger.
- `qiskit_simulation/local_reference_evaluation.py`: local composed-candidate, teleportation, resource, and offline consistency checks. Its serial composed-candidate rows are circuit-level references, not the physical-copy protocol model.

## IBM Aer simulation

- `ibm_aer_simulation/aer_circuit_generation.py`: Aer-oriented circuit construction.
- `ibm_aer_simulation/aer_complete_pipeline.py`: complete ideal Aer pipeline.
- `ibm_aer_simulation/aer_verification_experiments.py`: focused ideal Aer verification entry point.

## IBM hardware and offline processing

- `ibm_hardware/ibm_offline_analysis.py`: offline computation from included immutable result files.
- `ibm_hardware/ibm_hardware_result_analysis.py`: direct-versus-derived classification, Wilson intervals, and Figure 7 processing.
- `ibm_hardware/ibm_hardware_circuit_generation.py`: circuit-generation and explicitly guarded IBM utilities.
- `ibm_hardware/ibm_hardware_complete_pipeline.py`: complete hardware-oriented pipeline with explicit connection and submission controls.
- `ibm_hardware/ibm_hardware_result_pipeline.py`: result-processing pipeline.
- `ibm_hardware/ibm_single_qpu_candidate.py`: single-QPU circuit candidate.
- `ibm_hardware/ibm_transpilation_artifacts.py`: transpilation artifact utilities.

Ordinary validation and offline processing do not initialize IBM Runtime or submit a job. Online access requires an explicit user-selected mode and valid IBM credentials. The three-Bell-pair circuit modules reproduce the included direct `m=1` circuit-level evidence; they do not define the physical-copy protocol-batch model.
