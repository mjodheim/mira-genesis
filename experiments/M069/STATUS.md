# M069 status

**POST-HOC DISQUALIFIED DEVELOPMENT RESULT — EVALUATOR-ISOLATION FALSIFIER.**

The original run below met its recorded task and control thresholds. A later interface audit proved
that candidate code ran in the evaluator process holding hidden cases and could return them through
admitted public-evaluator output. This fires the Phase 8 hidden-evidence-reachability falsifier.
There is no evidence that the frozen learner exploited the path; its outcomes remain diagnostic,
but the positive qualification is withdrawn. See
[`EVALUATOR_ISOLATION_DISCLOSURE.md`](EVALUATOR_ISOLATION_DISCLOSURE.md).

## Historical run record

Freeze commit `9d482d2` predates exact learner commit `c603dd5`. One unchanged policy found one
public survivor for each of four compatible real-file/process tasks and each passed 3/3 hidden
cases. The incompatible task returned `policy_refused` before any write or process. All ten frozen
controls pass and a second process reproduces the exact manifest digest `c5c80701`.

Exact learner commit `c603dd5` passed CI run `31319062535`: 1,181 tests on Python 3.11 in
1,241.52 seconds, 1,181 on Python 3.13 in 1,260.38 seconds and repository integrity. Attribution
run `31319062599` passed.

The evaluator and finite complete repair statements remain project-authored. Registered commands
are governed host processes, not an OS security sandbox. See
[`DEVELOPMENT_RESULT.md`](DEVELOPMENT_RESULT.md).
