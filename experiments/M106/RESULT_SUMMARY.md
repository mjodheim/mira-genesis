# M106 / H51 — canonical result

> **VERDICT: POSITIVE (attempt 1). H51 supported within its frozen bounds. D075.**

This file is deliberately **outside** the protocol's bound apparatus list. Every bound member keeps
the exact bytes it had at freeze time, so `experiment/m106-frozen-protocol-v1` stays verifiable by
anyone, forever. Recording a verdict inside a bound document would silently change the binding and
make the freeze unreproducible — `require_frozen` would refuse with `bound apparatus changed`, which
is exactly what the replication tests assert must never happen.

| | |
|---|---|
| frozen protocol | `e92e1b087f7417c5e12811cb03a6204067049553ff6ffe35c6eeebe88be11b70` |
| bound apparatus | `2a37e36728f93d1f6ede352fc8c744664729bb4f8ddaf9111be379b835170659` |
| result | `7c22c889f5852ef4e8b6e63fa7c78352c741ee4d32dc2ed0c90061fd5cc8f394` |
| stable evidence | `7c7cabc440eeaedbf198f4d316769c57c9589ceb8e2bb9e805e2317258f1aa4f` |
| raw result bytes | `7a7c015ecfb5506c1eec5e6073773c021bd8b5caf94fb40a65a1e2f521436770` |
| check report | `762990181bbe096bcc8b407b8abc75adf2816073822bcbd424827748bfcc4f00` |
| runtime | CPython 3.11.16 / SQLite 3.53.1 |

P1-P16 all computed true; replay performed and equal; zero model, network and remote-execution
calls. Both fresh arms refused with four surviving behavioural classes per carrier and the semantic
image exhausted — underdetermination, not search exhaustion.

The mechanism module `metamorphosis/m105_runtime.py` was imported unchanged, and the target semantic
`(True, False, False, True)` was fixed before implementation, so this replicates the question M105
could never evaluate. **M105 remains negative; D074 is unchanged.**

See `../../DECISIONS.md` (D075), `PRE_REGISTRATION.md` and `ADVERSARIAL_REVIEW.md`.
