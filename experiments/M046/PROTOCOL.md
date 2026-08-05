# M046 — integrated scalable non-exhaustive lineage

**Status: IN DEVELOPMENT.**

## Why M046 exists

M042 and M044 show that one bounded lineage can repeatedly transform, preserve tools,
migrate, continue learning, roll back and replay exactly. Their central remaining limitation
is candidate search: useful rewrites are found inside small finite spaces that can still be
traversed broadly or exhaustively.

M046 is one integrated experiment, not a new sequence of component gates. It reuses the
qualified M043/M044 Mealy body, rewrite certificates, disposable validator, transaction
store, causal journal and exact rollback. Its only new construction claim is that a longer
lineage can generate and select promising transformations from bounded observations while
examining only a small fraction of a conservative lower bound on the candidate space.

## Fixed integrated sequence

One deterministic lineage must:

1. start from the public two-state M043 founder;
2. face six successively generated hidden structural tasks from two task families;
3. collect a bounded diagnostic observation set without receiving the target body or a
   witness rewrite;
4. generate only evidence-backed capacity-changing proposals;
5. rank proposals using observation fit and causal memory from prior successes and failures;
6. submit ranked proposals to an exact validator outside the generator;
7. submit an admitted proposal to the existing disposable M043 validator;
8. adopt exactly six accepted transformations transactionally, growing from two to eight
   states;
9. preserve the registered rewrite tools, original lineage learning state and journal;
10. preserve a separate causal proposal memory containing accepted, rejected and dominated
    proposal evidence;
11. create a verified combined checkpoint after every accepted cycle;
12. force one journal-corruption fault on a valid provisional seventh adoption and restore
    the exact combined lineage-and-memory checkpoint;
13. face a two-growth hidden challenge that cannot be certified by the fixed one-growth,
    depth-three proposal surface;
14. terminate explicitly for insufficient evidence without modifying the accepted body;
15. replay the complete experiment to byte-identical manifest bytes.

## Proposal mechanism

The generator computes shortest access words to reachable parent states and spends its
observation budget on diagnostic words of the form:

`access(state) + entry_symbol + probe_symbol`

A last-symbol mismatch is treated as evidence that a transition target may need to be split
and specialised. The generator builds only proposals supported by those mismatches:

- duplicate one reachable transition target;
- edit one observed clone emission; or
- edit the complete observed clone-emission set when two mismatches support it.

It does not enumerate unseen output values, all operation permutations, the powerset of
edits, all rewrite traces or the complete candidate space. Exact equivalence is absent from
the proposal module.

## Independent validation

The proposal generator sees only bounded observations. A separate task-side validator checks
ranked proposals for exact target equivalence and returns only acceptance or rejection, not
the hidden target or a distinguishing witness. An accepted trace is then replayed again by
the existing isolated M043 validation worker before transactional adoption.

A language model is not required for this development experiment. A future generator may use
one, but it must retain the same validation separation.

## Frozen resource bounds

- accepted adaptive cycles: `6`;
- diagnostic observations per task: `128` maximum;
- generated candidates per task: `48` maximum;
- exact task-side validation attempts: `8` maximum;
- rewrite depth: `3` operations maximum;
- body ceiling: `10` states;
- working search memory: `262,144` bytes maximum;
- persistent causal proposal memory: `262,144` bytes maximum;
- proposal-search wall-clock allowance: `30` seconds per task;
- maximum explored fraction: `100,000` parts per million of the conservative candidate-space
  lower bound;
- forced rollback fault: causal-journal corruption;
- terminal challenge: two required minimal-state growth steps.

Wall-clock duration is enforced but not written into the deterministic manifest. The manifest
records whether the time bound was respected.

## Non-exhaustive evidence

For every accepted cycle, M046 records:

- diagnostic observations used;
- generated and invalid proposal counts;
- a conservative lower bound consisting only of valid depth-three traces beginning with a
  safe duplicate and followed by two distinct emission edits;
- the explored fraction in parts per million;
- an explicit `complete_candidate_space_enumerated = false` marker;
- independent validation attempts and rejections;
- working and persistent memory consumption.

The experiment fails closed if generated candidates equal or exceed the lower bound, if the
explored fraction exceeds ten percent, or if any fixed resource limit is exceeded.

## Causal memory and reuse

The original M043 lineage state continues to preserve exact successful traces as registered
tools and operation-priority learning. M046 adds an immutable proposal memory containing:

- selected successful templates;
- exact validator rejections;
- proposals dominated by stronger evidence;
- terminal insufficient-evidence episodes.

Later searches receive only this memory, the current parent and the bounded evaluator
observation interface. Reuse is counted separately for registered exact tool-effect patterns
and causal proposal templates.

## Success criteria

M046 passes in development only if all permanent tests establish:

- six accepted cycles and final growth from two to eight states;
- both hidden task families solved by generator-selected traces;
- no complete candidate-space enumeration;
- every explicit resource budget respected;
- generator/validator separation preserved;
- exact disposable validation before every adoption;
- causal success and failure memory retained and reused;
- registered tools reused on later cycles;
- six verified combined checkpoints;
- exact combined rollback after the forced fault;
- explicit insufficient-evidence termination on the terminal challenge;
- accepted body unchanged by that termination;
- immediate deterministic replay;
- bounded, noncanonical claim metadata.

## Claim boundary

M046 remains a bounded formal development experiment. It does not claim open-ended evolution,
general program synthesis, unrestricted self-modification, AGI, consciousness or authority
over repositories, networks, credentials, deployments or external systems. It does not
replace M045, select a canonical seed or authorise a canonical workflow.
