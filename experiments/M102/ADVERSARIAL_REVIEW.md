# M102 pre-freeze adversarial review

Status: **clean for owner review; not frozen; qualification not executed**  
Review date: 2026-08-24  
Scientific track: Track A, bounded mechanism evidence

## Scope

This review attacks the M102 implementation against H47 and the falsifiers in
`PRE_REGISTRATION.md`. It covers the state migration, registry policy K, later SQLite capability C,
fresh-process capsules, destructive baselines, dependency controls, rollback, population authoring,
canonical runner and independent checker.

It does not inspect a qualification outcome. No M102 qualification acquisition, migration, hidden
scoring, baseline, mutation, rollback or replay has been run. The only end-to-end executions used
distinct `development-*` fixtures constructed outside `QUALIFICATION_POOL.json`.

## Falsifiers found and corrected before freeze

### F1 — declared B dependency could have been dead

The first C decoder required `definition_dependencies == [B]` but did not separately require the C
body to execute a `CALL:B:*` token. Development behavior happened to select B, but a digest-valid
state could have declared B while calling A.

Correction: both acquisition and execution decoders now require an executed live B call. The
independent definition checker separately requires exactly one B call, one direct effect and four
distinct opaque effects. A targeted dead-dependency mutation is rejected.

### F2 — host-side K gate manufactured causality

The first C acquisition implementation explicitly returned failure unless the policy origin label
was `m102-acquired-policy`. That would make K necessary by host authorization rather than by
constructive reach.

Correction: the origin gate was removed. C acquisition now asks only whether the live policy can
reconstruct the complete registered relation and resolve the demanded SQLite descriptors. The
no-K lineage receives the same predecessor, events, atomics, runtime and public C observations but
fails because the flat image contains unequal collisions. More search budget cannot change that
image. SQLite qualification slots deliberately collide with earlier record slots, making K's
cross-carrier addressing behavior materially necessary.

### F3 — Python docstring rendering was interpreter-sensitive

The DEVELOPMENT full-run rehearsal exposed that `ast.unparse` can render a docstring with different
quote forms across supported Python interpreters. Exact source equality would therefore mix
representation formatting with M101 B conservation.

Correction: the M102 conservation world uses semantic `wrap_return(abs)` as the third B effect and
keeps docstring insertion only as a distractor. The change was made before freeze and before any
qualification execution.

### F4 — protocol construction did not fail closed outside the canonical runtime

The first owner-review candidate recorded CPython 3.11.16 and SQLite 3.53.1, but its builder derived
those fields from the interpreter that invoked it. The Python 3.13 CI matrix therefore constructed
an alternate candidate instead of refusing construction. The frozen runner would later have bound
that alternate identity consistently, so the original candidate alone did not prevent a runtime
substitution before final freeze.

Correction: candidate and final protocol construction now require the exact canonical CPython
3.11.16 and SQLite 3.53.1 identities and fail closed otherwise. The multi-version CI test reads the
committed candidate as evidence and separately mutates the observed runtime identity to verify the
refusal. This correction occurred before final protocol acceptance and before any qualification
execution; it requires a superseding owner-review candidate with fresh apparatus bindings.

## Shortcut and leakage audit

The current source audit verifies all of the following:

- the execution capsule contains no acquisition, enumeration, registration, pool or result writer;
- every official registry lookup executes the serialized policy body;
- C execution interprets its serialized body and live B dependency rather than calling a host
  four-effect pipeline;
- the acquisition capsule contains no hidden-case loader, pool reader, result checker or repository
  enumerator;
- K receives no target body, target digest, qualification SQLite world or hidden lookup;
- C receives only its trigger's public cases and descriptors reached through the live registry;
- C search has no exact target-order prefilter;
- the pool author imports no M102 mechanism and performs no scientific execution;
- qualification hidden record material is materialized only after U1 producer exit;
- SQLite hidden/reuse material is materialized only after U2 producer exit;
- all scientific actions use synchronous isolated base-Python subprocesses;
- model, network, remote execution, credential, repository and deployment authority are absent;
- the result checker independently implements policy execution, registry reconstruction, A/B/C
  symbolic order, real SQLite execution, stable projection and P1–P15;
- the canonical writer is exclusive-create, attempt-one only, owner-armed and refuses a dirty tree.

## Development evidence only

The frozen-style apparatus has been rehearsed twice on a separate DEVELOPMENT population. After the
precommitted stable projection, both evidence objects had the same digest. The rehearsal exercised:

- U0 creation from exact M101 T2 bytes;
- structural flat collision;
- K construction without registration and K adoption;
- destructive last-write forgetting and fail-closed flat registration;
- post-producer record retention;
- SQLite registry migration;
- no-K C failure from unrepresentable joint state;
- C construction without registration and C adoption;
- actual SQLite trigger/reuse execution;
- M101/M100 conservation;
- K mutation/ablation, B mutation/ablation, C mutation/ablation and corruption;
- selective unrelated-capability controls;
- exact byte rollback and full capability restoration.

This is apparatus validation, not scientific evidence for H47.

## Residual limits and claim boundary

The unique qualification attempt remains unknown. A clean positive would support only **bounded
continual interference and registry meta-improvement mechanism evidence under an independently
maintained SQLite execution interface**. It would not establish independent task authorship, close
G4 or G5, demonstrate broad continual learning, provide real-environment general-agent evidence,
or support an AGI claim.

SQLite is independently maintained, but the task family, adapters, fixtures and evaluator are
project-authored. External reproduction and adversarial review remain future requirements for any
stronger claim.
