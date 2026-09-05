# Historical reproducibility findings — M095–M112

**Audit date:** 2026-09-05  
**Scope:** reproduction engineering only; no historical verdict is changed.

## Interpretation rule

A preserved checker failure can mean: (1) the scientific predicates no longer reproduce; (2) the
historical checkout/runtime has not been reconstructed; or (3) the frozen replay contract contains a
machine/working-tree accident that is not portable. This audit keeps those cases separate. It never
turns a replay defect into a scientific refutation and never edits an old checker until it passes.

All final replays below used fresh hosted runners. Where the milestone froze the identity, CPython
**3.11.16** and SQLite **3.53.1** were restored before execution. Historical LF/CRLF bytes were changed
only in temporary worktrees and only when an already-frozen digest proved the exact representation.

## Final reproduction ledger

| Milestone | Historical verdict | Fresh audit | Classification |
| --- | --- | --- | --- |
| M095 / H40 | negative | negative | reproduced negative; historical mechanism raw binding also non-portable |
| M096 / H41 | positive | P2–P10 true; P1 false | scientific/causal predicates reproduced; exact mechanism binding not reconstructible |
| M097 / H42 | positive | **12/12 true** | full positive reproduction |
| M098 / H43 | negative | P1–P11 true; P12 false | reproduced negative; stable replay mismatch remains decisive |
| M099 / H44 | positive | **12/12 true** | full positive reproduction |
| M100 / H45 | positive | **12/12 true** | full positive reproduction |
| M101 / H46 | positive | P2–P14 true; P1/P15 false | scientific core reproduced; exact historical mechanism binding unavailable |
| M102 / H47 | positive | P2–P14 true; P1/P15 false | same inherited source-byte portability limit |
| M103 / H48 | negative | negative | reproduced negative |
| M104 / H49 | positive | **15/15 true**, replay byte-stable | full positive reproduction |
| M105 / H50 | negative | negative | reproduced negative |
| M106 / H51 | positive | P1–P15 true; P16 false | scientific predicates reproduced; stable projection contains absolute Python path |
| M107 / H52 | positive | **16/16 true**, replay byte-stable | full positive reproduction |
| M108 / H53 | positive | **16/16 true**, replay byte-stable | full positive reproduction |
| M109 / H54 | positive | **18/18 true**, replay byte-stable | full positive reproduction |
| M110 / H55 | positive | **24/24 true**, replay byte-stable | full positive reproduction |
| M111 / H56 | positive | **24/24 true**, replay byte-stable | full positive reproduction |
| M112 / H57 | mixed | procedure 10/10; diagnosis 24/24 positive; transfer 22/24 negative | exact mixed reproduction |

## R-HIST-01 — M095 negative direction reproduces

M095 again returns `negative`. P3, P5 and P6 remain scientifically false, while the old P1 mechanism
raw-byte binding is also not reconstructible from a clean checkout. The additional P1 issue cannot
turn the historical negative into a stronger claim, but the direction of the preserved result is
stable.

## R-HIST-02 — M096 scientific core reproduces; P1 is historically non-portable

The audit recovered M096's qualification-apparatus aggregate exactly and restored every individually
recoverable historical line-ending digest. **P2 through P10 all recomputed true.** P1 alone remains
false because no assignment of each committed mechanism source to its checkout/LF/CRLF bytes reaches
the mechanism aggregate frozen by M096.

**Classification:** historical positive with a non-reconstructible working-tree mechanism binding.
H41 is not freshly refuted; its nine non-binding conditions reproduce. M096 must not, however, be
advertised as independently byte-identical cross-machine reproducible from the preserved snapshot.

## R-HIST-03 — M097 fully reproduces

For M097, the finite aggregate solver recovered both mechanism and qualification-apparatus bindings
exactly. Two inherited mechanism files were restored to the CRLF representation proven by the frozen
aggregate. The original checker then returned **12/12 true** and `positive`.

**Classification:** full independent positive reproduction.

