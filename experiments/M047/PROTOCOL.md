# M047 — integrated modular-software lineage

**Status: PASSED IN DEVELOPMENT.**

## Development qualification

The first generic CI workflow run `31039609326` (run number `400`) qualified marker commit
`c791ad0b460faebde6625cc986f4b14cdf304ea9` without a failed job or rerun:

- **788 tests passed on Python 3.11** in `577.03` seconds;
- **788 tests passed on Python 3.13** in `587.07` seconds;
- repository imports, orphan detection and dependency consistency passed.

This remains a positive integrated development result, not a canonical result.

## Why M047 exists

M046 demonstrated that one bounded lineage can propose and select useful transformations
without enumerating the complete candidate space. Its mutable body, however, remained a
formal Mealy machine. M047 moves the construction frontier to a small executable software
architecture whose modules are represented as real Python source files.

M047 is one integrated experiment. It is not a new sequence of representation, search,
validation and rollback gates. It reuses the causal and transactional discipline established
by M043–M046 while replacing the automaton body with executable modular software.

## Mutable software body

The founder contains eight independently versioned source modules:

- `interpretation` — parses prefix requests into structured expressions;
- `planning` — converts expressions into executable plans;
- `selection` — maps plan operations to registered tools;
- `execution` — executes the selected tool plan;
- `critique` — transforms or approves raw results;
- `allocation` — assigns an explicit execution budget;
- `orchestration` — coordinates the complete pipeline and records traces;
- `tool_core` — provides the founder arithmetic tools.

The body also owns executable generated regression tests. A transformation may replace one
or more source modules, add a new `tool_*` module and append new regression tests. Accepted
source text, tests, patch registry and causal journal are all part of the versioned body.

Every source module:

- has a deterministic metadata header;
- is parsed as Python before admission;
- has a fixed source-size limit;
- forbids imports, global/nonlocal declarations and unsafe dynamic or external-system tokens;
- is executed only inside a disposable worker process.

The lineage receives no repository, network, credential, deployment or external-system
authority.

## Fixed integrated sequence

One deterministic lineage must complete six accepted adaptations:

1. diagnose the interpreter when the public alias `sum` is unknown and add the alias;
2. diagnose the planner when nested expressions fail and replace its root-only strategy with
   recursive postorder planning;
3. diagnose missing tool selection for `mean`, create a new executable `tool_mean` source
   module and route the operation to it;
4. diagnose the critic when exact raw values need two-decimal presentation and replace its
   policy;
5. diagnose the allocator when valid deep plans exceed the fixed budget and replace it with
   a plan-dependent policy;
6. diagnose the interpreter for the new alias `average`, reuse the acquired alias-patch
   template and execute the previously acquired `mean` tool.

After the six accepted cycles the lineage must:

- instantiate the already acquired alias-patch template for a valid provisional `total`
  adaptation;
- validate it independently;
- force causal-journal corruption during transactional adoption;
- restore the exact combined lineage-and-memory checkpoint;
- face a compound `maximum` task requiring simultaneous interpreter, selection and new-tool
  changes beyond the one-boundary proposal surface;
- terminate explicitly for insufficient evidence without modifying the accepted body;
- replay the accepted source patches, registry, memory, checkpoints and forced rollback
  exactly.

## Diagnosis and proposal boundary

The generator receives only:

- the accepted public body;
- public task cases;
- disposable execution traces for those public cases;
- the causal proposal memory;
- fixed resource limits.

It does not receive hidden cases, expected hidden outputs, validator decisions from untried
patches or release authority.

Failures are diagnosed by pipeline stage:

- interpretation failures identify an unknown lexical token;
- planning failures identify unsupported structure;
- execution routing failures identify a missing selected tool;
- execution budget failures identify allocation;
- successful execution with a mismatching final value identifies critique.

The generator then instantiates only the small patch family associated with that diagnosed
boundary. It does not enumerate Python programs, module combinations, source strings or the
complete program space.

## Independent validation and adoption

A separate task-side validator owns the hidden cases. It executes the incumbent and ranked
candidate bodies in disposable workers and requires:

- every baseline and previously accepted protected case to remain correct;
- every generated regression test to execute successfully;
- all current public and hidden cases to pass;
- the patch to change exactly the independently declared module boundary;
- source and validation resource limits to be respected.

The generator cannot adopt a patch. Only an accepted independent validation object may enter
the transactional store. Adoption versions the executable body, patch registry and
hash-chained causal journal. A failed audit restores the exact prior snapshot.

Hidden cases from every accepted cycle are retained as protected validator-only cases for
all later cycles. They are never added to the generator-visible regression suite.

## Frozen resource bounds

- accepted adaptive cycles: `6`;
- public diagnostic cases per task: `8` maximum;
- generated patches per task: `8` maximum;
- independent validation attempts per task: `4` maximum;
- complete candidate source body: `131,072` bytes maximum;
- working proposal memory: `262,144` bytes maximum;
- persistent causal proposal memory: `262,144` bytes maximum;
- proposal-search wall time: `60` seconds per task;
- disposable runtime timeout: `30` seconds per batch;
- maximum explored fraction: `100,000` parts per million of the conservative program-space
  lower bound;
- forced rollback fault: causal-journal corruption.

Wall-clock values affect fail-closed decisions but are excluded from deterministic manifest
identity.

## Causal memory and reuse

The immutable causal memory records:

- the diagnosed module;
- selected successful patch templates;
- independently rejected templates;
- dominated proposals;
- insufficient-evidence episodes;
- proposal and validation counts;
- causal reasons for acceptance or termination.

M047 must demonstrate both:

- reuse of an acquired source-patch template on a later task; and
- reuse of an acquired executable runtime tool after the cycle that created it.

## Replay scope

M047 does not rerun stochastic or heuristic discovery merely to manufacture a second result.
It replays every accepted patch against its exact parent, reconstructs the complete accepted
source body, patch registry, causal memory and checkpoints, and repeats the forced rollback.
The replay must reproduce the recorded bytes and digests exactly.

## Success criteria

M047 passes in development only if permanent falsification tests establish:

- six accepted module-level adaptations;
- correct diagnosis of interpretation, planning, selection, critique and allocation defects;
- creation of a new executable tool module;
- persistent executable generated tests;
- hidden validation independent from proposal generation;
- preservation of all prior hidden capabilities on later cycles;
- disposable execution of every candidate source body;
- non-exhaustive bounded proposal generation;
- source-patch template reuse;
- acquired runtime-tool reuse;
- causal success and failure memory;
- six verified combined checkpoints;
- exact rollback of body, registry, journal and memory after the forced fault;
- explicit insufficient-evidence termination on the compound terminal task;
- accepted body unchanged by that termination;
- exact replay of accepted sources and lineage state;
- bounded, noncanonical claim metadata.

## Claim boundary

M047 is a bounded modular-software development experiment. Its task language, module
interfaces, patch templates and validators remain fixed. It does not establish arbitrary
self-programming, unrestricted source-code generation, open-ended evolution, general
intelligence, consciousness, production safety or authority over repositories and external
systems.

M047 selects no seed, freezes no hidden bank and authorises no canonical workflow. M042
remains the only positive canonical continuous-lineage completion. M045 remains reserved for
the separate proxy-measurement track.
