"""The selection rule must match its stated definition, and the tests must prove it.

M035's selector was documented as a minimal criterion chosen from M021's measurement.
Both halves were wrong: it ranked the admitted by score and size, and M021's
`rank_by_minimal_criterion` is viability plus **novelty** plus truncation, whose 750 per
mille belongs to that composite alone.

`positive_population_floor_admission_with_body_diversity` separates admission from capacity
reduction. These tests pin the separation, so a ranking pressure cannot return unnoticed.

The unit is the distinct body. That is a declared diversity policy, not neutrality between
organisms, and the tests below state which of the two is being asserted.
"""

from __future__ import annotations

from metamorphosis.m012b_dfa import random_minimal_dfa
from metamorphosis.m035_evolution import (
    Organism,
    duplicable_states,
    duplicate_state,
    positive_population_floor_admission_with_body_diversity,
    thresholded_elitist_truncation,
)
from metamorphosis.structural import normalize_dfa

COMMITMENT = "m037-development"
SEED = 4242


def _bodies(count: int):
    return [
        normalize_dfa(random_minimal_dfa(seed * 7919 + 11, 4, 6)) for seed in range(count)
    ]


def _reduce(population, threshold=1, capacity=3, generation=0, seed=SEED):
    return positive_population_floor_admission_with_body_diversity(
        population,
        threshold,
        capacity,
        commitment=COMMITMENT,
        reduction_seed=seed,
        generation=generation,
    )


def test_score_above_the_threshold_does_not_affect_survival():
    """The threshold is the only decision that consults the score."""

    organisms = [Organism(body=b) for b in _bodies(8)]
    low = [(org, 5) for org in organisms]
    high = [(org, 5 + index) for index, org in enumerate(organisms)]

    assert {o.digest() for o in _reduce(low)} == {o.digest() for o in _reduce(high)}


def test_a_larger_body_is_not_penalised_after_admission():
    base = _bodies(1)[0]
    twin = duplicate_state(base, index=duplicable_states(base)[0])
    assert twin is not None
    small, large = Organism(body=base), Organism(body=twin, duplications=1)

    survivors = _reduce([(small, 9), (large, 9)], capacity=1)
    # Whichever wins must be decided by the key, not by size. Run it both ways round.
    reversed_order = _reduce([(large, 9), (small, 9)], capacity=1)
    assert [o.digest() for o in survivors] == [o.digest() for o in reversed_order]


def test_permuting_the_input_does_not_change_the_survivors():
    organisms = [(Organism(body=b), 7) for b in _bodies(10)]
    forward = _reduce(organisms, capacity=4)
    backward = _reduce(list(reversed(organisms)), capacity=4)
    assert [o.digest() for o in forward] == [o.digest() for o in backward]


def test_the_same_commitment_seed_and_generation_reproduce_the_survivors():
    organisms = [(Organism(body=b), 7) for b in _bodies(10)]
    assert [o.digest() for o in _reduce(organisms, capacity=4)] == [
        o.digest() for o in _reduce(organisms, capacity=4)
    ]


def test_a_different_reduction_seed_can_select_a_different_subset():
    organisms = [(Organism(body=b), 7) for b in _bodies(12)]
    a = [o.digest() for o in _reduce(organisms, capacity=4, seed=1)]
    b = [o.digest() for o in _reduce(organisms, capacity=4, seed=2)]
    assert a != b


def test_a_different_generation_can_select_a_different_subset():
    organisms = [(Organism(body=b), 7) for b in _bodies(12)]
    a = [o.digest() for o in _reduce(organisms, capacity=4, generation=0)]
    b = [o.digest() for o in _reduce(organisms, capacity=4, generation=1)]
    assert a != b


def test_everyone_admitted_is_kept_when_capacity_allows():
    organisms = [(Organism(body=b), 7) for b in _bodies(3)]
    assert len(_reduce(organisms, capacity=10)) == 3


def test_below_the_threshold_is_rejected():
    organisms = [(Organism(body=b), 2) for b in _bodies(4)]
    assert _reduce(organisms, threshold=5) == []


# -- the declared unit: distinct bodies, not individuals -------------------------------


def test_clones_present_one_candidacy():
    """Declared policy: the unit of reduction is the body, so multiplicity is removed."""

    base = _bodies(1)[0]
    clones = [(Organism(body=base), 7) for _ in range(9)]
    other = [(Organism(body=b), 7) for b in _bodies(3)[1:]]
    survivors = _reduce(clones + other, capacity=3)
    digests = [o.digest() for o in survivors]
    assert len(digests) == len(set(digests))


