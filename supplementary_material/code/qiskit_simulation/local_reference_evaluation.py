"""Offline local validation for the organized verification code."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicSimulator
from qiskit.quantum_info import Statevector, partial_trace, state_fidelity
from qiskit_aer import AerSimulator

from qiskit_protocol_reference import (
    build_composed_staged_emulation_candidate,
    coherent_teleportation,
    composed_candidate_expected_outputs,
    prepare_named_state,
    success_probability_from_counts,
)
from verification_experiment_suite import SEED, fidelity, write_rows


VALIDATION_STATES = ("0", "1", "+", "-", "i+", "i-")
COMPOSED_STATES = ("0", "1", "+", "-", "i+", "i-", "global_phase_i+")
STAGES = ("S2", "S4", "S6")


def named_statevector(label: str) -> np.ndarray:
    if label == "0":
        return np.array([1, 0], dtype=complex)
    if label == "1":
        return np.array([0, 1], dtype=complex)
    if label == "+":
        return np.array([1, 1], dtype=complex) / np.sqrt(2)
    if label == "-":
        return np.array([1, -1], dtype=complex) / np.sqrt(2)
    if label == "i+":
        return np.array([1, 1j], dtype=complex) / np.sqrt(2)
    if label == "i-":
        return np.array([1, -1j], dtype=complex) / np.sqrt(2)
    raise ValueError(f"unsupported validation state: {label}")


def coherent_chain_fidelity(input_state: str, rounds: int) -> float:
    if rounds not in (1, 2, 3):
        raise ValueError("rounds must be 1, 2, or 3")
    qc = QuantumCircuit(1 + 2 * rounds)
    prepare_named_state(qc, 0, input_state)
    for round_index in range(rounds):
        sender = 1 + 2 * round_index
        receiver = sender + 1
        qc.h(sender)
        qc.cx(sender, receiver)
        source = 0 if round_index == 0 else 2 * round_index
        coherent_teleportation(qc, source, sender, receiver, STAGES[round_index])
    state = Statevector.from_instruction(qc)
    receiver = 2 * rounds
    reduced = partial_trace(state, [q for q in range(qc.num_qubits) if q != receiver])
    return float(np.clip(state_fidelity(reduced, named_statevector(input_state)), 0.0, 1.0))


def conditioned_outcome_fidelities(input_state: str) -> dict[str, float]:
    """Exact Bell-outcome branches with X^b then Z^a receiver corrections."""
    target = named_statevector(input_state)
    qc = QuantumCircuit(3)
    prepare_named_state(qc, 0, input_state)
    qc.h(1)
    qc.cx(1, 2)
    qc.cx(0, 1)
    qc.h(0)
    tensor = np.asarray(Statevector.from_instruction(qc)).reshape(2, 2, 2)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)
    results = {}
    for message_bit in (0, 1):
        for sender_bit in (0, 1):
            receiver = tensor[:, sender_bit, message_bit]
            norm = np.linalg.norm(receiver)
            if norm <= 0:
                raise RuntimeError("zero-probability teleportation branch")
            receiver = receiver / norm
            if sender_bit:
                receiver = X @ receiver
            if message_bit:
                receiver = Z @ receiver
            results[f"{message_bit}{sender_bit}"] = fidelity(target, receiver)
    return results


def generate_teleportation_regression(path: Path) -> None:
    rows = []
    for state_name in VALIDATION_STATES:
        conditioned = conditioned_outcome_fidelities(state_name)
        phase_fidelity = fidelity(named_statevector(state_name), np.exp(1j * 0.731) * named_statevector(state_name))
        for rounds, stage in enumerate(STAGES, start=1):
            rows.append(
                {
                    "input_state": state_name,
                    "stage": stage,
                    "sequential_rounds": rounds,
                    "coherent_deferred_measurement_fidelity": coherent_chain_fidelity(state_name, rounds),
                    "measurement_conditioned_min_fidelity": min(conditioned.values()),
                    "measurement_conditioned_branch_fidelities_json": json.dumps(conditioned, sort_keys=True),
                    "global_phase_invariance_fidelity": phase_fidelity,
                    "expected_fidelity": 1.0,
                }
            )
    write_rows(path, rows)


def _candidate_for_label(label: str):
    if label == "global_phase_i+":
        circuit = build_composed_staged_emulation_candidate("i+")
        circuit.global_phase += math.pi / 3
        circuit.metadata = dict(circuit.metadata)
        circuit.metadata["input_state"] = label
        return circuit, "i+"
    return build_composed_staged_emulation_candidate(label), label


def generate_composed_candidate_reference(path: Path, shots: int = 4096) -> None:
    rows = []
    engines = (("BasicSimulator", BasicSimulator()), ("AerSimulator-ideal", AerSimulator()))
    for engine_index, (engine_name, backend) in enumerate(engines):
        for state_index, label in enumerate(COMPOSED_STATES):
            for m in (1, 2, 4, 8):
                instance_probabilities = []
                instance_counts = []
                valid_outputs = None
                for j in range(m):
                    circuit, semantic_label = _candidate_for_label(label)
                    valid_outputs = composed_candidate_expected_outputs(semantic_label)
                    seed = SEED + engine_index * 100_000 + state_index * 1_000 + m * 10 + j
                    executable = transpile(circuit, backend, optimization_level=1, seed_transpiler=seed)
                    counts = backend.run(executable, shots=shots, seed_simulator=seed).result().get_counts()
                    instance_counts.append(counts)
                    instance_probabilities.append(success_probability_from_counts(counts, valid_outputs))
                logical_probability = float(np.prod(instance_probabilities))
                dominant_probability = float(np.prod([max(item.values()) / shots for item in instance_counts]))
                rows.append(
                    {
                        "engine": engine_name,
                        "input_state": label,
                        "m": m,
                        "shots_per_instance": shots,
                        "circuit_instances": m,
                        "valid_expected_outputs": json.dumps(sorted(valid_outputs)),
                        "expected_measurement_distribution": json.dumps({value: 1.0 for value in sorted(valid_outputs)}),
                        "dominant_output_probability": dominant_probability,
                        "logical_success_probability": logical_probability,
                        "absolute_difference_between_metrics": abs(logical_probability - dominant_probability),
                        "relative_difference_between_metrics": abs(logical_probability - dominant_probability) / dominant_probability if dominant_probability else math.nan,
                        "interpretation": "Logical success is evaluated over the input-dependent valid-output set; the dominant output is a separate diagnostic.",
                        "counts_per_instance_json": json.dumps(instance_counts, sort_keys=True),
                    }
                )
    write_rows(path, rows)
