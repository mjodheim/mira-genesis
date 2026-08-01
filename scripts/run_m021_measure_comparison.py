"""M021 — do selection measures move true quality? **Development only.**

Four measures, four paired populations, one decidable ground truth.

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

    If all four land within the pre-registered separation floor, the held-out set does
    not separate them and the rig must be rebuilt before concluding anything.

The default one-seed run is a structural smoke test only. A comparison is never
considered development-ready below `DEVELOPMENT_MIN_SEEDS`.
"""

from __future__ import annotations

import argparse
import copy
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import random
import statistics
from typing import Sequence

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
DEVELOPMENT_MIN_SEEDS = 24
SEPARATION_FLOOR_PER_MILLE = 100


def median(values: list[int]) -> int:
    return int(statistics.median(values)) if values else 0


def selection_rng(seed: int) -> random.Random:
    """Common random numbers for every measure at a given seed."""
    return random.Random(seed * 977 + 21)


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


def build_held_out_cases(seed: int) -> list[Case]:
    environment = make_environment(302_000 + seed * 11)
    episodes = generate_episodes(
        environment, 303_000 + seed * 11, count=HELD_OUT_EPISODES
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


def audit_organism(
    organism: object,
    cases: Sequence[Case],
    *,
    adaptive: bool,
    ceiling: int = CEILING,
) -> tuple[int, list[int]]:
    """Evaluate a deep copy, never the selected organism itself."""
    solved = 0
    costs: list[int] = []
    template = copy.deepcopy(organism)
    runner = copy.deepcopy(template)

    for case in cases:
        if not adaptive:
            runner = copy.deepcopy(template)
        runner.search_budget = ceiling
        result = runner.solve(case.base, case.make_oracle())
        if result.status != "success":
            continue
        assert result.solution is not None
        assert case.verify(result.solution), "false success"
        solved += 1
        costs.append(result.search_nodes)

    return solved, costs


def true_quality(population: Population, seed: int) -> dict[str, int]:
    cases = build_held_out_cases(seed)
    adaptive_solved = 0
    adaptive_costs: list[int] = []
    frozen_solved = 0
    frozen_costs: list[int] = []

    for individual in population.alive:
        solved, costs = audit_organism(individual.organism, cases, adaptive=True)
        adaptive_solved += solved
        adaptive_costs.extend(costs)

        solved, costs = audit_organism(individual.organism, cases, adaptive=False)
        frozen_solved += solved
        frozen_costs.extend(costs)

    attempted = max(1, len(population.alive) * len(cases))
    return {
        "held_out_attempted": attempted,
        "adaptive_held_out_solved": adaptive_solved,
        "adaptive_held_out_solved_per_mille": adaptive_solved * 1000 // attempted,
        "adaptive_held_out_median_nodes": median(adaptive_costs),
        "frozen_held_out_solved": frozen_solved,
        "frozen_held_out_solved_per_mille": frozen_solved * 1000 // attempted,
        "frozen_held_out_median_nodes": median(frozen_costs),
        "macros_median": median(
            [len(i.organism.library.macros) for i in population.alive]
        ),
    }


def run_measure(task: tuple[str, int]) -> dict[str, object]:
    name, seed = task
    ranker = MEASURES[name]
    rng = selection_rng(seed)
    population = Population.seed(
        POPULATION, seed, energy=ENERGY, reward=REWARD, ceiling=CEILING
    )

    for generation in range(GENERATIONS):
        population.live_generation(build_cases(seed, generation))
        if not population.alive:
            break
        if (generation + 1) % SELECT_EVERY == 0:
            population.select(rng, ENERGY, ranker=ranker)

    quality = true_quality(population, seed) if population.alive else {
        "held_out_attempted": 1,
        "adaptive_held_out_solved": 0,
        "adaptive_held_out_solved_per_mille": 0,
        "adaptive_held_out_median_nodes": 0,
        "frozen_held_out_solved": 0,
        "frozen_held_out_solved_per_mille": 0,
        "frozen_held_out_median_nodes": 0,
        "macros_median": 0,
    }
    return {
        "measure": name,
        "seed": seed,
        "selection_rng_seed": seed * 977 + 21,
        "alive": len(population.alive),
        "deaths": population.deaths,
        "median_energy_after_selection": median(
            [i.ledger.energy for i in population.alive]
        ),
        "episodes_solved_during_life": sum(
            i.ledger.solved for i in population.individuals
        ),
        **quality,
    }


def summarize_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    """Summarise complete paired rows, whether produced together or by shards."""
    seed_sets = {
        name: {int(row["seed"]) for row in rows if row["measure"] == name}
        for name in MEASURES
    }
    if any(not seeds for seeds in seed_sets.values()):
        raise ValueError("every measure must have at least one row")
    reference = seed_sets[sorted(MEASURES)[0]]
    if any(seeds != reference for seeds in seed_sets.values()):
        raise ValueError(f"measure seed sets are not paired: {seed_sets}")

    expected_pairs = {(name, seed) for name in MEASURES for seed in reference}
    observed_pairs = {(str(row["measure"]), int(row["seed"])) for row in rows}
    if observed_pairs != expected_pairs or len(rows) != len(expected_pairs):
        raise ValueError("rows contain a missing or duplicate measure/seed pair")

    summary: dict[str, object] = {
        "development_only": True,
        "seeds": len(reference),
        "paired_seed_values": sorted(reference),
        "development_min_seeds": DEVELOPMENT_MIN_SEEDS,
        "population": POPULATION,
        "generations": GENERATIONS,
        "select_every": SELECT_EVERY,
        "common_random_numbers": True,
        "ground_truth": (
            "held-out episodes, exact equivalence, never visible to any ranking"
        ),
        "primary_ground_truth": (
            "adaptive held-out sequence on a deep copy of each selected organism"
        ),
        "secondary_ground_truth": (
            "frozen held-out episodes, each starting from the same pre-audit state"
        ),
        "audit_mutates_selected_population": False,
        "trace_number_format": "integers_only",
        "separation_floor_per_mille": SEPARATION_FLOOR_PER_MILLE,
    }

    for name in sorted(MEASURES):
        rows_for = [row for row in rows if row["measure"] == name]
        for metric in (
            "adaptive_held_out_solved_per_mille",
            "adaptive_held_out_median_nodes",
            "frozen_held_out_solved_per_mille",
            "frozen_held_out_median_nodes",
            "macros_median",
            "median_energy_after_selection",
        ):
            summary[f"{name}_{metric}"] = median(
                [int(row[metric]) for row in rows_for]
            )

    ranked = sorted(
        MEASURES,
        key=lambda name: -int(
            summary[f"{name}_adaptive_held_out_solved_per_mille"]
        ),
    )
    summary["ranking_by_true_quality"] = ranked
    spread = int(
        summary[f"{ranked[0]}_adaptive_held_out_solved_per_mille"]
    ) - int(summary[f"{ranked[-1]}_adaptive_held_out_solved_per_mille"])
    summary["true_quality_spread_per_mille"] = spread

    enough_seeds = len(reference) >= DEVELOPMENT_MIN_SEEDS
    separated = spread >= SEPARATION_FLOOR_PER_MILLE
    summary["enough_seeds_for_comparison"] = enough_seeds
    summary["rig_separates_measures"] = enough_seeds and separated
    if not enough_seeds:
        summary["rig_invalidation_reason"] = "insufficient_paired_seeds"
    elif not separated:
        summary["rig_invalidation_reason"] = "spread_below_pre_registered_floor"
    else:
        summary["rig_invalidation_reason"] = None
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "M021_measure_comparison_development.json",
    )
    arguments = parser.parse_args()
    if arguments.seeds < 1:
        parser.error("--seeds must be at least 1")
    if arguments.seed_start < 0:
        parser.error("--seed-start must be non-negative")

    seed_values = range(arguments.seed_start, arguments.seed_start + arguments.seeds)
    tasks = [(name, seed) for name in sorted(MEASURES) for seed in seed_values]
    with ProcessPoolExecutor(max_workers=arguments.workers) as pool:
        rows = list(pool.map(run_measure, tasks))

    summary = summarize_rows(rows)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps({"summary": summary, "runs": rows}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
