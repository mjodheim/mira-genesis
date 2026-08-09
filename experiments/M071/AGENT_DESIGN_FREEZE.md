# M071 agent-and-bridge freeze

**FROZEN BEFORE EXTERNAL TASK SELECTION — NO M071 SCIENTIFIC RESULT.**

The generic governed runtime is fixed at commit
`0820ebc3a638e8ae0e06fceed7addbdb71bafbb7`. The separately named Harbor bridge is fixed at
`132476a5db532812a0cd223d02f8eba9ad88e346`. This two-commit boundary avoids pretending that the
bridge can embed the hash of the commit that contains that same embedded hash.

The machine-readable artifact [`AGENT_DESIGN_FREEZE.json`](AGENT_DESIGN_FREEZE.json) binds every
runtime and test blob needed by the composed agent. Its commitment is
`2e76a1b8b390bee0ee55095a6f3f61366176e7a4ac0791add9d6d37fca5c30a2` and is checked by
`scripts/check_m071_agent_design_freeze.py`.

At this boundary, no benchmark revision is pinned, no new task identifier has been selected, and
no new task content has been inspected or executed. Terminal-Bench 2 is only the declared public
development benchmark family.

M071 is a Track B, model-mediated experiment. A future reward belongs to the named composed system
(Codex model, governed policy, process transport, Harbor body and evaluator), not to Mira's
governance layer in isolation. The experiment does not amend Genesis Gate 2 and cannot establish
AGI, endogenous task proposal, broad transfer or safe deployment.
