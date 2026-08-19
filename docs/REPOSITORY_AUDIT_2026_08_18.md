# Repository audit — 18 August 2026

Audit performed at `2dc997b` (branch `research/m094-protocol-freeze`, open as PR #175); the audit's
own changes live on `research/repository-audit-and-acceleration` so the freeze PR stays untouched.
Scope: the whole repository, not only M093/M094. Every number below was measured on this checkout
with `.venv-win` (CPython 3.11.16, Windows) and can be re-measured with the commands quoted.

**Verification state of the final branch:** full suite **2531 passed, 0 failed, 12 skipped in
15 m 11 s** (`-n 10 --dist loadscope`, CPython 3.14.6); repository integrity imports/orphans/
dependencies all pass; the diagnosis digest is unchanged at `48cd5e9c2354a365…` and
`CHECK_REPORT.json` still digests to `cbd3ff14caf18051…` with verdict `incomplete` (7 passed, 0
failed, 5 uncomputed). Every digest this audit touched is byte-identical to what it found.

**Toolchain note (19 August).** An application-control policy on this machine now blocks every
executable under `%APPDATA%`, which includes the uv-managed CPython 3.11.16 the earlier measurements
used and `uv` itself ("Une stratégie de contrôle d'application a bloqué ce fichier"). The only usable
interpreter is the system CPython **3.14.6** at `C:\Python314`, and a venv built from it runs
normally — the policy discriminates by publisher, not by path. Measurements taken before that change
are marked 3.11; anything after is 3.14.

This forced a check worth having: **the M094 mechanism is digest-stable across the two
interpreters.** Under 3.14.6 the diagnosis still digests to `48cd5e9c2354a365…`, the search still
examines 767 and refuses 764, and the adopted mechanism still digests to `3cd1314f4ed0fea0…` — the
same values recorded under 3.11.16. `ast.unparse`, which the mechanism digest ultimately depends on,
did not change its output. Reproducibility across 3.11/3.13 was assumed; across 3.11/3.14 it is now
measured.

This document reports what is true. It repairs nothing scientific: where a claim is too strong the
correction is to the claim, never to the record behind it.

---

## A. What the project actually demonstrates

### Demonstrated, with preserved artifacts and a replaying checker

| Milestone | What it establishes | Evidence |
|---|---|---|
| M087–M091 | Endogenous language extension over a state-owned meta-language, with arms, rollback proofs and conservation reports | `RESULT.json` + `check_m0*_result.py --require-result`, all gated in CI |
| M093 | The transformation *infrastructure* works on a real repository component: subprocess sandbox, A/B comparison, independent validation, transactional adoption, digest-verified persistence, exact rollback | `experiments/M093/M093.md`, adopted patch live at `mira_core/memory.py:107` |

M091's checker is the reference standard in this repository: it **replays the science** — re-runs the
acquisition, re-verifies certificates, re-materialises the qualification from a recomputed salt,
re-runs every arm — rather than reading booleans out of a result file.

### Precommitted and open

**M094** is frozen and unrun. Seven of twelve conditions are computed and true; five are
`uncomputed`; the checker's verdict is `incomplete`. This is accurately reported everywhere I
checked (`PROTOCOL.json`, `SCIENTIFIC_HYPOTHESES.md` H39, `DESIGN_AUDIT.md`, `CHECK_REPORT.json`).

### Not demonstrated — and correctly not claimed

- No autonomous diagnosis-and-repair result exists. H39 is neither supported nor refuted.
- No sequential repair, no improvement-enabling-improvement, no persistent multi-generation lineage.
- M092 is **aborted without verdict**; H38 and D062 remain unresolved.

I found **no overstated claim** in the top-level registers. The claim boundary in
`experiments/M094/PROTOCOL.json` sets all fourteen flags to `false`, including
`recursive_self_improvement` and `h39_supported`. The discipline here is working.

### Adversarial findings against M094

I tried to falsify the M094 mechanism rather than confirm it. Four probes:

**1. Rename invariance — passes at the component level, fails at the class level.**
Renaming `Goal`→`Zqx` and `Observation`→`Wvb` across a clean `git archive` copy of the repository
left the selected component unchanged (`mira_core/contracts.py`), which is the property that
matters most. But the *selected class* moved from `Goal` to `Wvb`. `Goal` and `Observation` both
measure demand 4, and the tie is broken by `sort` on the class name:

```python
key=lambda i: (-i.demand, i.component_path, i.capability, i.target, i.detail)
```

`i.target` is the class name. So which class gets repaired — and therefore the adopted mechanism
digest, and therefore the qualification draw — is currently decided by alphabetical order on an
identifier. This is a live tie, not a hypothetical one. **See §G, blocker 3.**

**2. Capability injection inverts the verdict — passes.** Inserting a structurally-matching
`as_mapping` into `Goal` removed it from the unmet set (5 → 4 unmet) without changing the selected
component. Supply genuinely reduces insufficiency; it never raises it.

**3. The adopted repair runs and agrees with the callers — passes.** The search accepts candidates on
a *structural* predicate and never executes them, so I executed the winner. It compiles, returns
`{'goal_id': …, 'instruction': …, 'success_criteria': …}`, agrees exactly with what the call sites
write by hand, and is JSON-serialisable. That the search never executes a candidate is still a real
gap (§G, blocker 2).

**4. Budget is not load-bearing above the closure point — passes, but `12` is arbitrary.**
Sweeping `MAX_COMPOSITION_LENGTH` over 2–14:

| length | examined | survivors | distinct behaviours | adopted |
|---|---|---|---|---|
| 2 | 92 | 0 | 0 | — |
| 3 | 308 | 0 | 9 | — |
| 4 | 605 | 0 | 36 | — |
| **5** | **767** | **3** | **63** | `3cd1314f4ed0` |
| 6–14 | 767 | 3 | 63 | `3cd1314f4ed0` (identical) |

The search **saturates at length 5**. The declared bound of 12 is therefore inert — which is what
P9 wants — but it is also more than twice the closure point and reads as a chosen number. The
honest statement is "the search closes at 5 and is saturated"; that is stronger than the current
disclosure and costs nothing.

Note also **survivors = 3 but surviving behaviours = 1**: all three winners are the same method
under three names (`as_mapping`, `to_dict`, `as_dict`). The accepted behaviour is unique; the digest
tie-break only chooses a spelling. Worth stating plainly, because "3 survivors" reads as more
search than actually happened.

---

## B. Repository debt

Measured over 644 tracked Python files / 148 053 lines.

### Real duplication

| Pattern | Copies | Assessment |
|---|---|---|
| `def _canonical_json` | 37 modules | Semantically identical in most cases |
| `def _digest` | 57 modules | Same |
| `class LineageError(RuntimeError)` | 8 modules | Identical |
| `def run_arm(...)` | 17 modules | Same shape, different bodies |
| `def rollback_proof(...)` | 5 modules | Same shape |
| `def meta_search(...)` | 6 modules | Same shape |
| Bespoke subprocess sandboxes | 9 modules | `tempfile.TemporaryDirectory` + `subprocess.run` |

**I did not factor these.** Retrofitting 57 modules to save ~200 lines, when many of them compute
digests recorded in frozen artifacts, is a large risk for a cosmetic gain — exactly the refactor the
brief says not to do. The right move is forward-only: a shared module used by *new* code, with the
historical copies left alone. See §C.

### Confirmed dead code

- `scripts/check_m094_result.py:187` — `_qualification_exists()` is defined and **never called**.
- `metamorphosis/m094_composition.py` — four of six refusal reasons never fire on the real target:
  `composition_does_not_apply`, `unrenderable`, `could_not_be_placed_in_the_class`,
  `modified_source_does_not_parse`. Measured: the refusal histogram at every budget contains only
  `incomplete_draft_is_not_a_method` and `requirement_not_satisfied`. `composition_does_not_apply`
  is *structurally* unreachable: `_compositions` only yields chains it has already grown
  successfully, and `search` then re-applies the same chain to the same initial draft.
- `build/` — 155 `.py` files, untracked and gitignored, a stale local artifact tree.

### Docstrings that do not match behaviour

1. **`scripts/run_m094_experiment.py`** — the headline defect. Its docstring says it connects
   diagnosis and synthesis with "the existing M093 transformation infrastructure (sandbox,
   comparison, adoption, rollback)". It imports `m094_diagnosis` and `m094_synthesis` and **nothing
   else**. It does diagnosis → synthesis → an in-memory `apply()`, prints a byte count, and exits.
   It never writes a file, never sandboxes, never compares, never validates, never adopts, never
   rolls back, and never produces a result artifact.
