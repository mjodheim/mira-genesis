# Changelog

## Unreleased

- Added M091, in which the lineage adds an operation to the language it actually owns. **Positive,
  attempt 1, no retry**, fourteen frozen conditions computed and passed; H37 supported, no gate.
  Protocol frozen at `5e4a0fe`, result `d83b836d...4c07af`, 0 model calls.
- Chose an expressive gap that is deliberately **not** M089's. That one was fan-in and is spent;
  M091's requirement reads one input position and is instead **non-affine**, and the validator
  refuses M090's fan-in probe as overbroad. The insufficiency is proved by a closure lemma over the
  whole abstract domain — a one-step property that induction carries to any length and therefore any
  budget — an abstraction re-checked against the concrete interpreter, and a finite certificate that
  refutes an infinite class with three non-collinear points.
- Answered the M055 falsifier by measurement rather than argument: the `macro_only_extension` arm
  reproduces M055 on purpose, memoizing a composition and cutting its own search from 38,848
  programs to 5,477 and its program from four operations to three, and solves 0/2 qualifying worlds.
  The adopted primitive appears in the same table with the opposite entry — unreachable without it,
  two operations with it. Cost is not reach.
- Split the generic search into `m091_search` so the persistence check holds the interpreter, the
  requirement schema and nothing that could rebuild a primitive. The fresh process prints its own
  import census and it is checked.
- Registered M091's digest-bearing artifact paths in `.gitattributes` in the same commit as the
  frozen protocol, before any digest existed, and verified the committed blob is byte-identical to
  the working tree. Recorded the pre-publication IP disposition as P-007 in the same commit.
- Raised the sealed-bank CI job's timeout to 30 minutes and made `check_m091_result.py` decisive
  there: it re-runs the acquisition, re-verifies every certificate against the requirement and the
  body, re-materializes the qualification from a recomputed salt, replays every arm including the
  depth-six budget arm, and recomputes the verdict.

- Added M086-C, the third attempt at H32 and the first that could have failed for a scientific
  reason. **Nine of ten conditions passed; P2 failed.** H32 moves from untested to **not supported**
  by the two attempts with a qualified instrument, M086-B and M086-C — a statement about those
  attempts, not a finding that meta-plasticity is impossible.
- Corrected the bank grammar after M086-B by probing what M047's templates can actually repair:
  `add` and `mul` collide with `tool_core`, `mul` has no product expression, and a tool named
  `max` shadows its own builtin. **`mean` is the only repairable missing-route operation**, so the
  routeless operation cannot vary and the protocol says so rather than pretending to a choice.
- Recorded, before the run, the falsifier that then fired: a `mean a b c` case is passed by both
  the `mean` and `midpoint` expressions whenever the operands are arithmetic, the frozen order
  takes `midpoint`, and the hidden cases decide. The salt drew `1 2 3`, and the adopted patch was
  `synthesize_tool:mean:midpoint`.
- Recorded D054 and a FAILURE_LOG entry naming what was never mutable: every meta-primitive acts on
  the hypothesis schema or the rule set, and the greedy selection rule that picks the adopted
  candidate is frozen and human-authored. Capability to generate is not capability to solve.

- **Reclassified M086 as M086-A, post-hoc disqualified development evidence.** Review of PR #130
  found four defects: the recorded protocol digest binds the CRLF working-tree copy rather than the
  committed blob (the M064 class recurring), P8 was never implemented and P7–P10 never entered
  `evaluate()`, the holdout existed before the meta-search, and the replay covered 3 of 14 fields
  per arm. H32 returns to untested; no gate moves.
- Preserved every M086-A artifact, digest, CI record and history entry unchanged. Only the claim was
  withdrawn, and `experiments/M086/DISQUALIFICATION.md` states why.
- Recorded D053 and a FAILURE_LOG entry. The four defects share a shape: each makes part of the
  frozen contract unenforceable while leaving every visible signal green.

- Added M086, which makes the mechanism that turns evidence into candidate transformations a mutable
  artifact. M047 froze it in one line — `ModuleDiagnosis.sufficient` is `self.module is not None` —
  and against evidence naming two stages at once it emits **zero** candidates.
- Proved the expression faithful before using it: over 10 differential probes on two bodies, M0
  returns the same diagnoses and the same candidate sets as M047's own functions.
- Enumerated the starting mechanism's complete constructive image for the holdout and found it empty,
  so the control's failure is structural rather than budgetary — a capability difference, which is
  what M084's efficiency-only result said the next milestone had to produce.
- Recorded that the lineage rejected seven meta-transformations on disposable descendants before
  adopting one, and that the adopted one was **not** the composition the protocol predicted: widening
  the hypothesis schema alone sufficed.
- Kept the evaluator outside the mutable body, enforced by a checker: the mechanism cannot name the
  hidden cases, cannot reach the sandbox, and the meta-search is only ever handed the development
  limitation. M069 is the recorded precedent.
- Studied HyperAgents (arXiv 2603.19461) from the paper and the official repository and recorded
  `docs/HYPERAGENTS_COMPARISON.md`: their question was taken, their method refused, and the archive,
  population and parent selection deliberately postponed.
- Recorded H32, D052, and two FAILURE_LOG entries: a latent defect in M047's `render_tool_module`,
  which emits a self-recursive `def max` for a tool named `max` and is deliberately **not** repaired
  because it would change M047's preserved digests; and an M086 bank whose repair revealed a new
  fault while a greedy tie-break locked in a wrong alias, which looked like a clean negative and was
  a property of the bank.

- Prepared M085, the first experiment here aimed directly at G4, and left it **blocked**. Its design
  protocol, domain adapter contract, intake kit, maintainer brief, fail-closed gate and 32
  regressions are committed; no scientific protocol is frozen, no bank exists, no payload has been
  requested and no held-out domain has been drawn.
- Built a separate external boundary rather than reusing M075's. That validator hard-codes refusal
  thresholds, the `gpt-5.6-sol` identity and a refusal-transfer-only claim, so a G4 protocol fails
  it on every such field. `exact_mcnemar_two_sided` is imported from M075 rather than restated, and
  M075's own private experiment remains open and unsubstituted.
- Made correctness the primary outcome, not cost. The bank must supply tasks where an action is
  accepted without effect, a later step is only correct if it took effect, and committing on the
  false premise reaches a terminal state the budget cannot undo. The freeze validator rejects a
  protocol that promotes a cost metric to the primary outcome.
- Made the held-out domain undrawable in advance: it comes from the sealed payload digest and a salt
  the maintainer withholds until after the protocol is frozen.
- Chose the threshold and the minimum bank size together — six discordant tasks give an exact
  two-sided p of 0.03125, five give 0.0625 — and asserted both halves in a regression so neither can
  be moved alone.
- Recorded H31 and D051. Running M085 on project-authored domains is listed as a prohibited
  adaptation, because it is the cheap substitute available on any day the external route feels slow.
- Built the organism-side shim before any bank exists, and found what named negative 5 anticipated:
  M084's `Embodiment` abstracted acting and observing, while the organism still reached into M084's
  own carrier tables in **ten** places — memory keys, memory contexts, carrier costs, probe carriers,
  the seeded carrier, the value alphabet and the one-carrier-at-a-time read.
- Routed all ten through a registered `DomainView`. M084's three substrates register views built from
  the tables they already used, and every arm re-derives its recorded numbers exactly.
- Added a wiring control on a toy domain sharing no vocabulary with M084, and recorded in
  `FAILURE_LOG.md` that its first version passed while running zero probes and zero repair cycles: a
  modulo cost formula made the discarding slot expensive, so the planner routed around the trap it
  existed to hit. The control now fails if it does not exercise repair.

- Added M084, one persistent lineage crossing `shell → browser → desktop → shell` in four separate
  operating system processes. It reached 11/11 reachable goals scored from environment state,
  refused 5/5 unreachable ones with zero false refusals, and on its return to the shell — with
  carrier names the first stage never saw — needed no diagnostic probe, no repair cycle and no
  affordance discovery.
- Composed the Phase 8 mechanisms instead of restating them: M077's journal, M080's bounded table,
  M079's plan enumeration and the M081–M083 environments are all imported, and a regression and the
  checker fail if any is redefined.
- Extracted M079's uniform-cost plan enumeration into `metamorphosis/bounded_search.py` so both
  experiments use one copy. Behaviour-preserving: M079's checker re-derives its arms live and still
  reproduces result `5f7ccf21`.
- Added `DesktopEnvironment.colour_at` for targeted single-cell reads, 0.3 s against 8.9 s for the
  whole grid. `state` is unchanged and the M083 result is untouched.
- Recorded that M081, M082 and M083 are **interface** results: the agent they carry across four real
  substrates replays an action list computed by their bank generator and detects no failure. M084
  deliberately does not import it, and the protocol, a regression and the checker enforce that.
- Answered the M082 state-ownership failure structurally rather than by inspection. Each stage runs
  in a separate process against an organism file, the parent never calls a perception, planning or
  action function, and the organism records the digest of the file it loaded.
- Detected a corruption injected after stage 1 **in the stage-2 child** and restored to the digest
  stage 1 had recorded before the corruption existed, never to the checkpoint's own digest.
- Recorded amendments A1–A3 from two pre-materialization rehearsals on throwaway salts. A1 fixes a
  carrier-rejection predicate that generalized from one-sided evidence and made the lineage falsely
  refuse a reachable goal; the zero-false-refusal clause is what caught it.
- Recorded H30 and D050. **No generality gate advances.** The ablation costs no correctness, so
  persistence bought cost and earliness rather than capability, and a fact learned in one substrate
  is never offered to another, so nothing here is cross-domain transfer.

