# M039 — canonical three-cycle cumulative lineage protocol

**Status: FROZEN PROTOCOL CANDIDATE.** These bytes become active only when their SHA-256
and the fully tested mechanism commit are recorded in `results/M039_FREEZE.md`. No canonical
task has been derived or observed at this point.

## 1. Canonical question

Can one bounded deterministic lineage, starting from one founder and one unrevealed seed:

1. complete three sequential strict body expansions `F0 -> F1 -> F2 -> F3`;
2. prove before every expansion that the active body is structurally insufficient;
3. construct one lineage-owned macro from the accepted cycle-1 trace;
4. use that exact earlier macro as a proposing block in adopted cycles 2 and 3;
5. fail equal-budget primitive-only ablation on both later targets;
6. survive one fixed failing provisional change per cycle and restore the exact accepted state;
7. reproduce from seed every task, observation, certificate, symbolic expansion, rejection,
   proposal, evaluation, event byte, tool event, rollback, counter, head and final body?

The Gate-2 and Gate-9 verdicts are separate. Neither may compensate for failure of the other.

## 2. Bounded claims

A positive first run supports **bounded Gate 2** only if one tool:

- has `origin = lineage_constructed`;
- has `construction_kind = composition` and `introduction_phase = cycle`;
- is described exactly by one valid persisted `ToolConstructed` event;
- consumes only registry entries that predate its construction cycle;
- appears in a later adopted proposal's exact `ToolReused` event;
- is required by equal-budget ablation.

A positive first run supports **bounded Gate 9** only if:

- exactly three cumulative cycles are accepted;
- the same earlier tool is reused in a later accepted cycle;
- the full seed-to-head replay reproduces the causal journal byte for byte;
- exhaustive search-audit mappings and digests reproduce every hidden rejected path;
- the final body, manifest, counters and externally committed heads match.

The experiment does not claim migration, unknown-substrate transport, post-migration
plasticity, open-ended evolution, general intelligence or consciousness.

## 3. Domain and state

Bodies are deterministic finite automata over alphabet `{0, 1}`. Exact equivalence,
separating words and minimal state counts are decidable.

The state carried across cycles is:

```text
active DFA
portable learning state
persistent tool registry
accepted-cycle count
RNG algorithm/state where applicable
```

Cycle `n + 1` receives the exact accepted state of cycle `n`. The registry and portable state
may not reset. Audit state is append-only and rollback never erases it.

## 4. Frozen task generator

The canonical master seed is unknown until the marker-only arming commit exists. From it the
implementation derives independent 64-bit cycle seeds by the committed domain-separated
function in `metamorphosis/m039_lineage.py`.

The generator is exactly:

1. `F0 = normalize(random_minimal_dfa(cycle_seed_1, 4, 4))`;
2. cycle 1 selects the first deterministic primitive-registry program, in committed order and
   within depth/budget, whose normalized target:
   - has more minimal states than F0;
   - is not reachable at a shorter symbolic depth;
   - admits the exact incapacity certificate from all words of length at most 6;
3. the accepted cycle-1 primitive expansion is composed into one lineage-owned macro;
4. cycles 2 and 3 select the first deterministic two-block program containing that macro and
   one birth primitive, in committed order, whose normalized target:
   - has more minimal states than the current body;
   - admits the exact incapacity certificate;
   - is not reachable by primitive-only search at depth 2;
5. generator exhaustion within any committed bound is a canonical negative result. No seed
   replacement, bound widening or task-family substitution is permitted.

The proposal mechanism receives the current body, admitted oracle evidence, registry and
budgets, never the hidden target DFA. The independent exact evaluator receives the target.

## 5. Frozen constants

| Constant | Value |
|---|---:|
| cycles | `3` |
| alphabet | `{0, 1}` |
| observation words | all binary words of length at most `6` (`127`) |
| founder minimal states | `4` |
| cycle-1 symbolic depth | `3` |
| later symbolic depth | `2` |
| task attempts | `32` |
| task program ceiling | `100000` |
| candidate-search node ceiling per cycle | `150000` |
| exact certificate node bound | M038 committed value |
| exact certificate prefix bound | M038 committed value |
| provisional failure probe | `flip(initial)` after each adoption |
| canonical Python | `3.11` |
| task-family count | one three-cycle chain |

## 6. Birth registry and macro cost

The birth registry is the deterministic sequence returned by `all_atoms() + growth_atoms()`.
Every birth entry is protocol-supplied and permanently ineligible for Gate 2.

A composed macro counts as one symbolic block for later depth. Every primitive in its
expansion is still charged in `primitive_expansion_operations`; macro use cannot erase its
computational cost. The canonical result reports symbolic and expanded costs separately.

## 7. Structural trigger

For each target the lineage queries exactly the 127 committed words. It computes the exact
maximum pairwise-distinguishable-prefix certificate under M038's frozen deterministic
bounds. Escalation is allowed only if:

```text
certificate lower bound > minimal active-body state count
```

The checkpoint commits body, registry, evidence, certificate, rolling trace, counters,
protocol and task identities. Slow-path verification recomputes the certificate from the
admitted evidence.

## 8. Candidate search and exhaustive transcript

