"""Continuous protocol-level implementation of I1-I2 and S1-S7."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from math import ceil, comb, exp, floor, log, sqrt
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector


# 1. Shared state and matrix definitions

I = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
T_STRENGTHENED = np.sqrt(1j / 3) * (X - Y + Z)
STATES = {'0': np.array([1, 0], dtype=complex), '1': np.array([0, 1], dtype=complex), '+': np.array([1, 1], dtype=complex) / np.sqrt(2), '-': np.array([1, -1], dtype=complex) / np.sqrt(2)}

def normalized(vector) -> np.ndarray:
    array = np.asarray(vector, dtype=complex)
    return array / np.linalg.norm(array)

def fidelity(left, right) -> float:
    return float(abs(np.vdot(normalized(left), normalized(right))) ** 2)

def tensor(*items) -> np.ndarray:
    out = np.array([1.0 + 0j])
    for item in items:
        out = np.kron(out, np.asarray(item, dtype=complex))
    return out

def pauli_from_record(record: str) -> np.ndarray:
    return {'00': I, '01': X, '10': Z, '11': Z @ X}[record].copy()

@dataclass
class ComparisonRecord:
    stage: str
    fidelity: float
    p_accept_single: float
    p_accept_repeated: float
    outcome_accept: bool
    lambda_repetitions: int
    seed: int
    mode: str

@dataclass
class ProtocolState:
    message_label: str = '+'
    key_at: str = '0101101000111100'
    key_bt: str = '101001011100001110010110'
    key_parts: dict[str, str] = field(default_factory=dict)
    p1: np.ndarray | None = None
    p2: np.ndarray | None = None
    p3: np.ndarray | None = None
    bell_resources: Any = None
    x_records: dict[str, str] = field(default_factory=dict)
    teleportation: dict[str, Any] = field(default_factory=dict)
    encrypted_records: dict[str, Any] = field(default_factory=dict)
    recovered_records: dict[str, str] = field(default_factory=dict)
    p3_encrypted: np.ndarray | None = None
    p3_recovered: np.ndarray | None = None
    trent_state: np.ndarray | None = None
    bob_state: np.ndarray | None = None
    comparisons: list[ComparisonRecord] = field(default_factory=list)
    trent_accept: bool = False
    bob_accept: bool = False
    final_accept: bool = False
    audit_trail: list[dict[str, Any]] = field(default_factory=list)

    def log(self, stage: str, **details) -> None:
        self.audit_trail.append({'stage': stage, **details})

# 2. Key partition

def partition_keys(key_at: str, key_bt: str) -> dict[str, str]:
    if len(key_at) != 16 or set(key_at) - {'0', '1'}:
        raise ValueError('K_AT must be 16 bits')
    if len(key_bt) != 24 or set(key_bt) - {'0', '1'}:
        raise ValueError('K_BT must be 24 bits')
    return {'K_AT_prime': key_at[:4], 'K_AT_double': key_at[4:8], 'K_AT_triple': key_at[8:16], 'K_BT_prime': key_bt[:4], 'K_BT_double': key_bt[4:12], 'K_BT_triple': key_bt[12:16], 'K_BT_fourth': key_bt[16:24]}

# 3. Three Bell resources

def bell_phi_plus() -> np.ndarray:
    return np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)

@dataclass
class BellPairResource:
    pair_id: str
    sender: str
    receiver: str
    stage: str
    state: np.ndarray
    consumed: bool = False
    measurement_bits: str | None = None
    correction: str | None = None

@dataclass
class BellResources:
    alice_bob_pair: BellPairResource
    bob_trent_pair: BellPairResource
    trent_bob_pair: BellPairResource

def prepare_bell_pair(pair_id: str, sender: str, receiver: str, stage: str) -> BellPairResource:
    return BellPairResource(pair_id, sender, receiver, stage, bell_phi_plus())

def prepare_three_bell_pairs() -> BellResources:
    return BellResources(prepare_bell_pair('AB_S2', 'Alice', 'Bob', 'S2'), prepare_bell_pair('BT_S4', 'Bob', 'Trent', 'S4'), prepare_bell_pair('TB_S6', 'Trent', 'Bob', 'S6'))

# 4. Strengthened-QOTP

def encryption_unitary(key4: str) -> np.ndarray:
    if len(key4) != 4 or set(key4) - {'0', '1'}:
        raise ValueError('key block must be 4 bits')
    a, b, c, d = map(int, key4)
    return np.linalg.matrix_power(X, a) @ np.linalg.matrix_power(Z, b) @ T_STRENGTHENED @ np.linalg.matrix_power(X, c) @ np.linalg.matrix_power(Z, d)

def encrypt_state(state, key4: str) -> np.ndarray:
    return encryption_unitary(key4) @ np.asarray(state, dtype=complex)

def decrypt_state(state, key4: str) -> np.ndarray:
    return encryption_unitary(key4).conj().T @ np.asarray(state, dtype=complex)

def encrypt_two_qubit_state(state, key8: str) -> np.ndarray:
    if len(key8) != 8:
        raise ValueError('two-qubit record key must be 8 bits')
    return tensor(encryption_unitary(key8[:4]), encryption_unitary(key8[4:])) @ np.asarray(state, dtype=complex)

def decrypt_two_qubit_state(state, key8: str) -> np.ndarray:
    unitary = tensor(encryption_unitary(key8[:4]), encryption_unitary(key8[4:]))
    return unitary.conj().T @ np.asarray(state, dtype=complex)

# 5. Teleportation

@dataclass
class TeleportationResult:
    stage: str
    pair_id: str
    measurement_bits: str
    branch_probability: float
    receiver_before_correction: np.ndarray
    receiver_after_correction: np.ndarray
    correction: str
    fidelity: float

def teleportation_branch(message, bell_resource, record: str, stage: str) -> TeleportationResult:
    if record not in {'00', '01', '10', '11'}:
        raise ValueError('record must be two bits')
    qc = QuantumCircuit(3)
    qc.initialize(normalized(message), 0)
    qc.h(1)
    qc.cx(1, 2)
    qc.cx(0, 1)
    qc.h(0)
    sv = Statevector.from_instruction(qc).data
    m0, m1 = map(int, record)
    receiver = np.array([sv[m0 + 2 * m1], sv[m0 + 2 * m1 + 4]], dtype=complex)
    probability = float(np.vdot(receiver, receiver).real)
    receiver = normalized(receiver)
    correction = pauli_from_record(record)
    corrected = correction @ receiver
    bell_resource.consumed = True
    bell_resource.measurement_bits = record
    bell_resource.correction = record
    return TeleportationResult(stage, bell_resource.pair_id, record, probability, receiver, corrected, record, fidelity(message, corrected))

def alice_to_bob_teleportation(message, resources, record='01'):
    return teleportation_branch(message, resources.alice_bob_pair, record, 'S2')

def bob_to_trent_teleportation(message, resources, record='10'):
    return teleportation_branch(message, resources.bob_trent_pair, record, 'S4')

def trent_to_bob_teleportation(message, resources, record='11'):
    return teleportation_branch(message, resources.trent_bob_pair, record, 'S6')

# 6. Repeated swap-test verification

def swap_test_accept_probability(F: float) -> float:
    value = float(F)
    if not -1e-12 <= value <= 1.0 + 1e-12:
        raise ValueError('fidelity must lie in [0, 1]')
    value = min(1.0, max(0.0, value))
    return (1 + value) / 2

def repeated_swap_test_accept_probability(F: float, lam: int) -> float:
    if int(lam) != lam or lam < 1:
        raise ValueError('lambda must be a positive integer')
    return swap_test_accept_probability(F) ** int(lam)

def repeated_swap_test_detection_probability(F: float, lam: int) -> float:
    return 1 - repeated_swap_test_accept_probability(F, lam)

def sample_repeated_swap_test(F: float, lam: int, rng) -> bool:
    return bool(rng.random() < repeated_swap_test_accept_probability(F, lam))

def false_acceptance_upper_bound(delta: float, lam: int) -> float:
    """Conditional bound when F(rho_hon, rho_adv) <= 1-delta."""
    if not 0.0 < delta <= 1.0:
        raise ValueError("delta must lie in (0, 1].")
    if int(lam) != lam or lam < 1:
        raise ValueError("lambda must be a positive integer.")
    return (1.0 - delta / 2.0) ** int(lam)

def repetitions_for_target_error(delta: float, target_error: float) -> int:
    """Smallest integer lambda making the fidelity-gap bound <= target_error."""
    if not 0.0 < delta <= 1.0:
        raise ValueError("delta must lie in (0, 1].")
    if not 0.0 < target_error < 1.0:
        raise ValueError("target_error must lie in (0, 1).")
    return ceil(log(target_error) / log(1.0 - delta / 2.0))

def compare_states(left, right, lam, rng, mode='repeated_swap_test'):
    F = fidelity(left, right)
    single = swap_test_accept_probability(F)
    repeated = single ** lam
    if mode in {'classical_statevector_reference', 'exact_reference'}:
        accepted = F > 1 - 1e-10
    elif mode == 'repeated_swap_test':
        accepted = sample_repeated_swap_test(F, lam, rng)
    else:
        raise ValueError(f'unknown comparison mode: {mode}')
    return (F, single, repeated, accepted)

def build_swap_test_circuit(left_label='0', right_label='0', name='swap_test'):
    q = QuantumRegister(3, 'q')
    c = ClassicalRegister(1, 'accept')
    qc = QuantumCircuit(q, c, name=name)
    for idx, label in ((1, left_label), (2, right_label)):
        if label == '1':
            qc.x(idx)
        elif label == '+':
            qc.h(idx)
        elif label == '-':
            qc.x(idx)
            qc.h(idx)
    qc.h(0)
    qc.cswap(0, 1, 2)
    qc.h(0)
    qc.measure(0, 0)
    return qc

# 7. Encrypted records

def record_basis_state(record: str) -> np.ndarray:
    out = np.zeros(4, dtype=complex)
    out[int(record, 2)] = 1
    return out

def encrypt_computational_record(record: str, key8: str) -> np.ndarray:
    return encrypt_two_qubit_state(record_basis_state(record), key8)

def recover_computational_record(cipher, key8: str) -> str:
    state = decrypt_two_qubit_state(cipher, key8)
    return f'{int(np.argmax(abs(state) ** 2)):02b}'

def encrypted_bell_record(record: str, key4: str) -> np.ndarray:
    operator = encryption_unitary(key4) @ pauli_from_record(record)
    return tensor(I, operator) @ bell_phi_plus()

def recover_bell_record(cipher, key4: str) -> str:
    for record in ('00', '01', '10', '11'):
        if fidelity(cipher, encrypted_bell_record(record, key4)) > 1 - 1e-10:
            return record
    return 'UNRESOLVED'

# 8. Attack injection used by protocol execution

def _flip_first(cipher):
    array = np.asarray(cipher, dtype=complex)
    return tensor(X, np.eye(2)) @ array if array.size == 4 else array[::-1].copy()

def apply_attack(state, name: str, stage: str):
    if name == 'none':
        return state
    if stage == 'after_s3':
        if name == 'tamper_X1_bell_record':
            state.encrypted_records['X1_bell'] = _flip_first(state.encrypted_records['X1_bell'])
        elif name == 'tamper_X1_encrypted_record':
            state.encrypted_records['X1_comp'] = _flip_first(state.encrypted_records['X1_comp'])
        elif name == 'tamper_p2':
            state.p2 = Z @ state.p2
        elif name == 'tamper_p3':
            state.p3_encrypted = state.p3_encrypted[::-1].copy()
        # Deprecated alias retained only for callers of the pre-revision API.
        elif name in {'fixed_state_ciphertext_replacement', 'impersonation_attempt'}:
            state.p3_encrypted = np.array([1, 0], dtype=complex)
    if stage == 'after_s4':
        if name == 'tamper_X2_bell_record':
            state.encrypted_records['X2_bell'] = _flip_first(state.encrypted_records['X2_bell'])
        elif name == 'tamper_X2_encrypted_record':
            state.encrypted_records['X2_comp'] = _flip_first(state.encrypted_records['X2_comp'])
        # Deprecated alias retained only for callers of the pre-revision API.
        elif name in {'cross_stage_record_substitution', 'replay_mismatched_record'}:
            state.encrypted_records['X2_comp'] = state.encrypted_records['X1_comp'].copy()
    if stage == 'after_s6':
        if name == 'tamper_X3_bell_record':
            state.encrypted_records['X3_bell'] = _flip_first(state.encrypted_records['X3_bell'])
        elif name == 'tamper_X3_encrypted_record':
            state.encrypted_records['X3_comp'] = _flip_first(state.encrypted_records['X3_comp'])
    state.log('ATTACK', name=name, injection_stage=stage)
    return state

# 9. Protocol steps I1-I2

def execute_i1(state):
    state.key_parts = partition_keys(state.key_at, state.key_bt)
    state.log('I1', key_at_bits=16, key_bt_bits=24, partitions={k: len(v) for k, v in state.key_parts.items()})
    return state

def execute_i2(state):
    state.bell_resources = prepare_three_bell_pairs()
    state.log('I2', pairs=['AB_S2', 'BT_S4', 'TB_S6'], static_bell_qubits=6)
    return state

# 10. Protocol steps S1-S3

def execute_s1(state):
    template = STATES[state.message_label]
    state.p1 = template.copy()
    state.p2 = template.copy()
    state.p3 = template.copy()
    state.log('S1', copies=3, preparation='independent from known classical description')
    return state

def execute_s2(state, record='01'):
    result = alice_to_bob_teleportation(state.p1, state.bell_resources, record)
    state.x_records['X1'] = record
    state.teleportation['S2'] = result
    state.bob_state = result.receiver_before_correction.copy()
    state.log('S2', pair=result.pair_id, X1=record, branch_probability=result.branch_probability, corrected_fidelity=result.fidelity)
    return state

def execute_s3(state):
    p = state.key_parts
    x1 = state.x_records['X1']
    state.p3_encrypted = encrypt_state(state.p3, p['K_AT_prime'])
    state.encrypted_records['X1_bell'] = encrypted_bell_record(x1, p['K_AT_double'])
    state.encrypted_records['X1_comp'] = encrypt_computational_record(x1, p['K_AT_triple'])
    state.log('S3', objects=['p2', 'E_KAT_prime(p3)', 'encrypted_X1_bell', 'encrypted_X1_comp'])
    return state

# 11. Protocol step S4

def execute_s4(state, record='10'):
    result = bob_to_trent_teleportation(state.bob_state, state.bell_resources, record)
    state.x_records['X2'] = record
    state.teleportation['S4'] = result
    state.trent_state = result.receiver_before_correction.copy()
    p = state.key_parts
    state.encrypted_records['X2_bell'] = encrypted_bell_record(record, p['K_BT_prime'])
    state.encrypted_records['X2_comp'] = encrypt_computational_record(record, p['K_BT_double'])
    state.log('S4', pair=result.pair_id, X2=record, branch_probability=result.branch_probability)
    return state

# 12. Protocol steps S5-S6

def execute_s5(state, lam, rng, mode='repeated_swap_test', seed=0):
    p = state.key_parts
    recovered = {'X1_bell': recover_bell_record(state.encrypted_records['X1_bell'], p['K_AT_double']), 'X1_comp': recover_computational_record(state.encrypted_records['X1_comp'], p['K_AT_triple']), 'X2_bell': recover_bell_record(state.encrypted_records['X2_bell'], p['K_BT_prime']), 'X2_comp': recover_computational_record(state.encrypted_records['X2_comp'], p['K_BT_double'])}
    state.recovered_records.update(recovered)
    records_ok = recovered['X1_bell'] == recovered['X1_comp'] and recovered['X2_bell'] == recovered['X2_comp']
    x1 = recovered['X1_comp'] if recovered['X1_comp'] in {'00', '01', '10', '11'} else '00'
    x2 = recovered['X2_comp'] if recovered['X2_comp'] in {'00', '01', '10', '11'} else '00'
    recovered_p1 = pauli_from_record(x1).conj().T @ pauli_from_record(x2).conj().T @ state.trent_state
    state.p3_recovered = decrypt_state(state.p3_encrypted, p['K_AT_prime'])
    F, single, repeated, accepted = compare_states(recovered_p1, state.p3_recovered, lam, rng, mode)
    state.comparisons.append(ComparisonRecord('S5', F, single, repeated, accepted, lam, seed, mode))
    state.trent_accept = bool(records_ok and accepted)
    state.trent_state = recovered_p1
    state.log('S5', records_ok=records_ok, fidelity=F, p_accept_single=single, p_accept_repeated=repeated, outcome=accepted, trent_accept=state.trent_accept)
    return state

def execute_s6(state, record='11'):
    result = trent_to_bob_teleportation(state.trent_state, state.bell_resources, record)
    state.x_records['X3'] = record
    state.teleportation['S6'] = result
    state.bob_state = result.receiver_before_correction.copy()
    p = state.key_parts
    state.encrypted_records['X3_bell'] = encrypted_bell_record(record, p['K_BT_triple'])
    state.encrypted_records['X3_comp'] = encrypt_computational_record(record, p['K_BT_fourth'])
    state.log('S6', pair=result.pair_id, X3=record, branch_probability=result.branch_probability)
    return state

# 13. Protocol step S7

def execute_s7(state, lam, rng, mode='repeated_swap_test', seed=0):
    p = state.key_parts
    xb = recover_bell_record(state.encrypted_records['X3_bell'], p['K_BT_triple'])
    xc = recover_computational_record(state.encrypted_records['X3_comp'], p['K_BT_fourth'])
    state.recovered_records.update({'X3_bell': xb, 'X3_comp': xc})
    records_ok = xb == xc
    record = xc if xc in {'00', '01', '10', '11'} else '00'
    state.bob_state = pauli_from_record(record).conj().T @ state.bob_state
    F, single, repeated, accepted = compare_states(state.bob_state, state.p2, lam, rng, mode)
    state.comparisons.append(ComparisonRecord('S7', F, single, repeated, accepted, lam, seed, mode))
    state.bob_accept = bool(records_ok and accepted)
    state.final_accept = bool(state.trent_accept and state.bob_accept)
    state.log('S7', records_ok=records_ok, fidelity=F, p_accept_single=single, p_accept_repeated=repeated, outcome=accepted, bob_accept=state.bob_accept, final_accept=state.final_accept)
    return state

# 14. Complete protocol execution

def run_protocol_v7(message_label='+', attack='none', comparison_mode='repeated_swap_test', lambda_repetitions=8, seed=20260803):
    state = ProtocolState(message_label=message_label)
    rng = np.random.default_rng(seed)
    execute_i1(state)
    execute_i2(state)
    execute_s1(state)
    execute_s2(state)
    # ``alice_scenario_1`` is a deprecated compatibility alias, not a security claim.
    if attack in {'alice_consistent_record_manipulation', 'alice_scenario_1'}:
        true = state.x_records['X1']
        sent = next((x for x in ('00', '01', '10', '11') if x != true))
        state.x_records['X1'] = sent
        state.p2 = pauli_from_record(sent) @ pauli_from_record(true) @ state.p1
        state.p3 = state.p2.copy()
        state.log('ALICE_CONSISTENT_RECORD_MANIPULATION', X1_true=true, X1_sent=sent,
                  traceability_relation='p2=p3=U(X1_sent)U(X1_true)p1',
                  interpretation='consistency-only checks cannot distinguish this path from an honest path')
    execute_s3(state)
    apply_attack(state, attack, 'after_s3')
    execute_s4(state)
    apply_attack(state, attack, 'after_s4')
    execute_s5(state, lambda_repetitions, rng, comparison_mode, seed)
    execute_s6(state)
    apply_attack(state, attack, 'after_s6')
    execute_s7(state, lambda_repetitions, rng, comparison_mode, seed + 1)
    return state

def run_honest_protocol(**kwargs):
    return run_protocol_v7(attack='none', **kwargs)

def run_protocol_with_attack(attack, **kwargs):
    return run_protocol_v7(attack=attack, **kwargs)


def _write_protocol_summary(path: Path, attack: str) -> None:
    state = run_protocol_with_attack(attack, comparison_mode="exact_reference", seed=20260803)
    row = {
        "attack": attack,
        "message": state.message_label,
        "X1": state.x_records.get("X1"),
        "X2": state.x_records.get("X2"),
        "X3": state.x_records.get("X3"),
        "trent_accept": state.trent_accept,
        "bob_accept": state.bob_accept,
        "final_accept": state.final_accept,
    }
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader(); writer.writerow(row)

# 2. Grover-based scheme

def basis_state(index: int, dimension: int=4) -> np.ndarray:
    state = np.zeros(dimension, dtype=complex)
    state[index % dimension] = 1.0
    return state

def public_message_state(dimension: int=4) -> np.ndarray:
    return np.ones(dimension, dtype=complex) / np.sqrt(dimension)

def message_state_from_bits(m: str) -> np.ndarray:
    if m not in {'00', '01', '10', '11'}:
        raise ValueError("Grover message bits must be one of '00', '01', '10', '11'.")
    plus = np.array([1.0, 1.0], dtype=complex) / np.sqrt(2)
    minus = np.array([1.0, -1.0], dtype=complex) / np.sqrt(2)
    first = minus if m[0] == '0' else plus
    second = minus if m[1] == '0' else plus
    state = np.kron(first, second)
    return state / np.linalg.norm(state)

def signing_unitary(key_index: int, dimension: int=4) -> np.ndarray:
    key = basis_state(key_index, dimension)
    return np.eye(dimension, dtype=complex) - 2.0 * np.outer(key, key.conj())

def verification_unitary(message_state: np.ndarray) -> np.ndarray:
    message_state = message_state / np.linalg.norm(message_state)
    return 2.0 * np.outer(message_state, message_state.conj()) - np.eye(len(message_state), dtype=complex)

def equivalent_key_index(state: np.ndarray) -> int:
    return int(np.argmax(np.abs(state) ** 2))

@dataclass
class GroverStepwiseState:
    message_label: str = '00'
    dimension: int = 4
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(2026))
    keys: Dict[str, int] = field(default_factory=dict)
    objects: Dict[str, object] = field(default_factory=dict)
    transcript: list[str] = field(default_factory=list)
    accepted_by_tc: Optional[bool] = None
    accepted_by_bob: Optional[bool] = None
    recovered_keys: Dict[str, int] = field(default_factory=dict)

def step_AT1_alice_tc_key_setup(state: GroverStepwiseState) -> None:
    state.objects['M_AT'] = message_state_from_bits(state.message_label)
    state.keys['K_AT'] = int(state.rng.integers(0, state.dimension))
    state.transcript.append(f'AT1: public message m={state.message_label} and Alice-TC key initialized.')

def step_AT2_construct_alice_signing_unitary(state: GroverStepwiseState) -> None:
    state.objects['U_SAT'] = signing_unitary(state.keys['K_AT'], state.dimension)
    state.transcript.append('AT2: Alice signing unitary U_SAT constructed.')

def step_AT3_generate_alice_signature(state: GroverStepwiseState) -> None:
    state.objects['alice_signature'] = state.objects['U_SAT'] @ state.objects['M_AT']
    state.transcript.append('AT3: Alice signature state U_SAT|M> generated.')

def step_AT4_AT7_transmit_to_tc_with_decoy_proxy(state: GroverStepwiseState, attack: str='none') -> None:
    state.objects['tc_received_signature'] = state.objects['alice_signature'].copy()
    state.objects['channel_check_AT'] = attack != 'channel_block'
    state.objects['decoy_proxy_AT'] = 'AT4-AT7 channel/transcript proxy'
    state.transcript.append('AT4-AT7: Alice-to-TC decoy-assisted channel represented by proxy.')

def step_AT8_tc_verify_and_recover_key(state: GroverStepwiseState) -> None:
    verifier = verification_unitary(state.objects['M_AT'])
    recovered_state = verifier @ state.objects['tc_received_signature']
    recovered = equivalent_key_index(recovered_state)
    state.objects['U_V_AT'] = verifier
    state.objects['recovered_state_AT'] = recovered_state
    state.recovered_keys['K_AT'] = recovered
    state.accepted_by_tc = bool(state.objects.get('channel_check_AT', False) and recovered == state.keys['K_AT'])
    state.transcript.append('AT8: TC recovered and checked K_AT.')

def step_TB1_tc_bob_key_setup(state: GroverStepwiseState) -> None:
    state.objects['M_TB'] = message_state_from_bits(state.message_label)
    state.keys['K_TB'] = int(state.rng.integers(0, state.dimension))
    state.transcript.append(f'TB1: public message m={state.message_label} and TC-Bob key initialized.')

def step_TB2_construct_tc_signing_unitary(state: GroverStepwiseState) -> None:
    state.objects['U_STB'] = signing_unitary(state.keys['K_TB'], state.dimension)
    state.transcript.append('TB2: TC signing unitary U_STB constructed.')

def step_TB3_generate_tc_signature(state: GroverStepwiseState) -> None:
    state.objects['tc_signature'] = state.objects['U_STB'] @ state.objects['M_TB']
    state.transcript.append('TB3: TC signature state U_STB|M> generated.')

def step_TB4_TB7_transmit_to_bob_with_decoy_proxy(state: GroverStepwiseState, attack: str='none') -> None:
    state.objects['bob_received_signature'] = state.objects['tc_signature'].copy()
    state.objects['channel_check_TB'] = attack != 'channel_block'
    state.objects['decoy_proxy_TB'] = 'TB4-TB7 channel/transcript proxy'
    state.transcript.append('TB4-TB7: TC-to-Bob decoy-assisted channel represented by proxy.')

def step_TB8_bob_verify_and_recover_key(state: GroverStepwiseState) -> None:
    verifier = verification_unitary(state.objects['M_TB'])
    recovered_state = verifier @ state.objects['bob_received_signature']
    recovered = equivalent_key_index(recovered_state)
    state.objects['U_V_TB'] = verifier
    state.objects['recovered_state_TB'] = recovered_state
    state.recovered_keys['K_TB'] = recovered
    state.accepted_by_bob = bool(state.objects.get('channel_check_TB', False) and recovered == state.keys['K_TB'])
    state.transcript.append('TB8: Bob recovered and checked K_TB.')

def run_at_protocol(seed: int=2026, message_bits: str='00') -> GroverStepwiseState:
    state = GroverStepwiseState(message_label=message_bits, rng=np.random.default_rng(seed))
    step_AT1_alice_tc_key_setup(state)
    step_AT2_construct_alice_signing_unitary(state)
    step_AT3_generate_alice_signature(state)
    step_AT4_AT7_transmit_to_tc_with_decoy_proxy(state)
    step_AT8_tc_verify_and_recover_key(state)
    return state

def run_tb_protocol(seed: int=2026, message_bits: str='00') -> GroverStepwiseState:
    state = GroverStepwiseState(message_label=message_bits, rng=np.random.default_rng(seed))
    step_TB1_tc_bob_key_setup(state)
    step_TB2_construct_tc_signing_unitary(state)
    step_TB3_generate_tc_signature(state)
    step_TB4_TB7_transmit_to_bob_with_decoy_proxy(state)
    step_TB8_bob_verify_and_recover_key(state)
    return state

def recover_public_key_from_signature(signature: np.ndarray, message_state: np.ndarray) -> int:
    return equivalent_key_index(verification_unitary(message_state) @ signature)

# 3. Grover key recovery and recovered-key forgery

def run_key_recovery_and_forgery(message_bits: str, key_index: int):
    message = message_state_from_bits(message_bits)
    signature = signing_unitary(key_index) @ message
    recovered_state = verification_unitary(message) @ signature
    recovered = int(np.argmax(abs(recovered_state) ** 2))
    recovery_fidelity = float(abs(np.vdot(basis_state(recovered), recovered_state)) ** 2)
    forged = signing_unitary(recovered) @ message
    check = verification_unitary(message) @ forged
    return {'message': message_bits, 'true_key': key_index, 'recovered_key': recovered, 'key_recovery_rate': float(recovered == key_index), 'recovery_fidelity': recovery_fidelity, 'forged_accept_rate': float(int(np.argmax(abs(check) ** 2)) == recovered)}

# 4. Attack scenario catalogue

TARGETED_ATTACKS = ('tamper_X1_bell_record', 'tamper_X1_encrypted_record', 'tamper_X2_bell_record', 'tamper_X2_encrypted_record', 'tamper_X3_bell_record', 'tamper_X3_encrypted_record', 'tamper_p2', 'tamper_p3', 'cross_stage_record_substitution', 'fixed_state_ciphertext_replacement')

# 5. Alice repudiation probability model

def abstract_binomial_repudiation_model(n: int, alpha: float, beta: float) -> float:
    """Phenomenological model; it is not derived from the complete protocol game."""
    p = 0.25 + alpha
    kmax = floor(n * beta)
    return sum((comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(kmax + 1)))

def exact_binomial_probability(n: int, alpha: float, beta: float) -> float:
    """Deprecated compatibility wrapper for abstract_binomial_repudiation_model."""
    return abstract_binomial_repudiation_model(n, alpha, beta)

def chernoff_upper_bound(n: int, alpha: float, beta: float) -> float:
    p = 0.25 + alpha
    q = beta
    if q <= 0:
        return (1 - p) ** n
    divergence = q * log(q / p) + (1 - q) * log((1 - q) / (1 - p))
    return exp(-n * divergence)

def monte_carlo_probability(n: int, alpha: float, beta: float, trials: int, rng) -> tuple[float, int]:
    successes = int(np.count_nonzero(rng.binomial(n, 0.25 + alpha, size=trials) <= floor(n * beta)))
    return (successes / trials, successes)


# 6. Result generation
def generate_attack_results(output_dir: Path, seed: int = 20260803) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    grover_rows = [run_key_recovery_and_forgery(message, key) for message in ("00", "01", "10", "11") for key in range(4)]
    with (output_dir / "grover_attack_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(grover_rows[0])); writer.writeheader(); writer.writerows(grover_rows)

    attacks = [
        "none", "tamper_X1_bell_record", "tamper_X1_encrypted_record",
        "tamper_X2_bell_record", "tamper_X2_encrypted_record",
        "tamper_X3_bell_record", "tamper_X3_encrypted_record",
        "tamper_p2", "tamper_p3", "cross_stage_record_substitution", "fixed_state_ciphertext_replacement",
    ]
    protocol_rows = []
    for attack in attacks:
        state = run_protocol_with_attack(attack, comparison_mode="exact_reference", seed=seed)
        protocol_rows.append({"attack": attack, "attack_scope": "targeted", "models_general_cptp_attack": False,
                              "trent_accept": state.trent_accept, "bob_accept": state.bob_accept, "final_accept": state.final_accept})
    with (output_dir / "targeted_attack_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(protocol_rows[0])); writer.writeheader(); writer.writerows(protocol_rows)

    rng = np.random.default_rng(seed)
    repudiation_rows = []
    for n in range(10, 201, 10):
        monte_carlo, count = monte_carlo_probability(n, 0.05, 0.06, 20000, rng)
        repudiation_rows.append({"n": n, "alpha": 0.05, "beta": 0.06, "trials": 20000, "success_count": count,
            "monte_carlo_probability": monte_carlo, "exact_binomial_probability": exact_binomial_probability(n, 0.05, 0.06),
            "chernoff_upper_bound": chernoff_upper_bound(n, 0.05, 0.06)})
    with (output_dir / "alice_repudiation_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(repudiation_rows[0])); writer.writeheader(); writer.writerows(repudiation_rows)


if False and __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the complete attack benchmark locally.")
    parser.add_argument("--output-dir", type=Path, default=Path("attack_results"))
    parser.add_argument("--seed", type=int, default=20260803)
    args = parser.parse_args(); generate_attack_results(args.output_dir, args.seed); print(args.output_dir)

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# Numerical data generation for the four-panel figure
import hashlib


NUMERICAL_SEED = 20260803


def generate_swap_test_detection_data(path: Path, trials: int = 20000) -> None:
    rng = np.random.default_rng(NUMERICAL_SEED); rows = []
    for F in (0.0, 0.25, 0.5):
        for lam in (1, 2, 4, 8, 12, 16, 24, 32, 40):
            analytical = repeated_swap_test_detection_probability(F, lam)
            detected = int(np.count_nonzero(rng.random(trials) < analytical))
            rows.append({"fidelity": F, "lambda": lam, "trials": trials,
                         "analytical_detection_probability": analytical,
                         "monte_carlo_detection_probability": detected / trials})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def generate_protocol_acceptance_data(path: Path, trials: int = 2000, lam: int = 8) -> None:
    rows, trial_rows = [], []
    for attack in ("none", "alice_consistent_record_manipulation", "tamper_p2", "fixed_state_ciphertext_replacement"):
        for noise in (0.0, 0.02, 0.05):
            final_accepts = trent_accepts = bob_accepts = 0
            s5_fidelities, s7_fidelities = [], []
            for index in range(trials):
                # The reference mode computes fidelities and record consistency without
                # drawing an ideal comparison outcome.  The noisy experiment then draws
                # exactly once from each noisy acceptance probability.
                state = run_protocol_v7(attack=attack, comparison_mode="classical_statevector_reference",
                                        lambda_repetitions=lam, seed=NUMERICAL_SEED + index)
                logs = {entry['stage']: entry for entry in state.audit_trail if entry['stage'] in {'S5', 'S7'}}
                comparisons = {item.stage: item for item in state.comparisons}
                rng = np.random.default_rng(NUMERICAL_SEED + index + 100003 * int(noise * 100))
                sampled = {}
                for stage in ('S5', 'S7'):
                    ideal_fidelity = comparisons[stage].fidelity
                    effective_fidelity = (1.0 - noise) * ideal_fidelity + noise / 2.0
                    accept_probability = repeated_swap_test_accept_probability(effective_fidelity, lam)
                    sampled_accept = bool(rng.random() < accept_probability)
                    records_ok = bool(logs[stage]['records_ok'])
                    sampled[stage] = records_ok and sampled_accept
                    trial_rows.append({"attack": attack, "attack_scope": "targeted", "noise_parameter": noise,
                        "lambda": lam, "trial": index, "stage": stage, "records_ok": records_ok,
                        "ideal_fidelity": ideal_fidelity, "effective_fidelity": effective_fidelity,
                        "accept_probability": accept_probability, "sampled_accept": sampled_accept,
                        "stage_accept": sampled[stage], "sampling_model": "single direct noisy draw"})
                trent_accepts += int(sampled['S5'])
                bob_accepts += int(sampled['S7'])
                final_accepts += int(sampled['S5'] and sampled['S7'])
                s5_fidelities.append(comparisons['S5'].fidelity)
                s7_fidelities.append(comparisons['S7'].fidelity)
            rows.append({"attack": attack, "attack_scope": "targeted", "models_general_cptp_attack": False,
                         "noise_parameter": noise, "noise_model": "rho'=(1-p)rho+pI/2", "lambda": lam,
                         "trials": trials, "seed": NUMERICAL_SEED, "final_accept_count": final_accepts,
                         "final_accept_rate": final_accepts / trials, "trent_accept_rate": trent_accepts / trials,
                         "bob_accept_rate": bob_accepts / trials, "mean_s5_fidelity": float(np.mean(s5_fidelities)),
                         "mean_s7_fidelity": float(np.mean(s7_fidelities))})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with path.with_name("protocol_acceptance_trials.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trial_rows[0])); writer.writeheader(); writer.writerows(trial_rows)


def generate_repudiation_data(path: Path, trials: int = 20000) -> None:
    rng = np.random.default_rng(NUMERICAL_SEED); rows = []
    for n in range(10, 201, 10):
        monte_carlo, success_count = monte_carlo_probability(n, 0.05, 0.06, trials, rng)
        rows.append({"n": n, "alpha": 0.05, "beta": 0.06, "trials": trials,
                     "success_count": success_count, "monte_carlo_probability": monte_carlo,
                     "exact_binomial_probability": exact_binomial_probability(n, 0.05, 0.06),
                     "chernoff_upper_bound": chernoff_upper_bound(n, 0.05, 0.06),
                     "model": "abstract phenomenological binomial model; not a protocol security proof"})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def generate_resource_data(path: Path, lam: int = 8) -> None:
    rows = []
    for n in range(1, 21):
        base_protocol_operations = 7 * n
        trent_swap_cswaps = n * lam
        bob_swap_cswaps = n * lam
        total_swap_cswaps = trent_swap_cswaps + bob_swap_cswaps
        rows.append({"n": n, "lambda": lam, "static_bell_qubits": 6 * n,
            "dynamic_message_qubits": 3 * n, "peak_protocol_qubits": 9 * n,
            "classical_key_bits": 40 * n, "trent_swap_cswaps": trent_swap_cswaps,
            "bob_swap_cswaps": bob_swap_cswaps, "total_swap_cswaps": total_swap_cswaps,
            "base_protocol_operations": base_protocol_operations,
            "total_operation_model": base_protocol_operations + total_swap_cswaps,
            "state_pairs_per_verification": lam, "number_of_verifications": 2,
            "total_comparison_state_pairs": 2 * lam,
            "scope": "analytical independent-copy model; 7n is normalized base work, not an exact gate count"})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

def generate_fidelity_gap_data(path: Path, target_error: float = 1e-6) -> None:
    rows = []
    for delta in (0.01, 0.05, 0.10, 0.25, 0.50, 1.00):
        required = repetitions_for_target_error(delta, target_error)
        for lam in (8, 16, 32, 64, 128, required):
            bound = false_acceptance_upper_bound(delta, lam)
            rows.append({"delta": delta, "lambda": lam, "false_acceptance_upper_bound": bound,
                         "detection_lower_bound": 1.0 - bound, "target_error": target_error,
                         "required_lambda": required, "assumption": "F(rho_hon,rho_adv)<=1-delta"})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

def generate_attack_scope_data(path: Path) -> None:
    rows = [
        {"attack_name": "alice_consistent_record_manipulation", "attack_scope": "targeted", "attack_class": "insider consistent misreport", "changes_message_state": True, "changes_classical_record": True, "models_general_cptp_attack": False, "security_interpretation": "negative result: consistency-only checks may be indistinguishable from honest execution"},
        {"attack_name": "tamper_p2", "attack_scope": "targeted", "attack_class": "plaintext Pauli modification", "changes_message_state": True, "changes_classical_record": False, "models_general_cptp_attack": False, "security_interpretation": "benchmark only"},
        {"attack_name": "fixed_state_ciphertext_replacement", "attack_scope": "targeted", "attack_class": "fixed-state ciphertext replacement", "changes_message_state": True, "changes_classical_record": False, "models_general_cptp_attack": False, "security_interpretation": "benchmark only"},
        {"attack_name": "cross_stage_record_substitution", "attack_scope": "targeted", "attack_class": "cross-stage record substitution", "changes_message_state": False, "changes_classical_record": True, "models_general_cptp_attack": False, "security_interpretation": "not a complete replay-security experiment"},
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def generate_complete_numerical_figure(data_dir: Path, output_path: Path) -> None:
    swap = pd.read_csv(data_dir / "swap_test_detection.csv")
    acceptance = pd.read_csv(data_dir / "protocol_acceptance.csv")
    resources = pd.read_csv(data_dir / "resource_scaling.csv")
    gaps = pd.read_csv(data_dir / "fidelity_gap_security_bounds.csv")
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    for F, color, marker in ((0.0, "0.15", "o"), (0.25, "0.4", "s"), (0.5, "0.65", "^")):
        part = swap[swap["fidelity"] == F]
        axes[0, 0].plot(part["lambda"], part["analytical_detection_probability"], color=color, label=f"F={F:g} analytical")
        axes[0, 0].scatter(part["lambda"], part["monte_carlo_detection_probability"], color=color, marker=marker, label=f"F={F:g} Monte Carlo")
    axes[0, 0].set(title="(a) Swap-test detection probability", xlabel=r"Independent repetitions $\lambda$", ylabel="Detection probability", ylim=(0, 1.02)); axes[0, 0].legend(fontsize=8)
    for attack, label, marker in (("none", "Honest", "o"), ("alice_consistent_record_manipulation", "Consistent Alice manipulation", "s"), ("tamper_p2", r"Tamper $p_2$", "^"), ("fixed_state_ciphertext_replacement", "Fixed-state replacement", "v")):
        part = acceptance[acceptance["attack"] == attack]
        axes[0, 1].plot(part["noise_parameter"], part["final_accept_rate"], marker=marker, label=label)
    axes[0, 1].set(title="(b) Protocol acceptance rate", xlabel=r"Depolarizing replacement probability $p$", ylabel="Final acceptance rate", ylim=(-0.02, 1.02)); axes[0, 1].legend(fontsize=8)
    for column, label in (("classical_key_bits", "Classical key bits"), ("total_swap_cswaps", "Controlled-SWAPs"), ("total_operation_model", "Total operation model")):
        axes[1, 0].plot(resources["n"], resources[column], label=label)
    axes[1, 0].set(title=r"(c) Resource scaling ($\lambda=8$)", xlabel=r"Message qubits $n$", ylabel="Count / model units"); axes[1, 0].legend(fontsize=8)
    for delta, marker in ((0.01, "o"), (0.05, "s"), (0.10, "^"), (0.25, "v")):
        part = gaps[(gaps["delta"] == delta) & (gaps["lambda"].isin([8, 16, 32, 64, 128]))]
        axes[1, 1].semilogy(part["lambda"], part["false_acceptance_upper_bound"], marker=marker, label=rf"$\Delta={delta:g}$")
    axes[1, 1].set(title="(d) Conditional fidelity-gap bounds", xlabel=r"Independent repetitions $\lambda$", ylabel="False-acceptance upper bound"); axes[1, 1].legend(fontsize=8)
    fig.suptitle("Numerical models and targeted benchmarks", fontsize=16); fig.tight_layout()
    for extension in ("pdf", "png", "eps"):
        fig.savefig(output_path.with_suffix("." + extension), dpi=300, bbox_inches="tight")
    plt.close(fig)


def run_numerical_full_pipeline(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_swap_test_detection_data(output_dir / "swap_test_detection.csv")
    generate_protocol_acceptance_data(output_dir / "protocol_acceptance.csv")
    generate_repudiation_data(output_dir / "alice_repudiation_probability.csv")
    generate_resource_data(output_dir / "resource_scaling.csv")
    generate_fidelity_gap_data(output_dir / "fidelity_gap_security_bounds.csv")
    generate_attack_scope_data(output_dir / "attack_model_scope.csv")
    generate_complete_numerical_figure(output_dir, output_dir / "combined_numerical_simulations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the complete protocol-level numerical pipeline.")
    parser.add_argument("--output-dir", type=Path, default=Path("numerical_pipeline_results"))
    arguments = parser.parse_args(); run_numerical_full_pipeline(arguments.output_dir)
