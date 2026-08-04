# M040 development result 006 — positive resource-bounded prefix transfer

**Status: consumed positive development result for the actual mechanism executed. Not
canonical. Not a lineage-anchor result.**

Evaluated workflow head: `4637acdce71b7719668a734621669e04472bfe55`  
Development seed: `400046`  
Workflow run: `30921173303`  
Equal symbolic-node budget: `4,096`

The lineage-anchor integration compiled and added its task family, but only the private
`_execute` default was changed. The public `run_m040_development` default remained
`prefix_adaptation`, so the run executed the earlier full-prefix-plus-one-primitive family.

The actual result object reported:

- `trans_substrate_continuity_supported = true`;
- `post_migration_plasticity_supported = true`;
- `replay_supported = true`;
- task family `prefix_plus_primitive`.

Fourteen focused tests passed. The sole failure asserted that the task family was
`lineage_anchor`; the observed value was correctly `prefix_plus_primitive`.

This is therefore a valid consumed positive development observation for amendment 003's
equal 4,096-node prefix mechanism on a new seed. It is **not** evidence for amendment 004.

Seed `400046` is consumed and may not confirm the corrected lineage-anchor mechanism. The
first valid lineage-anchor evaluation must change both task-family defaults before execution
and use a new seed.
