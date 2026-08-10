# Brief for an independent task-bank maintainer

You have been asked to hold a private task bank for one experiment in this repository. This document
is written for someone with no prior knowledge of the project. Reading it should take ten minutes,
and the work itself is roughly an afternoon.

## Why the project cannot do this itself

M075 tests whether an agent stops working on tasks it cannot complete, instead of burning its budget
trying. The public version of that test already ran: the agent refused 2 of 3 impossible tasks with
no false refusals. That result cannot be used as evidence, because the project wrote the tasks. An
author who writes both the test and the answer measures their own expectations.

So the tasks must come from someone outside the project, and must stay unseen until the project has
committed, in public and by digest, to exactly how it will be scored. That person is you.

The repository enforces this in code rather than by promise. `check_m075_private_readiness.py`
refuses to proceed while your signed attestation is missing, and it rejects the attestation outright
if the signer identity is the project author. The project literally cannot sign its own
independence.

## What you are attesting

Five things, all about *you and your bank* — never about whether the agent is good:

1. You maintain the bank independently and have disclosed any relationship to the project.
2. The bank spans at least **four materially different domains**.
3. It contains at least **eight matched pairs**: for each pair, one task that is genuinely doable in
   the environment, and one that is impossible because a required capability is absent.
4. No task reuses public benchmark content the agent may have seen.
5. Success is decided by your evaluator from environment state, not by the agent's own report.

You are not asked to vouch for the project, predict the outcome, or endorse any conclusion.

## What you must not do

- **Do not send the tasks.** You send metadata and a signature. The archive stays with you until the
  project has frozen and published its scientific protocol against your envelope digest.
- **Do not let the project see the task content, filenames or descriptions**, even informally. The
  domain identifiers in the envelope are deliberately opaque strings.
- **If anyone asks for the payload before the protocol freeze, refuse.** The ordering is the entire
  scientific content of the arrangement. A bank revealed early is worthless as evidence.
- **Do not hand over your private key.** You sign on your own machine.

## How to do it

```bash
python scripts/run_m075_intake_kit.py --template > PRIVATE_BANK_ENVELOPE.json
python scripts/run_m075_intake_kit.py --instructions
```

The first writes a skeleton with every required field. Replace each `REPLACE...` value and set the
payload digest, payload size and your public-key digest. The second prints the exact `ssh-keygen`
commands for signing and for the allowed-signers line.

Then check your work before sending anything:

```bash
python scripts/run_m075_intake_kit.py --validate PRIVATE_BANK_ENVELOPE.json --signature-verified
```

This runs the same validator the gate enforces, so if it accepts your envelope the gate will too.
The kit cannot sign anything — it has no process module in its import graph — and it never opens
task content.

## What happens next

1. You send three files: the envelope, its `.sshsig` signature, and the allowed-signers line.
2. The project runs the readiness gate, which verifies your signature against your own key.
3. The project freezes its scientific protocol — agent, budgets, thresholds, causal design, single
   attempt — bound to your envelope digest, and commits it publicly.
4. Only then do you release the payload.
5. The experiment runs once. No retry, no task replacement, whatever the outcome.
6. A separate party reproduces it from your bank.

If the result is negative, it will be published as negative. This repository preserves failed
results rather than rerunning them; several of its recorded outcomes are refutations.

## What your name will appear on

Your identity string, your public-key digest, the domain count and the pair count. Not the tasks,
not their content, and not any claim about what the result means.
