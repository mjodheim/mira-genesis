# Historical reproducibility findings — M101–M106

**Audit date:** 2026-09-05  
**Scope:** reproduction engineering only; no historical verdict is changed.

## Interpretation rule

A failure of a preserved checker can mean at least three different things:

1. the causal/scientific predicates no longer reproduce;
2. the historical execution environment has not been reconstructed faithfully; or
3. the frozen reproducibility contract contains an environment-dependent binding that was true on
   the original machine but is not portable to another machine.

This audit keeps those cases separate. A binding/replay defect is not silently promoted into a
scientific refutation, and a positive historical verdict is not silently rewritten to hide a
reproducibility defect.

## R-HIST-01 — M101 carries a checkout-dependent raw-byte binding

A fresh Linux replay at the frozen M101 v4 source reconstructed the exact CPython 3.11.16 / SQLite
3.53.1 runtime and reproduced thirteen of fifteen decisive predicates. P1 refused because the
pre-registration raw SHA-256 did not match; P15 then also failed because stable replay equality was
lost.

This is consistent with M101's own pre-run record. `PRE_RUN_AMENDMENT_001.md` states that the frozen
work happened on a Windows checkout where tracked text existed as CRLF while Git object identity
remained unchanged. That amendment correctly changed the qualification-pool freeze comparison to Git
object identity, but the final protocol/checker still retains raw-byte SHA-256 commitments for other
research records such as `PRE_REGISTRATION.md`.

At the M101 freeze, `.gitattributes` did not force canonical line endings for M101 Markdown/source
members; its conventional digest rules still matched only `experiments/M0*`.

**Classification:** historical cross-checkout reproducibility defect / environment reconstruction
requirement. The thirteen passing causal predicates are not converted into a new positive result,
and the two binding/replay failures are not called a scientific refutation.

**Audit action:** reconstruct the documented Windows `core.autocrlf=true` checkout in a disposable
worktree and replay without altering the preserved files or checker.

## R-HIST-02 — M102 is explicitly known to have inherited checkout-specific bytes

A fresh Linux replay at the M102 frozen source likewise reproduced thirteen of fifteen predicates.
P1 reported moved mechanism/apparatus bindings; P15 reported stable-evidence inequality.

This is not a newly invented explanation. The current repository's `.gitattributes` records the
exact historical defect prospectively fixed by M103:

> the older M0* convention stopped matching at M100, which allowed M102's checker and two retained
> runtime sources to acquire checkout-specific CRLF bytes

`build_m102_protocol.py` confirms why this matters: M102 freezes raw SHA-256 values and raw file-set
digests over Markdown, Python and JSON apparatus members. Without a line-ending attribute, a Windows
working tree and a POSIX working tree can therefore represent the same Git text object with different
raw bytes.

**Classification:** known historical cross-checkout binding defect, corrected prospectively by M103.

**Audit action:** reproduce the original Windows checkout semantics. Do not retrofit M103's later
line-ending attributes into the frozen M102 protocol and call that the original result.

## R-HIST-03 — M103's negative reproduces

Under the reconstructed freeze + first-result working state, M103's checker again reaches the same
fail-closed direct-script bootstrap failure and reproduces the preserved negative verdict.

**Classification:** successful historical negative reproduction.

## R-HIST-04 — M104 requires the RESULT-only preservation commit as replay HEAD

M104 intentionally strengthened its checker after a superseded candidate failed to seal the result
commit boundary. The final checker requires `HEAD` to equal the preserved annotated first-result tag,
which is the direct RESULT-only child of the frozen protocol. Replaying with HEAD left at the freeze
therefore correctly refuses before predicates are evaluated.

**Classification:** audit-context error discovered by the checker, not an M104 failure.

**Audit action:** checkout `experiment/m104-canonical-first-result`, ensure no checker report is
present in the disposable worktree, and run the frozen replay there.

## R-HIST-05 — M105's negative reproduces

M105 again reproduces its recorded direct-script `ModuleNotFoundError` / fail-closed checker
instrument failure. M106's source explicitly documents this failure as the reason it bootstraps the
repository root before deferred imports.

**Classification:** successful historical negative reproduction.

## R-HIST-06 — M106 P1–P15 reproduce; P16 contains an absolute-path accident

With exact CPython 3.11.16 / SQLite 3.53.1 and the frozen M106 source, a fresh replay computed
**P1 through P15 true**. Only P16 (`replay_confirmed`) failed because the stable projection differed.

The frozen code exposes a specific machine-dependent field that explains why cross-machine stable
replay cannot be byte-identical:

- the evidence records `runtime.isolated_python = str(ISOLATED_PYTHON)`, an absolute filesystem path;
- `EPHEMERAL_KEYS` excludes `python_executable`, `search_path`, PID fields, stderr and elapsed time;
- it does **not** exclude `isolated_python`.

Therefore the stable projection includes a path such as a local Windows Python executable on the
original machine and a hosted-runner path on a fresh Linux reproduction, even when the interpreter
version and every scientific predicate are identical.

**Classification:** genuine frozen stable-projection portability defect. This limits the strength of
M106's *cross-machine byte-stable replay* claim. It does not falsify the H51 mechanism result: all
fifteen non-replay scientific/integrity predicates recomputed true in the fresh audit.

**Prospective lesson:** a stable projection must encode runtime identity semantically (implementation,
version, linked SQLite identity) while excluding absolute installation paths. M107 and later
milestones already use a more aggressive ephemera policy; historical M106 remains immutable.

## Current audit status

The audit workflow is now testing three historical shards with exact Python/SQLite identity and
milestone-specific Git chronology. M101/M102 additionally reconstruct their documented Windows CRLF
checkout semantics. Results not yet final in that run are deliberately not recorded here as passing
or failing.