Operational proposal follows the exact registry and depth ordering in
`metamorphosis/m039_engine.py`. Evidence-admitted candidates are causally journalled before
independent exact evaluation.

An independent audit in `metamorphosis/m039_search_audit.py` re-enumerates every symbolic
expansion and every completed body up to the adopted candidate, including bodies rejected by
the first mismatching observation. It commits:

- registry order;
- symbolic prefix and selected tool;
- primitive expansion count and success;
- raw and normalized body digests;
- evidence verdict and first mismatch;
- exact evaluation and separating word;
- accepted candidate identity;
- a canonical transcript digest.

The audit's nodes, primitive operations and completed-body count must equal the engine's
committed counters. Initial execution and independent replay must produce identical audit
mappings, not merely identical totals.

## 9. Tool provenance and reuse

The cycle-1 macro contains its canonical expanded atom program, committed input tool IDs,
lineage/cycle/protocol identities, replay digest and deterministic construction identifier.

The independent provenance verifier starts from authoritative journal bytes. It verifies the
journal chain, then requires:

- exactly one `ToolConstructed` event for the identifier;
- exact field-for-field equality between that event and the final registry entry;
- every input present and introduced before cycle 1;
- exact equality between manifest uses and all `ToolReused` events;
- every reuse after construction and during a later cycle;
- the tool ID in the equal-budget ablation-required set.

The engine's own eligibility list is diagnostic only. The canonical public Gate-2 list is the
output of this independent journal verifier.

## 10. Rollback

After each exact adoption, the fixed `flip(initial)` provisional body is evaluated. The run is
invalid if it remains exactly equivalent. Otherwise the journal appends provisional adoption,
evaluation, rejection, rollback request and rollback completion. The completed rollback state
digest must equal the accepted pre-probe state digest exactly while audit history remains.

## 11. Journal and replay

M039 uses `m039-lineage-journal/1`, leaving frozen M038 bytes unchanged. The journal spans all
three cycles in one chain and allows only ordered checkpoints 1, 2 and 3.

Replay receives only:

- canonical master seed;
- frozen protocol commitment and constants;
- primitive-registry specification/digest;
- externally committed expected manifest/final-body/cycle-head values.

It does not receive generated DFAs, evidence tables, accepted programs, candidate IDs, tool
outputs or final bodies as construction inputs.

Success requires:

- exact manifest digest;
- exact final body digest;
- exact cycle heads;
- byte-identical full journal record sequence;
- identical journal-record digest and final lineage head;
- identical independent provenance result;
- identical exhaustive search-audit mappings/digests.

## 12. Canonical seed derivation

The arming commit must be the direct child of the frozen parent and change exactly
`experiments/M039/CANONICAL_ARMED.json` with commit message:

```text
m039(canonical): arm first immutable run
```

Let `arming_head_sha` be its full lowercase 40-hex SHA and `protocol_sha256` the hash of this
file's exact bytes.

```text
master_nonce = SHA256(
  "m039:sealed-head:" || arming_head_sha || ":protocol:" || protocol_sha256
)

task_seed = uint64_be(first_8_bytes(SHA256(
  "m039:" || master_nonce || ":task:0"
)))
```

No task value may be calculated before the immutable arming commit exists.

## 13. Canonical outcomes

The workflow must preserve one JSON artifact regardless of scientific sign.

`gate2_supported = true` only when the journal-verified public tool list is non-empty and both
later ablations fail.

`gate9_supported = true` only when three cycles, later reuse, rollback, seed-to-head records
and exhaustive search audits all pass.

`combined_expected_claim_supported = gate2_supported and gate9_supported`.

Generator exhaustion, capacity-certificate failure, search exhaustion, missing reuse,
ablation success, provenance mismatch, rollback divergence or replay divergence is a
canonical negative. Integrity failures in marker/protocol/head binding abort execution.

## 14. Falsifiers

The combined claim is false if any occurs:

1. fewer or more than three accepted cumulative cycles;
2. a cycle begins from anything other than the previous accepted state;
3. any target does not require more minimal states than its starting body;
4. any trigger lacks an exact valid incapacity certificate;
5. the tool lacks one exact construction event or consumes a non-prior input;
6. later adopted traces lack exact reuse events;
7. either later primitive-only ablation succeeds;
8. any provisional probe fails to force a rejection or exact rollback;
9. replay receives generated outputs from the first run;
10. any journal byte, head, manifest field, counter or final body diverges;
11. any hidden search expansion/rejection/order or transcript digest diverges;
12. the run uses another seed, widened bounds or replacement first result;
13. ordinary tests or non-arming commits open the block;
14. any M038 frozen identity or artifact changes.

## 15. First-run procedure

1. freeze these bytes and the tested mechanism in `results/M039_FREEZE.md`;
2. archive all development/freeze workflows;
3. create exactly one marker-only arming commit;
4. guarded workflow checks head, parent, message, changed path and protocol hash;
5. derive the unseen seed and run once on Python 3.11;
6. write and upload the JSON even for a negative scientific outcome;
7. verify first-run metadata and archive/disable the live canonical workflow;
8. commit the artifact byte for byte and publish a scoped report;
9. merge only after permanent Python 3.11/3.13 and repository-integrity CI are green.
