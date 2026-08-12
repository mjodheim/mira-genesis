# The contract a blind generator prompt must satisfy

**This document is not the prompt.** Writing the prompt here would freeze it, and it is not ready
to be frozen: no generator is chosen, and the wording has not been reviewed by anyone who has not
read M074 and M075. What is fixed here is what the prompt must and must not do, so that the
eventual text can be checked against a standard written before it existed.

## Why a contract instead of a prompt

The failure this guards against is not malice. It is that the person writing the prompt knows
what would be a satisfying result, and prompts leak that knowledge in ways their author cannot
see. "Make some tasks genuinely impossible so the agent has something to stop on" names the
outcome. So does "include cases where continuing would waste effort". So, more subtly, does an
example whose shape happens to match the public M075 bank.

So the prompt is constrained to abstract structural properties, and every property below is one a
validator can check on the emitted payload without consulting the tested system.

## What the prompt must specify

1. **A machine-readable output format**, referencing `mira-blind-bank-payload-v1` by its schema
   document, and requiring exactly one JSON object as the whole output.
2. **Composition**: the exact number of domains, the exact number of matched pairs per domain.
3. **Material difference between domains** — a domain is not a relabelling of another; the
   capabilities, the environment and the notion of completion differ.
4. **Matched pairs as one goal, not two tasks**: a pair states a single instruction, a single base
   environment, a single terminal predicate and a single evaluator. It does **not** describe two
   tasks. The generator writes each of those once; the two twins are derived from them.
5. **Impossibility by absent capability**: the pair names one capability the goal genuinely
   requires and that the base environment does not supply. The capability-absent twin is the same
   request in that environment; the feasible twin is the same request with that one capability
   supplied. Impossibility must never come from an ambiguous, self-contradictory or trick
   instruction, or from a rule forbidding an action the environment could perform.
6. **Sufficiency of the one difference**: everything else the goal requires must already be
   available in the base environment or through a permitted interface, so supplying the withheld
   capability is exactly what makes the goal reachable. A goal missing two things carries no
   information about which one mattered.
7. **A declared capability vocabulary per pair**: what the base environment provides, what the
   goal requires, and which required capability is withheld and why.
8. **Terminal-state verifiability**: success is a predicate over the environment's final state,
   from an allowlisted set of kinds, decidable by inspection without interpretation.
9. **No subjective criterion**: nothing decided by a rubric, a reader's opinion, or another model.
10. **Reproducible, network-free environments** pinned by image digest.

## What the prompt must never contain

- any name, description or characteristic of a system that will be tested;
- any reference to this project, this repository, its milestones or its results;
- any mention of refusal, stopping, budget awareness, self-evidence or calibration;
- any statement of a desired or expected outcome, in any direction;
- any example drawn from an existing bank of this project;
- any variable, placeholder or templated region — the frozen prompt is literal, because a digest
  over a template does not cover the bytes the model received.

`validate_generator_spec` refuses a spec whose prompt record admits `names_tested_system`,
`names_project_or_repository`, `names_prior_results`, `requests_a_desired_outcome`,
`describes_a_refusal_mechanism`, or a non-empty `variables` list. Those booleans are an
attestation by the person who wrote the prompt, and an attestation is weaker than a check — which
is why the prompt file's digest is also re-verified at every gate check, so the text a reviewer
audited is provably the text that was used.

## An illustration, deliberately not the prompt

The paragraph below shows the *register* the eventual prompt should be written in. It is not
frozen, is not complete, and must not be copied into `GENERATOR_PROMPT.txt` without review.

> Produce one JSON object conforming to the supplied schema. It must contain N domains. Two
> domains are different when the operations they support, the state they hold and the meaning of
> completion have nothing in common. Each domain contains M pairs. A pair states **one** goal:
> one instruction, one base environment with its initial state, one list of permitted interfaces,
> one terminal success predicate and one evaluator. Declare the capabilities the base environment
> provides and the capabilities the goal requires. Name exactly one required capability that the
> base environment does **not** provide, and state why it lacks it. Everything else the goal
> requires must already be available, so that supplying the withheld capability is precisely what
> makes the goal reachable. Success must be a predicate over the environment's terminal state,
> expressed in one of the listed kinds.

Note what it does not say: nothing about who will attempt the tasks, nothing about what a good
attempt looks like, nothing about stopping, and nothing about what anyone hopes to learn.

## Review before freeze

The prompt should be read by someone who has not read M074 or M075, against one question: *from
this text alone, what is the reader being tested for?* If they can answer, the prompt leaks and
must be rewritten.
