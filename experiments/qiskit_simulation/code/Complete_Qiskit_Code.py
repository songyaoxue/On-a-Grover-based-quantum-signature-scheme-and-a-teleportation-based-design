"""Complete IBM/Qiskit circuit, retrieval, evaluation, and guarded-submission code."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from math import sqrt
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.qasm3 import dumps as qasm3_dumps
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2


# 1. Bell resources

def build_bell_pair_circuit(name='bell_pair'):
    q = QuantumRegister(2, 'bell')
    qc = QuantumCircuit(q, name=name)
    qc.h(q[0])
    qc.cx(q[0], q[1])
    return qc

def build_three_bell_pair_circuit():
    q = QuantumRegister(6, 'bell')
    qc = QuantumCircuit(q, name='three_v7_bell_pairs')
    for a, b in ((0, 1), (2, 3), (4, 5)):
        qc.h(q[a])
        qc.cx(q[a], q[b])
    qc.metadata = {'pairs': {'AB_S2': [0, 1], 'BT_S4': [2, 3], 'TB_S6': [4, 5]}}
    return qc

# 2. Teleportation

def coherent_teleportation(qc, message, bell_sender, bell_receiver, label):
    qc.barrier(label=f'{label}_Bell_measurement')
    qc.cx(message, bell_sender)
    qc.h(message)
    qc.cx(bell_sender, bell_receiver)
    qc.cz(message, bell_receiver)

def build_teleportation_circuit(input_state='0'):
    qc = QuantumCircuit(3, 1, name=f'teleport_{input_state}')
    if input_state == '1':
        qc.x(0)
    elif input_state == '+':
        qc.h(0)
    elif input_state == '-':
        qc.x(0)
        qc.h(0)
    qc.h(1)
    qc.cx(1, 2)
    coherent_teleportation(qc, 0, 1, 2, 'S2')
    if input_state in {'+', '-'}:
        qc.h(2)
    qc.measure(2, 0)
    return qc

def build_three_teleportation_rounds(input_state='0'):
    qc = QuantumCircuit(7, 1, name='three_teleportation_rounds')
    if input_state == '1':
        qc.x(0)
    elif input_state == '+':
        qc.h(0)
    for a, b in ((1, 2), (3, 4), (5, 6)):
        qc.h(a)
        qc.cx(a, b)
    coherent_teleportation(qc, 0, 1, 2, 'S2')
    coherent_teleportation(qc, 2, 3, 4, 'S4')
    coherent_teleportation(qc, 4, 5, 6, 'S6')
    if input_state == '+':
        qc.h(6)
    qc.measure(6, 0)
    return qc

# 3. Strengthened-QOTP

def append_qotp(qc, qubit, key4, label='E_K'):
    U = encryption_unitary(key4)
    qc.unitary(U, [qubit], label=label)

def append_qotp_inverse(qc, qubit, key4, label='E_K^-1'):
    U = encryption_unitary(key4)
    qc.unitary(U.conj().T, [qubit], label=label)

def build_qotp_roundtrip_circuit(key4='0101', input_state='0'):
    qc = QuantumCircuit(1, 1, name='strengthened_qotp_roundtrip')
    if input_state == '1':
        qc.x(0)
    elif input_state == '+':
        qc.h(0)
    elif input_state == '-':
        qc.x(0)
        qc.h(0)
    append_qotp(qc, 0, key4)
    append_qotp_inverse(qc, 0, key4)
    if input_state in {'+', '-'}:
        qc.h(0)
    qc.measure(0, 0)
    return qc

# 4. Encrypted Bell records

def append_encrypted_record_roundtrip(qc, carrier, key4, record, label):
    if record[1] == '1':
        qc.x(carrier)
    if record[0] == '1':
        qc.z(carrier)
    append_qotp(qc, carrier, key4, f'{label}_encrypt')
    append_qotp_inverse(qc, carrier, key4, f'{label}_decrypt')
    if record[0] == '1':
        qc.z(carrier)
    if record[1] == '1':
        qc.x(carrier)

def build_encrypted_bell_record_circuit(key4='1010', record='01'):
    qc = QuantumCircuit(2, 2, name='encrypted_bell_record_roundtrip')
    qc.h(0)
    qc.cx(0, 1)
    append_encrypted_record_roundtrip(qc, 1, key4, record, 'E_KU_X')
    qc.cx(0, 1)
    qc.h(0)
    qc.measure([0, 1], [0, 1])
    return qc

# 5. Repeated swap tests

def build_repeated_swap_test_circuits(left='0', right='1', lam=8):
    return [build_swap_test_circuit(left, right, name=f'swap_{index + 1}_of_{lam}') for index in range(lam)]

# 6. Staged components

def build_staged_components():
    return {'S2': build_teleportation_circuit(), 'S3_record': build_encrypted_bell_record_circuit(), 'S5_QOTP': build_qotp_roundtrip_circuit(), 'S6': build_teleportation_circuit()}

# 7. Composed staged-emulation candidate

FIXED_KEY = '0101'

def _prepare_message_copies(qc, qubits, input_state):
    for q in qubits:
        if input_state == '1':
            qc.x(q)
        elif input_state == '+':
            qc.h(q)
        elif input_state == '-':
            qc.x(q)
            qc.h(q)

def _swap_test(qc, anc, left, right, label):
    qc.barrier(label=label)
    qc.h(anc)
    qc.cswap(anc, left, right)
    qc.h(anc)

def build_composed_staged_emulation_candidate(input_state='0'):
    q = QuantumRegister(9, 'v7')
    c = ClassicalRegister(3, 'out')
    qc = QuantumCircuit(q, c, name='composed_staged_emulation_candidate')
    _prepare_message_copies(qc, (0, 1, 2), input_state)
    qc.barrier(label='S1_three_message_copies')
    for a, b, label in ((3, 4, 'AB_S2'), (5, 6, 'BT_S4'), (7, 8, 'TB_S6')):
        qc.h(a)
        qc.cx(a, b)
        qc.barrier(label=f'I2_{label}')
    coherent_teleportation(qc, 0, 3, 4, 'S2')
    append_encrypted_record_roundtrip(qc, 3, FIXED_KEY, '01', 'S3_X1_record')
    coherent_teleportation(qc, 4, 5, 6, 'S4')
    append_encrypted_record_roundtrip(qc, 5, FIXED_KEY, '10', 'S4_X2_record')
    qc.reset(0)
    _swap_test(qc, 0, 6, 2, 'S5_swap_test')
    coherent_teleportation(qc, 6, 7, 8, 'S6')
    append_encrypted_record_roundtrip(qc, 7, FIXED_KEY, '11', 'S6_X3_record')
    qc.reset(4)
    _swap_test(qc, 4, 8, 1, 'S7_swap_test')
    if input_state in {'+', '-'}:
        qc.h(8)
    qc.measure(0, 0)
    qc.measure(4, 1)
    qc.measure(8, 2)
    qc.metadata = {'candidate_type': 'faithful_v7_three_explicit_bell_resources', 'success_predicate': 'out=000', 'paper_resource_qubits': 9, 'swap_ancillas': 'reuse of consumed/dead measured-stage wires', 'not_implemented': ['QKD', 'authentication', 'network separation', 'abstract arbitration']}
    return qc

def build_faithful_v7_unitary_reference(input_state='0'):
    qc = QuantumCircuit(11, name='faithful_v7_unitary_reference')
    _prepare_message_copies(qc, (0, 1, 2), input_state)
    for a, b in ((3, 4), (5, 6), (7, 8)):
        qc.h(a)
        qc.cx(a, b)
    coherent_teleportation(qc, 0, 3, 4, 'S2')
    append_encrypted_record_roundtrip(qc, 3, FIXED_KEY, '01', 'S3_X1_record')
    coherent_teleportation(qc, 4, 5, 6, 'S4')
    append_encrypted_record_roundtrip(qc, 5, FIXED_KEY, '10', 'S4_X2_record')
    _swap_test(qc, 9, 6, 2, 'S5_swap_test')
    coherent_teleportation(qc, 6, 7, 8, 'S6')
    append_encrypted_record_roundtrip(qc, 7, FIXED_KEY, '11', 'S6_X3_record')
    _swap_test(qc, 10, 8, 1, 'S7_swap_test')
    if input_state in {'+', '-'}:
        qc.h(8)
    return qc

def build_optimized_staged_candidate(input_state='0'):
    q = QuantumRegister(7, 'opt')
    c = ClassicalRegister(3, 'out')
    qc = QuantumCircuit(q, c, name='optimized_v7_staged_candidate')
    _prepare_message_copies(qc, (0, 1, 2), input_state)
    qc.barrier(label='S1')

    def leg(label):
        qc.h(3)
        qc.cx(3, 4)
        coherent_teleportation(qc, 0, 3, 4, label)
        qc.swap(0, 4)
        qc.reset(3)
        qc.reset(4)
    leg('S2')
    append_encrypted_record_roundtrip(qc, 6, FIXED_KEY, '01', 'S3_record')
    leg('S4')
    qc.reset(5)
    _swap_test(qc, 5, 0, 2, 'S5_swap_test')
    leg('S6')
    qc.reset(4)
    _swap_test(qc, 4, 0, 1, 'S7_swap_test')
    if input_state in {'+', '-'}:
        qc.h(0)
    qc.measure(5, 0)
    qc.measure(4, 1)
    qc.measure(0, 2)
    qc.metadata = {'candidate_type': 'optimized_staged_reset_reuse', 'success_predicate': 'out=000', 'not_paper_resource_count': True}
    return qc
import csv
import matplotlib.pyplot as plt
from qiskit import qasm3, transpile
from qiskit.qasm3 import dumps as qasm3_dumps

# Self-contained matrix definitions used by the strengthened-QOTP circuit.
import numpy as np

X_MATRIX = np.array([[0, 1], [1, 0]], dtype=complex)
Y_MATRIX = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z_MATRIX = np.array([[1, 0], [0, -1]], dtype=complex)
T_STRENGTHENED = np.sqrt(1j / 3) * (X_MATRIX - Y_MATRIX + Z_MATRIX)


def encryption_unitary(key4):
    """Return the one-qubit strengthened-QOTP unitary for a four-bit key block."""
    if len(key4) != 4 or set(key4) - {"0", "1"}:
        raise ValueError("key block must contain four binary digits")
    a, b, c, d = map(int, key4)
    return (
        np.linalg.matrix_power(X_MATRIX, a)
        @ np.linalg.matrix_power(Z_MATRIX, b)
        @ T_STRENGTHENED
        @ np.linalg.matrix_power(X_MATRIX, c)
        @ np.linalg.matrix_power(Z_MATRIX, d)
    )


# Circuit collection used for the modular and complete folders.
def build_swap_test_verification_circuit(left="0", right="1"):
    qc = QuantumCircuit(3, 1, name="swap_test_verification")
    if left == "1":
        qc.x(1)
    elif left == "+":
        qc.h(1)
    elif left == "-":
        qc.x(1); qc.h(1)
    if right == "1":
        qc.x(2)
    elif right == "+":
        qc.h(2)
    elif right == "-":
        qc.x(2); qc.h(2)
    qc.h(0); qc.cswap(0, 1, 2); qc.h(0); qc.measure(0, 0)
    return qc


def build_swap_test_circuit(left="0", right="1", name="swap_test"):
    """Compatibility wrapper used by the repeated swap-test circuit builder."""
    circuit = build_swap_test_verification_circuit(left, right)
    circuit.name = name
    return circuit


def circuit_collection():
    staged = build_staged_components()
    modular = {
        "Bell_Pair": build_bell_pair_circuit(),
        "Three_Bell_Pairs": build_three_bell_pair_circuit(),
        "Teleportation": build_teleportation_circuit(),
        "Three_Teleportation_Rounds": build_three_teleportation_rounds(),
        "Strengthened_QOTP_Roundtrip": build_qotp_roundtrip_circuit(),
        "Encrypted_Bell_Record": build_encrypted_bell_record_circuit(),
        "Swap_Test_Verification": build_swap_test_verification_circuit(),
        "Stage_S2": staged["S2"],
        "Stage_S3_Record": staged["S3_record"],
        "Stage_S5_QOTP": staged["S5_QOTP"],
        "Stage_S6": staged["S6"],
    }
    complete = {
        "Composed_Full_Candidate": build_composed_staged_emulation_candidate(),
        "Optimized_Staged_Candidate": build_optimized_staged_candidate(),
    }
    return modular, complete


def save_circuit(circuit, base_path):
    base_path.parent.mkdir(parents=True, exist_ok=True)
    (base_path.with_suffix(".qasm")).write_text(qasm3_dumps(circuit), encoding="utf-8")
    (base_path.with_suffix(".txt")).write_text(str(circuit.draw("text", fold=160)), encoding="utf-8")
    figure = circuit.draw("mpl", style="iqp", fold=80, idle_wires=False)
    for extension in ("pdf", "png", "svg"):
        figure.savefig(base_path.with_suffix("." + extension), dpi=300 if extension == "png" else None, bbox_inches="tight", facecolor="white")
    plt.close(figure)

def generate_logical_circuits():
    root = Path(__file__).resolve().parent
    modular, complete = circuit_collection()
    for name, circuit in modular.items():
        save_circuit(circuit, root / "Modular_Circuits" / name)
    for name, circuit in complete.items():
        save_circuit(circuit, root / "Complete_Circuits" / name)


if False and __name__ == "__main__":
    generate_logical_circuits()


# Qiskit reference execution and result plotting
from qiskit.providers.basic_provider import BasicSimulator


def _measured_copy(circuit):
    measured = circuit.copy()
    if measured.num_clbits == 0:
        measured.measure_all()
    return measured


def run_qiskit_reference_data(output_csv: Path, shots: int = 1024, seed: int = 20260803) -> None:
    """Run modular and complete circuits with Qiskit's basic reference simulator."""
    backend = BasicSimulator()
    modular, complete = circuit_collection()
    rows = []
    for group, circuits in (("modular", modular), ("complete", complete)):
        for name, logical in circuits.items():
            measured = _measured_copy(logical)
            executable = transpile(measured, backend=backend, optimization_level=0, seed_transpiler=seed)
            counts = backend.run(executable, shots=shots, seed_simulator=seed).result().get_counts()
            rows.append({
                "group": group, "circuit": name, "shots": shots,
                "depth": executable.depth(), "size": executable.size(),
                "dominant_probability": max(counts.values()) / shots,
                "counts_json": json.dumps(counts, sort_keys=True),
            })
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def generate_qiskit_result_figure(input_csv: Path, output_path: Path) -> None:
    rows = list(csv.DictReader(input_csv.open(encoding="utf-8")))
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    ax.bar(range(len(rows)), [float(row["dominant_probability"]) for row in rows], color="0.35")
    ax.set(xticks=range(len(rows)), xticklabels=[row["circuit"] for row in rows],
           ylabel="Dominant-output probability", ylim=(0, 1.05), title="Qiskit reference execution")
    ax.tick_params(axis="x", rotation=65); fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path.with_suffix(".png"), dpi=300); fig.savefig(output_path.with_suffix(".pdf")); plt.close(fig)


def run_complete_qiskit_pipeline(output_dir: Path, shots: int = 1024) -> None:
    generate_logical_circuits()
    data = output_dir / "qiskit_reference_results.csv"
    run_qiskit_reference_data(data, shots)
    generate_qiskit_result_figure(data, output_dir / "qiskit_reference_results")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Qiskit circuits, data, and result figures.")
    parser.add_argument("--output-dir", type=Path, default=Path("qiskit_results"))
    parser.add_argument("--shots", type=int, default=1024)
    arguments = parser.parse_args(); run_complete_qiskit_pipeline(arguments.output_dir, arguments.shots)
