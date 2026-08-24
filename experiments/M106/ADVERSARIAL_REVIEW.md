# M106 adversarial pre-freeze review

**Date:** 25 August 2026
**Status:** apparatus complete; DEVELOPMENT rehearsals only; no final protocol or canonical result

This review attacks H51 before the freeze. Where the honest answer weakens the claim, the claim is
narrowed rather than the answer softened.

## The strongest objections

**1. The answer is already in the world generator.** Partly true, and stated plainly: the
DEVELOPMENT fixture *is* F's truth table, labelled over all four signal rows. F is not invented, it
is identified. H51 does not claim invention. It claims that acquiring, validating, persisting and
content-addressing F changes what the lineage can later *construct*. The scientific content is the
downstream reach difference, not the origin of F.

**2. The new mechanism is only a selection among coded solutions.** True, and bounded by
construction: F is one of exactly sixteen two-input Boolean semantics, and the lineage enumerates
all sixteen. H51 says "bounded state-owned constructor-vocabulary extension" for this reason. Any
reading stronger than that is unsupported.

**3. The fresh control is handicapped.** It is not. It receives the same exact M104 predecessor, the
same runtime, the same lower substrate, the same later observations, and it enumerates the complete
sixteen-function image (`semantic_image_exhausted: true`, `enumerated_feature_semantics: 16`). It
fails with four surviving behavioural classes per carrier — **underdetermination, not exhaustion**.
More budget cannot help it: the image is already complete.

**4. This is a cost improvement dressed as a reach improvement.** No. The two public cases constrain
only rows `(F,F)` and `(F,T)`. Four of the sixteen semantics remain consistent with them and they
disagree on the unseen rows, so the fresh lineage cannot determine the hidden behaviour at all. The
difference is what is determinable, not how long determining it takes.

**5. The predecessor's complete image is asserted, not computed.** It is computed. M104's inherited
definitions are finite exact-context dispatches; the independent closure checker constructs a fresh
omitted context per definition and an isolated execution witness fails to materialise it. Repetition
cannot change a representation image.

**6. The target reaches the lineage by name, digest, order, fixture or evaluator.** Checked
mechanically and one leak was found and removed: the DEVELOPMENT nonces originally carried the
qualification literal `harbor`. The nonce is neutralised, the fixture digest rebound, and the audit
now asserts that no qualification-only literal appears in DEVELOPMENT material, that the serialized
feature carries no carrier or fixture identity, and that the acquisition source names no future
carrier or action.

**7. Hidden data is reachable through a dependency, path or exception.** The producer capsule
contains the bound runtime, the exact M104 bytes, DEVELOPMENT observations and an ambiguity control
only — no qualification pool, no demand, no hidden case, no result and no checker. Later capsules do
not contain DEVELOPMENT.

**8. The validator trusts self-report.** Three independent checkers validate the definitions, the
semantic census and the M104 closure without importing the mechanism's search or qualification code.

**9. The ablation is decorative.** Each consumer definition stores F's content address and resolves
F at execution. Removal breaks decoding, acquisition and execution. A valid complementary feature
plus dependency rebinding executes and reverses the precommitted hidden behaviour.

**10. This is recursive self-improvement.** It is not, and M106 must never be cited as such. One
bounded classifier is acquired once and used by later acquisitions. Nothing modifies the acquisition
machinery, the search, the interpreter or the substrate. There is no second generation.

## The instrument, which is what actually killed the predecessor

M105 died on `ModuleNotFoundError: No module named 'scripts'` in a deferred replay import, and its
pre-freeze verification exercised only the refusal path, which returns before that import. M106
therefore treats the checker as the primary risk:

- the repository root is bootstrapped onto `sys.path` at import time, not lazily;
- the full `CANONICAL -> PRESERVE -> CHECK -> REPLAY` chain is rehearsed end to end against a
  materialized DEVELOPMENT result in a throwaway clone, using exactly the frozen commands;
- the checker is exercised as a **direct script**, through the **replay branch**;
- result-present, result-absent, corrupted-result and report-already-exists paths are exercised and
  their exit codes asserted;
- every predicate must be computed, not merely true.

The same import defect reappeared while authoring `author_m106_qualification_pool.py` and was caught
within seconds because the real command was run instead of assumed to work.

## The ceiling this milestone cannot touch, recorded before any result

`execute_expression` is **semantically complete** over its two-signal space: all sixteen Boolean
functions are reachable inside the eight-node bound. No acquisition in this substrate can extend
Boolean reach, ever. M106's reach claim is therefore about the **consumer dispatch image** only.

A genuine lower-interpreter result requires a substrate that is *deliberately incomplete*, where a
target provably lies outside the complete image of the current primitives and an acquired executable
primitive brings it inside. That cannot be obtained by another milestone in this substrate, and it
is the next ceiling.

## The rehearsal, and what it caught

The complete `CANONICAL -> PRESERVE -> CHECK -> REPLAY` chain was rehearsed end to end in a
throwaway clone with its own rehearsal freeze, using exactly the commands the canonical chronology
will use. It consumed no canonical attempt and wrote nothing to the repository's evidence path.

**The first rehearsal returned `verdict: negative`, P14 false, 15/16.** The mechanical M105->M106
rename had renamed the isolated-process schema the runner filters on, while the capsule entry point
`scripts/run_m105_process.py` is a mechanism file M106 preserves unchanged and still emits
`m105-isolated-process-v1`. The filter matched nothing, `isolated_records` was empty, and both
isolation booleans became false through `bool([])` rather than through any error — an isolation
predicate reporting "no isolated process violated isolation". Without this rehearsal M106 would have
spent its unique canonical attempt on that. The filter is now bound to the schema the mechanism
actually emits, and a systematic sweep confirmed no other renamed schema is compared against
mechanism output.

After the correction the rehearsal returns `verdict: positive`, **16/16 computed and true, zero
uncomputed, replay equal, exit 0**.

Exit codes and artefacts were exercised on the rehearsal result:

| case | exit | behaviour |
|---|---|---|
| result present, replay | 0 | all sixteen predicates computed; report materialized |
| report already exists | 3 | refuses; does not overwrite |
| result absent | 3 | `m106-check-refusal-v1`; writes nothing; attempt preserved |
| result digest corrupted | 1 | negative, failed closed, report materialized |
| evidence tampered with a recomputed digest | 1 | negative; caught by independent stable-projection recomputation |

The last row matters: a coherent forgery that repairs `result_digest` is still detected, because the
checker recomputes the stable projection itself rather than trusting the result's own summary.