2. **`metamorphosis/m094_diagnosis.py:754`** — "Ties break on (demand, component path)". The
   implemented key is `(-demand, component_path, capability, target, detail)`. The omitted part is
   the part that decides (§A.1).
3. **`Dockerfile`** — "Default command: run the complete test suite", but it copies only
   `mira_core/`, `metamorphosis/`, `scripts/`, `tests/`. **56 test files read `experiments/` or
   `results/`**, neither of which is copied. The declared command cannot pass. Added in the same
   commit as the M094 runner (`a9cdaaf`) and, on this evidence, never built.

### Blocker 5 — seven of nine frozen qualification entries cannot be executed

Found by building the pipeline and running the qualification, which is the first time anyone
executed the pool's hidden cases rather than regenerating them.

The pool's *requirements* were produced by measurement, as the design audit says. Its **hidden
case values were synthesised from a seed and never run**. Constructing each entry's class from
its own five committed cases:

| entry | cases that construct | first error |
|---|---|---|
| `container.py::ContainerLimits` | 5/5 | — |
| `harbor.py::HarborEpisodeLimits` | 5/5 | — |
| `agent.py::AgentResult` | **0/5** | unexpected keyword `succeeded` (it is a computed property) |
| `calibration.py::EpisodeOutcome` | **0/5** | enum member passed as a keyword |
| `skills.py::SkillDemonstration` | **0/5** | missing required argument `source` |
| `container.py::ContainerSpec` | **0/5** | missing required argument `image` |
| `model.py::StructuredModelPolicy` | **0/5** | missing required argument `backend` |
| `model.py::ModelRequest` | **0/5** | missing required argument `output_schema` |
| `skills.py::TeacherCallTrap` | **0/5** | unexpected keyword `calls` (set in `__init__`, not declared) |

