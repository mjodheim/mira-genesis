# M040 development result 001 — duplicate dependency representation failure

**Status: consumed infrastructure failure. Not a plasticity measurement. Not canonical.**

Evaluated head: `9619b5d86fead0a3a2ad57446a48c568595ad5f0`  
Development seed: `400041`  
Repair commitment: `experiments/M040/AMENDMENT_001_CONTINUATION_FRONTIER.md`  
Workflow run: `30916962084`

The continuation-frontier patch was applied in the workflow worktree, but the focused suite
failed before migration or post-migration search.

The newly derived M039-style pre-migration lineage selected a valid program that invoked the
same birth tool more than once. `LineageTool.input_tool_ids` rejected the resulting tool
because that field required unique IDs.

This exposed a representation mismatch:

- the executable program is an ordered invocation sequence and may repeat an operation;
- `input_tool_ids` is a dependency set used for provenance and should contain each dependency
  once in first-use order.

The failure occurred during cycle-1 tool construction. It produced no M040 packet, migration,
post-migration task or control result. All eight focused tests consequently errored at fixture
setup.

Seed `400041` is consumed for this implementation state. The repair must normalise dependency
IDs without changing the ordered executable program. M039 canonical artefacts, frozen
identities and historical event bytes must remain unchanged.
