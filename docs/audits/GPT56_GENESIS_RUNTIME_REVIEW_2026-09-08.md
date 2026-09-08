# GPT-5.6 Genesis runtime hostile review — 8 September 2026

Status: independent review notes against PR #275 head `a23f78120e573f8fa1e708e21a1ded249119bec8`. No scientific gate moves and no recorded result is reinterpreted.

The review found concrete counterexamples that must be closed before the DEVELOPMENT demonstration can support the stronger persistence, retention, migration-verification, certificate, or causal-chain claims currently attached to the integrated runtime.

## Blocking findings

1. `task_set_digest()` hashes only task identifiers, so a migration caller can reuse identifiers with easier task contents and make an unevaluated verification set appear previously evaluated.
2. `Genesis.restore()` does not restore the original admission envelope: budget, isolation, trust-root admission, evaluated task-set identities and executable body binding are not persisted as one checkpoint. State and journal are individually authenticated but not transactionally cross-bound.
3. Acquired component/vocabulary certificates are not semantically reconstructed by `create_state()` / `decode_state()`; a self-consistent forged certificate can therefore carry the right schema/name while violating the evidence rules enforced by the certificate builders.
4. `trust_root.decide()` compares solved counts, not retention. A candidate can forget tasks the parent solved, gain more elsewhere and still be accepted.
5. `Proposal.ablated_body_factory` is an arbitrary callable. The runtime does not prove that the ablation arm is the candidate with exactly the named earlier acquisition removed, so a deliberately weak unrelated body can manufacture an apparent causal dependency.

These are engineering findings about DEVELOPMENT apparatus, not scientific observations. Each must receive a failing counterexample test before any fix is described as closed.