- Added M083, a real X11 desktop session as a fourth environment under M081's unchanged
  four-action interface. It is addressed only by mouse clicks at screen coordinates and observed
  only by decoding exact palette colours from a screenshot; the interface completed all five
  completable tasks.
- Stated in the protocol, the result, a regression and the checker that this is **not a virtual
  machine**. A container shares the host kernel, no hypervisor was available, and the only VM
  present was the host's own WSL2 distribution. G6's desktop-VM clause remains unmet.
- Discovered the client-area origin from the X server at run time instead of assuming it. The
  window manager places the window where it chooses, and an assumed origin painted and read
  different cells while every call still returned success.
- Dropped the keyboard by design, with the reason recorded: xdotool could not focus a Tk entry,
  and a clicked palette exercises coordinate-and-pixel interaction fully.
- Recorded H29 and D049. G6 stays at partial mechanism evidence: no desktop VM, no physical
  device, no external suite, and coordinate-and-pixel competence on one authored window rather
  than general desktop competence.

- Added M082, a real Chromium browser as a third environment under M081's unchanged four-action
  interface. The interface completed 5/5 completable tasks in the container shell, the HTTP
  service and the browser, covering all three in one run.
- Kept the browser from being the service in a costume. Its store lives in localStorage with no
  HTTP route, reachable only by filling inputs, clicking and reading rendered DOM nodes; the
  crossed-driver arm completes nothing in all three environments, which demonstrates rather than
  asserts that the substrate differs.
- Imported M081's agent and both prior environments unchanged rather than restating them, with a
  regression and the checker failing if any is redefined.
- Recorded three transport defects found while proving the mechanics: MSYS path conversion
  mangling `docker exec` arguments on Windows, the same class as the negative M070; a fresh
  browser profile per action that would have left the harness holding the state instead of the
  browser while every test still passed; and a page flattened into an environment variable where
  a `//` comment silently disabled the save handler.
- Recorded H28 and D048. G6 stays at partial mechanism evidence: **no desktop VM**, no physical
  device, no external suite, and DOM competence on one authored page rather than general web
  competence.

- Added M081, a second real environment under one unchanged agent interface. A POSIX shell in a
  network-disabled Alpine container and a real Python HTTP server process in its own container
  both receive the same four abstract actions; the shared interface completed 5/5 completable
  tasks in each, judged from a fresh environment-state read.
- Made the scoring rule measurable rather than asserted. Each environment carries one task whose
  action returns success while the state does not change — a shell script swallowing a failed
  write with `; true`, and a service answering `204` to a write it discards. Judged by the
  agent's claim the interface looks 12/12; judged by environment state it is 10/12.
- Added a crossed-driver control that completes nothing, which is what shows the two environments
  are distinct systems rather than one mock wearing two labels.
- Recorded amendment A1 and two construction fixes. The first freeze required all six tasks per
  environment to complete while specifying one that is uncompletable by construction; A1 resolves
  it by strengthening, requiring the sealed task to be observed failing while claimed. The crossed
  arm originally swapped both driver and environment and crossed nothing, and the sealed task
  originally expected nothing and scored its own discard as a pass.
- Recorded H27 and D047. G6 stays at partial mechanism evidence: **no browser, no desktop VM**, no
  physical device and no external suite, and the container-backed regressions skip in CI under the
  existing opt-in, so CI attests the structural half only.

- Added M080 and measured forgetting for the first time. Six skills are acquired in sequence into
  one bounded 24-slot table where later skills reuse an earlier rule and demand a different output
  for an exception key the donor owns, so the cheap in-place rewrite is always available and always
  destructive. The lineage lost zero capabilities, used 19 slots against a private-slot ceiling of
  24, reused three rules and rolled back twice byte-identically.
- Recorded the limitation as a headline, not a caveat: retention is **replay-dependent**. Removing
  the replay of earlier examples costs five capabilities, exactly as much as removing consolidation.
  The protocol preregistered no direction for this measure so neither outcome could be chosen after
  the fact.
- Fixed and recorded three instrument defects before materialization: capacity pressure alone never
  bound so no arm evicted anything; retention scored on holdouts alone hid damage that lands on
  exception keys; and the rollback check compared the checkpoint against its own digest and could
  never fail. A regression and the checker now assert that a rollback mismatch stays reachable.
- Recorded H26 and D046. G5 stays at stronger partial bounded evidence with forgetting measured;
  closure needs capabilities maintained outside this project plus independent reproduction.

- Added M079 and exercised all four G3 clauses in one bank: planning with no supplied
  decomposition, plan revision under revealed evidence, terminal verification from world state,
  and calibrated clarification. The planner solved 8/8 static and 8/8 revision tasks within
  budget, revised on all eight, asked on 8/8 ambiguous goals and 0/16 unambiguous ones, and
  reached zero unsafe terminal states.
- Made committing on an ambiguous goal demonstrably harmful rather than merely possible. Every
  ambiguous episode admits two terminal states that both satisfy the literal goal and differ on
  safety, with the hazardous one strictly closer, so the `never_ask` control took it
  deterministically and reached six unsafe terminal states. The `always_ask` floor solved
  nothing, and asking is never scored as success.
- Recorded two construction fixes rather than hiding them: sealed states became terminal in the
  search, and the revision family now blocks an edge the initial plan actually traverses after an
  arbitrary block was routed around in three of eight episodes. No threshold moved.
- Recorded H25 and D045. G3 stays at partial bounded evidence with all four clauses exercised;
  closure needs a world maintained outside this project plus independent reproduction.

- Added M078 and exercised the one G1 clause M068 never tested: an incompatible opaque body must
  produce a calibrated refusal rather than an invented adapter. One unchanged procedure adapted all
  four compatible bodies with 12/12 hidden observations each, refused all four incompatible bodies,
  and produced zero false refusals, zero invented adapters and zero empty-set refusals.
- Built each incompatible body so refusal cannot be an exhausted search. One command is stitched
  from two skills over their disjoint public inputs, so a candidate fitting every public observation
  always exists. The `never_refuse` control adopted one on all four bodies and failed hidden
  validation four times, which is what establishes the public evidence as insufficient; the
  `always_refuse` control recovers nothing.
- Enforced the M069 information boundary structurally: a regression and the checker both parse the
  `discover` function and assert it never reads hidden observations, the body class, the aliased pair
  or the internal operation table.
- Recorded H24 and D044. G1 does **not** advance: the bodies are project-authored, and closure needs
  an externally maintained interaction language plus independent reproduction. D044 also forbids
  citing M078 as repairing M074, whose negative remains the only result on model refusal.
- Added the M075 independent-maintainer intake kit. The readiness gate already states that the
  project may not proceed without a signed external attestation, but reconstructing its 22-field
  closed envelope, opaque domain identifiers and signature namespace from source was hours of work
  for an outside volunteer. `metamorphosis/m075_intake_kit.py` and
  `scripts/run_m075_intake_kit.py` emit the template, print the exact `ssh-keygen` commands and
  validate a candidate envelope before it is sent, reusing the gate's own validator so the two
  cannot diverge.
- Added `experiments/M075/MAINTAINER_BRIEF.md`, a standalone brief for someone with no prior
  knowledge of the project: what they attest, what they must refuse to hand over, and the ordering
  that makes the arrangement evidence rather than theatre.
- Pinned the boundary in regressions: the kit has no process, network or archive module in its
  import graph, so it cannot sign or open payload, and it still rejects a project author as signer.
  Readiness remains fail-closed and unchanged at four blockers.
- Added M077 and preserved it as a **negative** result on H23. One persistent lineage ran shifts of
  32, 128, 512 and 2048 episodes over a typed sixteen-slot pool with a digest-chained journal, under
  four declared invariants and four injected fault kinds.
- Refuted the preregistered dissociation. Removing checkpoint recovery cost exactly restoration
  (0.00 at every horizon) while leaving detection numerically identical, as predicted. Removing the
  boundary constraint monitor did **not** cost detection: silent corruption eventually breaks a
  guarded operation, so the monitor buys detection latency rather than coverage.
- Preserved two positive sub-results without promoting them to a gate advance: the full arm held
  every invariant, recovered every fault and required zero interventions at all four horizons with
  no degradation as the horizon grew; and checkpoint recovery was causally isolated by its matched
  ablation. G7 remains open.
- Recorded both M077 instrument corrections in the result rather than hiding them, and added a
  checker that fails closed if the preserved negative is ever silently converted to positive.
- Added M076, the first endogenous result to address generality gate G2. One persistent
  deterministic agent consumes a UTF-8 instruction, an ordered structured mapping and a raw
  1728-byte RGB888 raster, and emits both symbolic `set_dial` calls and embodied effector moves
  scored from terminal grid state. The full arm reached 36/36 across three precommitted families.
- Recorded an exact triple dissociation under matched ablations that preserve byte length, key
  order and token count: each ablation zeroes its own dependent family and leaves both others at
  exactly the full-arm score, against a measured guessing floor of 3/36. G2 moves from open to
  partial mechanism evidence and is explicitly not closed.
- Preserved M076 amendment A1 rather than repairing it silently. The first freeze paired a
  chance-distribution floor with a bound of one success across 36 episodes, which no faithful
  guessing policy can satisfy; the bound was corrected before materialization and the arithmetic
  is recorded in the protocol.
- Added M075's fail-closed pre-private readiness layer. It accepts only a signed closed-metadata
  envelope from a non-project maintainer, requires at least eight matched capability pairs across
  four opaque domains, and refuses reveal until an exact scientific protocol binds the envelope.
