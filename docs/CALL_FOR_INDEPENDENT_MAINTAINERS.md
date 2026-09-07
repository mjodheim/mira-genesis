# Call for independent task-bank maintainers

Mira Genesis needs people it does not control. This document says exactly what the role is, what it
costs, and what disqualifies a candidate — so that anyone considering it can decide honestly, and so
that no one later has to guess whether the independence was real.

It is written to be sent to a stranger. Nothing in it requires knowing anything about the project's
results.

## The short version

Two claims in this project are blocked, permanently and by design, until someone outside it authors
a set of tasks, withholds them, and lets the project be measured against them. The project cannot
lift this by any internal work, and it is forbidden from substituting its own output — or an AI's —
for yours.

If you take the role, **you must be able to make this project fail.** That is not a risk of the job.
It is the job.

## What the role is not

- Not a witness. You are not attesting that something happened.
- Not a reviewer. You do not read the project's code and give an opinion.
- Not a rubber stamp. Four of the attestations you sign are technical judgments only you can make.
- Not a favour to the author. A favour is precisely what would void it.

## What you actually do

You author a **sealed task bank**: a set of task families in domains you invent, packaged so the
project's system can be driven against them without knowing what they are. You keep the payload.
You send the project only a signed commitment to its hash.

Concretely, for the cross-domain bank (M085):

- **at least 4 opaque domains**, each a directory in your archive;
- **8 tasks per domain**, of which **at least 6** must be *correctness-critical* (defined below);
- each domain exposes exactly four operations — `describe()`, `observe(carriers)`,
  `act(kind, carrier, value)`, `evaluate(task)` — and nothing else;
- one short paragraph per domain justifying that the domains are materially different, whose SHA-256
  you commit to now and whose text the project checks *after* the payload is released;
- an SSH-signed envelope, an allowed-signers line, and a secret assignment salt you release only
  after the project has frozen its protocol.

A task is a goal — the values certain carriers must end up holding — plus a step budget. **You must
not supply a decomposition, a hint, or an ordering.** Working out how to reach the goal is the thing
being measured.

### What makes a task correctness-critical

All three must hold:

1. some action is accepted by your domain and has **no effect** on its state;
2. a later step is only correct if that action actually took effect;
3. committing on the false premise reaches a terminal state the task's own budget **cannot undo**.

Condition 3 is not decoration. An earlier experiment here found that an agent which trusted what its
actions reported merely spent more steps than one that checked — it still arrived. That makes a weak
claim. Here, an agent that trusts its actions must end up **wrong, and unable to tell**.

### What "materially different" means

Two domains are materially different if a strategy exploiting the first's structure buys nothing in
the second: different state, different vocabulary of carriers, different way of observing. Three
flavours of the same file store are not three domains.

## The cost, stated plainly

This is several days of real engineering work by someone competent, who cannot be coached through
it. There is no version of this role that takes an afternoon. Anyone who tells you otherwise has
misunderstood the requirement.

## What disqualifies a candidate

These are not formalities. Each one has voided the requirement in practice.

| Disqualifier | Why |
|---|---|
| Being one of the project author identities (`Anthony Mets`, `mjodheim`), under any address | A second email address is not a second person |
| Having the task content authored by an AI on your behalf | The requirement is explicitly for a *person* to author and withhold tasks; an AI-written bank is drawn from the distribution the sealed bank exists to escape |
| Being unable to evaluate what you sign | You attest four technical properties; a signature on a document you cannot assess is a proxy signature |
| Being unwilling to produce a bank the project fails | Independence that cannot fail is not independence |
| Accepting compensation contingent on the outcome | See below |

**Using AI as a tool is not disqualifying.** If you design your domains and tasks with your own
judgment and use an assistant for Python syntax, or to explain an `ssh-keygen` invocation, that is
tooling — disclose it and proceed. The line is that the *content and the choice of domains must be
your judgment*, not an assistant's.

**Being paid is not disqualifying.** A contracted, compensated evaluator is standard research
practice. Two conditions: compensation must **not** be contingent on the result, and the arrangement
must be recorded in `conflicts_disclosed`.

**A personal relationship to the author is not automatically disqualifying, but it is corrosive.**
The envelope has a `conflicts_disclosed` field for exactly this. Disclosure is the requirement;
concealment is the disqualifier. Be aware that a reviewer will, correctly, discount a bank authored
by someone close to the author — so if the project has any alternative, it should take it.

## What the project will and will not do

**It will** give you the validator, the schema, the signing instructions and the adapter contract.
Run these:

```sh
python scripts/run_m085_intake_kit.py --instructions
python scripts/run_m085_intake_kit.py --adapter-contract
python scripts/run_m085_intake_kit.py --template
python scripts/run_m085_intake_kit.py --validate your-envelope.json
```

**It will not** author your bank, propose tasks or domains, show you examples that encode a desired
result, tell you what its system handles well or badly, inspect your payload early, select a
favourable domain after seeing your bank, replace failed tasks after execution, or silently rerun an
attempt.

If the project asks you for the payload or the salt **before** it has frozen its protocol against
your envelope digest, **refuse**. The ordering is the whole point, and your refusal is a designed
part of the protocol rather than an obstruction of it.

## The ordering, so you can police it

1. You author the bank and keep it.
2. You send the envelope, the signature and the allowed-signers line — never the archive.
3. The project runs `python scripts/check_m085_readiness.py --require-ready`.
4. The project publishes how the held-out domain will be derived from a salt it does not have.
5. The project freezes its scientific protocol against your envelope digest.
6. **Only then** do you release the salt, and afterwards the payload.

Step 4 before step 6 is what stops the project choosing which of your domains it is tested on.

## A second, separate role

The paired private bank (M075/H21) requires **two** independent maintainers and **two** independent
banks before its claim can be supported. One maintainer can produce the first private result only.
Its intake kit is `scripts/run_m075_intake_kit.py` and its readiness check is
`scripts/check_m075_private_readiness.py`.

Two further requirements — **independent reproduction** of a result, and an **external adversarial
audit** — are different roles again, and the audit specifically requires an adversary the project
does not choose. A task-bank maintainer does not satisfy either.

## If you are considering it

Read [`AGENTS.md`](../AGENTS.md), [`MIRA_GENERALITY_CRITERIA.md`](../MIRA_GENERALITY_CRITERIA.md)
and [`audits/EXTERNAL_VALIDATION_HANDOFF_2026-09-05.md`](audits/EXTERNAL_VALIDATION_HANDOFF_2026-09-05.md).
The second of those states, in the project's own words, that while these blockers stand an
AGI-candidate claim is **NO regardless of any internal result**. That is the thing your work would
change, and it is why the role cannot be filled by anyone the project can lean on.