def test_adding_clones_does_not_change_the_result():
    bodies = _bodies(6)
    population = [(Organism(body=b), 7) for b in bodies]
    with_clones = population + [(Organism(body=bodies[0]), 7) for _ in range(20)]
    assert [o.digest() for o in _reduce(population, capacity=3)] == [
        o.digest() for o in _reduce(with_clones, capacity=3)
    ]


# -- the historical selector is preserved, and still behaves as it did ------------------


def test_the_historical_selector_still_ranks():
    """M035's 6/12 belongs to this implementation, which is kept unchanged."""

    base = _bodies(1)[0]
    twin = duplicate_state(base, index=duplicable_states(base)[0])
    assert twin is not None
    small, large = Organism(body=base), Organism(body=twin, duplications=1)

    survivors = thresholded_elitist_truncation([(large, 7), (small, 7)], 1, 1)
    assert survivors[0].size == small.size


# -- the canonical representative within a body group ----------------------------------


def _lineage(body, steps: int, atom_index: int):
    """An organism with a given body and a distinguishable ancestry."""

    from metamorphosis.m035_evolution import Mutation

    return Organism(
        body=body,
        generation=steps,
        edits=steps,
        ancestry=tuple(Mutation("atom", atom_index + k, -1, -1) for k in range(steps)),
    )


def test_the_representative_of_a_body_does_not_depend_on_input_order():
    """The weaker test compared digests only, and passed while this was broken.

    Two organisms may share a body and differ in ancestry. Keeping whichever the loop met
    first made the surviving *lineage* depend on input order even when the surviving
    *bodies* did not.
    """

    body = _bodies(1)[0]
    a = _lineage(body, 3, 0)
    b = _lineage(body, 5, 7)
    c = _lineage(body, 2, 11)

    forward = _reduce([(a, 7), (b, 7), (c, 7)], capacity=1)
    shuffled = _reduce([(c, 7), (a, 7), (b, 7)], capacity=1)
    reversed_ = _reduce([(b, 7), (c, 7), (a, 7)], capacity=1)

    from metamorphosis.m035_evolution import ancestry_digest

    assert ancestry_digest(forward[0]) == ancestry_digest(shuffled[0])
    assert ancestry_digest(forward[0]) == ancestry_digest(reversed_[0])


def test_converging_lineages_are_separated_without_score_size_or_order():
    body = _bodies(1)[0]
    short = _lineage(body, 2, 0)
    long = _lineage(body, 9, 4)

    from metamorphosis.m035_evolution import ancestry_digest

    # Different scores, still above the threshold: must not change the representative.
    low = _reduce([(short, 5), (long, 5)], capacity=1)
    high = _reduce([(short, 5), (long, 20)], capacity=1)
    assert ancestry_digest(low[0]) == ancestry_digest(high[0])


def test_adding_clones_changes_neither_bodies_nor_representative():
    from metamorphosis.m035_evolution import ancestry_digest

    bodies = _bodies(6)
    population = [(Organism(body=b), 7) for b in bodies]
    with_clones = population + [(_lineage(bodies[0], 4, 2), 7) for _ in range(15)]

    base = _reduce(population, capacity=3)
    padded = _reduce(with_clones, capacity=3)
    assert [o.digest() for o in base] == [o.digest() for o in padded]
    assert [ancestry_digest(o) for o in base] == [ancestry_digest(o) for o in padded]


def test_the_two_decisions_use_different_domain_separators():
    from metamorphosis.m035_evolution import (
        BODY_SELECTION_DOMAIN,
        REPRESENTATIVE_DOMAIN,
        body_selection_key,
        representative_key,
    )

    assert BODY_SELECTION_DOMAIN != REPRESENTATIVE_DOMAIN
    shared = dict(commitment=COMMITMENT, reduction_seed=SEED, generation=0)
    assert body_selection_key("abc", **shared) != representative_key("abc", "abc", **shared)


def test_the_commitment_is_an_explicit_input():
    """Not an environment value: replay must supply it."""

    organisms = [(Organism(body=b), 7) for b in _bodies(10)]
    a = _reduce(organisms, capacity=4)
    b = positive_population_floor_admission_with_body_diversity(
        organisms, 1, 4, commitment="other", reduction_seed=SEED, generation=0
    )
    assert [o.digest() for o in a] != [o.digest() for o in b]