- Precommitted the paired causal minimum: each private task runs once per condition on fresh clones;
  thresholds require 6/8 true refusals, zero false refusal, complete feasible success, eight saved
  steps, six context-only/zero baseline-only correct terminals, exact McNemar `p <= 0.05`, zero
  faults and separate-bank reproduction. Current readiness correctly remains false.
- Completed M075's single committed public model-development comparison: 12/12 fresh containers,
  43 live decisions, zero defect/retry/replacement. Epistemic context produced 2/3 true refusals,
  no false refusal, 3/3 feasible external success and four wasted steps versus baseline 0/3, no
  false refusal, 3/3 and twelve.
- Preserved the read-only-write miss: even with three visible failures and one remaining decision,
  the model acted again. D041 closes tuning on the contaminated bank and requires a causal-control
  and sealed external-bank review before any private execution. H21 remains untested.
- Added permanent byte-exact protocol/result verification for all task/code/runtime bindings, 43
  request/response records, information boundaries, ledgers, Docker attestations, live labels,
  external outcomes and recomputed calibration. Result SHA-256 `dadd2028`; calibration `d0226c09`.
- Exact evidence commit `0c19d6b` passed the complete local Python 3.14.6 suite on its first run:
  1,369 passed, two skipped in 2,390.27 seconds, plus all repository-integrity modes.
- Published head `2dd6ccb` passed first CI run `31398661236`: 1,370 passed/1 skipped on Python 3.11
  and Python 3.13, plus integrity. Attribution run `31398661318` passed; no workflow rerun was used.
- Began M075 as a separately numbered successor to the negative M074 result. Added a task-agnostic
  epistemic projection of remaining budget, failure persistence and exact action repetition without
  exposing labels, solutions, evaluators or arm identity.
- Added a distinct public Node/write/read development bank. Its zero-token deterministic policy
  completed 12 fresh real-container episodes with six exact live labels and zero defect; preserved
  record SHA-256 `cb194a40`. This is apparatus evidence only and H21 remains untested.
- Preserved M074's single frozen scientific campaign as a negative result. All 12 paired episodes
  completed without defect or retry; all six feasible arm episodes succeeded and no impossible
  episode did, but the model emitted zero refusals, producing margin 0.0 and zero saved steps.
- Froze M074 at protocol commit `28ddd8b` before every model decision. First CI run `31385331662`
  and attribution `31385331849` passed without rerun. The result's raw SHA-256 is `75e84682` and
  its calibration digest is `78d7b27e`.
- Added permanent verification of code/task/runtime bindings, live container attestations,
  capability labels, 24 live decisions, 24 exact paired replays, ledgers, evaluator outcomes and
  the negative verdict. D039 closes M074 and prohibits an in-place retry.
- Exact result commit `1eeb345` passed first CI run `31388068187`: 1,341 passed and one skipped on
  Python 3.11 and Python 3.13, plus integrity. Attribution run `31388066466` passed; both workflows
  used attempt 1 and no rerun.
- Qualified the M074 refusal-calibration apparatus locally without a scientific model call. Six
  exact real-container labels split 3/3 feasible/capability-impossible; a label-blind zero-token
  policy completed 12 fresh two-arm episodes with external final-state checks and no defect.
- Reduced M074 to one causal contrast: identical authority, isolation, budgets and hash-chained
  audit, with only refusal termination ablated. The terminal arm produced development margin 1.0
  and zero wasted steps; the nonterminal arm produced margin 0.0 and 12 wasted steps.
- Hardened capability certificates with explicit absence codes, probe/environment SHA-256 binding,
  cross-environment rejection and exact per-arm task coverage. Preserved the first live failure in
  which unexpected BusyBox code 127 correctly became `INCONCLUSIVE` instead of false absence.
- Added persistent non-root, no-network, read-only-root Docker workspaces with materialized fixtures,
  exact `/workspace` probes, external final-state evaluation and a permanent verifier for the two
  non-scientific M074 development records. The later frozen scientific result remains separate.
- Exact M074 apparatus commit `27a2e1f` passed first CI run `31377768229`: 1,322 passed and one
  skipped on Python 3.11 and Python 3.13, plus repository integrity. Attribution run `31377768244`
  passed; no workflow rerun was used.
- Post-hoc disqualified M069's positive qualification under D037. Candidate code executed in the
  evaluator process holding hidden cases and could return them through an admitted public-output
  path, so the Phase 8 hidden-evidence-reachability falsifier fires. Historical rewards and learner
  behavior remain diagnostic; there is no evidence the frozen learner exploited the path.
- Added an append-only evaluator-isolation disclosure and corrected the status, hypothesis,
  generality, state and roadmap registers without rewriting M069's frozen protocol, bank, learner,
  evaluator or result bytes.
- Preserved M073's first preregistered result: four frozen single-call external demonstrations
  induced one committed identifier-generalized AST capsule. After teacher removal it passed 12/12
  holdouts and 84/84 cases; unchanged-source and exact-hash memorizer controls passed 0/12, the
  corrupted-teacher control induced no capsule and no scientific retry occurred. Result `edaf03b4`.
- Added a permanent M073 verifier that reconstructs teacher prompt bindings, induction, the
  capsule-before-holdout commit boundary, all holdout outcomes, controls and final verdict. The
  supported claim is bounded model-to-lineage skill appropriation, not general programming,
  Genesis Gate 2, safe deployment or AGI.
- Exact M073 evidence head `2eaa5c7` passed first CI run `31370311326`: 1,257 passed and one
  skipped on both Python 3.11 and Python 3.13, plus repository integrity. Attribution run
  `31370349333` passed; no workflow rerun was used.
- Recorded M072's already-fused positive causal-governance result in the root registers: full
  governance satisfies the frozen authored invariants over 48 scenarios, while admission and audit
  ablations each lose 18 matching invariants. No represented action or external model was executed.
- Froze M071 runtime `0820ebc`, Harbor bridge `132476a` and 17 committed blobs before pinning a
  benchmark revision or selecting a fresh external identifier. Commitment `2e76a1b8`; no M071
  scientific result exists.
- Pinned the unchanged Terminal-Bench 2 remote head and a one-draw cryptographic blind-selection
  salt before enumerating eligible identifiers. The rule excludes both closed M070 tasks before
  ranking and forbids replacement.
- Applied the committed M071 rule once: 87 of 89 identifiers were eligible and the fresh pair is
  `sqlite-with-gcov`, then `custom-memory-heap-crash`. Inventory digest `c21c3e62`; neither task
  was opened before the binding.
- Froze M071 execution before any trial: Harbor 0.20.0, digest-pinned images, no-network agent
  phases, four ordered single attempts, zero valid retries/replacements, external success and
  composed-system score attribution. Solutions and verifier tests remain unopened.
- M071 passed its narrow external threshold: official rewards were `0.0` on SQLite and `1.0` on
  custom-memory, while both `nop` floors were `0.0`. All four jobs had zero Harbor exception,
  retry or replacement; success remained evaluator-owned.
- The final local Python 3.14 preservation suite passed 1,225 tests with two skips in 2,257.69
  seconds; repository integrity and every committed external artifact check passed.
- Exact M071 evidence commit `0875fa7` passed first CI run `31332620871`: 1,226 passed and one
  skipped on Python 3.11 and 3.13, plus integrity. Attribution run `31332620902` passed; no
  workflow rerun was used.
- Replaced locale-dependent model and Docker control pipes with strict UTF-8 bytes transport and
  replaced parent-only timeout kills in the model, container and terminal paths with one shared
  whole-process-tree supervisor. Real Windows regressions prove that `U+2011` survives and delayed
  descendants cannot act after a timeout.
- Changed the closed M070 freeze audit to verify the exact historical commit and its committed
  blobs instead of forbidding legitimate post-M070 evolution of the current working tree.
- Rebound the task-agnostic Harbor bridge to a separately named M071 policy, manifest schema and
  agent identity so new evidence cannot be mistaken for a rerun of the closed M070 design.
- Split the endogenous bounded-lineage and M070+ model-mediated tracks explicitly. Genesis Gate 2
  remains unchanged; external model proposals are not lineage-owned and benchmark rewards belong
  to the named composed system rather than Mira's governance layer alone.
- Corrected the stale prior-art statement that no runtime used an external model. The Python
  package still has no provider dependency, but M070+ has an explicit operational Codex/model
  dependency. Added D033 and the Track B attribution rule before M071 target selection.
- Preserved M070 as a negative external development result. The agent design and blind selection
  rule were committed before two of 89 Terminal-Bench 2 tasks were opened or executed.
- Official Harbor v0.20.0 returned reward `0.0` for both Mira trials and both `nop` controls, with
  no Harbor exception, scientific retry or task replacement. Agent phases were `no-network` and
  success remained evaluator-owned.
- Diagnosed the frozen backend failure: locale-dependent subprocess text mode rejected a true
  `U+2011` under Windows `cp1252`, while orphan `node`/`codex` descendants retained the pipe after
  the wrapper timeout. M070 remains unmodified; M071 must freeze a UTF-8/process-tree correction
  before selecting a fresh pair.
- Added the M070 pre-target engineering baseline before selecting any external task: a strict
  provider-neutral structured-model policy, explicit read-only Codex adapter and digest-pinned
  isolated Docker body.
- The container body verifies Docker's realized no-network, no-capability, no-new-privileges,
  read-only-rootfs, resource-limit and single-task-mount contract, and fails closed on mismatch.
