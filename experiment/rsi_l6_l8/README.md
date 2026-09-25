# RSI L6-L8 apparatus

Status: **development-only preparation before V22 adjudication**.

This directory contains mechanisms that can be built safely before L4/L5 results exist.

## What is already executable

- `ladder.py` validates prospective evidence packages for L6, L7 and L8.
- `descent_state.py` advances or stops a repeated causal generation chain without discretionary continuation.
- `bottleneck_selector.py` evaluates an identity-blind metric program over a frozen bottleneck snapshot.
- `selector_search.py` searches a bounded selector grammar on development episodes with realized matched interventions.

## What is deliberately not frozen

`development_config.example.json` is a working example, not an experimental preregistration.

Before any canonical level is attempted, a successor protocol must bind the exact:

- transition/domain/episode counts;
- represented budgets;
- task/domain population;
- evaluator and holdout commitments;
- selector-development population;
- candidate model/generator identities;
- external-maintainer criterion;
- success margins, if any.

Those choices must be made after the preceding level is adjudicated but before candidate exposure for
the new level.

## L8 selector boundary

The selector expression cannot read component identity. It sees integer metrics only and the same
expression is applied to every component.

Development selector search may use only episodes for which all compared component interventions
were actually executed. The future holdout is never used to select the selector program.

The canonical L8 evaluation must re-execute the frozen selector on the frozen pre-intervention
snapshot and run matched equal-budget interventions for every available target. Adaptive utility must
strictly exceed the best single fixed-target strategy across the same episodes.

## Example

Development evidence can be checked with:

```bash
python3 experiment/rsi_l6_l8/ladder.py evidence.json \
  experiment/rsi_l6_l8/development_config.example.json
```

A positive result from the example config is **not** a scientific L6/L7/L8 result.
