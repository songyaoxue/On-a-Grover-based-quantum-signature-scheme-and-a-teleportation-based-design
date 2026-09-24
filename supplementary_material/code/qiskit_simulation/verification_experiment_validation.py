"""Regression validation for the physical-copy protocol-batch implementation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from qiskit import transpile
from qiskit.providers.basic_provider import BasicSimulator
from qiskit_aer import AerSimulator


QISKIT_DIR = Path(__file__).resolve().parent
HARDWARE_DIR = QISKIT_DIR.parent / "ibm_hardware"
for directory in (QISKIT_DIR, HARDWARE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import ibm_hardware_circuit_generation as HARDWARE_CIRCUITS
import ibm_offline_analysis as IBM_OFFLINE
import local_reference_evaluation as LOCAL
import qiskit_protocol_reference as REFERENCE
import resource_operation_ledger as LEDGER
import verification_experiment_suite as MODEL


def execute_honest_batch(lambda_parameter: int, seed: int = MODEL.SEED):
    rng = np.random.default_rng(seed)
    batch = MODEL.prepare_protocol_batch(lambda_parameter, rng)
    MODEL.execute_protocol_batch(batch, "honest", 0.0, rng)
    return batch


def test_general_fidelity_product():
    fidelities = [0.0, 0.25, 0.9]
    expected = np.prod([(1 + value) / 2 for value in fidelities])
    assert np.isclose(MODEL.swap_accept_all(fidelities), expected)


def test_orthogonal_special_case_only():
    for m in (1, 2, 4, 8, 16):
        assert np.isclose(MODEL.repeated_swap_accept_probability(0.0, m), 2.0**-m)
        assert not np.isclose(MODEL.repeated_swap_accept_probability(0.25, m), 2.0**-m)


def test_lambda_keyword_is_only_a_generic_swap_compatibility_alias():
    assert MODEL.repeated_swap_accept_probability(0.5, lambda_repetitions=4) == MODEL.repeated_swap_accept_probability(0.5, m=4)


@pytest.mark.parametrize("lambda_parameter", (1, 2, 4, 8))
def test_protocol_batch_physical_copy_cardinalities(lambda_parameter):
    batch = MODEL.prepare_protocol_batch(lambda_parameter, np.random.default_rng(MODEL.SEED))
    assert len(batch.p1_copies) == 2 * lambda_parameter + 1
    assert len(batch.p2_copies) == lambda_parameter
    assert len(batch.p3_copies) == lambda_parameter
    assert len(batch.p1_copies) + len(batch.p2_copies) + len(batch.p3_copies) == 4 * lambda_parameter + 1


@pytest.mark.parametrize("lambda_parameter", (1, 2, 4, 8))
def test_protocol_batch_records_match_physical_paths(lambda_parameter):
    batch = MODEL.prepare_protocol_batch(lambda_parameter, np.random.default_rng(MODEL.SEED))
    assert len(batch.x1_records) == 2 * lambda_parameter + 1
    assert len(batch.x2_records) == 2 * lambda_parameter + 1
    assert len(batch.x3_records) == lambda_parameter + 1


def test_all_physical_message_arrays_are_distinct_allocations():
    batch = MODEL.prepare_protocol_batch(8, np.random.default_rng(MODEL.SEED))
    arrays = batch.p1_copies + batch.p2_copies + batch.p3_copies
    assert len({id(value) for value in arrays}) == len(arrays)


@pytest.mark.parametrize("lambda_parameter", (1, 2, 4, 8))
def test_s5_sampling_without_replacement(lambda_parameter):
    batch = execute_honest_batch(lambda_parameter)
    all_indices = set(range(2 * lambda_parameter + 1))
    assert len(batch.s5_test_indices) == lambda_parameter
    assert len(batch.s5_test_indices) == len(set(batch.s5_test_indices))
    assert len(batch.s5_remaining_indices) == lambda_parameter + 1
    assert set(batch.s5_test_indices).isdisjoint(batch.s5_remaining_indices)
    assert set(batch.s5_test_indices) | set(batch.s5_remaining_indices) == all_indices
    assert batch.inputs_committed_before_sampling


@pytest.mark.parametrize("lambda_parameter", (1, 2, 4, 8))
def test_s7_sampling_and_unique_retained_copy(lambda_parameter):
    batch = execute_honest_batch(lambda_parameter)
    assert len(batch.s7_test_indices) == lambda_parameter
    assert len(batch.s7_test_indices) == len(set(batch.s7_test_indices))
    assert set(batch.s7_test_indices).issubset(batch.s5_remaining_indices)
    retained = set(batch.s5_remaining_indices) - set(batch.s7_test_indices)
    assert retained == {batch.retained_p1_index}


def test_same_seed_reproduces_sampling():
    first = execute_honest_batch(4, MODEL.SEED + 100)
    second = execute_honest_batch(4, MODEL.SEED + 100)
    assert (first.s5_test_indices, first.s7_test_indices, first.retained_p1_index) == (
        second.s5_test_indices,
        second.s7_test_indices,
        second.retained_p1_index,
    )


def test_different_seeds_can_produce_different_sampling():
    selections = {
        (
            tuple(execute_honest_batch(4, MODEL.SEED + offset).s5_test_indices),
            tuple(execute_honest_batch(4, MODEL.SEED + offset).s7_test_indices),
        )
        for offset in range(8)
    }
    assert len(selections) > 1


@pytest.mark.parametrize("lambda_parameter", (1, 2, 4, 8))
def test_each_stage_executes_lambda_explicit_comparisons(lambda_parameter):
    batch = execute_honest_batch(lambda_parameter)
    assert len(batch.s5_comparisons) == lambda_parameter
    assert len(batch.s7_comparisons) == lambda_parameter
    assert all(item.stage == "S5" for item in batch.s5_comparisons)
    assert all(item.stage == "S7" for item in batch.s7_comparisons)


@pytest.mark.parametrize("lambda_parameter", (1, 2, 4, 8))
def test_honest_ideal_batch_accepts(lambda_parameter):
    batch = execute_honest_batch(lambda_parameter)
    assert batch.trent_accept and batch.bob_accept and batch.final_accept


def test_noise_is_applied_per_physical_comparison():
    rng = np.random.default_rng(MODEL.SEED)
    batch = MODEL.prepare_protocol_batch(4, rng)
    MODEL.execute_protocol_batch(batch, "honest", 0.02, rng)
    for item in batch.s5_comparisons + batch.s7_comparisons:
        assert np.isclose(item.effective_fidelity, 0.99)
        assert np.isclose(item.accept_probability, 0.995)


def test_record_mismatch_scenarios_retain_zero_final_acceptance():
    for scenario in ("bob_tampering_s6_record", "replay_record_mismatch"):
        rng = np.random.default_rng(MODEL.SEED)
        batch = MODEL.prepare_protocol_batch(4, rng)
        assert MODEL.execute_protocol_batch(batch, scenario, 0.0, rng) is False
        assert batch.attacked_index == 0


def test_alice_consistency_only_scenario_remains_indistinguishable_in_ideal_model():
    rng = np.random.default_rng(MODEL.SEED)
    batch = MODEL.prepare_protocol_batch(4, rng)
    assert MODEL.execute_protocol_batch(batch, "alice_scenario_1", 0.0, rng) is True


@pytest.mark.parametrize("lambda_parameter", (1, 2, 4, 8))
def test_bell_allocation_by_stage(lambda_parameter):
    row = LEDGER.summarize_resources(1, lambda_parameter)
    assert row["s2_bell_pairs"] == 2 * lambda_parameter + 1
    assert row["s4_bell_pairs"] == 2 * lambda_parameter + 1
    assert row["s6_bell_pairs"] == lambda_parameter + 1
    assert row["total_bell_pairs"] == 5 * lambda_parameter + 3


@pytest.mark.parametrize(("n", "lambda_parameter"), ((1, 1), (1, 8), (7, 4), (20, 8)))
def test_resource_physical_copy_batch_formulas(n, lambda_parameter):
    row = LEDGER.summarize_resources(n, lambda_parameter)
    assert row["message_physical_qubit_instances"] == (4 * lambda_parameter + 1) * n
    assert row["total_bell_pairs"] == (5 * lambda_parameter + 3) * n
    assert row["total_bell_qubits"] == 2 * (5 * lambda_parameter + 3) * n
    assert row["teleportation_operations"] == (5 * lambda_parameter + 3) * n
    assert row["total_controlled_swap_gates"] == 2 * lambda_parameter * n


@pytest.mark.parametrize("lambda_parameter", (1, 2, 4, 8))
def test_fresh_key_total_is_derived_from_encrypted_objects(lambda_parameter):
    objects = LEDGER.encrypted_object_ledger(lambda_parameter)
    derived = sum(item.bit_length for item in objects)
    assert derived == 64 * lambda_parameter + 36
    assert LEDGER.summarize_resources(1, lambda_parameter)["fresh_qotp_key_bits"] == derived


def test_qotp_step_attribution_preserves_total_and_matches_protocol_flow():
    lambda_parameter = 4
    n = 3
    steps = {row.step: row for row in LEDGER.protocol_step_ledger(n, lambda_parameter)}
    objects = LEDGER.encrypted_object_ledger(lambda_parameter)
    assert all(item.encryption_step == "S3" and item.recovery_step == "S5" for item in objects if item.purpose == "p3_key")
    assert steps["S1"].fresh_qotp_key_bits == 0
    assert steps["S3"].fresh_qotp_key_bits == n * sum(item.bit_length for item in objects if item.encryption_step == "S3")
    assert steps["S5"].qotp_unitary_applications == n * sum(1 for item in objects if item.recovery_step == "S5")
    assert steps["S7"].qotp_unitary_applications == n * sum(1 for item in objects if item.recovery_step == "S7")
    assert sum(row.qotp_unitary_applications for row in steps.values()) == 2 * n * len(objects)


def test_resource_total_is_sum_of_step_ledger():
    n, lambda_parameter = 5, 4
    steps = LEDGER.protocol_step_ledger(n, lambda_parameter)
    row = LEDGER.summarize_resources(n, lambda_parameter)
    assert row["total_modeled_operations"] == sum(item.modeled_operations for item in steps)
    assert row["total_modeled_operations"] != lambda_parameter * (40 * n + 2)


def test_ambiguous_communication_and_peak_resources_are_not_guessed():
    row = LEDGER.summarize_resources(3, 2)
    assert row["quantum_transmitted_qubits"] == LEDGER.REQUIRES_CONFIRMATION
    assert row["classical_transmitted_bits"] == LEDGER.REQUIRES_CONFIRMATION
    assert row["peak_live_qubits"] == LEDGER.REQUIRES_CONFIRMATION


@pytest.mark.parametrize("lambda_parameter", (1, 2, 4, 8))
def test_fresh_key_allocator_assigns_unique_single_use_block_ids(lambda_parameter):
    batch = MODEL.prepare_protocol_batch(lambda_parameter, np.random.default_rng(MODEL.SEED))
    blocks = list(batch.key_pool.blocks.values())
    assert len(blocks) == len(batch.encrypted_object_key_blocks)
    assert len({block.block_id for block in blocks}) == len(blocks)
    assert all(block.consumption_count == 1 and block.consumed for block in blocks)


def test_fresh_key_block_reuse_raises():
    pool = MODEL.FreshKeyPool(np.random.default_rng(MODEL.SEED))
    block = pool.allocate(4, "diagnostic", "copy[0]")
    pool.consume(block.block_id)
    with pytest.raises(RuntimeError, match="reused"):
        pool.consume(block.block_id)


def test_fresh_key_policy_does_not_require_unique_bit_patterns():
    pool = MODEL.FreshKeyPool(np.random.default_rng(MODEL.SEED))
    blocks = [pool.allocate(1, "diagnostic", f"copy[{i}]") for i in range(16)]
    for block in blocks:
        pool.consume(block.block_id)
    assert len({block.block_id for block in blocks}) == len(blocks)
    assert {block.bits for block in blocks}.issubset({"0", "1"})
    assert all(block.consumption_count == 1 for block in blocks)


def test_fidelity_zero_vector_rejected():
    with pytest.raises(ValueError):
        MODEL.fidelity(np.zeros(2), np.array([1, 0]))


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (np.array([2, 0]), np.array([7, 0]), 1.0),
        (np.array([1, 0]), np.array([0, 1]), 0.0),
        (np.array([1, 1]) * (1 + 1e-14), np.array([1, 1]), 1.0),
        (np.array([1, 1j]), np.exp(0.73j) * np.array([1, 1j]), 1.0),
    ],
)
def test_fidelity_valid_and_global_phase_invariant(left, right, expected):
    value = MODEL.fidelity(left, right)
    assert 0.0 <= value <= 1.0
    assert np.isclose(value, expected)


@pytest.mark.parametrize(("F", "m", "expected"), ((1.0, 8, 0.0), (0.0, 8, 1 - 2**-8)))
def test_swap_test_endpoints(F, m, expected):
    assert np.isclose(MODEL.swap_detection([F] * m), expected)


@pytest.mark.parametrize(("F", "m"), ((-0.1, 1), (1.1, 1), (0.5, 0), (0.5, -1), (0.5, 1.5)))
def test_explicit_swap_test_invalid_parameters(F, m):
    with pytest.raises(ValueError):
        MODEL.build_explicit_independent_swap_circuit(F, m)


def test_explicit_qiskit_swap_circuit_has_m_preparations_and_measurements():
    circuit = MODEL.build_explicit_independent_swap_circuit(0.9, 8)
    assert circuit.metadata["verification_instances"] == 8
    assert circuit.num_qubits == 24
    assert circuit.num_clbits == 8


@pytest.mark.parametrize("state", LOCAL.VALIDATION_STATES)
def test_single_teleportation_six_states(state):
    assert np.isclose(LOCAL.coherent_chain_fidelity(state, 1), 1.0, atol=1e-12)
    assert min(LOCAL.conditioned_outcome_fidelities(state).values()) >= 1 - 1e-12


@pytest.mark.parametrize("state", LOCAL.VALIDATION_STATES)
def test_three_sequential_teleportations_six_states(state):
    for rounds in (1, 2, 3):
        assert np.isclose(LOCAL.coherent_chain_fidelity(state, rounds), 1.0, atol=1e-12)


@pytest.mark.parametrize("state", ("0", "1", "+", "-", "i+"))
def test_composed_candidate_expected_outputs_aer(state):
    backend = AerSimulator()
    circuit = REFERENCE.build_composed_staged_emulation_candidate(state)
    executable = transpile(circuit, backend, optimization_level=1, seed_transpiler=MODEL.SEED)
    counts = backend.run(executable, shots=256, seed_simulator=MODEL.SEED).result().get_counts()
    expected = REFERENCE.composed_candidate_expected_outputs(state)
    assert REFERENCE.success_probability_from_counts(counts, expected) == 1.0


@pytest.mark.parametrize("state", ("0", "1", "+", "-"))
def test_composed_candidate_expected_outputs_basic_simulator(state):
    backend = BasicSimulator()
    circuit = REFERENCE.build_composed_staged_emulation_candidate(state)
    executable = transpile(circuit, backend, optimization_level=0, seed_transpiler=MODEL.SEED)
    counts = backend.run(executable, shots=128, seed_simulator=MODEL.SEED).result().get_counts()
    expected = REFERENCE.composed_candidate_expected_outputs(state)
    assert REFERENCE.success_probability_from_counts(counts, expected) == 1.0


def test_composed_candidate_global_phase_equivalence():
    state = LOCAL.named_statevector("i+")
    assert MODEL.fidelity(state, np.exp(1j * np.pi / 3) * state) == 1.0


def test_success_probability_sums_multiple_valid_outputs_and_normalizes_spaces():
    counts = {"0 00": 3, "1 00": 5, "0 01": 2}
    assert REFERENCE.success_probability_from_counts(counts, {"000", "100"}) == 0.8


def test_organized_composed_import_does_not_require_experiments_tree():
    circuit = MODEL.import_composed_candidate(Path("/path/without/experiments"), input_state="1")
    assert circuit.metadata["valid_expected_outputs"] == ["100"]


def test_ibm_offline_m1_and_derived_classification(tmp_path):
    output = tmp_path / "ibm_offline.csv"
    IBM_OFFLINE.analyze_existing_hardware(output)
    data = pd.read_csv(output)
    composed = data[data.record_type == "composed_candidate_final"].iloc[0]
    assert composed.m == 1 and composed.DIRECT_HARDWARE == "YES"
    swap = data[data.record_type == "swap_test"]
    assert set(swap.loc[swap.DIRECT_HARDWARE == "YES", "m"]) == {1}
    assert set(swap.loc[swap.DERIVED_FROM_SINGLE_TEST == "YES", "m"]) == {2, 4, 8}
    assert data.absolute_difference.max() < 1e-12


def test_default_hardware_target_generation_never_initializes_ibm(monkeypatch):
    initialized = False

    class ForbiddenService:
        def __init__(self, *args, **kwargs):
            nonlocal initialized
            initialized = True

    monkeypatch.setattr(HARDWARE_CIRCUITS, "QiskitRuntimeService", ForbiddenService)
    with pytest.raises(RuntimeError, match="offline mode is the default"):
        HARDWARE_CIRCUITS.generate_ibm_target_circuits(connect_ibm=False)
    assert initialized is False
