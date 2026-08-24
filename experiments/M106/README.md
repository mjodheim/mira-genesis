# M106 — corrective replication of the executable constructor-vocabulary extension

> **VERDICT: POSITIVE (attempt 1). H51 supported within its frozen bounds. D075.**
>
> Protocol `e92e1b08…`; result `7c22c889…`; report `76299018…`. P1-P16 all computed true, replay
> equal, zero model/network/remote calls. Both fresh arms refused with four surviving behavioural
> classes and the semantic image exhausted.
>
> M105 remains negative and is not repaired by this result.

M105/H50 attempt 1 is negative by fail-closed checker instrumentation (D074). Its unique canonical
runner completed and its result `0ae9c096…` is preserved, but the single frozen checker raised
`ModuleNotFoundError: No module named 'scripts'` in a deferred replay import and evaluated **no**
predicate. The mechanism was never falsified and never supported.

M106 asks H50's question again as **H51**, on a fresh population, with a corrected instrument. It is
a successor, not a repair: M105's result stays immutable and diagnostic only.

## The integrity property that makes this a replication

`metamorphosis/m105_runtime.py` — the mechanism — is **imported unchanged**. It is not copied,
forked, adapted or edited, and the final protocol binds its raw SHA-256. Only three things differ
from M105:

1. the qualification population;
2. the DEVELOPMENT fixture;
3. the orchestration and checker entry points, which is where M105's defect lived.

This is what separates *the mechanism works* from *we improved the system until it passed*. The
M106 orchestration and checker were derived from their M105 counterparts by a mechanical milestone
rename that explicitly protected every mechanism reference, so the instrument logic is inherited
rather than rewritten.

## Fresh population

| | M105 | M106 |
|---|---|---|
| target semantic | `(False, True, True, False)` | `(True, False, False, True)` |
| JSON carrier key | `route` | `channel` |
| carrier values | `amber` / `violet` | `harbor` / `quartz` |
| identifiers, nonces, payloads, hidden cases | — | all fresh |

The target semantic was fixed in `PRE_REGISTRATION.md` before implementation. A mechanism tuned to
M105's target cannot pass here: the two are distinct semantic classes with distinct content
addresses.

The exact M104 V3 predecessor bytes are **not** refreshed. The predecessor is what H50/H51 is about
and is fixed by the frozen M104 result.

## Instrument correction

`scripts/check_m106_result.py` bootstraps the repository root onto `sys.path` at import time. M105's
checker deferred `from scripts import run_m105_qualification` into its `--replay` branch with no
bootstrap, and its pre-freeze verification exercised only the refusal path, which returns before
that import. Exercising a refusal path is not evidence that the checking path runs.

The same defect reappeared during M106 authoring, in `author_m106_qualification_pool.py`, and was
caught immediately because the real command was run rather than an import assumed to work.

## What M106 cannot establish

Ownership or extension of the lower Boolean interpreter; more than a bounded two-signal,
sixteen-function feature space; independently authored or unknown interfaces and tasks; G1-G10
closure; general-agent evidence; self-hosting; recursive or open-ended self-improvement.

**A structural note recorded before any result.** The lower interpreter `execute_expression` is
*semantically complete* over its two-signal space: all sixteen Boolean functions are reachable
within the eight-node bound. No acquisition in this substrate can therefore ever extend Boolean
reach. M106's reach claim is about the **consumer dispatch image** — generalization beyond M104's
finite exact-context dispatch — not about the interpreter. Demonstrating an endogenous *lower
interpreter* extension requires a substrate that is deliberately incomplete, which this one is not.
That is the next ceiling, and it cannot be reached by another milestone in this substrate.