- Model/backend and body-reset failures now enter the tamper-evident episode ledger. Submission
  never self-declares success; a later external evaluator must decide from final container state.
- Added the separately frozen M069 repair policy. One unchanged policy repairs four governed
  real-file/process workspaces, passes 3/3 hidden cases per task and refuses an incompatible
  protocol before any write or process execution.
- All ten M069 falsifiers pass, including write-authority ablation, under-declaration, traversal,
  immutable command schema, environment stripping, hidden-output suppression and source-
  inspection controls. A second process reproduces manifest digest `c5c80701` exactly.
- Added a compact governed-terminal demonstration and documented the finite supplied repair
  language, project-authored targets, trusted-host-command and non-AGI limits.
- Qualified exact learner `c603dd5` in run `31319062535`: 1,181 tests on Python 3.11 in
  1,241.52 seconds, 1,181 on Python 3.13 in 1,260.38 seconds and repository integrity all passed.
  Attribution run `31319062599` passed. The final local Python 3.14.6 suite passed 1,180 tests with
  one Windows symlink test skipped in 2,088.15 seconds.
- Recorded H15, D031 and the G1/G6/G10 evidence change; the next accepted step now requires
  post-design external tasks and container or VM isolation.
- Migrated the permanent CI and attribution workflows to the Node 24-based checkout, Python setup
  and Node setup action majors before GitHub's Node 20 action-runtime retirement.
- Added `GovernedTerminalBody` for bounded real-file reads, atomic writes and immutable registered
  subprocesses without a shell, plus path, symlink, environment, timeout and output controls.
- Added body-owned authority requirements so an action cannot gain access by under-declaring what
  its body needs; broken and under-declared contracts fail closed before execution.
- Froze M069 before its repair policy: four compatible real-terminal tasks, one incompatible
  protocol, eleven supplied replacements, hidden evaluator cases and ten falsifiers.
- Added the M068 open command-language learner after a separate target freeze. One unchanged
  engine scans all 37,448 admissible words and discovers four distinct complete adapters.
- All four unique public classes pass 12/12 disjoint hidden observations. Declaration-order,
  lexical-semantic, empty-transcript, corrupted-source, unknown-action, non-command and semantic-
  mutation controls reject, and a second process reproduces the exact manifest bytes.
- Recorded deterministic M068 manifest digest `0f012c41` and tamper-evident Mira Core evidence
  digest `75df381e`; preserved project-authored-target, finite-language and non-AGI limits.
- Qualified exact M068 learner commit `f033ac7` in first run `31314960014`: 1,153 tests on
  Python 3.11 and 1,153 on Python 3.13 plus integrity; attribution run `31314960009` passed.
- Added the first installable `mira_core` runtime with stable body/policy contracts, a bounded
  agent loop, immutable least-privilege admission and deterministic hash-chained memory.
- Added exact checkpoint restoration, tamper rejection, explicit policy refusal, body-fault
  evidence and fail-closed step budgets, plus a dependency-free runnable demonstration.
- Extended repository integrity checks from the historical `metamorphosis` package to every
  installable Mira package and documented the operational architecture and its current limits.
- Defined ten preregistered Mira generality gates covering interface novelty, multimodal grounding,
  planning, transfer, continual learning, real environments, long horizons, governed
  self-improvement, evaluation integrity and safety. M067 remains mechanism evidence, not AGI.
- Added the M068 pre-learner freeze: four opaque command-language bodies, eight action handles,
  37,448 admissible non-empty words, fixed public/hidden evidence and eight required controls.
- Bound the M068 runtime, bank and protocol by portable SHA-256 before any discovery engine exists.
  D028 forbids later target drift and explicitly declines an independent-authorship claim.
- Began Phase 8 with M067, a distinct adaptive-embodiment question that removes the complete
  supplied target adapter retained by the closed M043–M066 construction line.
- Added a separately executed four-body bank committed by SHA-256. Its interface exposes opaque
  handles, acceptance bits and raw replies but no frame, checksum, opcode or decoder descriptor.
- Added a bounded 288-candidate contract search. One uniform procedure discovered four distinct
  adapters across register, stack and mailbox frames; each unique public survivor passed 12/12
  disjoint hidden observations.
- Added empty-transcript, corrupted-transcript, default-adapter, framing-only and semantic-mutation
  falsifiers. All reject; the discovery API has no hidden-evidence parameter.
- Added the Phase 8 agenda, D027, H14, M067 protocol/result records and permanent tests. The result
  is positive and qualified in development. Exact experiment commit `7d38ac8` passed run
  `31311020868`: 1,130 tests on Python 3.11 and 1,130 on Python 3.13 plus integrity;
  attribution run `31311020869` passed.
- Licensed all project software under AGPL-3.0-only and the non-software research record
  under CC BY 4.0.
- Added explicit authorship, citation, provenance and trademark records naming Anthony Mets as
  project author and research director while disclosing AI-assisted implementation and analysis.
- Added Developer Certificate of Origin sign-off requirements for future contributions so that
  public authorship and licensing provenance remain auditable.

## 0.41.0 — 2026-08-09

M065 is preserved as a negative canonical guard qualification. M066 corrects only the Git-history
scope that caused the false rejection; every scientific input and result remains frozen.

- Qualified exact M065 parent `b1489d7a3a264de8a9e783eb139dafe28732b040` in first run
  `31286019961`: 1,101 tests on Python 3.11 and 1,101 on Python 3.13 plus integrity.
- Preserved canonical run `31287477458`, attempt 1, on marker commit
  `a517e6bb76e8476ab6aca8c0a68c5bcfc3501d57`. Guard job `93178824313` rejected before
  bank selection; result and reproduction jobs were skipped and no artifact was created.
- Identified the exact defect: `git rev-list --all` counted the canonical marker and the lateral
  pull-request ref. D025 now defines canonical marker identity over first-parent `main` history.
- Added M066 with no scientific changes, a new executable digest
  `f66ab480dfa0631e730753b7e45e3b83da7e2938d3e28e4aa2f497a6e383d66b` and a portable
  23-file commitment `02cabd7d86a93ceaba811b591b6c271cf066653add61044af83143558e2fd1c0`.
- Added a real Git graph falsifier proving that lateral marker refs are ignored while repeat
  first-parent occurrences are rejected. The first-result job remains attempt-one only.
- Repeated all four banks through the unchanged M065 engine: complete lineage 18/18 with three
  accepted cycles and 68/68 retained; every control 0/18 with zero accepted cycles. Eleven M066
  tests passed in 202.78 seconds; the complete repository passed 1,112 tests in 1,689.93 seconds
  and repository integrity passed.
- Qualified exact parent `4a4b4a1a1e4831a4e1f8a40f896e3b2921cdc6e5` in first run
  `31290364464`, then armed it with marker-only head `2cf454ca4e393a319f89ae5afbcd5e3f9250182c`.
- Preserved positive canonical run `31291899534`, attempt 1: bank 0, three accepted cycles, v12,
  68/68 retained and 18/18 hidden versus 0/18 for every control. Python 3.13.14 reproduced the
  exact 51,553 Python 3.11 result bytes with SHA-256
  `eaf6fee975bddaae583e0f739d0a5ad050209b303d304eddc81bb6320c642ace`.
- Added the immutable raw result, reproduction, first-result seal, independent evidence verifier
  and canonical audit. All ten bounded completion gates are true; D026 closes the M043–M066
  construction line while leaving M045's separate measurement question open.

## 0.40.0 — 2026-08-09

M064 is preserved as a failed pre-canonical qualification and M065 carries the required
scientific and governance corrections without changing the task bank, budgets, thresholds,
substrates, candidate grammar or four-arm decision rule.

- Preserved M064 commit `ec92af78b57203d32c2ee504db91b4166ec83fdf` and GitHub run
  `31281234286`, attempt 1. Integrity and attribution passed; Python 3.11 passed 1,084/1,085
  tests in 1,037.15 seconds and Python 3.13 passed 1,084/1,085 in 1,094.43 seconds. Both rejected
  the same checkout-dependent source hash. No marker or canonical result was created.
- Recorded the review finding that M064's rollback receipt compared the untouched saved input to
  itself. D023 therefore requires M065 rather than a scientific repair under M064.
- Added an M065 transaction that corrupts a distinct staged state, deserialises the committed
  pre-transaction bytes into the state actually returned, audits that object and requires exact
  byte and state-digest restoration before continuing.
- Repeated all four banks. The complete lineage remains 18/18 hidden with three accepted cycles
  and 68/68 retained cases; every control remains 0/18 with zero accepted cycles.
- Required the canonical marker to be its first occurrence anywhere in path history and gated the
  first-result job on `github.run_attempt == 1`; reruns can only consume the preserved artifact.
- Added portable LF-normalised source commitments. M064's historical 21-file audit and M065's
  22-file audit now agree across Windows and Linux checkouts.
- The complete corrected repository suite passes **1,101 tests in 1,762.37 seconds**. An earlier
  full M065 invocation passed 1,100 and exposed the last CRLF-based M064 guard fixture; that
  fixture alone was normalised before the clean rerun.

## 0.39.0 — 2026-08-08

M064 assembles the real-substrate completion experiment in one continuous
CPython → Node ESM → whole-WebAssembly lineage. It is positive in development and eligible for
freeze; no canonical verdict is added yet.

- Reconstructed M047 version six and M048 version eight, scanned all 256 arithmetic bytes and
  replayed M061's six structural shapes before compiling the entire accepted body into a
  1,834-byte, zero-import WebAssembly module with 32/32 inherited capabilities.
