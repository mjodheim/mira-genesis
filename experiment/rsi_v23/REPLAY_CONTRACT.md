# RSI V23 exact replay contract

Status: development apparatus prepared before V22 adjudication. It is not yet the V23 canonical evaluator.

## Purpose

V23 needs a cheap way to compare executable exploration policies on discovery history without pretending
that history contains outcomes for branches nobody actually expanded.

The replay engine therefore implements **exact realized-tree replay only**.

## Historical expansion model

A retained campaign state contains chronological observations. Each represented request creates one
recorded parent -> child expansion. If the same parent was requested multiple times, those child
expansions form a FIFO queue in the order actually observed.

A replay starts from the retained root only. At each round the candidate policy sees exactly the same
public node fields used by the online policy ABI:

- root node id;
- revealed node rows;
- eligible revealed parents;
- action features;
- scored outcome fields;
- lineage depth.

The runner enforces the candidate's declared parallelism, maximum rounds and stall-round count.

When a selected parent has a recorded unused child, replay consumes the next historical expansion,
charges one represented request and reveals that child.

## No counterfactual fabrication

If a candidate requests a parent for which history contains no unused expansion, replay stops with:

`unsupported_historical_expansion`.

The engine does **not**:

- invent a child;
- estimate a reward;
- assign zero;
- substitute a nearby branch;
- ask an LLM what might have happened.

Such a replay is marked `fully_supported=false` and cannot be treated as an exact policy comparison.

This makes the current deployed policy a naturally supported baseline while allowing alternative
policies to become increasingly replayable as the archive accumulates diverse expansions.

## What this apparatus does not freeze yet

V23's canonical:

- replay-pool membership;
- candidate-policy budget;
- policy-development model;
- ranking utility;
- support/coverage threshold;
- fresh holdout;
- causal ablation margin;

must be frozen only after V22's measured cost scale is known and before any V23 proposer call.

This file therefore defines replay **semantics**, not the final V23 success threshold.
