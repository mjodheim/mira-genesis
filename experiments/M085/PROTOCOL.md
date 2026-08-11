# M085 cross-domain transfer — design, frozen before any bank exists

**STATUS: AWAITING AN INDEPENDENT TASK-BANK ENVELOPE. NO SCIENTIFIC PROTOCOL IS FROZEN YET AND NO
RESULT EXISTS.**

This document freezes everything about M085 that does not depend on the external bank. The
scientific protocol proper — `CROSS_DOMAIN_SCIENTIFIC_PROTOCOL.json` — can only be frozen once a
signed envelope exists to bind, because it must carry that envelope's digest, bank identity, payload
digest and maintainer key. Writing it now would be writing a commitment to nothing.

## The question

G4 asks that knowledge acquired in one domain improve held-out performance in another, against a
fresh agent with the same tools, compute and observation budget.

M084 already has that shape: one lineage against a fresh organism at matched budget, with success
scored from environment state. It fails G4 on two counts, and this experiment exists to remove both.

**Its domains were not domains.** Four stages over three substrates, all driving one carrier family
that the project wrote. Moving between environments one author designed is not evidence about
crossing domains, and the repository's own rules forbid calling it that.

**Its ablation cost no correctness.** Every arm reached every reachable goal; persistence bought
steps and earliness. A G4 claim resting on efficiency would be weak, and M084's own status file says
so.

**H31:** a policy acquired by one organism in some domains improves its *correct terminal decisions*
in a materially different, externally maintained, held-out domain, relative to a fresh organism with
identical code and an identical budget.

## Why this cannot reuse M075's boundary

M075 built a fail-closed pre-private boundary for a different question. Its validator hard-codes
refusal thresholds — six true refusals, zero false refusals, a wasted-step advantage — the
`gpt-5.6-sol` agent identity, a `baseline-structured-request` versus `epistemic-context-request`
design, and a claim boundary reading `bounded_composed_system_refusal_transfer_only`. A G4 protocol
fails that validator on every one of those fields.

So M085 does not touch it, does not loosen it and does not route around it. It builds a separate
instrument at the same standard: signed envelope from a non-project identity, opaque domain
identifiers, payload held externally until the protocol is frozen, and a validator that refuses by
default. `exact_mcnemar_two_sided` is imported from M075 rather than restated.

M075's own private experiment remains open and blocked on its own maintainer. M085 does not
substitute for it.

## What the external bank must contain

Three materially different domains, at least eight tasks each, at least six of them
correctness-critical. A task is correctness-critical when all three hold:

1. some action is accepted by the domain and has no effect on its state;
2. a later step is only correct if that action actually took effect;
3. committing on the false premise reaches a terminal state the task's budget cannot undo.

Clause 3 is the whole point. It is what makes an organism that trusts what its actions reported end
up **wrong** rather than merely slow, and it is precisely what M084 lacked.

The maintainer chooses the instances; the project specifies only the structure, before seeing
anything. That is the same division M075 uses, where the project specifies "eight matched pairs, one
feasible and one impossible" and the maintainer picks the tasks.

## The held-out domain is drawn after the freeze

The project publishes the derivation before it knows the salt:

```
sha256("m085-target-assignment-v1\0" + payload_sha256 + "\0" + salt) mod domain_count
```

The maintainer releases the salt only after the scientific protocol is frozen. Without this the
project could inspect three domains and test itself on the one it happens to suit. Three domains
rather than two so that the draw cannot be guessed at better than one in three, and so that two
source domains show the acquisition is not a quirk of a single one.

## Arms

| Arm | What it is | Predicted |
|---|---|---|
| `transferred_lineage` | acquires in the two source domains, then meets the held-out domain carrying what it acquired | reaches correctness-critical goals |
| `fresh_agent` | identical code, identical budget, no acquisitions, meets the held-out domain cold | commits on false premises and cannot detect it |
| `acquisition_ablated` | the same lineage with its acquisitions cleared at the domain boundary; identity, version and journal preserved | must match `fresh_agent` metric for metric |

`fresh_agent` is G4's literal control. On this track it is cleaner than the gate's own wording: with
no model in the loop, the two arms differ *only* in acquired state, so nothing has to be argued about
matched base models.

`acquisition_ablated` exists to show the ablation is not leaking. In M084 it reproduced the fresh arm
exactly; if the two diverge here, something crossed that should not have.

## Thresholds, frozen now

- at least **6** tasks correct for `transferred_lineage` and not for `fresh_agent`;
- **0** tasks correct for `fresh_agent` and not for `transferred_lineage`;
- two-sided exact McNemar **p ≤ 0.05**;
- zero faulted episodes; success decided by the maintainer's evaluator from domain state;
- `acquisition_ablated` matches `fresh_agent` on every behavioural metric.

Six discordant tasks in one direction give an exact p of 2/2⁶ = 0.03125. Five would give 0.0625 and
could not clear 0.05, which is why the minimum bank size and the threshold were chosen together
rather than separately. Requiring at least six correctness-critical tasks per domain is what makes
the threshold reachable in principle while leaving it entirely possible to fail.

Cost metrics — steps, probes, repair cycles — are reported for comparability with M084 and are
**not** decisive. That is the correction M084 asks for.

## What a negative would mean

Named in advance so a negative is informative:

1. **the acquisition is substrate-shaped, not domain-general** — it survived three substrates because
   they shared a carrier ontology, and a real domain change dissolves it;
2. **the fresh agent does not actually fail** — the maintainer's correctness-critical tasks are
   recoverable in practice, and the category needs rewriting before any successor;
3. **the transfer is real but too small** — fewer than six discordant tasks, so the effect exists and
   the bank cannot resolve it;
4. **the ablation leaks** — `acquisition_ablated` beats `fresh_agent`, meaning identity or journal
   carried something the design assumed they did not;
5. **the adapter contract does not fit an externally written domain** — the abstraction M084
   introduced turns out to be shaped by the environments it was written against.

Outcome 5 would be the most valuable negative, and the most likely to be missed if the contract were
written after seeing the bank.

## Claim boundary

Even a positive result does **not** close G4. Closure additionally requires independent reproduction
from a separate bank and a separate maintainer, which the protocol makes a precondition rather than
a hope.

It would establish bounded cross-domain transfer of **one acquired policy** in one externally
maintained bank. Not AGI, not general autonomy, not open-ended evolution, not Genesis Gate 2 or 3,
not general competence in any of the domains involved.

## Current state

`python scripts/check_m085_readiness.py` returns `ready_for_payload_reveal: false` with four
blockers, and every one of them requires a person outside this project:

- `CROSS_DOMAIN_BANK_ENVELOPE.json`
- `CROSS_DOMAIN_BANK_ENVELOPE.sshsig`
- `CROSS_DOMAIN_BANK_ALLOWED_SIGNERS`
- `CROSS_DOMAIN_SCIENTIFIC_PROTOCOL.json`, which cannot be written until the first three exist

No payload has been requested, accessed or described. No held-out domain has been drawn.
