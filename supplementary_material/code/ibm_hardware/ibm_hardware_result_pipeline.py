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
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
except ImportError:  # Offline plotting and circuit construction do not need Runtime.
    QiskitRuntimeService = None
    SamplerV2 = None


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
    elif input_state == '-':
        qc.x(0)
        qc.h(0)
    for a, b in ((1, 2), (3, 4), (5, 6)):
        qc.h(a)
        qc.cx(a, b)
    coherent_teleportation(qc, 0, 1, 2, 'S2')
    coherent_teleportation(qc, 2, 3, 4, 'S4')
    coherent_teleportation(qc, 4, 5, 6, 'S6')
    if input_state in {'+', '-'}:
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
    q = QuantumRegister(9, 'candidate')
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
    qc.metadata = {'candidate_type': 'faithful_v7_three_explicit_bell_resources', 'input_state': input_state, 'valid_expected_outputs': ['100'] if input_state in {'1', '-'} else ['000'], 'measurement_order': 'out[2] out[1] out[0]', 'success_definition': 'sum over valid expected outputs', 'paper_resource_qubits': 9, 'swap_ancillas': 'reuse of consumed/dead measured-stage wires', 'not_implemented': ['QKD', 'authentication', 'network separation', 'abstract arbitration']}
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
    qc.metadata = {'candidate_type': 'optimized_staged_reset_reuse', 'input_state': input_state, 'valid_expected_outputs': ['100'] if input_state in {'1', '-'} else ['000'], 'measurement_order': 'out[2] out[1] out[0]', 'success_definition': 'sum over valid expected outputs', 'not_paper_resource_count': True}
    return qc


# 8. IBM Runtime utilities
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
JOB_INDEX = PACKAGE_ROOT / "data/ibm_hardware_existing/ibm_job_index.csv"


def runtime_service() -> QiskitRuntimeService:
    if QiskitRuntimeService is None:
        raise RuntimeError('qiskit-ibm-runtime is required only for online retrieval/submission modes')
    return QiskitRuntimeService(name="entropy-project")


def available_backends(service: QiskitRuntimeService):
    rows = []
    for backend in service.backends(operational=True, simulator=False):
        status = backend.status()
        rows.append({"backend": backend.name, "qubits": backend.num_qubits, "operational": status.operational, "pending_jobs": status.pending_jobs})
    return sorted(rows, key=lambda row: (row["pending_jobs"], -row["qubits"]))


def select_backend(service: QiskitRuntimeService, name: str = "ibm_fez"):
    backend = service.backend(name)
    if getattr(backend.configuration(), "simulator", True):
        raise RuntimeError("A real QPU is required.")
    return backend


def transpile_for_backend(circuit: QuantumCircuit, backend, optimization_level: int = 2):
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=optimization_level)
    return pass_manager.run(circuit)


def extract_counts(pub_result) -> dict[str, int]:
    for name in dir(pub_result.data):
        if name.startswith("_"):
            continue
        value = getattr(pub_result.data, name)
        if hasattr(value, "get_counts"):
            return dict(value.get_counts())
    raise RuntimeError("No classical result register with get_counts() was found.")