## R-HIST-04 — M098 negative reproduces

M098's mechanism and qualification bindings reconstruct exactly. P1–P11 are true and P12
(`stable_replay_chronology_track_a_and_local_only_execution`) remains false because the stable replay
projection differs. The checker therefore reproduces the historical `negative` verdict.

## R-HIST-05 — M099 and M100 fully reproduce

M099 and M100 each return **12/12 true** and `positive` on fresh hosted runners.

## R-HIST-06 — M101 scientific core reproduces, exact mechanism binding is not reconstructible

M101 recomputes **P2 through P14 true**. P1 and P15 alone remain false. The audit recovered its frozen
qualification-apparatus and checker aggregates exactly but no finite assignment of the committed
mechanism files to checkout/LF/CRLF representations produces the mechanism digest frozen in M101.

M101's own pre-run amendment records the Windows/Git raw-byte problem. At that freeze, the old
`.gitattributes` convention did not canonicalize the M101 Python mechanism members. The raw
working-tree representation that generated the frozen mechanism aggregate was therefore not
preserved as an independently recoverable blob.

**Classification:** historical binding/replay portability limit. The thirteen scientific/integrity
predicates P2–P14 reproduce; full byte-exact M101 replay does not.

## R-HIST-07 — M102 inherits the unrecoverable M101 source byte

M102 likewise recomputes **P2 through P14 true**. Its qualification-apparatus and checker bindings can
be reconstructed exactly, but its mechanism aggregate cannot. M102 preserves individual member
digests and exposes the decisive inherited member: `metamorphosis/m101_runtime.py` expects the
M101-era raw digest, while the frozen Git object plus canonical LF/CRLF alternatives do not yield that
digest.

The later M103 instrumentation explicitly fixes this class by extending line-ending canonicalization
past the old `M0*` convention that stopped matching after M100.

**Classification:** inherited historical source-byte portability defect; P2–P14 reproduce, P1/P15 do
not independently replay byte-exactly.

## R-HIST-08 — M103 negative, M104 positive, M105 negative all reproduce

M103 and M105 again hit their preserved fail-closed direct-script bootstrap failures and return the
same negative verdicts. M104, replayed in its exact first-result chronology, returns **15/15 true**,
`replay_equal=true`, and the same stable-evidence digest.

## R-HIST-09 — M106 P1–P15 reproduce; P16 contains an absolute-path accident

With the frozen M106 source, **P1 through P15 are true**. P16 alone fails because the supposedly stable
evidence retains `runtime.isolated_python`, an absolute installation path. A Windows path and a
hosted Linux path necessarily differ even when Python/SQLite identity and every scientific predicate
match.

**Classification:** genuine stable-projection portability defect, not an H51 refutation. Prospective
stable evidence should encode runtime identity semantically and exclude absolute installation paths;
the later line already hardens this.

## R-HIST-10 — M107 through M111 fully reproduce

The later line is substantially cleaner:

- M107: **16/16 true**, `replay_equal=true`;
- M108: **16/16 true**, `replay_equal=true`;
- M109: **18/18 true**, `replay_equal=true`; the handed counterfactual again reports
  `no_expressible_rule_reproduces_the_trial_record`;
- M110: **24/24 true**, byte-stable replay;
- M111: **24/24 true**, byte-stable replay.

All report zero model, network and remote-execution calls during verification where those counters are
part of the checker contract.

## R-HIST-11 — M112 mixed result reproduces exactly

The blind-bank M112 checker reproduces the historical structure exactly:

- procedural independence: **10/10 true**;
- diagnosis arm: **24/24 true**, positive;
- transfer arm: **22/24 true**, with P1 and P5 false, negative;
- overall verdict: **mixed**.

This is a successful reproduction of a mixed result, not a failed audit.

## Frozen-history rule

None of these findings modifies an old protocol, result, tag, threshold or hypothesis verdict. Where
an old exact-replay claim is not portable, the limitation is preserved explicitly and a prospectively
hardened successor carries the fix.