**7 of 9.** The cases carry only the fields the requirement mentions, not the fields the
constructor requires, and nothing checked that the class would accept them.

Why this is the most serious of the five: the draw with the current mechanism digest selects
`skills.py::TeacherCallTrap` and `container.py::ContainerSpec` — **both broken**. A run would
report that the adopted mechanism failed its qualification, and that would be false. The
mechanism does satisfy `TeacherCallTrap` when given cases that construct; `ContainerSpec` cannot
be constructed by any generic case builder, because `__post_init__` demands a sha256-pinned image
and an absolute path. The pool would refute H39 on its own account.

**Not repaired here.** `QUALIFICATION_POOL.json` is frozen, digest-bearing (`44f46e6b…`),
byte-exact protected, and pinned by tests. Editing it is the owner's decision. What is repaired
is the instrument's ability to lie about it: the harness now reports `unrunnable` as a third
outcome distinct from `refuted`, the qualification verdict is `incomplete` rather than `negative`
when any drawn entry is unrunnable, and P7 reports `uncomputed` in that case. A pool defect can
no longer present itself as evidence.

The options, in increasing cost: regenerate the hidden cases against the real constructors and
re-freeze the pool (changes `44f46e6b…`); or narrow the pool to the entries that can be
constructed, disclosing which were dropped and why; or keep the pool and accept that the
qualification is partly unrunnable, which means H39 cannot be settled on it.

### The frozen protocol carries an audit digest that matches nothing

`experiments/M094/PROTOCOL.json` records `design_audit.audit_digest = d41ea1ea84e0767c…`. That value
matches **no committed artifact**:

| candidate | digest |
|---|---|
| `sha256(DESIGN_AUDIT.md)` | `236c438dcc9547cd…` |
| `sha256(DESIGN_AUDIT.json)` | `8ddb92267591665a…` |
| `DESIGN_AUDIT.json`'s own `digest` field | `37eee413397f9907…` |
| **what the protocol records** | **`d41ea1ea84e0767c…`** |

Tracing the file's history explains it without excusing it: `d41ea1ea…` was the audit's internal
digest at commit `0d23bfd`. The next commit, `f516bc7` ("remove the constant that was deciding"),
changed the audit and moved its digest to `37eee413…`. The protocol, frozen later, carried the older
value forward. The same `design_audit` block then describes content that only exists in the *newer*
audit — `defects_found_before_freeze: 12`, and the whole Defect 5 narrative. So the block pairs a
stale digest with current prose.

Nothing catches this. `scripts/check_m094_result.py:48` binds `DESIGN_AUDIT_MD` and **never uses
it** — the check that would have caught the drift was named and not written. (I left that binding in
place rather than deleting it as dead code: unlike `_qualification_exists`, it marks a missing check
rather than a duplicated one.)

**Not repaired here, deliberately.** The protocol is frozen and says it may not be repaired. A frozen
artifact carrying an unverifiable digest is a disclosure item and possibly a withdrawal item, and
that is the owner's call, not an auditor's edit. Nothing scientific turns on it *yet* — no result
exists — but "the audit is bound by digest" is not currently true, and the run should not proceed
while it isn't.

### The freeze commit is not reachable from `main`

PR #175 was rebased before merging. `dd79665`, cited as the freeze commit by both
`SCIENTIFIC_HYPOTHESES.md` H39 and `experiments/M094/DESIGN_AUDIT.md`, is **not an ancestor of
`main`**; the freeze landed as `9b69d7f`, and the commit recording it as `312bbb1`. The trees are
byte-identical (`e2ab1c1b` and `73eab62b` respectively), so no content moved — but a verifier
starting from a fresh clone could not resolve the hash the record names. Both hashes are now recorded
in those two documents rather than the old one overwritten. `source_commit_audited` (`df88d24`) is
unaffected and still reachable.

### Unprotected digest-bearing artifacts

`experiments/M094/CHECK_REPORT.json` (carries `report_digest`) and
`experiments/M094/DESIGN_AUDIT.json` (carries `digest`) have **no `.gitattributes` entry**, while
M092's equivalents do. This is the checkout-dependent-hash defect the repository has already fixed
three times (M064, M086-A, and 34 artifacts on one day per `DESIGN_AUDIT.md`). Both files are LF on
this checkout today, so nothing is currently wrong — the guard is simply missing.

### Duplicated eligible-set literals

The M094 eligible component set is written out four times:
`scripts/check_m094_result.py:53`, `scripts/run_m094_experiment.py:29`,
`scripts/author_m094_qualification_pool.py:41`, and `experiments/M094/PROTOCOL.json`.
Only the checker's copy is guarded against drift (`check_p1` compares it to the protocol). The
runner's copy is unguarded.

### No CI gate for M093 or M094

