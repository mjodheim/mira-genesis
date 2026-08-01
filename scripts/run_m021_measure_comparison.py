"""M021 — do these selection measures move true quality? **Development only.**

Four measures, four populations, one decidable ground truth.

Every measure improves its own score under selection; that is what optimisation means
and it proves nothing. The experiment is whether **true quality** follows — measured
on held-out episodes, with exact behavioural equivalence, and never made available to
any ranking.

M019 established the horizon defect that invalidated its own rig: selection every
generation culls a learner before its investment repays. M021 selects every
`SELECT_EVERY` generations instead, which is the correction M019 named.

Prediction, written before the measurement:

    objective          true quality degrades, as in M019
    novelty            diversity holds, quality does not follow
    quality_diversity  best of the four
    minimal_criterion  close behind quality_diversity

    If all four land within noise of each other, the held-out set is too easy to
    separate them and the rig must be rebuilt before concluding anything.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import random
import statistics

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m017_lab import BehavioralOracle, generate_episodes, make_environment
from metamorphosis.m019_engine import Case, Population
from metamorphosis.m021_measures import MEASURES

ROOT = Path(__file__).resolve().parents[1]

POPULATION = 6
GENERATIONS = 6
EPISODES = 4
SELECT_EVERY = 2
GENERATIONS_PER_ENVIRONMENT = 3

ENERGY = 200_000
REWARD = 6_000
CEILING = 60_000

HELD_OUT_EPISODES = 4


def median(values: list[int]) -> int:
    return int(statistics.median(values)) if values else 0


def build_cases(seed: int, generation: int) -> list[Case]:
    era = generation // GENERATIONS_PER_ENVIRONMENT
    environment = make_environment(300_000 + seed * 11 + era)
    episodes = generate_episodes(
        environment, 301_000 + seed * 11 + generation, count=EPISODES
    )
    return [
        Case(
            base=episode.base,
            make_oracle=(lambda target=episode.target: BehavioralOracle(target)),
            verify=(lambda solution, target=episode.target: bool(
                exact_equivalence(solution, target)[0]
            )),
        )
        for episode in episodes
    ]


def true_quality(population: Population, seed: int) -> dict[str, int]:
    """Ground truth, computed after the fact and hidden from every ranking.

    Held-out episodes drawn from an environment the population never lived in. A
    measure that only looks good on the episodes it was selected on has told us
    nothing.
    """
    environment = make_environment(302_000 + seed * 11)
    episodes = generate_episodes(environment, 303_000 + seed * 11, count=HELD_OUT_EPISODES)

    solved = 0
    costs: list[int] = []
    for individual in population.alive:
        for episode in episodes:
            # A copy of the search budget so the audit cannot starve the organism.
            individual.organism.search_budget = CEILING
            result = individual.organism.solve(
                episode.base, BehavioralOracle(episode.target)
            )
            if result.status != "success":
                continue
            assert result.solution is not None
            assert exact_equivalence(result.solution, episode.target)[0], "false success"
            solved += 1
            costs.append(result.search_nodes)

    attempted = max(1, len(population.alive) * len(episodes))
    return {
        "held_out_solved": solved,
        "held_out_attempted": attempted,
        "held_out_solved_per_mille": solved * 1000 // attempted,
        "held_out_median_nodes": median(costs),
        "macros_median": median([len(i.organism.library.macros) for i in population.alive]),
    }


def run_measure(task: tuple[str, int]) -> dict[str, object]:
    name, seed = task
    ranker = MEASURES[name]
    rng = random.Random(seed * 977 + len(name))
    population = Population.seed(
        POPULATION, seed, energy=ENERGY, reward=REWARD, ceiling=CEILING
    )

    for generation in range(GENERATIONS):
        population.live_generation(build_cases(seed, generation))
        if not population.alive:
            break
        # The horizon correction M019 named: selecting every generation culls a
        # learner before its investment repays.
        if (generation + 1) % SELECT_EVERY == 0:
            population.select(rng, ENERGY, ranker=ranker)

    quality = true_quality(population, seed) if population.alive else {
        "held_out_solved": 0,
        "held_out_attempted": 1,
        "held_out_solved_per_mille": 0,
        "held_out_median_nodes": 0,
        "macros_median": 0,
    }
    return {
        "measure": name,
        "seed": seed,
        "alive": len(population.alive),
        "deaths": population.deaths,
        "own_score_median_energy": median([i.ledger.energy for i in population.alive]),
        "episodes_solved_during_life": sum(i.ledger.solved for i in population.individuals),
        **quality,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--workers", type=int, default=None)
    arguments = parser.parse_args()

    tasks = [(name, seed) for name in sorted(MEASURES) for seed in range(arguments.seeds)]
    with ProcessPoolExecutor(max_workers=arguments.workers) as pool:
        rows = list(pool.map(run_measure, tasks))

    for row in rows:
        print(json.dumps(row, ensure_ascii=False))

    summary: dict[str, object] = {
        "development_only": True,
        "seeds": arguments.seeds,
        "population": POPULATION,
        "generations": GENERATIONS,
        "select_every": SELECT_EVERY,
        "ground_truth": "held-out episodes, exact equivalence, never visible to any ranking",
        "trace_number_format": "integers_only",
    }
    for name in sorted(MEASURES):
        rows_for = [row for row in rows if row["measure"] == name]
        summary[f"{name}_held_out_per_mille"] = median(
            [int(row["held_out_solved_per_mille"]) for row in rows_for]
        )
        summary[f"{name}_held_out_median_nodes"] = median(
            [int(row["held_out_median_nodes"]) for row in rows_for]
        )
        summary[f"{name}_macros_median"] = median(
            [int(row["macros_median"]) for row in rows_for]
        )
        summary[f"{name}_own_score"] = median(
            [int(row["own_score_median_energy"]) for row in rows_for]
        )

    ranked = sorted(
        MEASURES,
        key=lambda name: -int(summary[f"{name}_held_out_per_mille"]),  # type: ignore[arg-type]
    )
    summary["ranking_by_true_quality"] = ranked
    spread = int(summary[f"{ranked[0]}_held_out_per_mille"]) - int(  # type: ignore[arg-type]
        summary[f"{ranked[-1]}_held_out_per_mille"]  # type: ignore[arg-type]
    )
    summary["true_quality_spread_per_mille"] = spread
    # Pre-registered invalidation: measures that cannot be separated have not been
    # compared, whatever the ordering suggests.
    summary["rig_separates_measures"] = spread >= 100

    path = ROOT / "results" / "M021_measure_comparison_development.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"summary": summary, "runs": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