- Added a serialised seven-node expression constructor and dynamic whole-body compiler. Each
  accepted route recompiles parser aliases, arities, route admission and tool dispatch into one
  native module; Node remains only a passive bounded host.
- Added four equal-budget post-migration arms and three committed task families. Across all four
  preverified banks the complete lineage accepts three rewrites, reaches version twelve and
  passes 18/18 hidden observations; fresh-on-B, unchanged-parent and learned-state-ablated arms
  each accept zero rewrites and pass 0/18.
- Required class-wide D021 admission: 12, 8 and 8 public survivors are each independently
  recompiled, inspected for zero imports and executed on retained, public and hidden evidence
  before digest selection.
- Archived exact parents 9, 10 and 11, appended three causal-memory episodes, forced a corrupt
  journal binding, restored code and behaviour exactly, and replayed the final state.
- Added a marker-only canonical guard, immutable first-result runner and separate Python 3.13
  exact-reproduction job. These mechanisms remain closed until the frozen-parent commit passes
  qualification and a separate marker commit is made.
- Preserved the authorship boundary: the whole-body compiler, block structure, finite grammar,
  task families and evidence remain human-written and precommitted. M064 claims bounded
  construction and continuity, not unrestricted compiler synthesis or open-ended evolution.
- The first complete four-bank test invocation finished every scientific computation. Nineteen
  tests passed; one fixture expected two intermediate module
  sizes incorrectly. The fixture was corrected without changing engine, protocol, bank,
  threshold or result. The clean M064 rerun then passed **26/26 tests in 274.65 seconds**. The
  complete local repository suite subsequently passed **1,085 tests in 2,035.10 seconds**.

## 0.38.0 — 2026-08-08

M063 transfers M062's bounded arrangement mechanism from byte copying to byte reduction. The
development result is qualified; no canonical claim is added.

- Replayed M061/M062 effect discovery and constructed 96 checksum-loop arrangements from the
  transferred topology, predicate, exit-position and step-permutation dimensions.
- Retained six public survivors and admitted all six on three disjoint hidden cases under both
  exit-region representatives: 12/12 complete programs.
- Emitted a 91-byte `(source, count) -> checksum` WebAssembly module with an accumulator local,
  zero imports and no memory write.
- Added a cross-body negative control: M062's selected copy body passes only the zero checksum
  case and fails both non-zero cases.
- Added D022: a claimed mechanism transfer needs a target with a distinct observable contract
  and a source-body control that the target evidence can falsify.
- Kept the boundary explicit. The checksum decomposition, three atomic steps, finite grammar,
  emitter, encodings and evidence cases remain authored. A third small loop using the same
  pattern would not count as the next advance.
- Added 16 permanent M063 falsifiers. The complete M063 file passes locally in 130.94 seconds,
  the joint M062–M063 regression passes 31 tests in 310.38 seconds and the complete repository
  suite passes **1,054 tests in 1,763.31 seconds**. The required GitHub matrices are recorded
  below.
- Qualified exact head `d4eb5ed981727fd1343e6e1031494771d9dec220` on the first and only
  GitHub Actions run `31275085485`, attempt 1: 1,054 tests on Python 3.11 in 969.51 seconds,
  1,054 on Python 3.13 in 985.12 seconds, repository integrity and attribution, with no failed
  job or rerun.

## 0.37.0 — 2026-08-08

M062 begins the arrangement frontier left by M061. This is a qualified development result; no
canonical or real-substrate claim is added.

- Replayed the six M061 structural scans and added a seventh 256-opcode region-effect scan.
  A discovered branch distinguishes exit behaviour from repetition without using `block` to
  expose `loop` or the reverse.
- Preserved the scan's real ambiguity: `0x02` and `0x06` form the observed exit-region class;
  `0x03` is the sole repeat-region candidate. No familiar opcode is preferred silently.
- Constructed 480 copy-loop arrangements from a finite grammar rather than a catalogue of
  finished programs. Sixteen satisfy the three public cases.
- Required all sixteen public survivors with both exit-region representatives to pass all three
  hidden cases: 32/32 complete programs admitted. The canonical digest therefore selects source
  representation, not hidden behaviour.
- Added D021: canonicalisation inside an observational equivalence class is allowed only after
  every member survives independent validation.
- Preserved the first region-scaffold defect: it declared an empty result and could not transport
  the value its post-region addition consumed. The permanent witness test caught it before the
  complete lineage; the fixed `i32` blocktype is now part of the explicit floor.
- Kept the boundary explicit. The task decomposition, grammar, emitter, scaffold shapes,
  blocktypes, label encoding and cases remain authored. M062 is not arbitrary compiler synthesis,
  and does not close the real-substrate canonical frontier.
- Qualified exact head `f5cfe35c265cf83640fddc2ae80e54805776f84f` on the first and only
  GitHub Actions run `31269732461`, attempt 1: 1,038 tests on Python 3.11, 1,038 on
  Python 3.13 and repository integrity, with no failed job or rerun.

## 0.36.0 — 2026-08-08

Register synchronisation, again. The previous release synchronised the registers on 6 August
with M053 as the frontier. Eight experiments landed in the two days since and none of them
reached the root registers, so `PROJECT_STATE.md` still announced a frontier that had been
superseded six times. No scientific claim is changed by this release; the records under
`experiments/` were already authoritative.

- **Recorded M053 as a positive bounded development result.** Documented head `12b0c31`, run
  `31162378285`, 852 tests. Its capability gain is structural and real; its mechanism filters a
  declared sixteen-AST meta-language, which is selection at a higher level.
- **Recorded M054** as construction rather than selection — 29,330,422 admissible candidates
  under a budget of 1,024 — together with the three design defects found before it ran and
  disclosed in its protocol.
- **Recorded M055 as negative on its central claim.** The construction, adoption, forced fault
  and exact restore all work. The ablation still solves the reuse task with 737 candidates
  against 48, so the acquisition bought a fifteen-fold search saving and no new expressive
  power. This is the result behind **D019**.
- **Added Phase 6 — substrate discovery and the whole-body crossing**, covering M056 through
  M061: an acquisition survives a second crossing; the authored migration map is removed; the
  authored list of operations is removed and discovery finds `copysign`, which a person had
  omitted; the lineage judges its substrate and reverses; the whole body crosses into a
  1,792-byte WebAssembly module with zero imports; and the structural instructions are
  identified by their effect alone.
- **Recorded that none of M056–M061 discharged its own qualification rule.** Each result was
  written before CI returned and none was updated, so all six still read *PENDING
  QUALIFICATION*. The CI runs are now listed retrospectively — one run per experiment commit,
  no rerun, no selection among runs — as evidence that the suite was green and explicitly not
  as a discharge of those rules.
- **Added D020 — a manifest field is a claim, and reading it back proves nothing.** M061
  asserted `copy_loop_uses_only_discovered_instructions: True` while its builder wrote seven
  opcodes in by hand. Sixteen permanent tests passed over it because the test read the field
  back. The same shape appears in M053's `rollback_exact` and M048's `replay_identical`: the
  falsifier's input was downstream of the thing it was supposed to falsify.
- **Entered the M061 false manifest into `FAILURE_LOG.md`.** It was found by external review of
  PR #90, not by the test suite, the integrity audit or the green CI run. It reached `main` in
  merge `1c7cceb` because the correction was pushed after the merge, and is corrected by PR #91.
- **Recorded that the scan contradicted the authored code and was right.** `i32.le_s` is
  `0x4c`; the hand-written copy loop carried `0x4d`, the unsigned comparison. Nothing caught it
  because the loop counter never goes negative. M060's emitter was independently correct.
- **Replaced the frontier with two questions instead of one experiment.** The compiler that
  arranges the discovered instructions is still written by a person, and nothing built on a
  real substrate is claimable: gates 8, 9 and 10 have no working parts there. Fifteen
  consecutive development results without a claimable one is the pattern **D016** and the M052
  series closure exist to prevent.
- Rewrote `PROJECT_STATE.yaml` with `phase_five`, `phase_six` and a two-question frontier,
  replacing the `active_construction_frontier` block that still described M053 as unqualified.

## 0.35.0 — 2026-08-06

Register synchronisation. The root registers had not been updated since M047 was still the
frontier, while `main` had advanced through M048–M052. No scientific claim is changed by
this release; the experiment records under `experiments/` were already authoritative.

- **Recorded M048 as a positive integrated development result.** The accepted M047
  version-six body was compiled into nine native Node.js ESM modules and executed without
  semantic delegation back to Python. Twenty-eight inherited capabilities survived, the
  inherited `mean` tool was used after migration, a new `tool_max` module was learned in the
  new runtime as version eight, forced journal corruption was detected and version eight
  restored exactly.
- **Recorded M049–M052** as bounded development results, with their run numbers, commits and
  test counts, and recorded that the series is closed at M052.
- **Added D016 — the M049–M052 series is closed at its own success.** Every step passed and
  none of them changed what the lineage can express; the closure lists the six continuation
  patterns that can no longer justify a successor experiment.
- **Added D017 — an infrastructure failure is not a qualification verdict.** A run enters the
  append-only qualification history only if the experiment's own code executed and produced
  the failure.
- **Entered the preserved negative verdicts into `FAILURE_LOG.md`.** M048's runs 402 and 403
  and M050's run 410 were documented only under `experiments/`, so the project's central
  failure register did not contain them. For a project whose append-only negative history is
  a load-bearing claim, that was the largest gap in the registers.
- **Recorded the M053 frontier as proposed and unqualified**, and recorded its first CI
  attempt as an infrastructure event rather than a negative result, per D017.