`.github/workflows/ci.yml`'s `sealed-bank-boundary` job gates M075, M085, M087, M088, M089, M090,
M091 and M092. **M093 and M094 appear nowhere.** `scripts/check_m094_result.py` is never executed by
CI, so the M094 freeze is currently enforced only by the unit tests in `tests/test_m094_checker.py`.

### Not debt — deliberately preserved

- 27 milestone runners with no inbound reference (`run_m076_grounding.py`, `run_m089_experiment.py`,
  …). These are the reproduction entry points for frozen results. Deleting them destroys
  reproducibility.
- `metamorphosis/m094_transform.py` (the authored template) and
  `metamorphosis/m094_component_discovery.py` (the substring diagnostic). Both are *superseded*, and
  both are load-bearing evidence: the design audit measures Defects 1–4 against them, and
  `m094_transform.py` is the substrate for the declared `template_only_repair` control arm.
- The 36 archived workflows in `archives/workflows/` and the six dormant M092 workflows.

I also checked for orphan-scanner gaming: **no test module exists that imports repository modules
without containing any test function.** That smell is absent.

---

## C. Architecture worth keeping

**The M087–M091 lineage shape.** Five milestones independently converged on the same seven steps,
which is empirical justification for an engine rather than speculation about one:

```
LineageError · observe_limitation/diagnose_limitation · meta_search/acquire_primitive
  · validate_candidate · rollback_proof · conservation_report · run_arm · evaluate → Verdict
```

**The M091 checker discipline.** `evaluate()` lives in the lineage module and the checker *replays*
it. This is what makes a result reproducible rather than assertable.

**The M093 transformation primitives.** `run_in_sandbox`, `compare_ab`, `validate_independently`,
`TransformationStore` (adoption + exact rollback + journal + restart). Sound, and explicitly not
re-litigated by M094.

**The protocol/freeze/falsifier/claim-boundary convention.** Genuinely rigorous. The M094 design
audit self-found twelve defects, including four in its own checker, and disclosed a withdrawn
result rather than tidying it away.

---

## D. Architecture to replace

**1. M094 put the verdict logic in the checker instead of the lineage.**
`scripts/check_m094_result.py` is 1121 lines containing all twelve conditions; there is no
`m094_lineage.py` with `run_arm`/`evaluate`/`rollback_proof`. Every other milestone from M087 does
it the other way round. This is not a style preference — it is *why* five conditions can never be
computed (§G, blocker 1).

**2. M093's "reusable" infrastructure is not reusable.** `validate_independently()` hardcodes the
module name `"memory"`; `run_in_sandbox()` defaults `dependency_modules=("contracts",)` and copies
from a fixed `mira_core`. M094 targets `contracts.py`, so it cannot call either as they stand. This
is the concrete reason the M094 runner has no pipeline: there was nothing generic to call.

**3. Exhaustive enumeration as the default search.** M092 spent an enormous canonical search and was
aborted without a verdict. M094's search is already the better pattern (BFS over a state graph with
fingerprint dedup, saturating at 767 examined in 0.4 s) — it just is not described that way.

---

## E. Cleaning performed

Every change in this pass is either a documentation-truth correction or a technical repair that
provably alters no measurement. Nothing scientific was repaired after the fact.

| Change | Justification |
|---|---|
| `scripts/run_m094_experiment.py` — docstring rewritten to state exactly what the script does; eligible set now read from `PROTOCOL.json` | The docstring claimed a pipeline that does not exist; the private copy of the eligible set was the one unguarded copy of four |
| `metamorphosis/m094_diagnosis.py` — `diagnose()` docstring states the real tie-break | The stated rule omitted the term that decides. **The rule itself is unchanged.** |
| `scripts/check_m094_result.py` — `_qualification_exists()` removed | Defined, never called |
| `metamorphosis/m094_composition.py` — dead refusal branch documented | Four of six refusal reasons cannot fire; silently deleting them would remove a defensive check, so they are labelled rather than removed |
| `Dockerfile` — copies `experiments/` and `results/` | Its declared default command could not pass without them. **Fix is static, not build-verified**: the Docker CLI is present (29.7.2) but the Desktop Linux engine was not running on this machine, so no image was built. |
| `.gitattributes` — `experiments/M0*/CHECK_REPORT.json` and `experiments/M0*/DESIGN_AUDIT.json` marked byte-exact | Both carry digests; both were unprotected; both are already LF, so no digest changes |
| `SCIENTIFIC_HYPOTHESES.md` (H39) and `experiments/M094/DESIGN_AUDIT.md` — the freeze's reachable commit recorded alongside the authored one | The recorded hash does not resolve on `main` after the rebase. Both hashes kept, so the chronology survives |
| `pyproject.toml`, `docs/THIRD_PARTY_DEPENDENCIES.md`, `COMMAND_LINE_TOOLS` — `pytest-xdist` declared | 3.0× on the full suite with identical results (§F.5). **A new third-party dependency — confirm or revert** |

**Refused, and why.**

- **No factoring of the 37/57 digest-helper copies.** Many feed frozen artifacts. Forward-only
  sharing instead.