def wilson_interval(successes: int, shots: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = successes / shots
    denominator = 1 + z * z / shots
    center = (p + z * z / (2 * shots)) / denominator
    half = z * sqrt(p * (1 - p) / shots + z * z / (4 * shots * shots)) / denominator
    return center - half, center + half


def read_job_index(path: Path = JOB_INDEX) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def retrieve_existing_jobs(output_csv: Path) -> None:
    service = runtime_service(); rows = []
    for record in read_job_index():
        job = service.job(record["job_id"]); result = job.result()
        rows.append({"job_id": record["job_id"], "backend": record["backend"], "shots": record["shots"], "status": str(job.status()), "pub_count": len(result)})
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def submit_one_candidate(shots: int, backend_name: str, confirm: bool) -> str:
    if not confirm:
        raise RuntimeError("Submission requires both --submit and --confirm-submit.")
    service = runtime_service(); backend = select_backend(service, backend_name)
    circuit = build_composed_staged_emulation_candidate(); circuit.name = "composed_staged_emulation_candidate"
    isa = transpile_for_backend(circuit, backend, optimization_level=2)
    two_qubit = sum(count for name, count in isa.count_ops().items() if name in {"cz", "cx", "ecr", "rzz"})
    print(json.dumps({"backend": backend.name, "shots": shots, "qubits": isa.num_qubits, "depth": isa.depth(), "size": isa.size(), "two_qubit_gates": two_qubit}, indent=2))
    sampler = SamplerV2(mode=backend); job = sampler.run([isa], shots=shots)
    print(job.job_id()); return job.job_id()


def save_probability(counts: dict[str, int], expected: str, output_csv: Path) -> None:
    shots = sum(counts.values()); success = counts.get(expected, 0); low, high = wilson_interval(success, shots)
    row = {"expected": expected, "shots": shots, "success_count": success, "correct_output_probability": success / shots, "wilson_95_low": low, "wilson_95_high": high, "counts_json": json.dumps(counts, sort_keys=True)}
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process existing IBM job results or explicitly submit one circuit candidate.")
    parser.add_argument("--mode", choices=["retrieve_existing_jobs", "list_backends"], default="retrieve_existing_jobs")
    parser.add_argument("--output", type=Path, default=Path("retrieved_jobs.csv"))
    parser.add_argument("--backend", default="ibm_fez"); parser.add_argument("--shots", type=int, default=128)
    parser.add_argument("--submit", action="store_true"); parser.add_argument("--confirm-submit", action="store_true")
    args = parser.parse_args()
    if args.submit:
        submit_one_candidate(args.shots, args.backend, args.confirm_submit)
    elif args.mode == "list_backends":
        print(json.dumps(available_backends(runtime_service()), indent=2))
    else:
        retrieve_existing_jobs(args.output); print(args.output)
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

def generate_ibm_target_circuits(backend_name="ibm_fez", *, connect_ibm=False):
    # This function connects only to obtain the backend target; it never submits a job.
    import os
    if not connect_ibm:
        raise RuntimeError("offline mode is the default; pass connect_ibm=True or --connect-ibm to query a backend target")
    if QiskitRuntimeService is None:
        raise RuntimeError("qiskit-ibm-runtime is required only for explicitly selected IBM online modes")
    root = Path(__file__).resolve().parent
    try:
        service = QiskitRuntimeService(name="entropy-project")
    except Exception:
        # Credentials remain in environment variables and are never written to output.
        service = QiskitRuntimeService(
            channel="ibm_quantum_platform",
            token=os.environ["QISKIT_IBM_TOKEN"],
            instance=os.environ["QISKIT_IBM_CRN"],
        )
    backend = service.backend(backend_name)
    if getattr(backend.configuration(), "simulator", True):
        raise RuntimeError("A real QPU target is required.")
    modular, complete = circuit_collection()
    rows = []
    for group, circuits in (("Modular_Circuits", modular), ("Complete_Circuits", complete)):
        for name, logical in circuits.items():
            pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=1)
            isa = pass_manager.run(logical)
            save_circuit(isa, root / group / name)
            two_qubit = sum(count for gate, count in isa.count_ops().items() if gate in {"cz", "cx", "ecr", "rzz"})
            rows.append({
                "group": group, "circuit": name, "backend": backend.name,
                "simulator": False, "physical_qubits": isa.num_qubits,
                "depth": isa.depth(), "size": isa.size(), "two_qubit_gates": two_qubit,
            })
    with (root / "IBM_Target_Transpilation_Metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


if False and __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate target-transpiled circuit diagrams without submitting a job.")
    parser.add_argument("--backend", default="ibm_fez")
    args = parser.parse_args()
    generate_ibm_target_circuits(args.backend)


# Existing IBM result-data processing and figure generation
import pandas as pd


IBM_DATA_ROOT = PACKAGE_ROOT / "data/ibm_hardware_existing"


def generate_ibm_hardware_figure(output_path: Path) -> None:
    """Plot included IBM results. This function does not connect to IBM or submit jobs."""
    teleportation = pd.read_csv(IBM_DATA_ROOT / "teleportation_hardware.csv")
    qotp = pd.read_csv(IBM_DATA_ROOT / "qotp_hardware.csv")
    swap = pd.read_csv(IBM_DATA_ROOT / "swap_test_hardware.csv")
    aer = pd.read_csv(IBM_DATA_ROOT / "composed_candidate_aer.csv").iloc[0]
    pilot = pd.read_csv(IBM_DATA_ROOT / "composed_candidate_pilot.csv").iloc[0]
    final = pd.read_csv(IBM_DATA_ROOT / "composed_candidate_final.csv").iloc[0]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    axes[0, 0].bar(teleportation["input_state"], teleportation["correct_output_probability"], color="0.35")
    axes[0, 0].set(title="(a) Quantum teleportation", ylabel="Correct-output probability", ylim=(0, 1.05))
    states = ["0", "1", "+", "-"]; positions = np.arange(4); width = 0.18
    keys = sorted(qotp["key"].unique())[:4]
    for index, key in enumerate(keys):
        part = qotp[qotp["key"] == key].set_index("input_state").reindex(states)
        axes[0, 1].bar(positions + (index - 1.5) * width, part["correct_output_probability"], width, label=f"K={int(key):04d}")
    axes[0, 1].set_xticks(positions, states); axes[0, 1].set(title="(b) Strengthened-QOTP roundtrip", ylabel="Correct-output probability", ylim=(0.94, 1.005)); axes[0, 1].legend(fontsize=8)
    cases = ["identical_0_0", "identical_plus_plus", "orthogonal_0_1", "orthogonal_plus_minus", "fixed_overlap_F_0.25"]
    selected = swap[(swap["execution"] == "Final") & (swap["lambda"] == 1)].set_index("case").loc[cases]
    ideal = (1 - selected["fidelity"].to_numpy()) / 2
    axes[1, 0].bar(np.arange(5) - 0.18, ideal, 0.36, label="Ideal", color="0.8", edgecolor="black")
    axes[1, 0].bar(np.arange(5) + 0.18, selected["single_test_detection_probability"], 0.36, label="IBM hardware", color="0.25")
    axes[1, 0].set_xticks(range(5), ["0/0", "+/+", "0/1", "+/-", "F=.25"]); axes[1, 0].set(title="(c) Swap-test verification", ylabel="Single-test detection probability", ylim=(0, 0.65)); axes[1, 0].legend(fontsize=8)
    values = [aer["success_probability"], pilot["success_probability"], final["success_probability"]]
    axes[1, 1].bar(["Aer ideal", "Pilot", "Final"], values, color=["0.75", "0.45", "0.15"])
    axes[1, 1].set(title="(d) Composed staged-emulation candidate", ylabel="Combined correct-output probability", ylim=(0, 1.05))
    fig.suptitle("IBM Quantum hardware results and local Aer reference", fontsize=16); fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for extension in ("pdf", "png", "eps"):
        fig.savefig(output_path.with_suffix("." + extension), dpi=300, bbox_inches="tight")
    plt.close(fig)


def main_complete_ibm_code() -> None:
    parser = argparse.ArgumentParser(description="Process existing IBM results; connection and submission require explicit flags.")
    parser.add_argument("--mode", choices=["plot-existing", "retrieve-existing", "list-backends", "generate-target-circuits"], default="plot-existing")
    parser.add_argument("--output", type=Path, default=Path("ibm_hardware_results"))
    parser.add_argument("--backend", default="ibm_fez"); parser.add_argument("--shots", type=int, default=128)
    parser.add_argument("--connect-ibm", action="store_true", help="Explicitly permit IBM account/backend access; never implies submission.")
    parser.add_argument("--submit", action="store_true"); parser.add_argument("--confirm-submit", action="store_true")
    args = parser.parse_args()
    if args.submit:
        submit_one_candidate(args.shots, args.backend, args.confirm_submit)
    elif args.mode == "retrieve-existing":
        retrieve_existing_jobs(args.output.with_suffix(".csv"))
    elif args.mode == "list-backends":
        print(json.dumps(available_backends(runtime_service()), indent=2))
    elif args.mode == "generate-target-circuits":
        generate_ibm_target_circuits(args.backend, connect_ibm=args.connect_ibm)
    else:
        generate_ibm_hardware_figure(args.output)


if __name__ == "__main__":
    main_complete_ibm_code()