- Added M047 to `PROJECT_STATE.yaml`, which had never carried it, and added a `phase_four`
  block for trans-runtime continuity.

## 0.34.0 — 2026-08-03

- **Corrected a selector that was named for a mechanism it did not implement.**
  `minimal_criterion_survivors` admitted on a threshold and then ranked the admitted by
  agreement, preferred the smaller body on a tie, and truncated. M037's own report
  asserted that "a minimal criterion admits or rejects; it does not rank" while the code
  ranked. Found by external review, not by the test suite or any audit.
- **Withdrew a false attribution.** The rule was justified by M021's 750 per mille.
  `rank_by_minimal_criterion` filters on viability, ranks the viable by **novelty**, ranks
  the rejected by energy and lets `Population.select` truncate; M035 implemented none of
  that. The figure was attributed to a mechanism that was never run.
- Named three selectors apart, so none borrows another's evidence:
  `thresholded_elitist_truncation` keeps M035's historical 6/12,
  `viability_then_novelty` keeps M021's 750 per mille, and the new
  `positive_population_floor_admission_with_body_diversity` inherits neither and has
  produced no experimental result at all. Every rate in M037 belongs to the historical
  selector, which the runner still uses unchanged.
- Named the admission bar for the whole of what it does. `max(1, min(score))` is a
  population floor **plus** a viability condition, and its cost is stated: the protection
  claimed for neutral duplicates applies only to viable lineages, since a neutral
  duplicate of a never-scoring parent sits below the bar with its parent and is rejected
  with it. Pinned by test, including the degenerate all-zero population.
- Separated admission from capacity reduction. Admission consults the score once, at the
  threshold. Reduction orders by `SHA-256(domain || commitment || seed || generation ||
  digest)`, which sees no score, no size, no structural cost and no input position, and
  draws from its own hash rather than the mutation generator — sharing that stream would
  couple selection to variation.
- **Fixed a second hidden dependency.** Deduplication kept whichever organism the loop met
  first per body digest, so permuting the population changed the surviving *lineage* while
  the surviving *bodies* stayed identical. A separate `representative_key`, under its own
  domain separator, now decides which lineage represents a body. The invariant test
  written alongside had compared digests only and passed while the defect was present.
- Declared the unit of reduction as the **distinct body**, chosen on mechanism before any
  measurement and named as a diversity policy rather than neutrality: ten clones present
  one candidacy. Per-individual reduction would let a heavily replicated clone crowd out
  rare structures by multiplicity alone.
- Named the admission rule for what it is. The threshold is the current population's
  minimum score, recomputed each generation and able to fall. A comment claiming it "rises
  only when the whole population clears it" was false. The near-vacuous bar is deliberate:
  a neutral duplication carries exactly its parent's score, so any rising bar would
  eventually exclude the duplicates before they could drift.
- Requalified M037's replay as **level 2, adopted-mutation replay from a supplied
  founder** — a Gate 9 prerequisite, not Gate 9. The founder is given as a DFA rather than
  rebuilt from a seed, and task reveals, observations, rejected candidates, costs and
  selection decisions are not reproduced.
- Marked cases 0–11 and 12–23 as consumed. Neither may choose a policy, tune a threshold
  or confirm a later claim; a fresh guarded block is required before the next experimental
  decision.
- Renamed the machine-readable replay fields to say what they demonstrate:
  `adopted_mutation_replayable`, `adopted_mutation_steps`, `adopted_mutations` and
  `all_winning_adopted_mutation_chains_replayable`. The code, the tests, the emitted JSON
  and the report now make the same claim, and none of them says Gate 9.
- Added a test exercising the runner's own threshold rule rather than a hand-supplied
  one. The earlier tests passed a threshold in directly and never exercised
  `max(1, min(score))` against a population containing a zero, which is exactly where the
  positive floor differs from the current minimum.
- Pinned the rejected alternative too: under an exact `min(score)` floor the null lineage
  would survive. Variant 1 is not adopted, and the trade-off stays visible in a test
  rather than only in prose.
- Added 19 metamorphic selection tests and recorded the misclassification in
  `FAILURE_LOG.md`.

## 0.33.0 — 2026-08-03

- Made the lineage replayable, as Gate 9 requires. Every organism now carries its full
  chain of mutations — the operation itself, not a pointer to its outcome — and
  `replay(founder, ancestry)` rebuilds any descendant from the founder body and the chain
  alone, with no seed, no population and no search. Verified 20/20 in development and
  **12/12 on untouched cases**, on chains up to 36 mutations deep. A truncated chain
  provably fails to rebuild the organism, so the record is load-bearing.
- Fixed the survival rule, which sorted by score and cut at capacity: elitist truncation
  wearing a minimal criterion's name, and the rule M021 measured as the most destructive
  of four at 0 per mille against 750. The symptom was unmistakable once swept — raising
  generations from 60 to 150 changed nothing on every configuration, because the
  population reached a fixed point and stopped exploring. Deduplicating by body before the
  cut restores exploration.
- Recorded an instructive intermediate error: ordering the distinct bodies by structural
  cost scored **0/12 everywhere**, because cost rises with size and a size-ordered cut
  discards exactly the organisms that have grown. Both errors share a shape — a minimal
  criterion admits or rejects, it does not rank, and each order slipped into it restored a
  pressure the mechanism cannot survive.
- **Rejected a tuning illusion.** A sweep found 9/12 on cases 0–11 against 6/12 for the
  delivered defaults. Confirmed on untouched cases 12–23 it scores 3/12, while the
  defaults score 5/12 — the swept configuration is not merely no better but worse, and the
  sweep had found the parameters that flattered the twelve cases being watched rather than
  improving the mechanism.
- Confirmed the delivered result generalises: 5/12 on cases never used to choose anything,
  against a control that stays at 0/12 by proved impossibility rather than by budget.

## 0.32.0 — 2026-08-03

- Added the `grow` atom to the structural language: duplicate the state holding a role,
  routing one incoming edge to the twin. It is the only capacity-increasing edit; every
  other preserves or reduces the state count. Additive by design — `all_atoms()` is
  unchanged, so every recorded experiment keeps its vocabulary, its reachable set and its
  digests.
- Added M036, a single organism that meets a task, proves its body too small, grows and
  retries. **Recorded as a negative**: it solves 2/8 where the M035 population solves 6/12
  on the same generator, and a control without growth solves 0 by impossibility.
- Established that the explicit Myhill–Nerode diagnosis is unnecessary and too weak to
  gate on. Once growth is in the search vocabulary the search finds when to grow by
  itself, and the greedy bound missed 3 of 6 cases that genuinely required growth, so
  gating suppressed exactly the episodes needing it. Failure is the better trigger.
- Established that growth must be composable rather than preparatory: inside the
  vocabulary 2/8, as a phase before the search 0/8. A depth-3 trajectory can be
  edit-grow-edit only if growth is a symbol.
- Established by exhaustive enumeration that growing is not sufficient: of six cases, the
  diagnosis missed three, two grew to a reachable target, and one grew to a target still
  unreachable at depth 3. A size bound says *that* a body must grow, never *where* the
  missing distinction lives.
- Corrected a measurement error of this session's own making. M036 was first reported at
  0/8 as a structural failure; the smoke test used a 60,000-node budget while depth-3
  enumeration over 44 symbols needs up to 85,184. At the protocol's 200,000 the same code
  solves 2/8. The conclusion stands, the first number did not.

## 0.31.0 — 2026-08-03

- Measured the structural ceiling of the existing organism: across 53,280 atom
  applications, 18,540 changed the state count and **none increased it**. Every change was
  a decrease. Capacity is fixed at birth and can only be lost, so no descendant can be
  structurally novel and "self-improvement" is search inside a budget the organism did not
  choose and cannot change.
- Added `metamorphosis/m035_evolution.py` with a capacity-increasing operator:
  duplication of a state into a behaviourally identical twin. Neutral at birth — 12/12
  preserve behaviour exactly, so selection cannot see it — and 12/12 increase the state
  count. This is NEAT's *add node* mutation, itself transposed from gene duplication; the
  contribution here is not the mechanism but a domain where "unreachable" is proved.
- Ran the decisive comparison against `make_out_of_language_target`, which M017 uses as a
  *negative* control precisely because it adds a state. Twelve cases, all requiring growth:
  the atoms-only arm solved **0/12**, by structural impossibility rather than bad luck, and
  the duplication arm solved **6/12**, using growth in 12/12.
- Added `required_states_lower_bound`, a Myhill–Nerode diagnosis by which an organism
  proves it needs more states **without seeing the target**, from oracle answers alone.
  Sound in 0/24 violations, never demanding growth against its own behaviour, firing on
  8/12 targets that require it. This is Gate 1, autonomous diagnosis of a limitation, in a
  decidable form.
- Recorded two failed refinements rather than tuning them away. Size-based speciation
  scored 1/12 and diagnosed growth 2/12, both against 6/12 for a random trigger, and both
  solved faster when they solved — more directed, less exploratory. Their mechanisms are
  identified in the result, and neither correction is applied: re-measuring a corrected
  rule on the same seeds is the post-hoc adjustment §7 of the M017 protocol and D010 forbid.
- Selected survivors by minimal criterion, chosen from this repository's own measurement:
  M021 scored it 750 per mille against 416 for novelty, 312 for quality-diversity and 0 for
  the direct objective. At equal agreement the smaller organism survives, so growth is
  never free.

## 0.30.0 — 2026-08-03

- Recorded the human signature on the §2 thresholds of M017 and translated the candidate
  protocol to English before hashing, because D012 governs the active surface and a
  document frozen forever must be frozen in the repository's language. The French
  candidate is retained unchanged as the pre-signature record.
