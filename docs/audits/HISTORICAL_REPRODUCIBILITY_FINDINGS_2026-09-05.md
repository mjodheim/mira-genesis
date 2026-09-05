# Historical reproducibility findings — M095–M112

**Audit date:** 2026-09-05  
**Scope:** reproduction engineering only; no historical verdict is changed.

## Interpretation rule

A failure of a preserved checker can mean at least three different things:

1. the causal/scientific predicates no longer reproduce;
2. the historical execution environment has not been reconstructed faithfully; or
3. the frozen reproducibility contract contains an environment-dependent binding that was true on
   the original machine but is not portable/reconstructible on another machine.

This audit keeps those cases separate. A binding/replay defect is not silently promoted into a
scientific refutation, and a positive historical verdict is not silently rewritten to hide a
reproducibility defect.

## R-HIST-01 — M101 scientific core reproduces, exact mechanism binding is not reconstructible

A fresh Linux replay reconstructed the exact CPython 3.11.16 / SQLite 3.53.1 identity and recomputed
**P2 through P14 true**. P1 and P15 alone remain false.

The audit first restored every text file whose LF or CRLF representation matched an individually
recorded historical SHA-256. It then solved, by exhaustive finite search, the LF/CRLF assignment for
each file-set binding whose protocol stored only an aggregate digest.

That procedure recovered M101's frozen qualification-apparatus binding exactly and recovered its
checker binding exactly. It did **not** recover the frozen mechanism digest: no assignment in which
each committed mechanism source is represented by its Git-checkout bytes, canonical LF bytes or
canonical CRLF bytes produces the mechanism aggregate frozen in M101.

This narrows the historical limitation substantially. M101's own pre-run amendment documents a
Windows working tree whose raw bytes could differ from Git object identity. At the M101 freeze,
`.gitattributes` still protected conventional `experiments/M0*` artifacts but did not canonicalize
M101 Python mechanism members. `git hash-object` can validate the normalized Git object while a raw
SHA-256 over the working-tree bytes remains checkout-specific.

The remaining mismatch is therefore not repairable from the preserved commit by a principled
line-ending reconstruction alone. The raw working-tree representation that produced the frozen M101
mechanism digest was not preserved as an independently recoverable blob.

**Classification:** historical binding/replay portability limit. The thirteen causal/integrity
predicates P2–P14 reproduced; full byte-exact M101 replay did not.

**Scientific consequence:** do not call H46 refuted. Also do not advertise M101 as independently
byte-identical cross-machine reproducible from the repository snapshot alone.

## R-HIST-02 — M102 inherits the same unrecoverable M101 source byte and reproduces P2–P14

M102 likewise recomputed **P2 through P14 true** on the canonical Python/SQLite identity. P1 and P15
remain false.

M102 is better instrumented than M101 because its protocol preserves per-file member digests. The
audit restored all individually recoverable LF/CRLF members and recovered the qualification-apparatus
and checker aggregates exactly. The mechanism aggregate still cannot be reconstructed.

The decisive inherited member is `metamorphosis/m101_runtime.py`: M102 freezes its expected raw digest
as the M101-era digest, but the M102 frozen Git object on a clean Linux checkout has another raw
SHA-256, and neither uniform LF nor uniform CRLF conversion reaches the frozen value. The historical
M102 result itself records the older digest, so the discrepancy is in source-byte preservation rather
than a newly changed scientific predicate.

The repository later documents this class of problem prospectively: M103 extends line-ending
canonicalization beyond the old `M0*` naming convention that stopped matching after M100.

**Classification:** inherited historical source-byte/binding portability defect, corrected
prospectively by the later instrumentation line. P2–P14 reproduce; full P1/P15 byte-stable replay does
not.

## R-HIST-03 — M103's negative reproduces

Under the reconstructed freeze + first-result working state, M103's checker again reaches the same
fail-closed direct-script bootstrap failure and reproduces the preserved negative verdict.

**Classification:** successful historical negative reproduction.

## R-HIST-04 — M104 fully reproduces

M104 intentionally binds its replay HEAD to the annotated first-result commit rather than the freeze
parent. Replaying in that exact chronology produces **15/15 true**, `replay_equal=true`, and the same
stable-evidence digest.

**Classification:** full independent historical reproduction on a fresh hosted runner.

## R-HIST-05 — M105's negative reproduces

M105 again reproduces its recorded direct-script `ModuleNotFoundError` / fail-closed checker
instrument failure. M106's source explicitly documents this failure as the reason it bootstraps the
repository root before deferred imports.

**Classification:** successful historical negative reproduction.

## R-HIST-06 — M106 P1–P15 reproduce; P16 contains an absolute-path accident

With exact CPython 3.11.16 / SQLite 3.53.1 and the frozen M106 source, a fresh replay computed
**P1 through P15 true**. Only P16 (`replay_confirmed`) failed because the stable projection differed.

The frozen evidence includes an absolute isolated-Python installation path while the ephemera policy
does not exclude that field. The original Windows path and a hosted Linux runner path therefore make
byte-identical cross-machine stable evidence impossible even when runtime version and all scientific
predicates are identical.

**Classification:** genuine frozen stable-projection portability defect. This limits M106's
cross-machine byte-stable replay claim. It does not falsify H51: all fifteen non-replay
scientific/integrity predicates recomputed true.

**Prospective lesson:** stable projections must encode runtime identity semantically
(implementation/version/SQLite identity) and exclude absolute installation paths. The later line
already hardens this.

## R-HIST-07 — M095/M098 negatives and M099/M100 positives

Fresh historical reconstruction has already shown the expected direction for these records in prior
audit attempts: M095 and M098 remain negative; M099 and M100 reproduce positive. The final sharded
audit run is the authority for whether their complete current audit classification is recorded as a
full replay or as a binding-limited replay.

## R-HIST-08 — M096/M097 positive mechanism predicates with early binding sensitivity

Repeated fresh replays of M096 and M097 have reproduced all their non-P1 conditions while P1 alone
has refused on the raw frozen mechanism/file binding in clean hosted checkouts. The current audit
solver now attempts the finite protocol-recorded LF/CRLF aggregate assignments before that status is
finalized.

Until the final sharded run closes, these records are classified conservatively as **historical
positive with unresolved cross-checkout P1 reproduction**, not as fresh positive reproductions.

## R-HIST-09 — M107–M112 later line

A previous fresh sharded run reproduced M107, M108, M109, M110 and M111 positive and M112 mixed exactly.
The audit reruns them alongside the older line so the final matrix can cite one common validation
campaign.

## Frozen-history rule

None of the findings above modifies an old protocol, result, tag, threshold or hypothesis verdict.
Where an old exact-replay claim is not portable, the repository should preserve that limitation as a
finding and rely on a prospectively hardened successor — never retrofit the old checker until it
passes.