- **No deletion of unreferenced milestone runners.** They are the reproduction path for frozen
  results.
- **No deletion of `m094_transform.py` or `m094_component_discovery.py`.** Superseded, but they are
  the evidence for the design audit's defects and the substrate for a declared control arm.
- **No change to the tie-break rule.** It is a genuine weakness (§A.1), but changing it moves the
  adopted mechanism and therefore the qualification draw. That is the owner's call, before the run.
- **No M092 workflow removal.** Dormant and provenance-bearing.

---

## F. Performance

Measured on this machine.

| Stage | Cost | Note |
|---|---|---|
| `diagnose()` over 3 components | **6.4 s** | Dominant cost of the whole M094 loop |
| — of which: repository AST parse | ~3.7 s | `ast.parse` called **1935×**: 644 files re-parsed once per component |
| — of which: `_reaches_component` | ~5 s cumulative | Called 2446×, each an `ast.walk` of a whole file |
| `composition.search()` at saturation | **0.4 s** | 767 candidates examined |
| Full `run_m094_experiment.py` | 8.5 s | 76 % diagnosis |
| M094 unit tests (diagnosis+composition+synthesis) | 1.7 s | Good inner loop |
| M094 checker + design-audit + pool tests | **57.8 s** | Dominated by repeated `diagnose()` calls |
| Full suite (2543 tests, 200 files) | **37 min** (3.11) / **46 min** (3.14) | 0 failures on 3.14 |

### F.1 Measured, output-identical acceleration

Memoising the repository parse **and** the reachability decision, verified against the baseline
diagnosis digest `48cd5e9c2354a365…`:

| variant | time | digest identical |
|---|---|---|
| baseline | 6.37 s | — |
| + parse cache | 6.40 s | yes |
| + reachability cache | **3.09 s** | yes |
| warm re-run in the same process | **0.67 s** | yes |

**2.1× cold, 9.5× warm, byte-identical output.** The parse cache alone buys nothing — `Path.resolve()`
per file on Windows eats the saving — so both caches are needed. This matters far more than 6 s
suggests: a qualification run re-diagnoses once per control arm, and there are six arms.

**Applied**, with the run-harness work, as this section said it should be. Two caches in
`m094_diagnosis`: parsed sources keyed by `(path, size, mtime_ns)`, and the reachability
predicate keyed by the same plus the module and its exported names. Both are pure functions of
file bytes, both self-invalidate when a file changes, and `TransformationStore` calls
`clear_caches()` on every write rather than trusting filesystem timestamp resolution to keep a
measurement honest.

Measured after the change: **5.4 s cold, 0.70 s warm**, diagnosis digest still
`48cd5e9c2354a365…`. It stopped being an optimisation and became a prerequisite:
`tests/test_m094_checker_replay.py` calls `compute_report` twenty times, and without the caches
that file exceeded a ten-minute timeout.

### F.2 Search — a correction: it does not scale

**This section originally said "search does not need accelerating", on the strength of 767
candidates in 0.4 s. That was one measurement of one target, generalised. It is wrong.**

Measuring the search on every unmet insufficiency in the eligible set, rather than only on the
one the diagnosis happens to rank first:

| class | fields | requirement keys | candidates examined | survivors | distinct behaviours | time |
|---|---|---|---|---|---|---|
| `Policy` | 1 | 1 | 47 | 3 | 1 | 0.0 s |
| **`Goal`** | **3** | **3** | **767** | **3** | **1** | **0.3 s** |
| `SafetyDecision` | 4 | 4 | 3 071 | 3 | 1 | 1.2 s |
| `Action` | 4 | 2 | 12 287 | 192 | **64** | 6.0 s |
| `Observation` | 5 | 7 | **196 607** | 3 | 1 | **101 s** |

Two things follow, and both matter more than the timing.

**The cost is exponential in field count, and the development target is the cheapest case in
the set.** `Goal` at 767 candidates is not representative; it is the minimum. The *next*
insufficiency the diagnosis would select after `Goal` is repaired is `Observation`, at 196 607
candidates and 101 seconds — 336× the development target. So M095's second repair is not
"another repair like the first"; it is the first thing that makes this search architecture hurt,
and a seven-field class would be in the millions.

**The adoption tie-break is arbitrary when the requirement is a strict subset of the fields.**
`Action` has four fields and a two-key requirement, so 192 survivors span **64 behaviourally
distinct** methods — any method binding those two keys correctly passes, whatever else it does.
For `Goal` the accepted behaviour was unique and the digest tie-break only chose a spelling
(§A.4). For `Action` the mechanism would pick one of 64 genuinely different methods by content
address, with no principled reason. That is not a defect in the frozen protocol — P6 asks the
repair to be assembled rather than templated, and it is — but a milestone claiming the lineage
*constructs the repair* is weaker when 64 constructions qualify and the choice among them is a
hash.

Both findings are properties of the operation set and the bound, which the protocol already
names as the expected next ceiling. Neither is a reason to delay M094's run; both are reasons
not to plan M095 around the assumption that repair #2 resembles repair #1.

### F.3 Docker

