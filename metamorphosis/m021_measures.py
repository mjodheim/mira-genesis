"""M021 — the selection measure becomes the object of study.

Four experiments failed before this one, and none failed in the organism. Each time
what was being built held; what gave way was the way of judging whether it was better.
M021 therefore stops varying the organism and starts varying **the measure**.

The four measures below are not inventions. Direct objective optimisation, novelty
search, quality-diversity and the minimal criterion are established answers to the
question "what should selection reward". What is unusual here is the domain: the
behavioural equivalence of two finite automata is decidable, so a population's *true*
quality can be computed exactly and compared against whatever the measure claims.

That comparison is the experiment. A measure is not judged by how well its own score
improves — every measure improves its own score under selection, that is what
optimisation means. It is judged by whether true quality follows.

Ground truth is never available to any measure. It is computed on held-out episodes
after the fact, and no ranking may consult it.
"""

from __future__ import annotations

from typing import Callable, Sequence

from .m019_engine import Individual

Ranker = Callable[[Sequence[Individual]], list[Individual]]


def _behaviour(individual: Individual) -> frozenset[str]:
    """Behavioural descriptor: which macros this organism ended up holding.

    Chosen because it is what the organism actually built, is comparable between
    individuals without consulting any target, and costs nothing to compute. It is a
    hand-picked descriptor, exactly as in the quality-diversity literature — and that
    choice is itself a measure decision, hence part of what M021 is testing.
    """
    return frozenset(symbol.name for symbol in individual.organism.library.macros)


def _novelty(individual: Individual, population: Sequence[Individual]) -> int:
    """Mean symmetric-difference distance to the rest of the population.

    Integer-only, so the ranking is reproducible bit for bit across environments —
    the traceability defect M014b paid for.
    """
    mine = _behaviour(individual)
    distances = [
        len(mine ^ _behaviour(other))
        for other in population
        if other.lineage != individual.lineage
    ]
    return sum(distances) * 100 // len(distances) if distances else 0


def rank_by_objective(population: Sequence[Individual]) -> list[Individual]:
    """Direct optimisation of the target quantity: energy left after paying.

    This is M019's measure, and M019 showed where it goes: selection discovered that
    not trying is cheaper than trying. Kept here as the first row of the table rather
    than as a straw man — it is what most systems actually do.
    """
    return sorted(population, key=lambda i: (-i.ledger.energy, i.lineage))


def rank_by_novelty(population: Sequence[Individual]) -> list[Individual]:
    """Novelty search: reward being different, ignore being good.

    Lehman and Stanley's argument is that an objective can be its own obstacle, since
    the stepping stones to a good solution rarely look good themselves. The cost is
    that nothing pulls towards quality at all.
    """
    return sorted(
        population, key=lambda i: (-_novelty(i, population), i.lineage)
    )


def rank_by_quality_diversity(population: Sequence[Individual]) -> list[Individual]:
    """MAP-Elites style: the best individual of each niche, before any second-best.

    A niche is (macro-count bucket, forgetting kind) — a coarse, hand-declared
    partition of behaviour space. Ranking takes one elite per niche first, then fills
    with the remainder by energy, so diversity is preserved without abandoning quality.
    """

    def niche(individual: Individual) -> tuple[int, str]:
        return (
            len(individual.organism.library.macros) // 4,
            individual.genome.forget_kind,
        )

    elites: dict[tuple[int, str], Individual] = {}
    for individual in sorted(population, key=lambda i: (-i.ledger.energy, i.lineage)):
        elites.setdefault(niche(individual), individual)

    chosen = sorted(elites.values(), key=lambda i: (-i.ledger.energy, i.lineage))
    remainder = sorted(
        (i for i in population if i not in chosen),
        key=lambda i: (-i.ledger.energy, i.lineage),
    )
    return chosen + remainder


def rank_by_minimal_criterion(population: Sequence[Individual]) -> list[Individual]:
    """Clear a viability bar, then rank by novelty among those who cleared it.

    The minimal criterion refuses to grade quality beyond "good enough", on the view
    that finer grading is what invites Goodharting. Here the bar is having solved at
    least one episode — deliberately low, since a high bar would smuggle the objective
    back in through the door the criterion is meant to close.
    """
    viable = [i for i in population if i.ledger.solved > 0]
    rejected = [i for i in population if i.ledger.solved == 0]
    return (
        sorted(viable, key=lambda i: (-_novelty(i, viable), i.lineage))
        + sorted(rejected, key=lambda i: (-i.ledger.energy, i.lineage))
    )


MEASURES: dict[str, Ranker] = {
    "objective": rank_by_objective,
    "novelty": rank_by_novelty,
    "quality_diversity": rank_by_quality_diversity,
    "minimal_criterion": rank_by_minimal_criterion,
}
