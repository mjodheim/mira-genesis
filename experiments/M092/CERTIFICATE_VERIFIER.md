# M092-B exact certificate verifier

**Status: implemented after the protocol freeze; development rehearsal only. No M092-B search,
candidate, qualification, validation receipt, extended substrate or result exists.**

`metamorphosis/m092_certificate_verifier.py` implements the independent algebraic boundary frozen
in `PROTOCOL.json`. It imports only `metamorphosis.m092_kernel` and
`metamorphosis.m092_runtime`; it does not import a candidate builder, qualification module or
artifact, and it does not execute a candidate while deciding its theorem.

## Accepted proof fragment

The verifier accepts a deliberately incomplete but sound fragment:

- exact arbitrary-precision integer affine equalities and inequalities;
- at most one recomputed loop header and two explicit ghost counters (`g0`, `g1`);
- no more than eight normalized constraints at that header;
- candidate-supplied integer combination witnesses for every establishment, preservation,
  infeasible-path, exit-postcondition, variant and initial-bound obligation;
- a non-negative affine variant that decreases by at least one on every feasible back path;
- a structural linear step bound recomputed from the CFG and checked against K1's frozen
  `256 + 4 * magnitude` fuel rule.

For an inequality goal `G >= 0`, a witness must show exactly

`G = sum(m_i * equality_i) + sum(n_j * inequality_j) + slack`,

where every `n_j` and `slack` is non-negative. Equality goals may use equality premises only and
have zero slack. The certificate carries the premises, goal, multipliers and slack; the verifier
recomputes the first two from the exact program and checks the latter two without searching for a
replacement. Strict integer branches are normalized as affine inequalities, so `a < b` becomes
`b - a - 1 >= 0`.

## Program and frame binding

The certificate's `program_digest` is SHA-256 over the exact canonical K1 program. Its CFG must
equal the verifier's recomputation, all instructions must be reachable, and the program is limited
to the twelve opcodes and three literals frozen in the protocol. A variable-by-variable `MUL`
leaves the accepted affine fragment and is refused.

The frame proof is structural rather than sampled. Symbolic execution begins with an opaque stack
prefix followed by `x`; no path may pop the prefix or grow above the entry depth; every feasible
loop path preserves the prefix; and every feasible halt leaves exactly one symbolic output above
it. The forbidden opcode partition proves slots and inputs unchanged and the call argument unread.

## Neutral development rehearsal

`tests/test_m092_certificate_verifier.py` supplies the one positive rehearsal authorized by the
frozen protocol: a seven-instruction countdown that maps every non-negative top operand to zero.
Its invariant, ghost counter, strictly decreasing variant and `5 + 3*x` step bound are proved over
the unbounded domain. Executions at `0`, `1` and `9` only check the harness and frame; they are not
used by the theorem verifier.

The same test file injects a wrong program digest, a false induction witness, a non-decreasing
variant, a wrong postcondition, a false frame claim and forbidden finite output vectors. All are
decisive refusals. It also parses the verifier's imports and fixes the project-module boundary to
the two modules named above.

The qualifying remainder program is not constructed or executed by this rehearsal. H38 and D062
remain unclaimed.
