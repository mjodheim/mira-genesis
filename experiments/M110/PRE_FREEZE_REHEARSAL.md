# M110 — pre-freeze dress rehearsal

Recorded **before** the freeze and before any canonical attempt, so the number below is a prediction
rather than a description. If the canonical run produces a different stable evidence digest, that
discrepancy is itself evidence and must be reported, not reconciled.

## What was rehearsed

A throwaway clone of this branch, checked out with `core.autocrlf true` so every Python and Markdown
member arrives with CRLF while the JSON members arrive raw. The clone then ran the entire canonical
path end to end: candidate protocol behind an annotated tag, final protocol behind a second, one
canonical attempt, one checker replay, and every refusal path the frozen instrument can meet.

The clone's own protocol and result digests are rehearsal artefacts and are deliberately **not**
recorded here: they depend on rehearsal tag names and would differ at the real freeze.

## The prediction

| | |
|---|---|
| population digest | `d4e8ae471eb46bbf1bc40f51746cef83d6f5ea3a65c1eadd4388b8b07cdaa33e` |
| **predicted stable evidence digest** | `92ee5e051d9a955c500f6006f273b17e8d70dd0ffeda48cba8aca17a7146bfb7` |
| predicted verdict | positive, P1–P24 all computed true |
| replay | performed and equal |

The stable projection excludes PIDs, search paths, return codes, elapsed times, temporary paths and
interpreter versions, so it should be identical on any machine running the canonical interpreter over
the same population and apparatus. That is what makes it a testable prediction rather than a note.

## Foreign checkout

| | |
|---|---|
| bound Python members received CRLF | yes |
| bound JSON members received raw bytes | yes |
| boundary audit | confirmed in both directions |
| test suite in the clone | 21 passed |

The bound-file record declares `raw` for JSON and `lf_normalized` for Python and Markdown, so a third
party recomputes exactly what was frozen instead of guessing which their checkout produced.

## Every refusal path, exercised

| path | outcome |
|---|---|
| canonical before any protocol exists | refused, failed closed |
| canonical with a candidate but no final protocol | refused, failed closed |
| canonical without the owner flags | refused, failed closed |
| canonical on a dirty worktree | refused, failed closed |
| a second canonical attempt | refused, failed closed |
| checker before any result exists | refused, failed closed |
| a second checker report | refused, failed closed |
| truncated result bytes | refused, failed closed |
| bound apparatus changed after freeze | refused, failed closed |

## The tamper that matters

The interesting case is not a broken file. It is a result whose evidence was **edited and whose every
digest was then recomputed**, so integrity alone cannot see it.

One outcome was flipped — `M1` recorded as resolving the row-5 demand — and every dependent digest
rebuilt. The checker's integrity block came back entirely true, and **P16 came back false**. The claim
is carried by predicates computed from the evidence, not by digests over it. A tamper that survives
the digests still has to survive the measurements, and this one did not.

## What the rehearsal does not establish

Nothing about H55. It establishes that the instrument runs, refuses correctly, replays byte-stably
across a foreign checkout and cannot be edited into a positive verdict without being caught. The
scientific question is decided only by the single canonical attempt, whatever it returns.
