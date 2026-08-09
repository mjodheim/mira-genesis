# M071 external result

**PASSED THE PREREGISTERED NARROW THRESHOLD — PUBLIC DEVELOPMENT EVIDENCE.**

Canonical result SHA-256:
`d352651327898c3d51bfab3a9b86814de6c8fe7a01c70be2ae66702109feb14e`.

The frozen M071 composed system earned official Harbor reward `1.0` on
`custom-memory-heap-crash` and `0.0` on `sqlite-with-gcov`. Both matching `nop` controls earned
`0.0`. All four jobs completed with zero Harbor exception, zero retry and no task replacement.

| Task | `nop` | M071 | Agent terminal state | Steps |
|---|---:|---:|---|---:|
| `sqlite-with-gcov` | 0.0 | 0.0 | `policy_refused` | 7 |
| `custom-memory-heap-crash` | 0.0 | **1.0** | `submitted_for_external_evaluation` | 12 |

The SQLite agent ran seven admitted commands and then refused because the no-network environment
did not expose a usable compiler for the vendored source. This is a valid negative task outcome,
not an infrastructure exception. The custom-memory agent submitted after 12 decisions; the
external verifier accepted the resulting workspace.

## Protocol compliance

- Runtime `0820ebc`, bridge `132476a`, design commitment `2e76a1b8`.
- Selection rule `fa5d896`, pair binding `b403920`, execution protocol `6cc064b`.
- Protocol SHA-256 `31d3c7bd968cb3fc381b8c3272b599695f3294c8537a1d8d805fc0ef334e0555`.
- Official Harbor 0.20.0, repository-digest images, one process at a time.
- Agent phases realized `no-network`; agent setup performed no action.
- The agent never claimed success; Harbor alone supplied reward.
- Solutions and verifier tests were not inspected by the operator or exposed to the agent.
- The final local Python 3.14 preservation suite passed 1,225 tests with two skips in 2,257.69
  seconds; repository integrity passed.

## What this establishes

This is the first positive Mira Genesis result on a fresh, blindly selected independently
maintained task under an official external verifier and OS-isolated no-network agent phase. It
falsifies the narrow hypothesis that the corrected composed system would solve none of the pair.

The result belongs to the named composed system: `gpt-5.6-sol`, the M071 governed policy and
transport, Harbor body and evaluator. There is no governance-layer ablation, and `nop` is only an
empty-action floor. Therefore the score does not show that Mira owns the model's transformation,
does not advance Genesis Gate 2, does not establish broad transfer, and is not AGI evidence.