- Added `metamorphosis/m017_sealed.py`, the sealed specification required by §10. Its
  nonce is derived from the immutable head SHA rather than drawn at random, per §8.3,
  which is stricter than M012b, M013e and M014b: the environments cannot be computed
  before the commit they judge, and they reproduce from that commit alone.
- **Blocked the freeze.** Writing that generator put the admission conditions under a seed
  set the development bench had never used, and the out-of-language negative control
  produced a false success: a 7-state target, a 6-state source, a 6-state announced
  solution that is not equivalent, separated by `(0, 0, 1, 0, 0, 0)`.
- Established the cause as a scope assumption rather than a coding error. `_confirm`
  states its own bound — the structural language does not create states, so a target
  cannot have more than the source — and the negative control is defined by adding one.
  §3.2 therefore asks the organism to reject targets its own confirmation cannot see.
- Measured the repair: raising the bound to `source + 1` grows the suite from 34 to 69
  words and restores detection. Because it also changes query cost, which §2 measures, the
  bound is a protocol parameter to be signed rather than adjusted after observation.
- Established that the development pass was a favourable draw. Gate 5 was declared passed
  on two negative controls; an independent sweep of 24 yields 2 false successes, an escape
  rate near 8 per cent, so two clean controls occur about 85 per cent of the time.
- Re-opened gate 5 and recorded the finding in `FAILURE_LOG.md` and §11 of the protocol.
  This is the third instance in M017 of a small favourable sample taken for a guarantee,
  after the 96-word probabilistic confirmation and the unminimised W-method hypothesis.

## 0.29.0 — 2026-08-03

- Repaired the D014 negative-constant defect in the rewrite kernel. The fix is in the
  reader rather than the writer: `_negative_int_literal` makes both `_TargetCollector` and
  `_IndexedNodeTransformer` treat a `-<int>` expression as one constant target, so a patch
  replaces the whole negation instead of the literal nested inside it.
- Constant patches are now idempotent for every sign, the AST no longer grows under
  repeated negative patches, and the effective behaviour no longer alternates.
- Measured the consequence honestly: the repair moves all four recorded M033 digests,
  because `ConstantRewriteTool.propose` filters on `value != current` and previously read a
  negative constant as positive. Every search in the construction stack was carrying
  phantom candidates; removing them lowers candidate medians by 3 to 7 per cent.
- **No finding changed.** Every paired outcome reproduces identically across the two kernel
  generations, along with exactness, held-out exactness, output-only immobility and the
  parent/ablation separation.
- Recorded D015: artifacts are scoped by the kernel generation that produced them rather
  than re-run, as M012 is scoped against M012b. A cost figure may only be compared against
  another from the same generation.
- Retired `tests/test_m020_negative_constant_defect.py`, which pinned the defective
  behaviour so a fix could not land unnoticed, and replaced it with
  `tests/test_m020_negative_constant_round_trip.py`, which guards the repair.
- Added `MacroCost`, an opt-in edit-budget rule. `PER_OPERATION` is the default and charges
  a learned tool what its constituent primitives cost; `UNIT` charges it as a single edit.
  `_rank_key` now ranks on budget rather than trace length, which is identical under the
  default and lets a one-step macro outrank the longer primitive path it replaces.
- Added `metamorphosis/m034_reachability.py`, an exact capability measure. Deterministic
  cost conflates how close a lineage started with how much it can do; the reachable
  behaviour set separates them, and is enumerable here rather than estimated.
- Established two results, both pinned: under `PER_OPERATION` a learned tool adds **nothing**
  to the reachable set at any budget, being a composition of primitives charged what they
  cost; under `UNIT` it enlarges the set — 2/16 to 4/16 at budget 1, 7/16 to 10/16 at
  budget 3 — with the old set a proper subset of the new.
- Gave M017 a decidable success criterion it lacked: does a self-extending language
  increase reachability at constant budget?

## 0.28.0 — 2026-08-03

- Added rewrite provenance: `RewriteCandidate.proposing_tools` and
  `RewriteResult.reused_learned_tools` record which tool proposed each adopted step, so
  Gate 9's reuse clause can be proved rather than guessed. Provenance is excluded from the
  ranking key, and all four recorded M033 digests reproduce exactly.
- Established that a learned tool costs the same edit budget as its constituent
  primitives: it saves search depth, not budget, since its operations count individually
  against `max_edits`.
- **Found a latent correctness defect in the M020 rewrite kernel.** `apply_patch` does not
  round-trip negative integer constants: `ast.unparse` writes `-2`, re-parsing yields
  `UnaryOp(USub, Constant(2))`, and each further patch at that index stacks another
  negation. Constant patches are non-idempotent for negative values, the AST grows without
  bound, and the search can reach bodies whose outputs leave the declared state range.
- Audited the blast radius: nothing recorded is contaminated. 776 of 776 adopted sources
  across the four M033 calibration blocks contain no negative constant.
- Recorded the defect as D014 and in `FAILURE_LOG.md`, and pinned it with
  `tests/test_m020_negative_constant_defect.py`. It is deliberately **not** repaired here,
  because correcting it changes the reachable candidate set and may move recorded digests.
- **Withdrew the Gate 9 demonstration.** An exhaustive finite check found 4 candidate
  reuse lineages out of 195 cycle-1/cycle-2 pairs; all four depended on the defect. Gate 9
  remains undemonstrated and must be re-measured on a corrected kernel.

## 0.27.0 — 2026-08-03

- Measured D013's predicted repair path instead of leaving it as an argument: a
  three-cycle lineage over three distinct finite targets accumulates three learned tools,
  one of which can still act on the final body.
- Established the exact mechanism: the newest tool is always inert, because it is by
  construction the trace that produced the current body, and an earlier tool becomes able
  to act again only once a later cycle moves the body away from what it wrote.
- Recorded that Gate 9 is a **precondition** for Gate 8's learned-tool comparison, which
  is a sequencing constraint on the roadmap rather than a threshold choice, and that
  M033's thresholds may not be frozen before repeated cycles exist.
- Added `tests/test_m020_multicycle_tool_reactivation.py`, five tests pinning the tool
  accumulation, the inert newest tool, the reactivation of an earlier tool, and the
  single-cycle contrast.

## 0.26.0 — 2026-08-03

- Established that a learned rewrite tool is a literal replay, not a generalising
  transformation: `PatchOperation` binds each edit to a positional AST index and
  `LearnedRewriteTool` returns its operations verbatim, so a tool cannot fire at an
  equivalent site with a different index.
- Established the consequence for Gate 8: the tool a single-cycle lineage carries is the
  trace that produced its body, so applying it there is a no-op and the learned-tool
  ablation compares two lineages whose only difference cannot act.
- Reclassified that control from failed to **structurally uninformative**, since a tie
  there is evidence about the rewrite language rather than about transported plasticity.
- Withdrew the requirement, added in 0.25.0, that the primary generator demand a component
  the migrated body does not encode. It was unsatisfiable: the precondition is a relation
  between registry and body, not between lineage and task.
- Recorded that Gate 8's tool control must be evaluated on a multi-cycle or rolled-back
  lineage, so Gates 8 and 9 are not independent.
- Added `tests/test_m020_learned_tool_replay_limit.py`, five tests pinning the index
  binding, the no-op property and the absence of site transfer.
- Recorded the finding as D013 and connected it to D009: the tool language is closed in
  the same way the retired catalogue was.
- Noted that the memory mechanism is unaffected, because it is decoded and re-applied
  against current evidence and can therefore act on a body it did not produce.

## 0.25.0 — 2026-08-03

- Found and repaired a control-design defect that removed one of Gate 8's four required
  controls: every earlier M033 block anchored all lineages on the task's own baseline
  source, so the migrated body was never read and the unchanged parent and the
  learned-tool ablation presented byte-identical surfaces.
- Added `TaskAnchor`, leaving `TASK_BASELINE` as the default so the fixed, structural and
  combined blocks stay byte-reproducible and are not retroactively re-scored; verified by
  re-running all three after the change and reproducing every recorded digest exactly.
- Added the body-anchored control block on the disjoint seed range 4096–4127, where the
  two collapsed controls separate on 32 of 32 seeds.
- Established that transported competence does real work: the complete lineage beats
  fresh-B 32/0/0 and its own unchanged parent 32/0/0, at a median of 26 candidates
  against 1,427.5 and 264.5.
- Established that the learned tool contributes nothing independent in this rig, tying the
  complete lineage 0/32/0 at an identical median of 26, because it encodes the same
  transformation the adopted rewrite already baked into the body.
- Recorded Gate 8 as unmet with a per-control verdict, and recorded that the remedy is a
  generator change rather than a threshold change.
- Verified the isolation and integrity audits and a byte-identical replay with raw digest
  `394f9904b675ac2a8c9d143b8265022b32285efb0d56a01799f45e43b17571a8`.
- Left the reserved primary block 0–63 uninstantiated and unobserved.

## 0.24.0 — 2026-08-03

- Added M033's combined memory-and-tool control block on the disjoint seed range
  3072–3103, running the four structural scaffolds through the memory-guided execution
  path so both transported mechanisms are measured together for the first time.
- Recorded a mixed and largely negative result: all five learning-capable variants were
  exactly equivalent on all 32 tasks, and the complete lineage beat fresh-B 24/0/8 but
  went 8/16/8 against its unchanged parent, 8/16/8 against the learned-tool ablation and
  16/0/16 against the learning-state ablation.
