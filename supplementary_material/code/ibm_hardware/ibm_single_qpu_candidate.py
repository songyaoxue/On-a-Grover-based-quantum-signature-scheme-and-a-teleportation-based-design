#!/usr/bin/env python3
"""Maximum-feasible complete protocol-core candidate for one IBM QPU.

This circuit represents Alice, Bob, and Trent with separate logical registers on one
backend.  It implements three message preparations, three explicit Bell resources,
three coherent teleportation stages, duplicated encrypted Bell-outcome records,
strengthened-QOTP protection of the Trent reference copy, Trent/Bob swap tests, and
an explicit post-processed final decision.  It is not a networked three-QPU deployment,
does not implement QKD/authentication/arbitration, and implements one comparison copy
per circuit execution (lambda=1).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.qasm3 import dumps as qasm3_dumps
from qiskit.transpiler import generate_preset_pass_manager

try:
    from qiskit_aer import AerSimulator
except ImportError:
    AerSimulator = None

try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
except ImportError:
    QiskitRuntimeService = None
    SamplerV2 = None


X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
T_STRENGTHENED = np.sqrt(1j / 3) * (X - Y + Z)

KEYS = {
    "K_AT_p3": "0101",
    "K_AT_X1_bell_z": "0011",
    "K_AT_X1_bell_x": "1100",
    "K_AT_X1_comp_z": "0110",
    "K_AT_X1_comp_x": "1001",
    "K_BT_X2_bell_z": "1010",
    "K_BT_X2_bell_x": "0101",
    "K_BT_X2_comp_z": "1110",
    "K_BT_X2_comp_x": "0001",
    "K_BT_X3_bell_z": "1000",
    "K_BT_X3_bell_x": "0111",
    "K_BT_X3_comp_z": "0010",
    "K_BT_X3_comp_x": "1101",
}


def encryption_unitary(key4: str) -> np.ndarray:
    if len(key4) != 4 or set(key4) - {"0", "1"}:
        raise ValueError("Each strengthened-QOTP key block must contain four bits.")
    a, b, c, d = map(int, key4)
    return (
        np.linalg.matrix_power(X, a)
        @ np.linalg.matrix_power(Z, b)
        @ T_STRENGTHENED
        @ np.linalg.matrix_power(X, c)
        @ np.linalg.matrix_power(Z, d)
    )


def append_qotp_roundtrip(qc: QuantumCircuit, qubit, key4: str, label: str) -> None:
    unitary = encryption_unitary(key4)
    qc.unitary(unitary, [qubit], label=f"{label}_enc")
    qc.unitary(unitary.conj().T, [qubit], label=f"{label}_dec")


def prepare_state(qc: QuantumCircuit, qubit, state: str) -> None:
    if state == "1":
        qc.x(qubit)
    elif state == "+":
        qc.h(qubit)
    elif state == "-":
        qc.x(qubit)
        qc.h(qubit)
    elif state != "0":
        raise ValueError("input_state must be one of 0, 1, +, -")


def return_to_zero_basis(qc: QuantumCircuit, qubit, state: str) -> None:
    if state in {"+", "-"}:
        qc.h(qubit)
    if state in {"1", "-"}:
        qc.x(qubit)


def prepare_bell_pair(qc: QuantumCircuit, sender, receiver, label: str) -> None:
    qc.h(sender)
    qc.cx(sender, receiver)
    qc.barrier(label=f"I2_{label}")


def coherent_teleport_with_duplicate_records(
    qc: QuantumCircuit,
    message,
    sender,
    receiver,
    bell_record,
    comp_record,
    key_prefix: str,
    stage: str,
) -> None:
    """Defer Bell measurements, coherently copy outcomes, and apply corrections."""
    qc.barrier(label=f"{stage}_Bell_transform")
    qc.cx(message, sender)
    qc.h(message)

    # Bell outcome ordering is (z outcome, x outcome) = (message, sender).
    for target in (bell_record[0], comp_record[0]):
        qc.cx(message, target)
    for target in (bell_record[1], comp_record[1]):
        qc.cx(sender, target)

    for suffix, qubit in (("bell_z", bell_record[0]), ("bell_x", bell_record[1]),
                           ("comp_z", comp_record[0]), ("comp_x", comp_record[1])):
        append_qotp_roundtrip(qc, qubit, KEYS[f"{key_prefix}_{suffix}"], f"{stage}_{suffix}")

    # Deferred-measurement form of X^x Z^z receiver correction.
    qc.cx(sender, receiver)
    qc.cz(message, receiver)
    qc.barrier(label=f"{stage}_receiver_corrected")


def append_swap_test(qc: QuantumCircuit, ancilla, left, right, stage: str) -> None:
    qc.barrier(label=f"{stage}_swap_test")
    qc.h(ancilla)
    qc.cswap(ancilla, left, right)
    qc.h(ancilla)


def build_complete_single_qpu_protocol(input_state: str = "+") -> QuantumCircuit:
    alice = QuantumRegister(3, "alice_msg")  # p1, p2, p3
    ab = QuantumRegister(2, "bell_AB")
    bt = QuantumRegister(2, "bell_BT")
    tb = QuantumRegister(2, "bell_TB")
    verify = QuantumRegister(2, "verify")  # Trent and Bob swap ancillas
    x1b = QuantumRegister(2, "X1_bell")
    x1c = QuantumRegister(2, "X1_comp")
    x2b = QuantumRegister(2, "X2_bell")
    x2c = QuantumRegister(2, "X2_comp")
    x3b = QuantumRegister(2, "X3_bell")
    x3c = QuantumRegister(2, "X3_comp")

    swap_bits = ClassicalRegister(2, "swap")
    message_bit = ClassicalRegister(1, "message")
    x1b_bits, x1c_bits = ClassicalRegister(2, "x1b"), ClassicalRegister(2, "x1c")
    x2b_bits, x2c_bits = ClassicalRegister(2, "x2b"), ClassicalRegister(2, "x2c")
    x3b_bits, x3c_bits = ClassicalRegister(2, "x3b"), ClassicalRegister(2, "x3c")

    qc = QuantumCircuit(
        alice, ab, bt, tb, verify, x1b, x1c, x2b, x2c, x3b, x3c,
        swap_bits, message_bit, x1b_bits, x1c_bits, x2b_bits, x2c_bits, x3b_bits, x3c_bits,
        name=f"complete_single_qpu_protocol_{input_state}",
    )

    # I1 is represented by fixed one-use key blocks in metadata; I2 and S1 are explicit.
    for qubit in alice:
        prepare_state(qc, qubit, input_state)
    qc.barrier(label="S1_three_independently_prepared_message_copies")
    prepare_bell_pair(qc, ab[0], ab[1], "AB")
    prepare_bell_pair(qc, bt[0], bt[1], "BT")
    prepare_bell_pair(qc, tb[0], tb[1], "TB")

    # S2-S3: Alice -> Bob, duplicate protected X1 records, and protected p3 reference.
    coherent_teleport_with_duplicate_records(qc, alice[0], ab[0], ab[1], x1b, x1c, "K_AT_X1", "S2_S3")
    p3_unitary = encryption_unitary(KEYS["K_AT_p3"])
    qc.unitary(p3_unitary, [alice[2]], label="S3_E_KAT_p3")

    # S4: Bob -> Trent and duplicate protected X2 records.
    coherent_teleport_with_duplicate_records(qc, ab[1], bt[0], bt[1], x2b, x2c, "K_BT_X2", "S4")

    # S5: Trent decrypts p3 and performs the comparison.
    qc.unitary(p3_unitary.conj().T, [alice[2]], label="S5_D_KAT_p3")
    append_swap_test(qc, verify[0], bt[1], alice[2], "S5_Trent")

    # S6-S7: Trent -> Bob, duplicate protected X3 records, then Bob comparison.
    coherent_teleport_with_duplicate_records(qc, bt[1], tb[0], tb[1], x3b, x3c, "K_BT_X3", "S6")
    append_swap_test(qc, verify[1], tb[1], alice[1], "S7_Bob")

    return_to_zero_basis(qc, tb[1], input_state)
    qc.measure(verify, swap_bits)
    qc.measure(tb[1], message_bit[0])
    qc.measure(x1b, x1b_bits); qc.measure(x1c, x1c_bits)
    qc.measure(x2b, x2b_bits); qc.measure(x2c, x2c_bits)
    qc.measure(x3b, x3b_bits); qc.measure(x3c, x3c_bits)

    qc.metadata = {
        "candidate_type": "complete_single_qpu_protocol_core",
        "input_state": input_state,
        "logical_roles": {"Alice": "alice_msg and AB sender", "Bob": "AB receiver and BT sender", "Trent": "BT receiver and TB sender"},
        "implemented_steps": ["I1_fixed_key_metadata", "I2", "S1", "S2", "S3", "S4", "S5", "S6", "S7"],
        "implemented_checks": ["X1_duplicate_record_consistency", "X2_duplicate_record_consistency", "X3_duplicate_record_consistency", "Trent_swap_test", "Bob_swap_test", "final_message_readout"],
        "lambda": 1,
        "decision_rule": "swap=00 and message=0 and x1b=x1c and x2b=x2c and x3b=x3c",
        "not_implemented": ["physical_node_separation", "inter_QPU_quantum_links", "QKD_execution", "authenticated_session_binding", "dispute_arbitration", "lambda_greater_than_one_in_one_circuit"],
        "security_interpretation": "hardware execution evidence only; not a security proof",
    }
    return qc


def _counts_from_result(result: Any) -> dict[str, int]:
    if hasattr(result, "get_counts"):
        counts = result.get_counts()
        if isinstance(counts, list):
            counts = counts[0]
        return {str(key): int(value) for key, value in counts.items()}
    if hasattr(result, "data") and hasattr(result.data, "keys"):
        register_names = list(result.data.keys())
        bit_arrays = [getattr(result.data, name) for name in register_names]
        if bit_arrays and all(hasattr(value, "get_bitstrings") for value in bit_arrays):
            shots = [value.get_bitstrings() for value in bit_arrays]
            if len({len(values) for values in shots}) != 1:
                raise RuntimeError("Runtime registers contain different shot counts.")
            # Match Qiskit's conventional count-key display: latest register first.
            return dict(Counter(" ".join(values[index] for values in reversed(shots)) for index in range(len(shots[0]))))
    for name in dir(result.data):
        if name.startswith("_"):
            continue
        value = getattr(result.data, name)
        if hasattr(value, "get_counts"):
            return {str(key): int(count) for key, count in value.get_counts().items()}
    raise RuntimeError("No result counts were found.")


def parse_register_key(key: str) -> dict[str, str]:
    fields = key.split()
    # Qiskit renders registers in reverse creation order.
    names = ["x3c", "x3b", "x2c", "x2b", "x1c", "x1b", "message", "swap"]
    if len(fields) != len(names):
        raise ValueError(f"Unexpected count key layout: {key!r}")
    return dict(zip(names, fields))


def is_success_key(key: str) -> bool:
    item = parse_register_key(key)
    return (
        item["swap"] == "00"
        and item["message"] == "0"
        and item["x1b"] == item["x1c"]
        and item["x2b"] == item["x2c"]
        and item["x3b"] == item["x3c"]
    )


def summarize_counts(counts: dict[str, int]) -> dict[str, Any]:
    shots = sum(counts.values())
    successes = sum(count for key, count in counts.items() if is_success_key(key))
    return {
        "shots": shots,
        "success_count": successes,
        "complete_core_acceptance_probability": successes / shots,
        "counts_json": json.dumps(counts, sort_keys=True),
    }


def component_metrics(counts: dict[str, int]) -> list[dict[str, Any]]:
    conditions = {
        "both_swap_tests_zero": lambda item: item["swap"] == "00",
        "message_readout_zero": lambda item: item["message"] == "0",
        "X1_duplicate_records_match": lambda item: item["x1b"] == item["x1c"],
        "X2_duplicate_records_match": lambda item: item["x2b"] == item["x2c"],
        "X3_duplicate_records_match": lambda item: item["x3b"] == item["x3c"],
        "complete_core_joint_acceptance": lambda item: is_success_key(" ".join(item[name] for name in ("x3c", "x3b", "x2c", "x2b", "x1c", "x1b", "message", "swap"))),
    }
    shots = sum(counts.values())
    parsed = [(parse_register_key(key), count) for key, count in counts.items()]
    return [
        {"metric": name, "pass_count": sum(count for item, count in parsed if predicate(item)), "shots": shots,
         "probability": sum(count for item, count in parsed if predicate(item)) / shots}
        for name, predicate in conditions.items()
    ]


def circuit_sha256(circuit: QuantumCircuit) -> str:
    return hashlib.sha256(qasm3_dumps(circuit).encode("utf-8")).hexdigest()


def save_circuit_artifacts(circuit: QuantumCircuit, output_dir: Path, prefix: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{prefix}.qasm").write_text(qasm3_dumps(circuit), encoding="utf-8")
    (output_dir / f"{prefix}.txt").write_text(str(circuit.draw("text", fold=180)), encoding="utf-8")


def run_aer(output_dir: Path, shots: int, seed: int) -> dict[str, Any]:
    if AerSimulator is None:
        raise RuntimeError("qiskit-aer is required for Aer validation.")
    rows = []
    for state in ("0", "1", "+", "-"):
        logical = build_complete_single_qpu_protocol(state)
        simulator = AerSimulator()
        compiled = generate_preset_pass_manager(backend=simulator, optimization_level=1, seed_transpiler=seed).run(logical)
        counts = simulator.run(compiled, shots=shots, seed_simulator=seed).result().get_counts()
        summary = summarize_counts(counts)
        rows.append({"input_state": state, "backend": "AerSimulator", "seed": seed, **summary})
        save_circuit_artifacts(logical, output_dir, f"complete_single_qpu_{state.replace('+', 'plus').replace('-', 'minus')}_logical")
    with (output_dir / "aer_complete_protocol_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    return {"rows": rows}


def runtime_service():
    if QiskitRuntimeService is None:
        raise RuntimeError("qiskit-ibm-runtime is not installed.")
    attempts = []
    try:
        return QiskitRuntimeService(name="entropy-project"), "saved_account"
    except Exception as exc:
        attempts.append(f"saved_account:{type(exc).__name__}")
    token = os.environ.get("QISKIT_IBM_TOKEN", "").strip()
    instance = os.environ.get("QISKIT_IBM_CRN", "").strip()
    if token and instance:
        return QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance=instance), "environment"
    raise RuntimeError("No callable IBM account was found (" + ", ".join(attempts) + "). No credential value was printed.")


def submit_ibm(output_dir: Path, backend_name: str, shots: int, state: str, wait: bool) -> dict[str, Any]:
    if SamplerV2 is None:
        raise RuntimeError("qiskit-ibm-runtime is required for submission.")
    service, credential_source = runtime_service()
    backend = service.backend(backend_name)
    logical = build_complete_single_qpu_protocol(state)
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=2, seed_transpiler=20260810)
    isa = pass_manager.run(logical)
    two_qubit = sum(value for gate, value in isa.count_ops().items() if gate in {"cz", "cx", "ecr", "rzz"})
    metadata = {
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "shots": shots,
        "input_state": state,
        "logical_qubits": logical.num_qubits,
        "logical_clbits": logical.num_clbits,
        "logical_depth": logical.depth(),
        "logical_size": logical.size(),
        "logical_qasm_sha256": circuit_sha256(logical),
        "isa_qubits": isa.num_qubits,
        "isa_depth": isa.depth(),
        "isa_size": isa.size(),
        "isa_two_qubit_gates": two_qubit,
        "credential_source": credential_source,
        "claim_scope": "complete single-QPU protocol-core candidate; not distributed and not a security proof",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    save_circuit_artifacts(logical, output_dir, "complete_single_qpu_logical")
    save_circuit_artifacts(isa, output_dir, "complete_single_qpu_isa")
    sampler = SamplerV2(mode=backend)
    job = sampler.run([isa], shots=shots)
    metadata["job_id"] = job.job_id()
    (output_dir / "submission_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({key: metadata[key] for key in metadata if key != "credential_source"}, indent=2))
    if wait:
        result = job.result()[0]
        counts = _counts_from_result(result)
        summary = summarize_counts(counts)
        metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
        metadata["status"] = str(job.status())
        metadata.update(summary)
        (output_dir / "raw_counts.json").write_text(json.dumps(counts, indent=2, sort_keys=True), encoding="utf-8")
        with (output_dir / "ibm_complete_protocol_result.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(metadata)); writer.writeheader(); writer.writerow(metadata)
        (output_dir / "submission_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def retrieve_ibm_job(output_dir: Path, job_id: str) -> dict[str, Any]:
    service, credential_source = runtime_service()
    job = service.job(job_id)
    result = job.result()[0]
    counts = _counts_from_result(result)
    summary = summarize_counts(counts)
    metadata_path = output_dir / "submission_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    metadata.update({
        "job_id": job_id,
        "backend": job.backend().name,
        "status": str(job.status()),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "credential_source": credential_source,
        **summary,
    })
    try:
        metadata["runtime_metrics"] = job.metrics()
    except Exception as exc:
        metadata["runtime_metrics_error"] = type(exc).__name__
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "raw_counts.json").write_text(json.dumps(counts, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "submission_metadata.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    csv_row = {key: (json.dumps(value, sort_keys=True, default=str) if isinstance(value, (dict, list)) else value) for key, value in metadata.items() if key != "credential_source"}
    with (output_dir / "ibm_complete_protocol_result.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_row)); writer.writeheader(); writer.writerow(csv_row)
    metrics = component_metrics(counts)
    with (output_dir / "ibm_complete_protocol_component_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics[0])); writer.writeheader(); writer.writerows(metrics)
    print(json.dumps({key: value for key, value in metadata.items() if key not in {"credential_source", "counts_json"}}, indent=2, default=str))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["build", "aer", "submit", "retrieve"], default="build")
    parser.add_argument("--output-dir", type=Path, default=Path("complete_single_qpu_run"))
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=20260810)
    parser.add_argument("--backend", default="ibm_fez")
    parser.add_argument("--input-state", choices=["0", "1", "+", "-"], default="+")
    parser.add_argument("--confirm-submit", action="store_true")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--job-id")
    args = parser.parse_args()

    if args.mode == "build":
        circuit = build_complete_single_qpu_protocol(args.input_state)
        save_circuit_artifacts(circuit, args.output_dir, "complete_single_qpu_logical")
        print(json.dumps({"qubits": circuit.num_qubits, "clbits": circuit.num_clbits, "depth": circuit.depth(), "size": circuit.size(), "qasm_sha256": circuit_sha256(circuit), "metadata": circuit.metadata}, indent=2))
    elif args.mode == "aer":
        print(json.dumps(run_aer(args.output_dir, args.shots, args.seed), indent=2))
    elif args.mode == "submit":
        if not args.confirm_submit:
            raise RuntimeError("IBM submission requires --confirm-submit.")
        submit_ibm(args.output_dir, args.backend, args.shots, args.input_state, args.wait)
    else:
        if not args.job_id:
            raise RuntimeError("Retrieval requires --job-id.")
        retrieve_ibm_job(args.output_dir, args.job_id)


if __name__ == "__main__":
    main()
