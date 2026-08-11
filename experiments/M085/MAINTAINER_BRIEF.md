# Brief for an independent cross-domain task-bank maintainer

You have been asked to hold a private task bank for one experiment in this repository. This document
is written for someone with no prior knowledge of the project. Reading it should take fifteen
minutes; the work itself is roughly a weekend.

## What is being tested

The project has built a software organism that learns something in one environment and keeps it when
it moves to another. In its last experiment it crossed a terminal, a browser and a desktop session,
and on returning to the terminal it no longer needed to rediscover what it had learned the first
time.

That experiment had two weaknesses, and this one exists to remove them.

**The first is that the project wrote every environment itself.** Moving between three environments
that one author designed is not evidence that knowledge crosses between genuinely different domains.
An author who writes both the lesson and the exam measures their own expectations.

**The second is that being ignorant only cost the organism time.** Without what it had learned it
still reached every goal, just more slowly. A claim resting on that is weak. This time, an organism
that has not learned the lesson must actually get things **wrong**.

So the domains must come from someone outside the project, and must stay unseen until the project
has committed, in public and by digest, to exactly how it will be scored. That person is you.

The repository enforces this in code rather than by promise. `check_m085_readiness.py` refuses while
your signed attestation is missing, and rejects it outright if the signer is a project author. The
project cannot sign its own independence.

## What you are building

**Three domains that are materially different from one another**, and at least **eight tasks in
each**. Two domains are materially different if a strategy that exploits the structure of one buys
nothing in the other — different state, different things a value can be held in, different way of
observing. Three flavours of the same file store are not three domains.

At least **six of the eight tasks in each domain must be correctness-critical**, meaning all three of:

  (a) some action is accepted by your domain and has no effect on its state;
  (b) a later step is only correct if that action actually took effect;
  (c) committing on the false premise reaches a terminal state that the task's own budget cannot
      undo.

Point (c) is the one that matters most, and it is what was missing last time. An organism that
believes what an action told it must end up wrong, and must have no way to tell that it is.

Each domain exposes four things and nothing else — the carrier names it accepts with their costs, a
way to observe what those carriers hold, a way to act, and your own evaluator that decides whether a
task succeeded from your domain's real state. Run this for the exact contract:

```bash
python scripts/run_m085_intake_kit.py --adapter-contract
```

A task is a goal — the values certain carriers must end up holding — plus a step budget. **You must
not supply a decomposition, a hint or an ordering.** Working out how to reach the goal is the thing
being measured.

## What you are attesting

Six things, all about *you and your bank* — never about whether the organism is any good:

1. You maintain the bank independently and have disclosed any relationship to the project.
2. It spans at least **three materially different domains**.
3. Each domain has at least **eight tasks**, of which at least **six are correctness-critical** by
   the definition above.
4. No task reuses public benchmark content the project may have seen.
5. Success is decided by your evaluator from your domain's state, never by what the organism says.
6. You have written a short paragraph justifying each domain's material difference, and the SHA-256
   of each paragraph is in the envelope. You keep the paragraphs; the project checks them against
   those digests after the payload is released, so this is falsifiable later rather than merely
   believed now.

You are not asked to vouch for the project, predict the outcome or endorse any conclusion.

## What you must not do

- **Do not send the tasks.** You send metadata and a signature. The archive stays with you until the
  project has frozen and published its scientific protocol against your envelope digest.
- **Do not let the project see task content, filenames or domain descriptions**, even informally.
  The domain identifiers in the envelope are deliberately opaque strings.
- **Do not send the assignment salt early.** See below — it is what stops the project choosing which
  of your domains it is tested on.
- **If anyone asks for the payload or the salt before the protocol freeze, refuse.** The ordering is
  the entire scientific content of the arrangement.
- **Do not hand over your private key.** You sign on your own machine.

## The one thing this brief adds over the project's earlier one

You also generate a **random assignment salt** and keep it back.

The project publishes, before it knows the salt, the exact rule by which one of your three domains
becomes the held-out target: the organism learns on the other two and is then tested on that one.
You release the salt only after the protocol is frozen. Without this, the project could look at your
three domains and pick the one its organism happens to suit.

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## How to do it

```bash
python scripts/run_m085_intake_kit.py --template > CROSS_DOMAIN_BANK_ENVELOPE.json
python scripts/run_m085_intake_kit.py --adapter-contract
python scripts/run_m085_intake_kit.py --instructions
```

The first writes a skeleton with every required field. Replace each `REPLACE...` value and set the
payload digest, payload size, your public-key digest and the per-domain statement digests. The last
prints the exact `ssh-keygen` commands for signing and for the allowed-signers line.

Then check your work before sending anything:

```bash
python scripts/run_m085_intake_kit.py --validate CROSS_DOMAIN_BANK_ENVELOPE.json --signature-verified
```

This runs the same validator the gate enforces, so if it accepts your envelope the gate will too.
The kit cannot sign anything, and it never opens task content.

## What happens next

1. You send three files: the envelope, its `.sshsig` signature, and the allowed-signers line.
2. The project runs the readiness gate, which verifies your signature against your own key.
3. The project freezes its scientific protocol — organism, budgets, thresholds, arms, single attempt
   — bound to your envelope digest, and commits it publicly.
4. Only then do you release the assignment salt, and then the payload.
5. The experiment runs once. No retry, no task replacement, whatever the outcome.
6. A separate party reproduces it from a separate bank before the project may claim anything.

If the result is negative it will be published as negative. This repository preserves failed results
rather than rerunning them; several of its recorded outcomes are refutations, including one where the
hypothesis the project most wanted was cleanly rejected.

## What your name will appear on

Your identity string, your public-key digest, the domain count, the task counts and the
correctness-critical counts. Not the tasks, not their content, and not any claim about what the
result means.