- Established that the two mechanisms act on disjoint scaffolds: memory carries scaffolds
  0 and 1 at a median of 264 candidates, learned tools carry scaffold 3 by cutting search
  from 1,879 to 568, and neither helps on scaffold 2.
- Established that the advantage is not attributable to the adopted rewrite, because the
  unchanged parent retains the same learning state and matches or beats the complete
  lineage on three of four scaffolds.
- Charged the memory probe honestly: one candidate evaluation whether accepted or
  rejected, which alone decides the scaffold-3 loss against the learning-state ablation
  at 569 against 568.
- Verified 236 repository tests, the isolation and integrity audits and a byte-identical
  replay with raw digest
  `0ef00f0f4168a95235f33050751b7871366ad1e2d2c08ed07bfb90b908423372`.
- Left the reserved primary block 0–63 uninstantiated and added two questions the
  threshold-freeze amendment must now answer: the status of the unchanged-parent
  comparison, and whether a one-candidate margin is a win or an abstention.

## 0.23.0 — 2026-08-03

- Added M033's post-migration plasticity rig: six lineage constructors covering the
  complete migrated M032 lineage, fresh-B, unchanged parent, output-only and the
  learning-state and learned-tool ablations.
- Added two disjoint development control blocks — fixed-structure seeds 1024–1031 and
  four-scaffold structural seeds 2048–2063 — with a static audit proving no pre-M033
  module reaches the M033 task, target or held-out surfaces.
- Isolated the learned-tool mechanism causally: median post-reveal candidates were 959
  for the complete lineage against 976 for fresh-B, the unchanged parent and the
  learned-tool ablation, cheaper on 8/8 seeds, with 0/8 on the disjoint negative family.
- Isolated the memory mechanism causally: a relevant transported trace reached a median
  of 264 candidates against 959 for empty memory and 960 for a permuted trace, cheaper on
  8/8 seeds, while all three stayed exactly equivalent.
- Recorded a deliberately mixed structural result — 12/16 complete-lineage wins with
  per-scaffold directions of 4/4, 4/4, 0/4 and 4/4 — and kept scaffold 2 as a declared
  counterexample to any rule demanding universal directional improvement.
- Reported every lifecycle cost as a separate vector rather than one synthetic score, and
  verified output-only immobility, fail-closed post-migration regression and exact
  rollback.
- Passed 27 focused tests, the repository integrity and task-isolation audits and
  byte-identical replays of both calibration families in run `30792247244`.
- Kept the reserved primary block 0–63 uninstantiated and unobserved; no post-migration
  plasticity advantage is claimed and no threshold is frozen.

## 0.22.0 — 2026-08-03

- Added M032's fail-closed bridge from M025's adopted executable rewrite to M013e's
  experimentally discovered opaque substrate and native DFA body.
- Added a canonical trans-substrate packet carrying the M025 passport, source DFA,
  opaque body, discovered opcode identifiers, memory, uncertainty and exploration
  frontier.
- Added exact rollback after finite-compilation or substrate-migration failure and
  integrity rejection for tampered passports, DFAs, opaque bodies and opcode registries.
- Verified five focused M032 controls, repository integrity and 211 repository tests on
  both Python 3.11 and Python 3.13.
- Preserved the boundary between this bounded integration result and the still-open
  post-migration learning, autonomous diagnosis and repeated-cycle claims.

## 0.21.0 — 2026-08-02

- Added M031's split-scaffold generator with length-three generic motifs and eight
  cyclic/permuted triad tasks.
- Transported the frozen component-uniform information rule: 737 per mille
  clade/exact-CMP concordance, +1,070 over development adaptive, and +500 per mille
  median paired final hidden quality with 43 wins, 18 ties and 3 losses.
- Passed every structural, probe, coverage, uniqueness, selector-isolation and aligned
  control on exactly 64 paired primary seeds.
- Recorded 256 trajectories, 65,792 expansions, 198,144 unique evaluations and a
  byte-identical 48,018,205-byte replay.

## 0.20.0 — 2026-08-02

- Added M030's pre-written confirmation of M029's component-uniform diagnostic on the
  untouched seed block 64–127.
- Confirmed every gate: component-uniform guidance reached 662 per mille
  clade/exact-CMP concordance, +1,186 over development adaptive, and +1,000 per mille
  median paired final hidden quality with 48 wins, 16 ties and no losses.
- Preserved the untouched boundary by using only seeds 128+ for unit and smoke
  validation before the frozen confirmation commit.
- Recorded 256 trajectories, 30,720 expansions, 92,928 unique evaluations and a
  byte-identical replay.

## 0.19.0 — 2026-08-02

- Added M029's hidden-disjoint compositional transfer probes and a frozen rerun of the
  M028 performance-adaptive baseline.
- Preserved the 64-seed mixed development result: component-adaptive clade/exact-CMP
  concordance reached 699 per mille, but its paired final advantage remained zero with
  31 wins, 32 ties and 1 loss, below the pre-written policy gates.
- Recorded the pre-declared component-uniform diagnostic: 50 wins, 14 ties and no
  losses against development-adaptive guidance, without promoting it to a registered
  claim on already observed seeds.
- Recorded 384 trajectories, 46,080 expansions, 139,392 unique evaluations and a
  byte-identical replay.

## 0.18.0 — 2026-08-02

- Added M028's finite adaptive evaluation-weighting comparison over the common M027
  breadth-seeded archive.
- Preserved the 64-seed negative development result: adaptive allocation improved
  clade/exact-CMP concordance by only 40 per mille, produced no median hidden-quality
  advantage and returned 2 wins, 60 ties and 2 losses against uniform allocation.
- Recorded 256 trajectories, 30,720 expansions, 92,928 unique evaluations and a
  byte-identical replay without exposing hidden fields to either selector.
- Localised the next measurement failure: performance-adaptive weighting can sharpen a
  misaligned proxy while allocating less evidence to high-potential lineages.

## 0.17.1 — 2026-08-02

- Hardened human-only attribution with exact registered identities and a trusted-base
  pull-request check that never executes proposed code.

## 0.17.0 — 2026-08-02

- Added M027's hidden-blind exhaustive coverage through the first reward-bearing depth.
- Preserved the 64-seed negative development result: exposing productive descendants
  did not align the unweighted clade estimator or improve final hidden quality.
- Added permanent human-attribution rules and pull-request checks for commit authors,
  committers, co-authors, branch names, titles and descriptions.
- Removed historical automated inline-review comments and neutralized the submitted
  review summaries that GitHub does not permit the repository owner to delete.

## 0.16.0 — 2026-08-02

- Added M026, the first direct literature-facing benchmark, with explicit mappings to
  DGM, HGM and SGM and equally explicit non-reproduction boundaries.
- Added an exact finite performance/potential reversal, an exhaustive aligned control,
  selector isolation, fixed-point stochastic policies and four-worker replay.
- Preserved the 64-seed negative development result: HGM-inspired clade aggregation
  did not beat DGM-inspired immediate guidance under the fixed expansion process.
- Recorded the frozen implementation and protocol identities, the reproducible
  512-run artifact hash and a byte-identical full replay.

## 0.15.0 — 2026-08-02

- Ran M021 across 24 paired seeds and preserved the development result: implemented
  selection measures produced different exact hidden transferred quality.
- Added M022's pre-written seed-0 positive and negative adaptation controls with full
  row-level evidence; cross-seed stability remains open.
- Hardened M023 so independent adoption fails closed when the parent workspace fails.
- Added M024's integrity-checked rewrite passport for the active body, rollback lineage
  and complete learned-tool registry.
- Added M025's transactional portable rewrite lifecycle. Rejection or exceptions now
  restore both the body and registry exactly; accepted state migrates, replays its
  learned transformation and survives forced rollback.
- Reconciled the public project narrative, state and roadmap in English and recovered
  the useful evidence that had existed only on stale local branches.

## 0.14.0 — 2026-08-01

- Reoriented the project onto what its own failures identified: **when does a proxy
  measure stop tracking what it claims to track?** (D011, H9)
- Added `MEASURES.md`, a first-class register beside `FAILURE_LOG.md`, cataloguing six
  measures that came loose from what they claimed to measure — with ground truth.
- Made that catalogue executable: `scripts/reproduce_measure_failures.py` replays every
  case on demand.
- Replaced the probabilistic confirmation with an exact conformance test
  (`metamorphosis/conformance.py`). M017's "zero false successes" had been a favourable
  draw, not a guarantee.
- M017: all six freeze gates passed. The 50-environment sweep invalidated the proposed
  10× threshold and the criterion became directional.
- M018: hypothesis not supported — destroying does not restore improvement.
- M019: rig not valid — selection too impatient to value learning.
- M021 opened: do these selection measures move true quality?
- Parallelised the measurement scripts, verified bit-identical against the sequential
  outputs.
- Repository made public and translated to English (D012).

## 0.13.0 — 2026-07-31

- Consolidated the repository around living code only: retired the orphan M012/M013b
  stack, about 2,400 lines forming a disconnected import subgraph (D007).
- Added the first permanent CI and `scripts/check_repository_integrity.py` (D008).
- Fixed `pytest -q` and `pip install -e ".[dev]"`, both of which had never worked.
- M014c halted before evaluation and replaced by M017 — self-extending language (D009).
- D010: a measured quantity must have an established dynamic range.

## 0.12.0 — 2026-07-31

- Created the canonical repository.
- Consolidated Metamorphosis M001–M011.
- Added protocols, reports, aggregated results, tests and scripts.
- Created the state, hypothesis, decision and failure registers.
- Opened phase M012: autonomous morphogenesis.
