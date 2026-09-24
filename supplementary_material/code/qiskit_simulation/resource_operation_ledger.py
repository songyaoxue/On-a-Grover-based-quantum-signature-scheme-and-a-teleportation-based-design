"""Step-derived resource accounting for one physical-copy protocol batch."""

from __future__ import annotations

from dataclasses import asdict, dataclass


EXECUTION_MODEL = (
    "one protocol execution with 2*lambda+1 p1 copies, lambda p2 copies, "
    "lambda p3 copies, and random S5/S7 subset verification"
)
REQUIRES_CONFIRMATION = "REQUIRES_MANUSCRIPT_CONFIRMATION"


@dataclass(frozen=True)
class EncryptedObjectSpec:
    encryption_step: str
    recovery_step: str
    purpose: str
    copy_id: str
    bit_length: int


@dataclass(frozen=True)
class StepContribution:
    step: str
    rationale: str
    message_state_preparations: int = 0
    message_qubit_instances: int = 0
    bell_pairs: int = 0
    bell_qubits: int = 0
    fresh_qotp_key_bits: int = 0
    teleportation_operations: int = 0
    controlled_swaps: int = 0
    teleportation_measurements: int = 0
    swap_measurements: int = 0
    message_preparation_operations: int = 0
    bell_pair_preparation_gates: int = 0
    qotp_unitary_applications: int = 0

    @property
    def measurements(self) -> int:
        return self.teleportation_measurements + self.swap_measurements

    @property
    def modeled_operations(self) -> int:
        return (
            self.message_preparation_operations
            + self.bell_pair_preparation_gates
            + self.teleportation_operations
            + self.controlled_swaps
            + self.measurements
            + self.qotp_unitary_applications
        )


def _validate_dimensions(n: int, lambda_parameter: int) -> tuple[int, int]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    if isinstance(lambda_parameter, bool) or not isinstance(lambda_parameter, int) or lambda_parameter < 1:
        raise ValueError("lambda_parameter must be a positive integer")
    return n, lambda_parameter


def physical_copy_counts(lambda_parameter: int) -> dict[str, int]:
    _, lam = _validate_dimensions(1, lambda_parameter)
    return {"p1": 2 * lam + 1, "p2": lam, "p3": lam, "total": 4 * lam + 1}


def encrypted_object_ledger(lambda_parameter: int) -> list[EncryptedObjectSpec]:
    """Return every single-qubit encrypted-object key block in one batch.

    A block is independently allocated; sampled bit strings are not required to
    be pairwise different.
    """
    counts = physical_copy_counts(lambda_parameter)
    rows: list[EncryptedObjectSpec] = []
    rows.extend(EncryptedObjectSpec("S3", "S5", "p3_key", f"p3[{j}]", 4) for j in range(counts["p3"]))
    for i in range(counts["p1"]):
        rows.append(EncryptedObjectSpec("S3", "S5", "s3_bell_key", f"p1[{i}]", 4))
        rows.append(EncryptedObjectSpec("S3", "S5", "x1_record_key", f"p1[{i}]", 8))
        rows.append(EncryptedObjectSpec("S4", "S5", "s4_bell_key", f"p1[{i}]", 4))
        rows.append(EncryptedObjectSpec("S4", "S5", "x2_record_key", f"p1[{i}]", 8))
    for j in range(counts["p1"] - counts["p3"]):
        rows.append(EncryptedObjectSpec("S6", "S7", "s6_bell_key", f"returned_p1[{j}]", 4))
        rows.append(EncryptedObjectSpec("S6", "S7", "x3_record_key", f"returned_p1[{j}]", 8))
    return rows


def fresh_key_bits_per_message_qubit(lambda_parameter: int) -> int:
    return sum(item.bit_length for item in encrypted_object_ledger(lambda_parameter))


