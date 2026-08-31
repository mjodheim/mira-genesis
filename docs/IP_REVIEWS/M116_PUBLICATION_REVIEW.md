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

Anthony Mets remains the sole human research director and the sole acceptance and release
decision-maker for this milestone.

OpenAI ChatGPT provided substantial earlier research-design and audit assistance for the prospective
successor, including the original M116 pre-registration candidate and the capacity diagnosis.

Anthropic Claude subsequently provided substantial implementation, code-review, testing and
research-analysis assistance for the prospective **pre-freeze instrument hardening** recorded after
that original pre-registration: the non-carrier telemetry allowlist and read boundary, the
deterministic terminal classifier, machine-only pre-seal admission and the positional carrier
envelope, the mechanically derived schema-complexity census, the pre-generation tested-system freeze
and its mechanical inventory checker, and the accompanying adversarial test suites. That work was
performed against the frozen public record and proposed for the owner's review; it was not accepted
into the scientific record by the assisting system.

OpenAI Codex or comparable tooling may additionally be used for independent review, local test or
execution assistance.

All of the above are recorded as AI tooling and AI development assistance. None is recorded as human
authorship, and none holds acceptance authority. This production-provenance record does not mean
provider terms clear third-party rights or settle legal authorship or inventorship.

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

Two defects in the inherited apparatus were identified during the pre-freeze hardening and are
corrected prospectively rather than retroactively: a terminal taxonomy wider than the classifier's
discriminating power, and an admission path that did not connect the frozen generator's output shape
to the frozen carrier host's expected payload. Neither finding revises M115's observed cause, and
neither derives from its sealed completion; both are properties of the frozen public source. The
historical limitation is recorded in `FAILURE_LOG.md` and stated exactly: truncation can be neither
established nor excluded from the M115 record.

The M115 record stays immutable. A future H61 positive, negative, mixed or instrument-aborted outcome
must be preserved as observed. Even a successful H61 remains bounded evidence from a blind generated
and sealed carrier bank; it does not by itself close G1, G4 or any other generality gate and does not
support an AGI claim.
