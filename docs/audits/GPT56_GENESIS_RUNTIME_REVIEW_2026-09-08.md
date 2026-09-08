# GPT-5.6 Genesis runtime hostile review — 8 September 2026

Status: independent review notes against the head of PR #275 as it stood when this review branch was created. The exact base commit is recorded by PR #276 itself rather than repeated here, so this DEVELOPMENT audit does not create a new scientific commit citation. No scientific gate moves and no recorded result is reinterpreted.

The review found concrete counterexamples that must be closed before the DEVELOPMENT demonstration can support the stronger persistence, retention, migration-verification, certificate, causal-chain, immutable-evaluator, or integrated-runtime claims currently attached to the apparatus.

## Blocking findings

1. **Task identity hashes labels, not questions.** `task_set_digest()` hashes only task identifiers, so a migration caller can reuse identifiers with easier task contents and make an unevaluated verification set appear previously evaluated.

2. **Process-death restoration creates a new admission envelope.** `Genesis.restore()` does not restore the original budget, isolation, trust-root admission, evaluated task-set identities or executable-body binding. State and journal are individually authenticated but not transactionally cross-bound. A restart can therefore manufacture fresh budget and accept a caller-selected body under the persisted state.

3. **Acquired certificates are not semantically reconstructed.** `create_state()` / `decode_state()` accept a structurally self-consistent acquired certificate after checking its schema/name, without replaying the semantic evidence rules enforced by the certificate builders. A forged certificate can therefore claim exhaustion or separation that its own records do not establish.

4. **Adoption can forget capability.** `trust_root.decide()` compares solved counts, not retention by task identity. A candidate can forget tasks the parent solved, gain more elsewhere and still be accepted.

5. **The causal ablation arm is caller-authored.** `Proposal.ablated_body_factory` is an arbitrary callable. The runtime does not prove that it is the candidate with exactly the named earlier acquisition removed, so a deliberately weak unrelated body can manufacture an apparent causal dependency.

6. **The proposer receives the mutable runtime object.** `cycle()` invokes `propose(self, tasks)` after measuring the parent. The callback can directly replace `Genesis.body_factory`, `budget`, `isolation`, `admitted_isolation`, `state`, `journal`, `admitted_source_sha256` or `grade`. It can therefore change the lineage without an adoption transaction, widen its own runtime envelope, or alter the evaluator between the parent and candidate arms. This directly violates the stated invariant that mutable Genesis cannot improve by modifying the measure that decides it is better.

7. **The grader is outside the immutable admission identity.** Candidate correctness is now decided by `Genesis.grade`, but that callable is neither in `trust_root.py` nor bound by the admitted trust-root digest. Even without the broader mutation surface in finding 6, changing the grader changes the measure while every verdict still names the same trust-root source digest.

8. **`Proposal.digest()` does not identify the executable candidate.** It hashes only proposal name, provenance and rationale. Two different `body_factory` implementations with the same metadata receive the same proposal digest, and an accepted state's `body_digest` is therefore not a digest of the body. This also makes strong executable continuity across restart impossible with the present representation.

9. **An aborted parent still marks the task set as evaluated.** `cycle()` adds `task_set_digest(tasks)` to `evaluated_task_digests` before `run_candidate(parent, ...)`. If the sandbox aborts, the migration gate can later treat a set as work the lineage was evaluated on even though no evaluation occurred.

10. **Metamorphosis success ignores migration capability preservation.** `metamorphosis_succeeded()` checks journal continuity, discovered operations, carried records and post-migration causal acceptance, but does not require `migration.capability.measured` or `migration.capability.preserved`. A migration whose executable capability was never measured — or one explicitly allowed to lose capability — can therefore be reported as succeeded.

11. **The DEVELOPMENT demonstration is host orchestration, not yet the integrated controller described by the target.** `run_genesis_demonstration.py` directly calls probe functions, assigns `genesis.state`, appends to the journal, calls migration, chooses every proposal and supplies the executable body again after restart. The primitives run in one Python process, but the host script still performs the architectural sequencing. The target's `observe -> diagnose -> hypothesize -> construct -> test -> adopt/reject -> persist -> continue` controller therefore remains to be built as a runtime capability rather than a demonstration script.

