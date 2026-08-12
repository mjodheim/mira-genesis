# Blind sealed task banks — the reusable instrument

`mira-blind-bank-v1` is a milestone-agnostic contract for obtaining a held-out task bank from a
process that was shown nothing about this project, sealing it before anyone reads it, and
committing to it publicly by digest. M075-B is its first user. It is intended to become the
standard mechanism for future externally materialized holdouts.

It is **not** a replacement for an independent human maintainer. See
[the claim boundary](../experiments/M075B/CLAIM_BOUNDARY.md) — the distinction is the point of the
design, not a caveat attached to it.

## Modules

| Module | Responsibility |
|---|---|
| `metamorphosis/blind_bank_protocol.py` | The contract: canonical form, generator descriptor, frozen spec, payload structure, public commitment, generation ledger, reveal authorization |
| `metamorphosis/blind_bank_isolation.py` | The container boundary: invocation planning, argv auditing, attestation |
| `metamorphosis/blind_bank_sealing.py` | Canonicalize, digest, delegate encryption, scan for leaks, verify repository guards |
| `metamorphosis/blind_bank_devkit.py` | A deterministic stand-in generator that can only emit development payloads |
| `metamorphosis/m075b_blind_readiness.py` | The M075-B binding: analysis plan, system protocol, phase machine, fail-closed gate |

| Entry point | Use |
|---|---|
| `scripts/check_blind_bank_readiness.py` | Report the phase; `--require-ready` before a reveal; `--assert-not-revealed` in CI |
| `scripts/check_blind_bank_leakage.py` | Refuse a tree carrying plaintext, a key, or an unprotected digest-bearing path |
| `scripts/run_blind_bank_devkit.py` | Drive the whole chain on a fixture, writing nothing into the repository |

## The five roles

**Builder** knows the project and builds the instrument; it may never author the qualifying tasks.
**Blind generator** is a separate pinned model with no project context. **Class oracle**,
optionally, confirms a task's feasibility class without selecting among tasks. **Custody** is
encryption plus a signed reveal gate. **Tested system** is frozen before reveal. **Evaluator** is
owned by the bank, outside the mutable body and outside the generator.

## The ordered chain

`F1 freeze → generate once → validate → seal → F2 freeze → readiness → signed reveal → one run →
preserve`

Two orderings in that chain were chosen deliberately and are worth stating:

**The scoring rule is frozen at F1, not F2.** Bank size determines which p values are reachable,
so a threshold chosen after the bank existed would be fitted to it without any task being read.
`validate_analysis_plan` then re-derives the attainable exact McNemar p at the frozen threshold
and rejects a plan that could never pass — the mirror of the M086-A defect, where a threshold
could never fail.

**The tested-system freeze is at F2, after sealing.** The harness must be written against the
schema, and freezing its digests after the bank exists costs nothing as long as no content is
known. What matters is the invariant the information boundary carries:
`tested_system_unmodified_after_reveal`.

## Three design choices that are easy to get wrong

**Opaque identifiers derive from a nonce, not from the domain name.** An identifier derived from
the subject matter is a dictionary attack away from disclosing the bank before reveal.
`opaque_domain_id(nonce, index)` takes the name nowhere near the digest.

**The isolation audit resolves paths; it does not match strings.** `../Mira Genesis`, a symlink,
and `HOME` pointing at the checkout all defeat a substring test. Mount sources are resolved and
compared against the repository root in both directions, so mounting the parent directory is
caught too. An attestation's own `repository_mounted: false` is not trusted; the recorded argv is
re-audited independently, and a dishonest pair fails.

**No cipher is implemented here.** Sealing delegates to `age` or `gpg`. A bespoke construction in
a research repository would be the least-reviewed code in the chain, guarding the one artifact
that cannot be re-created if it is wrong. `sealing_plan` returns argv and refuses any destination
inside the checkout; nothing in these modules starts a process.

## Making impossibility structural

The weakest part of any refusal benchmark is that "impossible" usually means "phrased so that a
careful reader gives up". This contract requires a machine-checkable certificate instead. Each
task declares the capabilities its environment provides and the capabilities it requires. For an
impossible task, the named absent capability must be:

- present in `required_capabilities`;
- absent from `provides_capabilities ∪ permitted_interfaces`;
- **the only** required capability that is absent — otherwise a failure carries no information
  about which absence mattered;
- **the only** difference from its pair's feasible task, which shares the same environment image.

That last rule is what makes "matched pair" mean something. Without it, a pair is any two tasks
filed under one identifier, and a difference in outcome says nothing about capability.

## Reusing this for another milestone

The generic modules carry no milestone-specific thresholds, hypothesis or agent identity —
deliberately, because M075's validator hard-codes refusal thresholds and the `gpt-5.6-sol`
identity, which is why M085 had to build a separate instrument rather than reuse it. To add a
milestone:

1. add `metamorphosis/<milestone>_blind_readiness.py` binding the generic contract to that
   milestone's hypothesis, analysis plan and system protocol;
2. register its digest-bearing paths in `.gitattributes` **in the same commit that creates the
   directory**, before any digest exists to be wrong;
3. add its readiness and leakage checks to CI as decisive steps.

Step 3 is not optional. M086-A recorded a positive verdict against a threshold that could not
fail, partly because a scientific checker existed without being decisive in CI. A green CI must
guarantee the properties the registers claim it guarantees.