# -- the viability condition, and what it costs ----------------------------------------


def test_a_null_lineage_and_its_neutral_duplicate_are_both_rejected():
    """The declared cost of the viability bar, made incontestable.

    A neutral duplication carries exactly its parent's score. When that score is zero,
    both sit below the runner's `max(1, ...)` floor and neither is admitted, so the
    protection the rule claims for neutral duplicates does not extend to lineages that
    have never scored.
    """

    base = _bodies(1)[0]
    twin = duplicate_state(base, index=duplicable_states(base)[0])
    assert twin is not None

    null_parent = Organism(body=base)
    null_twin = Organism(body=twin, duplications=1)
    scoring = [(Organism(body=b), 6) for b in _bodies(5)[1:]]

    # The runner's floor: max(1, minimum observed).
    threshold = max(1, min([0, 0] + [6] * len(scoring)))
    assert threshold == 1

    survivors = _reduce(
        [(null_parent, 0), (null_twin, 0)] + scoring,
        threshold=threshold,
        capacity=2,
    )
    kept = {o.digest() for o in survivors}
    assert null_parent.digest() not in kept
    assert null_twin.digest() not in kept
    assert len(survivors) == 2


def test_a_viable_lineage_and_its_neutral_duplicate_are_both_admitted():
    """Above the bar, the protection does hold: equal scores, both admissible."""

    base = _bodies(1)[0]
    twin = duplicate_state(base, index=duplicable_states(base)[0])
    assert twin is not None

    parent = Organism(body=base)
    duplicate = Organism(body=twin, duplications=1)

    survivors = _reduce([(parent, 3), (duplicate, 3)], threshold=3, capacity=10)
    kept = {o.digest() for o in survivors}
    assert parent.digest() in kept
    assert duplicate.digest() in kept


def test_an_all_zero_population_admits_nobody():
    """The degenerate case the caller must handle, pinned rather than assumed away."""

    population = [(Organism(body=b), 0) for b in _bodies(5)]
    threshold = max(1, min(score for _, score in population))
    assert _reduce(population, threshold=threshold, capacity=3) == []


def _runner_threshold(scored) -> int:
    """The rule the runner actually applies, reproduced exactly.

    Written out here rather than imported so the test fails if the runner's rule and the
    selector's documented expectation drift apart again.
    """

    return max(1, min(score for _, score in scored))


def test_the_runner_threshold_is_a_positive_floor_not_the_current_minimum():
    """The distinction that the earlier tests supplied by hand and never exercised.

    The selector's contract says the runner hands it a population floor. The runner hands
    it `max(1, minimum)`, which differs from the minimum exactly when some organism scores
    zero — and that is the case where a neutral duplicate would most need protection.
    """

    with_zero = [(Organism(body=b), score) for b, score in zip(_bodies(3), (0, 4, 9))]
    assert min(score for _, score in with_zero) == 0
    assert _runner_threshold(with_zero) == 1

    without_zero = [(Organism(body=b), score) for b, score in zip(_bodies(3), (2, 4, 9))]
    assert _runner_threshold(without_zero) == min(
        score for _, score in without_zero
    ) == 2


def test_the_runner_rule_excludes_a_null_lineage_from_a_mixed_population():
    """End to end: the runner's own threshold, applied by the selector."""

    bodies = _bodies(4)
    null_organism = Organism(body=bodies[0])
    scored = [(null_organism, 0)] + [
        (Organism(body=b), 5) for b in bodies[1:]
    ]

    survivors = _reduce(scored, threshold=_runner_threshold(scored), capacity=10)
    kept = {o.digest() for o in survivors}
    assert null_organism.digest() not in kept
    assert len(survivors) == 3


def test_under_an_exact_minimum_floor_the_null_lineage_would_survive():
    """The rejected alternative, measured rather than argued.

    Variant 1 — `min(score)` with no positive floor — would admit the null lineage. It is
    not adopted: a minimal criterion is defined by a viability bar, and removing it leaves
    a diversity sampler with no selection pressure. Pinned so the trade-off stays visible.
    """

    bodies = _bodies(4)
    null_organism = Organism(body=bodies[0])
    scored = [(null_organism, 0)] + [(Organism(body=b), 5) for b in bodies[1:]]

    exact_minimum = min(score for _, score in scored)
    survivors = _reduce(scored, threshold=exact_minimum, capacity=10)
    assert null_organism.digest() in {o.digest() for o in survivors}
    assert len(survivors) == 4
