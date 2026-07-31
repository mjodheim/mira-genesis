# M014c — Development protocol draft

**Status: DRAFT — canonical evaluation forbidden**

## Question

Can a structural meta-plasticity passport retain and improve its learning efficiency after migration by adapting an environment-level prior across multiple episodes, while repeatedly reconstructing exact old and new bodies on one runtime-opaque substrate?

## Correction relative to M014b

M014b represented changes as local state-index edits and carried a static distribution learned during development. M014c instead represents changes as structural programs over invariant graph roles such as initial state, deepest accepting state and maximum-indegree rejecting state.

The passport learns:

- a library of structural programs;
- program-family counts across multiple source environments;
- an integer adaptation rate;
- an active weighted query policy;
- a bounded confirmation policy;
- a canonical integer-only trace format.

## Environment stream

Each environment contains a persistent sequence of independent inherited competences on the same opaque machine. The distribution over transformation families is stable within an environment but differs from development environments.

The first four episodes are calibration episodes. Their behavioral queries count toward total cost, but only later episodes are used for the pre-registered adaptation-advantage comparison.

Every episode must expose at least seven behaviorally distinct candidate programs. Targets with ambiguous latent labels are rejected during generation.

## Development spaces

- source DFA sizes: 4–7 states;
- held-out DFA sizes: 7–10 states;
- source environments: flip-dominant, return-dominant, cross-dominant and mixed;
- held-out environment profiles: generated permutations with one dominant and one secondary transformation family;
- transformation groups: flip, return, cross, expand and combination.

## Baselines under development

- same learned meta-passport with online adaptation disabled;
- same hypothesis language with random query selection;
- uniform structural passport without learned environment counts;
- privileged L* learning from scratch;
- oracle structural program ceiling.

## Embodiment requirement

For the principal system, each environment uses one opaque Boolean machine. Genesis discovers it once, caches only the discovered public semantics, and repeatedly:

1. constructs the inherited body;
2. identifies the structural modification from behavioral queries;
3. confirms the candidate independently;
4. constructs the updated body;
5. verifies that the archived inherited body remains byte-identical.

## Negative controls still to implement

- programs outside the library;
- state-adding transformations;
- unstable or changing oracles;
- abrupt environment distribution changes after calibration.

## Freeze gate

The protocol may be frozen only after:

- all development tests pass in GitHub Actions;
- the full generated-profile benchmark is reproducible;
- adaptive learning beats every non-oracle baseline with a defensible margin;
- body construction succeeds across all three opaque machine families;
- all negative families abstain without archive mutation;
- source isolation and integer-only trace audits pass.

Any canonical cases must be generated only after the immutable sealed PR head exists.