The Docker CLI is installed (29.7.2) but **the Desktop Linux engine was not running during this
audit**, so nothing here is measured against a container — including the Dockerfile fix in §E.

The honest assessment regardless: **local Python is faster and sufficient today.** The whole M094
loop is 8.5 s single-threaded; container start-up alone would exceed the work.

Docker earns its place at exactly two points, both later:
- **parallel arm execution** once the six control arms exist and each costs seconds-to-minutes;
- **a stable Linux environment** for the two Windows-specific suite failures.

The Dockerfile must be fixed first (§E) — as committed it cannot run the suite it advertises.

### F.4 Where the 37 minutes actually go

Two full runs, on the two interpreters the toolchain change forced:

| interpreter | result | wall clock |
|---|---|---|
| CPython 3.11.16 (uv, now blocked) | 2529 passed, **2 failed**, 12 skipped | **36 m 49 s** |
| CPython 3.14.6 (system) | **2531 passed, 0 failed**, 12 skipped | **46 m 19 s** |

The two failures under 3.11 were the pair this project had recorded as expected on Windows —
`test_blind_bank_sealing.py::test_the_repository_itself_carries_no_leak` (stats a WSL symlink inside
`.venv`) and `test_m092a_substrate_migration.py::test_physical_isolation_without_the_legacy_module`
(rebuilds `sys.path` from the POSIX `lib-dynload` layout). **Under 3.14 both pass**, and the same
collection count means nothing was skipped instead.

I cannot attribute that cleanly, and will not pretend otherwise. Two things changed together: the
interpreter (3.11.16 → 3.14.6) and the venv's provenance (uv-built → `C:\Python314`-built). The
broken `.venv/lib64 → lib` symlink is still on disk, so the blind-bank case is more likely the
interpreter; the `lib-dynload` case is more likely the venv layout. With 3.11 now blocked I have no
way to A/B it. What is established is narrower and still useful: **the "two expected Windows
failures" note is no longer true of this environment**, so a future green run must not be explained
away by it.

3.14 is also **26 % slower** on this workload (46 m 19 s vs 36 m 49 s), consistently across the
per-fixture durations. Neither 3.14 nor this Windows host is in the CI matrix (3.11 and 3.13), so
this is a local datum, not a CI regression.

The cost is extremely concentrated. Eight fixtures account for roughly **18 of the 37 minutes** on
3.11 (**22 of the 46** on 3.14):

| duration | test |
|---|---|
| 204 s | `test_m064_real_substrate_completion.py` (setup) |
| 129 s | `test_m063_control_transfer.py` (setup) |
| 129 s | `test_m062_synthesized_control.py` (setup) |
| 110 s ×3 | `test_m061_discovered_structure.py` (setup ×2, call ×1) |
| 88 s | `test_m066_canonical_governance.py` (setup) |
| 87 s | `test_m065_qualified_completion.py` (setup) |

These are all **setup**, all in the frozen M061–M066 band, and all recomputing deterministic
substrate material. They are the single largest acceleration lever in the repository — larger than
anything in M094.

**Do not cache them.** My first instinct was a digest-keyed fixture cache, and it is the wrong
answer: the recomputation *is* the evidence. A cached fixture makes the test pass without
re-deriving the frozen result, which is the "checker passes in the absence of evidence" failure
this repository already guards against elsewhere. A stale or wrongly-keyed cache would turn a
reproduction proof into a tautology, and the saving is not worth that.

**Parallelise instead.** Everything still recomputes; it just recomputes concurrently. The machine
has 12 logical cores, the eight expensive fixtures are in different modules, and the tests are
already order-independent (`-p no:randomly` is a convenience, not a requirement). `pytest-xdist`
with `--dist loadscope` keeps each module-scoped fixture on one worker, so no fixture runs twice.

That means a new third-party dev dependency, which in this repository means a `pyproject.toml`
entry, a row in `docs/THIRD_PARTY_DEPENDENCIES.md`, and an addition to `COMMAND_LINE_TOOLS` in
`check_repository_integrity.py` (which otherwise reports it as declared-but-never-imported). That is
the owner's call, so the sequence is measure first, declare second — see §F.6.

Third on the list at 52 s is `test_m094_checker.py` setup, which the §F.1 memoisation addresses.

### F.5 Parallel execution — measured, 3.0×

| run | result | wall clock |
|---|---|---|
| serial (3.14.6) | 2531 passed, 12 skipped | 46 m 19 s |
| `-n 10 --dist loadscope` (3.14.6) | **2531 passed, 12 skipped** | **15 m 28 s** |

Identical outcomes, **3.0× faster**, on a 12-logical-core host. `loadscope` groups tests by module so
each module-scoped fixture is computed on exactly one worker — the eight expensive M061–M066 fixtures
run concurrently with each other instead of one after another. Nothing is cached and nothing is
skipped: every frozen result is still recomputed.

`pytest-xdist` (MIT, pulling `execnet`, MIT) is now declared in the `dev` extra, recorded in
`docs/THIRD_PARTY_DEPENDENCIES.md`, and allowlisted in `COMMAND_LINE_TOOLS` so
`check_repository_integrity.py --dependencies` still passes. **This is the audit's one new
third-party dependency**, and the IP register's per-milestone wording ("no new third-party package is
introduced") means it should be confirmed rather than assumed: it is dev-only, never imported, not
redistributed, and reverting it is a two-line change.