def protocol_step_ledger(n: int, lambda_parameter: int) -> tuple[StepContribution, ...]:
    """Derive resource contributions from the physical-copy protocol steps."""
    n, lam = _validate_dimensions(n, lambda_parameter)
    copies = physical_copy_counts(lam)
    objects = encrypted_object_ledger(lam)

    def key_bits(step: str) -> int:
        return n * sum(item.bit_length for item in objects if item.encryption_step == step)

    def encryption_count(step: str) -> int:
        return n * sum(1 for item in objects if item.encryption_step == step)

    def recovery_count(step: str) -> int:
        return n * sum(1 for item in objects if item.recovery_step == step)

    return (
        StepContribution(
            "S1",
            "Prepare all p1, p2, and p3 physical message copies.",
            message_state_preparations=copies["total"],
            message_qubit_instances=copies["total"] * n,
            message_preparation_operations=copies["total"] * n,
        ),
        StepContribution(
            "S2",
            "Teleport every one of the 2*lambda+1 p1 copies from Alice to Bob.",
            bell_pairs=copies["p1"] * n,
            bell_qubits=2 * copies["p1"] * n,
            teleportation_operations=copies["p1"] * n,
            teleportation_measurements=2 * copies["p1"] * n,
            bell_pair_preparation_gates=2 * copies["p1"] * n,
        ),
        StepContribution(
            "S3",
            "Encrypt p3 references, S3 Bell-path objects, and X1 records with fresh key blocks.",
            fresh_qotp_key_bits=key_bits("S3"),
            qotp_unitary_applications=encryption_count("S3"),
        ),
        StepContribution(
            "S4",
            "Teleport all received p1 copies from Bob to Trent and allocate fresh S4/X2 key blocks.",
            bell_pairs=copies["p1"] * n,
            bell_qubits=2 * copies["p1"] * n,
            fresh_qotp_key_bits=key_bits("S4"),
            teleportation_operations=copies["p1"] * n,
            teleportation_measurements=2 * copies["p1"] * n,
            bell_pair_preparation_gates=2 * copies["p1"] * n,
            qotp_unitary_applications=encryption_count("S4"),
        ),
        StepContribution(
            "S5",
            "Recover/check p3, X1, and X2 protected objects; sample lambda recovered p1 copies without replacement and compare them with p3 references.",
            controlled_swaps=lam * n,
            swap_measurements=lam,
            qotp_unitary_applications=recovery_count("S5"),
        ),
        StepContribution(
            "S6",
            "Teleport the lambda+1 remaining p1 copies from Trent to Bob and allocate fresh S6/X3 key blocks.",
            bell_pairs=(lam + 1) * n,
            bell_qubits=2 * (lam + 1) * n,
            fresh_qotp_key_bits=key_bits("S6"),
            teleportation_operations=(lam + 1) * n,
            teleportation_measurements=2 * (lam + 1) * n,
            bell_pair_preparation_gates=2 * (lam + 1) * n,
            qotp_unitary_applications=encryption_count("S6"),
        ),
        StepContribution(
            "S7",
            "Recover/check X3 protected objects, sample lambda returned p1 copies without replacement, compare with p2, and retain the unique unsampled copy.",
            controlled_swaps=lam * n,
            swap_measurements=lam,
            qotp_unitary_applications=recovery_count("S7"),
        ),
    )


def step_rows(n: int, lambda_parameter: int) -> list[dict]:
    rows = []
    for item in protocol_step_ledger(n, lambda_parameter):
        row = asdict(item)
        row["n"] = n
        row["lambda_parameter"] = lambda_parameter
        row["measurements"] = item.measurements
        row["modeled_operations_for_step"] = item.modeled_operations
        rows.append(row)
    return rows


def summarize_resources(n: int, lambda_parameter: int) -> dict:
    n, lam = _validate_dimensions(n, lambda_parameter)
    steps = protocol_step_ledger(n, lam)
    copies = physical_copy_counts(lam)

    def total(field: str) -> int:
        return sum(getattr(item, field) for item in steps)

    key_bits = total("fresh_qotp_key_bits")
    expected_key_bits = fresh_key_bits_per_message_qubit(lam) * n
    if key_bits != expected_key_bits:
        raise RuntimeError("step ledger and encrypted-object key ledger disagree")

    return {
        "n": n,
        "lambda_parameter": lam,
        "execution_model": EXECUTION_MODEL,
        "p1_physical_copies": copies["p1"],
        "p2_physical_copies": copies["p2"],
        "p3_physical_copies": copies["p3"],
        "total_message_state_preparations": total("message_state_preparations"),
        "message_physical_qubit_instances": total("message_qubit_instances"),
        "s2_bell_pairs": copies["p1"] * n,
        "s4_bell_pairs": copies["p1"] * n,
        "s6_bell_pairs": (lam + 1) * n,
        "total_bell_pairs": total("bell_pairs"),
        "total_bell_qubits": total("bell_qubits"),
        "fresh_qotp_key_bits": key_bits,
        "quantum_transmitted_qubits": REQUIRES_CONFIRMATION,
        "classical_transmitted_bits": REQUIRES_CONFIRMATION,
        "teleportation_operations": total("teleportation_operations"),
        "s5_controlled_swap_gates": lam * n,
        "s7_controlled_swap_gates": lam * n,
        "total_controlled_swap_gates": total("controlled_swaps"),
        "teleportation_measurements": total("teleportation_measurements"),
        "swap_test_measurements": total("swap_measurements"),
        "total_measurements": total("teleportation_measurements") + total("swap_measurements"),
        "bell_pair_preparation_gates": total("bell_pair_preparation_gates"),
        "qotp_unitary_applications": total("qotp_unitary_applications"),
        "total_modeled_operations": sum(item.modeled_operations for item in steps),
        "peak_live_qubits": REQUIRES_CONFIRMATION,
        "fixed_lambda_scaling_in_n": "O(n)",
        "joint_lambda_n_scaling": "O(lambda*n)",
    }


def resource_scaling_rows(n_values=range(1, 21), lambda_values=(1, 2, 4, 8)) -> list[dict]:
    return [summarize_resources(n, lam) for n in n_values for lam in lambda_values]
