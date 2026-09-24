# Methods and Scope

## Repeated Swap Test

For pure-state fidelity `F = |<psi|phi>|^2`, a single Swap Test accepts with probability `(1+F)/2`. For `m` independently prepared instances with identical fidelity, all tests accept with probability `((1+F)/2)^m`; for non-identical instances, the all-accept probability is the product of `(1+F_j)/2`. The orthogonal expression `1-2^(-m)` is used only when `F=0`.

The numerical table evaluates six fidelities and seven values of `m`, with 50,000 trials per point and a fixed seed. The maximum analytical-versus-Monte-Carlo absolute error is 0.0052066686517652.

## Protocol simulation

Each Monte Carlo trial represents one protocol execution with `2*lambda+1` independent physical `p1` copies, `lambda` `p2` copies, and `lambda` `p3` copies. After all relevant states and encrypted records are committed, Trent samples `lambda` of the recovered `p1` copies uniformly without replacement for S5. If every explicit S5 comparison accepts, the remaining `lambda+1` copies are returned through S6. Bob then samples `lambda` of those copies uniformly without replacement for S7 and retains the unique unsampled copy as the output instance associated with an accepted batch.

Seven scenarios are evaluated for `lambda=1,2,4,8` with 4,000 trials per point. Every selected physical pair has its own fidelity, effective fidelity, acceptance probability, and sampled outcome. The protocol noise parameter is the phenomenological state-level replacement `F_eff=(1-noise)F+noise/2`; it is not a gate-level, channel-level, Aer, or IBM hardware noise model. In the consistency-only diagnostic, `alice_scenario_1` can remain statistically indistinguishable from honest execution.

## Fresh key allocation

Every encrypted physical object receives an independently allocated key block from a deterministic simulated QKD key pool. A unique block identifier is bound to each object and may be consumed exactly once. Independent sampling does not require the resulting bit strings to be pairwise different. For an `n`-qubit message, the encrypted-object ledger derives `(64*lambda+36)n` fresh key bits under the object mapping used by the numerical model.

## State-fidelity diagnostics

Bob-operation detection is computed from the resulting state fidelity. A non-identity operation does not by itself imply state-level distinguishability. Pauli X acting on `|+>` gives fidelity 1 and zero Swap-Test detection probability. This observation concerns the verification component and does not by itself determine protocol-level forgery success.

## Resource accounting

The operation ledger accumulates resources from S1-S7. It derives `(4*lambda+1)n` physical message-qubit instances, `(5*lambda+3)n` Bell pairs, `2(5*lambda+3)n` Bell qubits, `(5*lambda+3)n` teleportation operations, `2*lambda*n` controlled-SWAP gates, and `(64*lambda+36)n` fresh QOTP key bits. Under the documented macro-count convention, its total modeled operation count is `(53*lambda+28)n+2*lambda`; this is not a backend-transpiled native-gate count.

For fixed `lambda`, the unambiguous cumulative quantities are linear in `n`; treating both variables jointly gives `O(lambda*n)`. Quantum/classical communication totals and peak-live-qubit counts are marked `REQUIRES_MANUSCRIPT_CONFIRMATION` because their exact values depend on unresolved definitions of encrypted records and staging/liveness.

## Hardware evidence

No new hardware execution was performed. The existing composed circuit-level candidate contains one verification instance (`m=1`) and has 773 successes in 1,024 shots. Repeated rows derived from direct single-test estimates assume independent identical executions and are explicitly classified as derived. The existing circuit is not the full physical-copy batch with `5*lambda+3` Bell pairs.
