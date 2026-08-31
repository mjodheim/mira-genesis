# M116 pre-publication review

**Decision date:** 31 August 2026  
**Disposition:** `PUBLIC_AGPL_COMMERCIAL_OPTION`

## Asset

M116/H61 is a prospective corrective replication of the closed M115/H60 instrument-aborted record.
M115 made one qualifying delivery, legitimately revealed the committed response once, and terminated
at strict-JSON admission with `invalid_json`; H60 remained untested and P1-P22 were not computed.
M116 does not repair, rerun, reinterpret or relabel that observation.

The successor may disclose only the instrument changes needed to reduce the risk that the external
blind-bank generator exhausts or misallocates its output budget before producing the already-defined
carrier payload. The scientific target, downstream qualification machinery, minimum-bank criteria,
scoring rules, P1-P22 semantics and claim boundary remain inherited from M115 unless a future
pre-registration explicitly proves that a change is scientifically neutral.

## Provenance and dependencies

Anthony Mets remains the sole human research director. OpenAI ChatGPT provides substantial
research-design and audit assistance for the prospective successor; OpenAI Codex may later provide
implementation, local-test or execution assistance. These systems are tooling, not human authorship.

The planned implementation uses Python standard-library facilities and the repository's existing
development tooling. External generation remains through OpenRouter and an explicitly attested
DeepSeek endpoint only if the pre-freeze development gate qualifies that route. No credential,
plaintext blind bank, confidential third-party payload or new system authority may be committed.

## Rights and publication decision

The work is project-controlled public research under the repository's AGPL/documentation licence
boundary. No patent-first, intentional trade-secret, contractual-embargo or confidential-third-party
reason for temporary private treatment is recorded. Alternative commercial permissions remain
possible only for rights controlled by the project owner.

## Scientific boundary

M116 is a new milestone and must receive a fresh H61 record. Development probes are instrument tests,
not scientific observations: they may use synthetic non-qualifying prompts and schemas, but they may
not send the H61 qualifying carrier input, inspect a future H61 bank, or influence downstream scoring.

The M115 record stays immutable. A future H61 positive, negative, mixed or instrument-aborted outcome
must be preserved as observed. Even a successful H61 remains bounded evidence from a blind generated
and sealed carrier bank; it does not by itself close G1, G4 or any other generality gate and does not
support an AGI claim.
