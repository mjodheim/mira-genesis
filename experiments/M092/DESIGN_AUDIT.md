# M092 design audit — resolved before any freeze

**Status: design gates 1–5 and 10 resolved. Nothing is frozen. H38 and D062 are unclaimed.
No qualification exists, and none may be generated until the M092-A checkpoint is frozen.**

This document exists because the M092 direction was approved *conditionally*. It records the audit
the approval demanded, including one place where the obvious design was wrong and had to be
changed. Numbers come from `scripts/audit_m092_design.py`, re-runnable, and are stored in
`DESIGN_AUDIT.json`.

Starting point: clean `main` at `e68b85ea43653fdeeb5ada4847a7a57f235eefc7`. M091 is historical
evidence from here on; its protocol, qualification, result, checker and record are read and imported,
never edited. M089 remains the preserved negative.

---

## Gate 1 — substrate ownership is separated from substrate extension

M092 stays one milestone with two causally distinct, separately frozen internal stages. The second
may not begin until the first is checkpointed.

### M092-A — state-owned substrate migration

Start from exactly M091 semantics. Move the micro-operation definitions out of host-language
authority into serialized substrate state that actually determines execution. **Zero new expressive
capability.** M092-A introduces no operation, no operator, no constant and no signature that M091
did not already have.

Today `run_body` in `metamorphosis/m090_language.py` is the authority: it branches on
`MICRO_OPERATIONS` by name, and `_binary` and `_unary` are host functions with hard-coded
arms. After M092-A the authority is serialized state, and the host retains only a lower kernel that
branches on no micro-operation identifier — the same move M090 made one level up, applied one level
down.

Conservation must be proved against the pre-M092 interpreter over: every inherited well-formed body;
every declared input/domain combination; every refusal; signatures; capability checks; M091 acquired
primitive behaviour; serialization and deserialization; and fresh-process execution.

State must be **execution authority, not metadata**. Deleting or corrupting an inherited
micro-operation in serialized substrate state must remove or corrupt that capability in a fresh
process, and the host source must not silently reconstruct it.

An explicit M092-A checkpoint digest is frozen before any extension search or qualification may run.
**If exact migration fails, M092 stops as negative or inconclusive.** It may not be rescued by
introducing new semantics at the same time.

### M092-B — endogenous substrate extension

Only after that checkpoint. The chain, each arrow with an ablation that breaks everything downstream:

```
frozen lower kernel
  → generated substrate-operation program
  → independent validation
  → registration into serialized substrate state
  → new language primitive built on the acquired substrate operation
  → previously unreachable correctness-critical transformation
```

---

## Gate 2 — the oscillation observation is replaced by an exact theorem

The 3,588-body enumeration is **not** the impossibility argument. It is corroboration, and it is
reported as corroboration.

### What was wrong with the informal version

Two things, and both were fatal as stated.

*"Alternations are bounded roughly by `2^(body length)`"* is length-dependent, so a larger search is
a live threat to it — which is exactly what `more_budget_same_substrate` must be immune to.

And **"monotone" was the wrong word.** The inherited substrate contains `neg`, so it contains
decreasing maps. A decreasing map has alternation count 1 and is not monotone nondecreasing, so the
two notions come apart and a bound proved in one does not transfer to the other. The replacement
below never counts alternations and never uses the word.

### Proposition M092-I (eventual polynomiality)

Fix a distinguished input position `k`. Fix every other input and every initial slot to integer
constants. Then for every program `P` over any language state whose primitive bodies are sequences
of M091 micro-operations — any number of primitives, any program length, any body length within the
interpreter's bound — and every slot `j`, there exist a polynomial `p ∈ Z[X]` and a threshold
`X₀ ∈ N`, **both computed from `P`**, such that

```
slots_j(x) = p(x)     for every integer x ≥ X₀.
```

**Assumptions**, stated so they can be attacked: integer semantics with no overflow or wraparound;
argument positions (`slot`, `input`, `const`, `unary_op`) are fixed per call and never data-dependent,
so there is no indirect addressing; the operator sets are exactly `{add, sub, mul, max}` and
`{inc, dec, neg, double}`; the initial state is all zeros, which is in the domain.

**Proof.** The germ at `+∞` of every value is a polynomial, by structural induction over the
micro-operations. `PUSH_CONST` and `PUSH_INPUT` on a fixed input give constants; `PUSH_INPUT` on `k`
gives `X`. `add`, `sub`, `mul` and the four unary operators are ring operations, and `Z[X]` is closed
under them. For `max(f, g)`, the difference `d = f − g` is a polynomial; if `d ≡ 0` the two agree,
and otherwise `sign(d(x))` equals the sign of `d`'s leading coefficient for every `x` beyond `d`'s
Cauchy bound `1 + max|aᵢ|/|a_lead|`, so `max` returns one of its arguments' germs and raises `X₀` to
that bound. `DUP`, `SWAP`, `PUSH_SLOT` and `STORE_SLOT` move germs without creating values. Programs
compose bodies, and composition of germ-preserving maps is germ-preserving, so the statement does not
weaken as programs lengthen. ∎

