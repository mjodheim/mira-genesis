# M021 — Development protocol draft

**Status: DEVELOPMENT RIG. Not frozen, not hashed, no canonical evaluation allowed.**

## 1. Question

When does a proxy selection measure stop moving true quality, and under what
optimisation pressure?

The domain is finite deterministic automata. Behavioural equivalence is decidable, so
true quality is measured exactly after selection rather than inferred from a human
judgement.

## 2. What changes, and what must stay paired

M021 varies only the population ranker:

1. direct objective — energy left after paying search cost;
2. novelty — distance between the macro libraries organisms built;
3. niche-first quality-diversity approximation — one energy elite per declared niche
   before any second-best individual;
4. minimal criterion — solve at least one episode, then rank viable organisms by
   novelty.

For a given seed, all four runs receive:

- the same initial population seed;
- the same environments and episodes;
- the same exogenous mutation random stream;
- the same energy, reward, search ceiling and selection horizon.

The ranking changes which parents consume that common mutation stream. That consequence
belongs to the measure. Changing the stream itself does not.

## 3. Selection horizon

Selection occurs every two generations. M019 selected every generation and removed a
learner before the library it paid for could repay its cost. M021 adopts the correction
M019 identified; it does not claim that two generations is already the correct horizon.

## 4. Ground truth hidden from selection

No ranker receives a target automaton, held-out result, exact-equivalence verdict or
quality field.

After the final selection, each surviving organism is audited on episodes from an
environment no compared population lived in. The audit uses deep copies and never
mutates the selected population.

Two quantities are reported:

- **primary — adaptive held-out quality:** one copied organism receives the whole
  held-out sequence and may learn across it;
- **secondary — frozen held-out quality:** every held-out episode starts from the same
  pre-audit state, so no learning can carry between episodes.

This distinction prevents adaptation in the audit from being reported as zero-shot
transfer.

## 5. Development scale and separation gate

A three-seed execution is a smoke test only.

The first comparison requires at least **24 paired seeds per measure**. Below that
number the output must state `insufficient_paired_seeds`, whatever ordering appears.

The rig separates the measures only when the median adaptive held-out solve rate differs
by at least **100 per mille** between the best and worst measure. If the spread is
smaller, the result is `spread_below_pre_registered_floor` and the rig must be rebuilt
before drawing a comparison.

This is a development gate, not a statistical significance claim. Confidence intervals
and a frozen decision rule are required before any canonical protocol.

## 6. Prediction written before the comparison

- direct objective: true quality degrades as cautious non-learning remains cheap;
- novelty: diversity persists, but quality does not reliably follow;
- niche-first quality-diversity: best adaptive held-out quality of the four;
- minimal criterion: close behind quality-diversity.

A different ordering is a legitimate development result. Failure to separate the
measures invalidates the rig, not the measures.

## 7. Admission conditions

Every development row must satisfy:

1. zero false successes under exact behavioural equivalence;
2. ground truth absent from all ranker signatures;
3. integer-only decision traces;
4. common random numbers for each paired seed;
5. selected organisms unchanged by held-out auditing;
6. every ranker returns every living individual exactly once.

## 8. Known limitation of the quality-diversity row

The current implementation is a fixed-population, niche-first approximation. It does
not maintain an unbounded MAP-Elites archive, and the survivor budget may contain fewer
slots than represented niches. M021 therefore tests this implementation, not the whole
quality-diversity family.

If it appears promising, a later experiment must compare a true persistent archive
against the same ground truth rather than silently broadening this row's claim.

## 9. What remains before freeze consideration

- run the branch smoke workflow and repair any failed guard;
- execute at least 24 paired seeds and retain the raw artifact;
- inspect per-seed paired differences, not only medians;
- add uncertainty estimates and choose a decision rule before seeing sealed results;
- decide whether the selection horizon itself must become a factorial variable;
- either freeze the exact four implementations or rename the experiment.

No result from `.github/workflows/m021-development.yml` is canonical.