The suggested default for local work is `-n 10 --dist loadscope`; CI should stay serial until the
owner decides, because a parallel CI run changes which failures are reproducible from the log.

### F.6 Validation pyramid

The current habit of running 40 minutes for a five-line change is the largest avoidable cost.

1. **Inner loop (1.7 s)** — `pytest tests/test_m094_{diagnosis,composition,synthesis}.py`
2. **Milestone (58 s → ~10 s with F.1)** — add `tests/test_m094_{checker,design_audit,qualification_pool}.py`
3. **Infrastructure (~1 min)** — `python scripts/check_repository_integrity.py --imports --orphans --dependencies`
4. **Integration** — the touched milestone's `check_m0*_result.py`
5. **Full suite** — before merge or freeze only. 15 m 28 s with `-n 10 --dist loadscope`,
   46 m serial.

---

## G. Is M094 ready to freeze?

> **Status as of 19 August.** Blockers 1 and 2 are closed — the pipeline exists and the checker
> can reach `positive`. Blockers 3 and 4 remain open and both need an owner decision. Building
> the pipeline surfaced a fifth, described in §B, which is the most serious of the five.


**It is already frozen and now merged to `main`** (authored at `dd79665`, landed as `9b69d7f`; PR
#175 closed). The correct question is whether it is **ready to run**, and the answer is **no**. Four
blockers. This is a minimal list, not a wishlist — each one is something without which the run cannot
produce a verdict, or cannot produce a verifiable one.

### Blocker 1 — the checker can never return `positive` — **CLOSED**

This is the serious one. `verdict_rule` is *"positive only when every condition is computed and
true"*. Trace what happens the moment a run produces artifacts:

- **P7** fails. Its implementation is `present = [n for n in ("RESULT.json", "QUALIFICATION.json",
  "REGISTER_CLAIM.json") if exists]; if present: passed=False`. Producing a result **fails** the
  condition named "the adopted repair satisfies a requirement drawn after the mechanism was fixed".
- **P12** fails too — `if (EXPERIMENT / "RESULT.json").exists(): failures.append(...)`.
- **P8, P9, P10, P11** contain no branch that reads a result at all. They validate protocol
  preconditions and then return `not_computed` unconditionally. They will return `not_computed`
  forever.

So: before a run the verdict is `incomplete`; after a run it becomes `negative`. **`positive` is
unreachable by construction.** The checker is a pre-run *protocol validator* wearing the name of a
result checker — which is what its own header admits ("Because M094 has never been run, there is no
RESULT.json to validate against"), but the protocol's `verdict_rule` does not know that.

*Fix:* give each of P7–P12 the branch it lacks — read the preserved artifacts and recompute — using
`scripts/check_m091_result.py` as the model. Not a rewrite: the pre-run behaviour stays as the
`else` branch.

### Blocker 2 — the pipeline the protocol assumes does not exist — **CLOSED**

The protocol commits to adoption (P7), independent validation (P8), a budget arm (P9), a
random-selection arm (P10), exact behavioural rollback (P11), and seven declared arms. What exists
is diagnosis → synthesis → an in-memory string. There is no `m094_lineage.py`, no `run_arm`, no
`evaluate`, no `rollback_proof`, no adoption, no sandbox execution of a candidate, no arm runner.
M093's primitives cannot be called as they stand (§D.2).

*Fix:* generalise M093's four primitives to take the module and its dependencies as parameters, then
build `m094_lineage.py` with `run_arm`/`evaluate`/`rollback_proof` in the M091 shape. The
qualification draw must stay in a separate process that the lineage cannot import — the existing
`tests/test_m094_qualification_pool.py::no_module_the_lineage_runs_reads_the_pool` already guards
this and must keep passing.

### Blocker 3 — the repair target is decided by alphabetical order

`Goal` and `Observation` tie at demand 4; `i.target` in the sort key breaks it by name (§A.1). The
choice determines the adopted mechanism digest, which seeds the qualification draw. It is
deterministic and reproducible, so it is not fraud — but "the selection is justified against rivals
by measurement" (P5) is not true of the class-level choice, and a reviewer who runs the rename probe
will find this in ten minutes.

*Fix — owner's decision, three options:*
1. **Disclose it.** Amend the design audit to state that class-level ties are broken by name, and
   narrow P5's claim to the component level. Cheapest; changes no digest.
2. **Break the tie by measurement.** Add a measured secondary term (e.g. number of distinct demand
   sites). Changes the adopted mechanism and the draw; must be done *before* the run and recorded.
3. **Repair both.** Synthesise for every class tied at the top. Strongest, and closest to what the
   milestone claims.

Option 1 is defensible and immediate. Option 3 is the one that makes the milestone say what it wants
to say.

### Blocker 4 — the frozen protocol's audit digest identifies nothing

`design_audit.audit_digest = d41ea1ea…` in the frozen `PROTOCOL.json` matches no committed artifact;
it is the audit's digest from two commits before the freeze (§B). The binding that would have caught
it, `DESIGN_AUDIT_MD` in the checker, was declared and never used.

This is the only blocker I cannot propose a fix for, because fixing it means editing a frozen
protocol. The options are the owner's: record an erratum alongside the protocol without touching it,
or withdraw and re-freeze. Either is legitimate; silently correcting the digest is not, and neither
is running while the protocol's own audit binding is unverifiable.

### Also worth closing before the run

- ~~Add the M094 gate to `ci.yml`'s `sealed-bank-boundary` job.~~ **Done.**
  `check_m094_result.py --strict --no-write` now runs there, and the checker has exit codes so it
  can actually gate: `--strict` fails on a failing computed condition, `--require-result` also
  demands a run and a positive verdict. The latter is deliberately not enabled yet — it would fail
  on a repository where the experiment has correctly not been performed.
- State the search closure at 5 rather than the inert bound of 12, and state that the three
  survivors are one behaviour under three names (§A.4).

---

## H. Roadmap — the shortest path to a cumulative loop

The target is not a milestone count. It is: **a persistent lineage that chains several autonomous
transformations, at least one of which causally increases its ability to produce the next.**

### The human dependencies, and where each one dies

| Human dependency | Removed by |
|---|---|
| Which component to change | **M094** (frozen, unrun) |
| What the change is | **M094** |
| What to fix *next*, with no human between repairs | **M095** |
| Whether the search *can* reach the next repair at all | **M095** (the causal control) |
| The repair language itself | **M096** |
| Context reconstruction across restarts | **M097** |

This is three milestones after M094, not four. The brief sketched sequential repair and
improvement-enabling-improvement as separate milestones (M095 and M096); §H.2 argues for merging
them, which shifts the two after it down by one.

### Step 0 — the Genesis Experiment Engine (prerequisite, not a milestone)

Justified by measurement, not by taste: M086B–M091 converged on the same seven functions
independently (§C), and M094's pipeline gap exists precisely because M093's primitives were
milestone-shaped.

```
GenesisExperiment
  Observe · Diagnose · Propose · Search · Sandbox · Evaluate · Compare
  Validate · Adopt · Persist · Restart · Rollback · RunControls · Qualify · Evidence
```

Generic and reusable: provenance, digests, transactions, sandbox, rollback, restart, evidence,
condition state, verdict, arm execution.
Supplied per milestone: hypothesis, admissible world, limitation measure, transformation language,
qualification generator, falsifiers, controls.

Build it by **generalising M093's four primitives** and extracting the M091 arm/verdict shape — not
by designing from scratch. Land it with the F.1 memoisation. Then M094's blockers 1 and 2 are
mostly instantiation.

### Step 1 — run M094

One scientific run. No reroll. Whatever the verdict says.

### Step 2 — M095, merged: sequential repair **and** improvement-enabling-improvement

The brief warns against milestone inflation, and this is where it applies. A second repair that
does not enable anything is a weak result; the enabling claim is the one that matters. Test both in
one protocol:

```
S0 —(limitation A, autonomous)→ repair A → S1 —(limitation B, autonomous)→ repair B → S2
```

with the causal control that carries the weight:

- **S0 cannot reach B** — demonstrated by exhausting S0's transformation language against B. (This
  is where exhaustive search is *right*: proving closure, not finding improvements.)
- **S1 can reach B** — B is found and adopted from S1.
- **Counterfactual: without A, B stays unreachable** — same budget, same operations, no A.

Conditions that must hold: the second target is not supplied; the second repair is not supplied; no
human input after S0; S1 is genuinely the starting state of the second search.

### Step 3 — M096, endogenous transformation-language extension

Genesis measures that its own operation set is insufficient, constructs a new operation, installs it
into the *active* language, and then performs a transformation that was previously impossible. The
falsifier that matters: the executor must actually consult the new operation. Registering it is not
extending the language. M090/M091 already did this for the meta-language; this does it for the
repair language.

### Step 4 — M097, persistent autonomous lineage

`S0 → S1 → persist → process death → restart → S2 → death → restart → S3`, each generation starting
only from persisted state, with no human reconstruction of context. M093's `TransformationStore` and
M084's persistent lineage are the substrate.

**On the merge.** Sequential repair and improvement-enabling-improvement share a state chain, an
arm set and a qualification generator; run separately, the second rebuilds almost all of the first.
The merge is only worth it if the causal control survives it. If the counterfactual arm turns out to
need its own protocol to stay honest, split them again — a weakened control is worth less than an
extra milestone.

### The rule to apply at every decision

Does this reduce a human dependency in the table above, or is it apparatus around the problem? If
apparatus: factor it, simplify it, or delete it. An experiment that removes no dependency does not
earn its place.

---

## What is deliberately not claimed here

No AGI claim. No recursive self-improvement claim. M094 has not run, and a single repair would not
support such a claim if it had. The target is narrow and stated in §H: a persistent lineage chaining
several autonomous transformations, at least one of which causally increases its capacity to produce
the next.