**This is a decision, not a widening.** `max` is *resolved*, not over-approximated, so
`germ_of_body` returns the true germ. That matters: a conservative abstraction could be vacuously
safe, and this one cannot hide behind imprecision.

**Exact bound.** Only `mul` raises degree, and it combines two stack entries, so one micro-operation
at most doubles the largest degree present: `deg ≤ 2^(body_length × program_length)`. The bound is
recorded because the gate asked for one; it is **not load-bearing**, because the evaluator computes
the actual degree and the corollary holds at every degree.

### Corollary M092-P (parity is unreachable at any budget)

No such `P` satisfies `slots_j(x) = x mod 2` for all `x ≥ 0`.

**Proof.** Otherwise `p(x) = x mod 2` for all `x ≥ X₀`, so `p` takes only the values 0 and 1 on an
infinite set of integers. A non-constant polynomial is unbounded, so `p` is a constant `c`. But
`x mod 2` takes both values above `X₀`, so `c = 0` and `c = 1`. ∎

The certificate is finite and re-checkable: for any germ, `refute_parity` returns an even and an odd
integer above the threshold, where the germ *is* the slot value, so the disagreement is real and not
an abstraction artefact.

### Concrete-interpreter cross-check

| Check | Scope | Result |
|---|---|---|
| Soundness against `m090_language.run_body` | 165,514 bodies over the full frozen assembly space, every declared binding, 4 probe points each | **1,941,600 exact agreements, 0 mismatches, 0 refusal disagreements** |
| Highest degree actually reached | — | 2 — so `mul` is exercised, not merely handled |
| Highest threshold actually reached | — | 7 — so the `max` decision is exercised, not merely handled |
| Closure under composition over M091's real `L1` | 1,500 programs, up to **200** primitive calls | **0 mismatches** |
| Parity among enumerated germs | 485,400 germs | **0 matches** |

The composition row is the one that retires the budget objection. `more_budget_same_substrate` is
negative because germ composition is closed, not because an enumeration was truncated.

---

## Gate 3 — the lower kernel is not tailored to parity

This was treated as the most important risk, and it produced the audit's strongest result.

### Several insufficiency axes, all blocked by the *same* invariant

| Axis | Blocked by M092-I? | Why |
|---|---|---|
| A1 parity, `x mod 2` | yes | germ would be a bounded polynomial, hence constant |
| A2 any non-constant periodic function | yes | same argument; boundedness forces a constant |
| A3 floor division, `floor(x/k)` | yes | differs from every polynomial on unboundedly many `x` |
| A4 bit or digit extraction | yes | periodic in `x`, so A2 applies |
| A5 super-polynomial growth, `2^x` | yes | outgrows every polynomial, so no germ matches |
| A6 `gcd(x, k)` for fixed `k` | yes | periodic in `x`, so A2 applies |

One invariant blocks periodicity, integer division, digit access **and** super-polynomial growth.
That is the evidence that it is a structural property of the inherited substrate rather than a
property reverse-engineered from parity.

### Several minimal lower-kernel designs

| Candidate | Escapes? | Contains the answer or its shape? | Note |
|---|---|---|---|
| K1 fuel-bounded conditional-jump register machine | **yes** | **no** | escapes with decrement, subtract and a conditional jump; no modulo, no target predicate |
| K2 counted `LOOP n { body }` | yes | yes | "repeat `x` times" hands the induction on `x` over directly |
| K3 primitive-recursion combinator `fold(n, init, step)` | yes | yes | same objection as K2 |
| K4 comparison + conditional `SELECT`, no iteration | **no** | no | eventually one branch wins; germ closed — **insufficient** |
| K5 more registers, wider constants, `min`/`abs`, longer bodies | **no** | no | all ring or lattice operations; germ closed — **insufficient** |
| K6 indirect addressing, address wraps modulo register count | yes | yes | escapes *only* because wraparound is modulo |
| K7 floor division by a constant | yes | yes | `floor(x/2)` and `x mod 2` are interdefinable |

### Why this answers the tailoring objection

The concern was that `LOOP` would be introduced *because parity needs iteration*, moving authored
expressive power one layer down. The audit answers it in the stronger direction available:

**Iteration is forced, not chosen.** K4 and K5 are genuine expressive additions — branching,
comparison, more registers, wider arithmetic, longer programs — and *every one of them stays inside
the invariant*. No non-iterative extension escapes. So iteration is not a convenience selected with
the target in view; it is the mathematically identified boundary.

**Among iterative designs, K1 is the most target-neutral.** K2 and K3 supply induction on `x`
directly, which is the shape of the answer. K6 and K7 escape only by containing modulo outright. K1
escapes using nothing but decrement, subtract and a conditional jump — demonstrated in the audit by
a generic two-register counter machine containing no parity operation.

**Selected: K1.** The smallest general, target-neutral execution kernel that could support a family
of substrate extensions — parity, floor division, digit extraction, bounded exponentiation — and not
a machine built around `x mod 2`.

### Prohibited kernel contents, to be enforced by scanner and checker

