# M096 — contract-safe compositional reach

M095 attempt 1 is a preserved negative result.  It showed that an adopted renderer could satisfy
its local demand while returning extra keys, then fail when the complete mapping was embedded in
the exact nested demand of B.  M096 does not retry or edit that experiment.  It asks the new,
falsifiable question H41: does a closed, exact mapping-output contract make the reach relation
behaviourally compositional?

## One additive change

The inherited M094/M095 diagnosis, operation enumeration, bounded composition, execution probe,
nested operation and lineage control flow are unchanged.  During an M096 run only, the two mapping
capability shapes require equality between the complete returned top-level key/binding set and the
observed requirement.  Open mappings, duplicate keys, omitted keys and extra keys are rejected.
The inherited shapes are restored in a `finally` block after every measurement or run.

This is contract selection, not a new repair operation.  M096 therefore still does not establish
endogenous operation acquisition; that is the next milestone.

## Development versus qualification

The mechanism was developed against M095's already observed nine-entry population.  It recovered
all six demand-bearing relations and preserved all three zero-demand negatives.  Because those
worlds and their verdict were already known, that result is labelled development evidence and
cannot support H41.

Qualification uses four new structures crossed exhaustively with three demand arrangements.  The
pre-freeze apparatus may construct and parse S0, measure demand, verify that no renderer exists and
exhaust B-from-S0.  It cannot adopt A, call either full chain runner or obtain an enabling outcome.

An initial candidate structure used collection wrappers inside the nested literal.  S0 preflight
showed that the inherited nested-demand syntax does not represent wrapped attribute chains, so that
candidate did not present B at all.  It was removed before freeze and before any chain execution.
This is a disclosed preflight-domain correction, not a dropped result.

## Paired legacy sensitivity arm

Every frozen entry is also run through the inherited subset-contract mechanism in a separate copy
of the same world.  This arm is descriptive: content-addressed ordering can occasionally make the
legacy search choose an exact survivor by chance.  The historical M095 negative remains the causal
evidence that subset acceptance can fail.  The paired arm must nevertheless be runnable, start from
the same measured S0 and pass the complete-contract liveness controls.

## Limits

The population, operation language and bound are authored and finite.  There is no external model,
network access, remote runner, human evaluator, experimenter blindness, generality claim, new
authority, open-ended evolution or persistence-after-termination claim.
