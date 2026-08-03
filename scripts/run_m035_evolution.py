"""M035 — can a population reach what its founder structurally cannot express?

**Development only. No canonical claim.**

The decisive target is `make_out_of_language_target`, which M017 uses as a *negative*
control: it adds a state, and the structural language cannot add states, so M017 requires
the organism to abstain on it. Today's ceiling measurement confirms why — of 53,280 atom
applications, 18,540 changed the state count and none grew it.

So the target is provably unreachable for the control arm. If the duplication arm reaches
it, that is not a better search: it is a capacity the lineage did not start with.

Two arms, identical in every respect but one:

- **control**: structural atoms only. Bounded by the founder's state count.
- **duplication**: the same atoms, plus the neutral duplication operator.

Same founders, same targets, same seeds, same population size, same generations, same
selection rule, same budget. Only the operator set differs.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import statistics

from metamorphosis.m012b_dfa import exact_equivalence, random_minimal_dfa
from metamorphosis.m017_lab import make_out_of_language_target
from metamorphosis.m035_evolution import (
    Organism,
    VariationBudget,
    agreement,
    minimal_criterion_survivors,
    offspring,
    replay,
    speciated_survivors,
)
from metamorphosis.structural import enumerate_words, normalize_dfa

ROOT = Path(__file__).resolve().parents[1]

POPULATION = 24
GENERATIONS = 60
CHILDREN_PER_PARENT = 3
MAX_SIZE_MARGIN = 3


def run_arm(
    founder: Organism,
    target,
    words,
    *,
    allow_duplication: bool,
    seed: int,
    generations: int,
    speciate: bool = False,
    diagnose: bool = False,
) -> dict[str, object]:
    rng = random.Random(seed)
    budget = VariationBudget()
    max_size = founder.size + MAX_SIZE_MARGIN

    evidence = (
        {tuple(w): target.accepts(tuple(w)) for w in words} if diagnose else None
    )
    population = [founder]
    best_score = agreement(founder.body, target, words)
    best_organism = founder
    solved_at: int | None = None
    total_words = len(words)

    for generation in range(1, generations + 1):
        children: list[Organism] = []
        for parent in population:
            for _ in range(CHILDREN_PER_PARENT):
                child = offspring(
                    parent,
                    rng,
                    allow_duplication=allow_duplication,
                    max_size=max_size,
                    evidence=evidence,
                )
                if child is None:
                    continue
                children.append(child)
                budget.bodies_evaluated += 1
                if child.duplications > parent.duplications:
                    budget.duplications_applied += 1
                else:
                    budget.atoms_applied += 1
                budget.structural_cost_paid += child.structural_cost()

        scored = [(org, agreement(org.body, target, words)) for org in population + children]
        for org, score in scored:
            if score > best_score or (
                score == best_score and org.structural_cost() < best_organism.structural_cost()
            ):
                best_score, best_organism = score, org

        # Minimal criterion: a bar, not a ranking. The bar rises only when the whole
        # population clears it, so the rule never chases the single best lineage.
        threshold = max(1, min(score for _, score in scored))
        select = speciated_survivors if speciate else minimal_criterion_survivors
        population = select(scored, threshold, POPULATION)
        if not population:
            population = [founder]

        if solved_at is None and best_score == total_words:
            if exact_equivalence(best_organism.body, target)[0]:
                solved_at = generation
                break

    exact, witness = exact_equivalence(best_organism.body, target)

    # Gate 9 requires the lineage to be replayable from the founder and immutable inputs.
    # Verify it here rather than assert it: rebuild the winner from its recorded mutation
    # chain alone — no seed, no population, no search — and compare byte for byte.
    rebuilt = replay(founder.body, best_organism.ancestry)
    replayable = (
        rebuilt is not None
        and rebuilt.transitions == best_organism.body.transitions
        and rebuilt.accepting == best_organism.body.accepting
        and rebuilt.initial == best_organism.body.initial
    )

    return {
        "allow_duplication": allow_duplication,
        "exact": bool(exact),
        "lineage_steps": len(best_organism.ancestry),
        "lineage_replayable": bool(replayable),
        "lineage": [step.to_dict() for step in best_organism.ancestry],
        "solved_at_generation": solved_at,
        "best_agreement": best_score,
        "words": total_words,
        "founder_states": founder.size,
        "target_states": target.n_states,
        "best_states": best_organism.size,
        "best_duplications": best_organism.duplications,
        "best_edits": best_organism.edits,
        "separating_witness": list(witness) if witness else None,
        "budget": budget.to_dict(),
    }


def run_case(index: int, generations: int) -> dict[str, object]:
    base = normalize_dfa(random_minimal_dfa(50_000 + index * 7919, 4, 6))
    target = make_out_of_language_target(base, 51_000 + index * 7919)
    words = enumerate_words(6)
    founder = Organism(body=base)

    control = run_arm(
        founder, target, words,
        allow_duplication=False, seed=52_000 + index, generations=generations,
    )
    evolved = run_arm(
        founder, target, words,
        allow_duplication=True, seed=52_000 + index, generations=generations,
    )
    # Third arm: the documented remedy for a topological innovation being culled before
    # it can be optimised. Same seed and same operators as `duplication`; only the
    # survival rule differs, so any gap is attributable to protecting new structure.
    speciated = run_arm(
        founder, target, words,
        allow_duplication=True, seed=52_000 + index, generations=generations,
        speciate=True,
    )
    # Fourth arm: growth on diagnosis rather than on a coin flip. The parent grows only
    # when the evidence it already holds cannot fit in a body its size — a limitation it
    # proves about itself, without seeing the target.
    diagnosed = run_arm(
        founder, target, words,
        allow_duplication=True, seed=52_000 + index, generations=generations,
        diagnose=True,
    )
    return {
        "case": index,
        "founder_states": base.n_states,
        "target_states": target.n_states,
        "target_needs_growth": bool(target.n_states > base.n_states),
        "control": control,
        "duplication": evolved,
        "speciated": speciated,
        "diagnosed": diagnosed,
    }


def run(cases: int, generations: int) -> dict[str, object]:
    rows = [run_case(index, generations) for index in range(cases)]

    control_exact = sum(1 for r in rows if r["control"]["exact"])
    dup_exact = sum(1 for r in rows if r["duplication"]["exact"])
    spec_exact = sum(1 for r in rows if r["speciated"]["exact"])
    needed_growth = sum(1 for r in rows if r["target_needs_growth"])
    dup_grew = sum(1 for r in rows if r["duplication"]["best_duplications"] > 0)

    solved_gens = [
        int(r["duplication"]["solved_at_generation"])
        for r in rows
        if r["duplication"]["solved_at_generation"] is not None
    ]
    spec_gens = [
        int(r["speciated"]["solved_at_generation"])
        for r in rows
        if r["speciated"]["solved_at_generation"] is not None
    ]

    return {
        "version": "m035-evolution/1",
        "development_only": True,
        "cases": cases,
        "generations": generations,
        "rows": rows,
        "summary": {
            "targets_requiring_growth": needed_growth,
            "control_exact": control_exact,
            "duplication_exact": dup_exact,
            "speciated_exact": spec_exact,
            "diagnosed_exact": sum(1 for r in rows if r["diagnosed"]["exact"]),
            "diagnosed_median_generation_to_solve": (
                int(statistics.median(
                    [int(r["diagnosed"]["solved_at_generation"]) for r in rows
                     if r["diagnosed"]["solved_at_generation"] is not None]
                ))
                if any(r["diagnosed"]["solved_at_generation"] is not None for r in rows)
                else None
            ),
            "diagnosed_bodies_evaluated": sum(
                int(r["diagnosed"]["budget"]["bodies_evaluated"]) for r in rows
            ),
            "duplication_used_growth": dup_grew,
            "all_winning_lineages_replayable": all(
                bool(r["duplication"]["lineage_replayable"]) for r in rows
            ),
            "deepest_lineage_steps": max(
                int(r["duplication"]["lineage_steps"]) for r in rows
            ),
            "median_generation_to_solve": (
                int(statistics.median(solved_gens)) if solved_gens else None
            ),
            "speciated_median_generation_to_solve": (
                int(statistics.median(spec_gens)) if spec_gens else None
            ),
            "control_bodies_evaluated": sum(
                int(r["control"]["budget"]["bodies_evaluated"]) for r in rows
            ),
            "duplication_bodies_evaluated": sum(
                int(r["duplication"]["budget"]["bodies_evaluated"]) for r in rows
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=12)
    parser.add_argument("--generations", type=int, default=GENERATIONS)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results" / "M035_evolution_development.json"
    )
    args = parser.parse_args()

    payload = run(args.cases, args.generations)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(raw, encoding="utf-8")

    print(json.dumps(payload["summary"], sort_keys=True, indent=2))
    print(f"sha256={hashlib.sha256(raw.encode('utf-8')).hexdigest()}")


if __name__ == "__main__":
    main()