The frozen kernel must contain no parity or modulo operation; no target-specific predicate; no target
lookup or table; no candidate catalogue containing the answer; no output vector; no qualifying-world
constants; no branch recognizing the experiment; no host callback implementing candidate semantics;
and no hidden developer import capable of recovering the solution.

### The kernel is still authored, and becomes the next ceiling

Stated here so it cannot be presented later as a discovery. K1's instruction set, register model,
numeric semantics, fuel rule, serialization and execution rules are **ours**. M092 moves the ceiling
from the assembly substrate to the lower execution kernel. That is not self-hosting and not substrate
independence, and neither term may appear in the result.

---

## Gate 4 — boundedness, and the flaw this audit actually caught

### The flaw

The obvious design was: fuel-bounded kernel, constant fuel `F`, so the acquired operation computes
parity on the declared domain `D = {0..N}` with `N` fixed by `F`.

**That design is broken, and it would have produced an unsound positive.** The impossibility theorem
M092-P is *unbounded* — no inherited program computes parity for all `x ≥ 0`. A constant-fuel
acquired operation is *bounded* — it computes parity only on `D`. The two never meet. And on a
bounded domain the impossibility does **not** hold: nothing in M092-I stops a sufficiently long
inherited program from matching a sawtooth on a finite set, so `more_budget_same_substrate` would
have been a live threat rather than a settled one. The two halves of the causal chain would have been
describing different claims.

### The fix

The kernel requires every loop to strictly decrease a designated non-negative register — a
**well-founded loop variant**. Termination is then structural, and the acquired operation is **total
on all of `x ≥ 0`**, not merely on a declared window. Fuel becomes a *safety net against malformed
candidates*, not the semantic bound.

Verified: with a variant-respecting program, `steps = x` exactly, and `fuel = 2x + 8` is total and
correct across `0..2999` with the step count linear in `x` by the variant argument.

The impossibility and the acquisition now cover **the same unbounded domain**, which is what makes
the comparison meaningful.

### Declared before qualification exists

Operand domain, machine-state domain, register count, maximum program length, fuel rule
(`fuel(x) = slope·|x| + base`, constants declared and target-neutral), serialization and execution
rules are all frozen before qualification information exists. The fuel rule is derived from the loop
variant — a property of the *program* — and never from a target value or a qualifying world.

### What is claimed, exactly

- **Proved unbounded:** no inherited program computes `x mod 2` for all `x ≥ 0` (M092-P).
- **Proved total:** the acquired operation computes `x mod 2` for all `x ≥ 0`, by the loop variant
  plus a linear step bound.
- **Verified finitely:** correctness is exhaustively checked on a declared finite verification domain,
  because a test is finite.

**Honest limit, recorded now.** The empirical arms are judged on a finite declared domain while the
theorem is unbounded. A fixed-substrate arm that passed the finite test would be a genuine
falsification of the design and will be **reported as such**, not explained away.

---

## Gate 5 — BFS is a synthesis mechanism, not an impossibility proof

Behaviour-deduplicated BFS is approved for candidate generation only. It is **not** the semantic
proof of unreachable behaviour. The impossibility argument is M092-I/M092-P and nothing else.

Deduplication from sampled observations is labelled a **search optimisation** unless the behavioural
abstraction is proved complete for the claimed state and domain. The default is the honest label.

Required record: generated programs; structurally invalid programs; deduplicated programs; validator
refusals by reason; surviving candidates; adopted candidate; exact program bytes and AST; semantics
digest; search order; deterministic seed.

---

## Gate 10 — parity-specific anti-cheating requirements

Periodic bounded targets invite truth-table solutions, so the leakage scanner must detect embedded
target vectors; ordered lists matching domain size; large literal sets correlated with outputs; chains
of equality tests over qualifying inputs; domain-indexed tables; encoded bit masks; candidate-specific
fixtures; and callbacks or imports providing equivalent semantics.

Deliberate cheating fixtures will be planted and the scanner and checker required to reject them,
after which the exact clean state is restored and re-digested. **A correct output table is not
endogenous semantic acquisition.**

---

## Gates 6–9 and 11–15 — carried forward as binding protocol obligations

Resolved in principle, to be encoded in `PROTOCOL.json` at the freeze and enforced by the checker:
registration as executable state rather than a host function (6); the `built_but_not_registered`
distinction (7); a genuinely downstream language acquisition with a full dependency ablation
matrix (8); qualifying tasks establishing new reach rather than cheaper reach, with no search-speed
improvement counting (9); independent validation with a binding receipt and a checker that recomputes
the verdict, with no `--skip-*` escape hatch (11); exact rollback at all three boundaries compared by
serialized bytes (12); cross-family reuse by composition rather than a second target-specific
operation (13); freeze discipline with artifact-derived attempt provenance (14); and the conjunctive
verdict rule (15).

---

## Standing constraints

Track A, zero model calls and zero network during qualification. Human-only attribution: Anthony Mets
is the sole human contributor identity, and no AI co-author trailer or tool-credit metadata is added.
M091 and M089 artifacts are read-only. M093 is not implemented. A clean negative M092 is a better
outcome than a positive whose lower kernel already contains the answer.
