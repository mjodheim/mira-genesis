# Independent-maintainer handoff — H21 / H31

**Audit date:** 2026-09-05  
**Status:** preparatory only. This document creates no external evidence and does not weaken either
independence boundary.

The two remaining external blockers are intentionally impossible for the project author, an internal
agent or another project-authored bank to satisfy. This handoff tells a future independent human
maintainer exactly what the existing fail-closed validators require without exposing, inventing or
pre-selecting task content.

## Independence rule common to both attempts

The maintainer must be a real identity outside the project author identities (`Anthony Mets`,
`mjodheim`) and must attest the independent-task-bank-maintainer role, independence and conflicts.
The task payload remains in the maintainer's custody and unrevealed to policy authors until the signed
envelope has been accepted and the corresponding scientific protocol has been frozen.

The project must **not** author the held-out bank for the maintainer, inspect the payload early, select
a favorable domain after seeing it, replace failed tasks after execution or silently rerun an
attempt.

For both attempts the signed envelope is verified with `ssh-keygen -Y verify`; an SSH signing key and
an allowed-signers entry are therefore required. The envelope itself is metadata only. It contains a
SHA-256 commitment to a sealed tar payload rather than the task content.

## H21 / M075 — private paired causal bank

Readiness command:

```text
python scripts/check_m075_private_readiness.py --require-ready
```

Required pre-reveal paths:

```text
experiments/M075/PRIVATE_BANK_ENVELOPE.json
experiments/M075/PRIVATE_BANK_ENVELOPE.sshsig
experiments/M075/PRIVATE_BANK_ALLOWED_SIGNERS
experiments/M075/PRIVATE_SCIENTIFIC_PROTOCOL.json
```

The envelope must use schema `m075-private-bank-envelope-v1`, status `sealed_unrevealed`, media type
`application/vnd.mira.m075-private-bank+tar`, signature namespace
`mira-m075-private-bank-v1`, and custody `external-until-protocol-freeze`.

Minimum bank shape already frozen by the validator:

- at least **4 opaque domains**;
- at least **8 matched capability pairs** total;
- exactly two task instances per pair;
- at least 2 pairs in every declared domain;
- no reused public-development tasks;
- evaluator-owned success labels;
- materially cross-domain coverage attested;
- payload unrevealed to policy authors before protocol freeze.

The scientific protocol is not freely editable. The existing validator freezes the two paired
conditions, single-attempt policy, budgets, exact McNemar analysis and thresholds. In particular the
protocol requires a separate-bank, separate-maintainer reproduction before H21 can be supported.
One maintainer/bank can therefore produce the first private result, but **a second independent bank and
maintainer are still required** for the H21 support claim.

The project should provide the maintainer the validator/schema and signing instructions, not proposed
task answers or examples that encode the desired result.

## H31 / M085 — cross-domain held-out transfer bank

Readiness command:

```text
python scripts/check_m085_readiness.py --require-ready
```

Required pre-reveal paths:

```text
experiments/M085/CROSS_DOMAIN_BANK_ENVELOPE.json
experiments/M085/CROSS_DOMAIN_BANK_ENVELOPE.sshsig
experiments/M085/CROSS_DOMAIN_BANK_ALLOWED_SIGNERS
experiments/M085/CROSS_DOMAIN_SCIENTIFIC_PROTOCOL.json
```

The envelope must use schema `m085-cross-domain-bank-envelope-v1`, status `sealed_unrevealed`, media
type `application/vnd.mira.m085-cross-domain-bank+tar`, adapter contract
`m085-domain-adapter-v1`, signature namespace `mira-m085-cross-domain-bank-v1`, and external custody
until protocol freeze.

Minimum bank shape already frozen by the validator:

- at least **3 materially distinct domains**;
- at least **8 tasks per domain**;
- at least **6 correctness-critical tasks per domain**;
- an opaque domain id for each domain;
- a different committed material-difference statement for every domain;
- evaluator-owned success;
- no reuse of public tasks.

The held-out target domain is deliberately **not selected by the project**. After the scientific
protocol is frozen, the maintainer releases the assignment salt and the target is derived from the
sealed payload SHA-256 plus that salt. All other domains become sources. The three scientific arms
are `transferred_lineage`, `fresh_agent` and `acquisition_ablated`, under matched budgets.

The central correctness-critical task definition is also frozen: an action may report acceptance
without effect, a later step is valid only if that effect really occurred, and committing on the
false premise reaches a terminal state the budget cannot undo. The claim is about evaluator-owned
correct terminal state, not merely efficiency.

H31 also requires independent reproduction under its frozen reproduction contract; the first external
result is preserved regardless of what the reproduction does.

## What a future maintainer should receive

A clean handoff should contain only:

1. a tagged repository snapshot containing the existing validators and adapter contracts;
2. this navigation note;
3. instructions for generating an SSH signing key / allowed-signers line and signing the raw envelope;
4. a machine-readable blank envelope template generated directly from the validator's closed schema;
5. a local preflight command that validates envelope structure without revealing the payload;
6. a clear statement that the project does not want task content, answers, labels, domain names or the
   assignment salt before the relevant freeze.

Templates or helper scripts may validate syntax, calculate hashes and sign metadata. They must never
generate the scientific task bank itself, choose domains, write expected answers or optimize the bank
against prior Genesis results.

## Current blocker status

As of this audit, no qualifying H21 or H31 external envelope was found in the repository or in the
user's searched Drive under the expected M075/M085/private/cross-domain identifiers. The readiness
commands correctly remain fail-closed.