12. **The experimental component certificate drops the positive experiment that licensed it.** `diagnose_by_experiment()` finds `resolving_composition`, but `certificate_from_experiment()` discards that record and calls `component_extension_certificate(... resolves_with_new_component=True)`. The certificate therefore retains prior failures and a caller boolean, not the composition that actually established wider reach.

13. **A newly acquired component is not bound to executable semantics.** The caller supplies a human-readable component name; the state stores the name and certificate, but no implementation/operation set is bound to that entry. In the DEVELOPMENT fixtures the component-operation registry still contains only the seed components. The runtime can therefore add a certified name without yet adding a component that future diagnosis can execute as such. This is a narrower statement than saying the experimental diagnosis is worthless: the diagnosis found real wider reach, but the evidence-to-component transition is not complete.

14. **The state's provenance claim is incomplete.** `create_state()` says every entry declares origin and provenance, but only component entries enforce provenance. Vocabulary entries carry no provenance, `extend_vocabulary()` accepts none, and tools/acquisitions/observations are copied as arbitrary records without a producer requirement. A state can therefore say a vocabulary or acquisition is lineage-owned by implication without containing evidence of who produced it.

15. **A substrate record reveals operations the lineage did not discover.** `Substrate.record()` includes both `operations_available` and `operations_discovered`, and `migrate()` writes that record into the lineage journal. Once the lineage can inspect its history, the record itself tells it the names of capabilities it never found by probing. This contradicts the intended information boundary that substrate semantics are learned only through discovery.

16. **Migration provenance is hard-coded rather than measured.** `migrate()` appends provenance `lineage_owned / lineage migration` regardless of who supplied the translation callable. In the DEVELOPMENT demonstration the translation is host-authored, yet the record labels the migration lineage-owned. The record therefore cannot currently support the provenance distinction it claims to preserve.

17. **The journal is hash-chained but not authority-safe in memory.** `append()` returns the same mutable record stored internally; iteration returns references to internal records; `entries()` and `of_kind()` copy only the outer dictionary, leaving nested payloads shared. Code holding the `Journal` object can therefore mutate historical entries in memory. A hash chain detects accidental tampering only if the mutator does not also own the ability to rewrite/rebuild the chain; the live runtime currently exposes both.

18. **`carried_intact()` loses multiset identity.** It tests each departing digest with `identifier in after_ids`. If an identical lineage record occurs twice before migration and once after, both departing occurrences are considered present. Extra arrival records are likewise not treated as a difference. If the claim is that the same lineage arrived intact, the comparison needs multiset/exact identity rather than membership-by-value.

## Known boundary that must remain explicit

The sandbox honestly reports limits it could not enforce, and its audit hook explicitly covers pure Python only. That honesty is good. The remaining requirement is architectural: any future strong claim about untrusted lineage-generated executable code must fail closed when the admitted isolation profile was not actually obtained, or move the execution into a boundary capable of enforcing the required controls. This review does not relabel the documented limitation as a newly discovered scientific failure.

## Required repair shape

These are engineering findings about DEVELOPMENT apparatus, not scientific observations. Each mechanically testable finding must receive a failing counterexample test before any fix is described as closed.

The most important architectural consequence is finding 6: the lineage-owned proposal mechanism must not receive authority over the host-side runtime object. It needs a read-only, content-addressed observation/context value and must return a proposal as data. Budget, isolation, evaluator identity, journal mutation, state mutation and the final adoption transaction must remain outside that capability surface.

Likewise, the grader has become part of the evaluator and must be admitted immutably. A verdict that binds only `trust_root.py` while correctness is decided by an unbound callable is not yet a verdict bound to its measure.

The component path needs one additional type: an acquired component artifact must bind the measured resolving construction to something the runtime can subsequently execute or compose, not merely to a new label. The certificate should preserve the raw/derived evidence required to reproduce that binding.

Finally, the demonstration driver should shrink over time. Its correct end state is a thin launcher that supplies an initial world/admission envelope and asks Genesis to run; it should not itself perform the diagnosis, extension, migration or state transitions whose integration it is meant to demonstrate.
