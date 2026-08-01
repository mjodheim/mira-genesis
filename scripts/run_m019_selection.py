"""M019 — sélection sous rareté. **Aucun résultat canonique.**

La question, posée pour la première fois dans ce projet :

    Une population sous sélection découvre-t-elle ce que je n'ai pas su concevoir ?

M018 a montré que trois mécanismes d'oubli écrits à la main ne payaient pas. Ici,
personne ne choisit de mécanisme : les quatre sont présents dans la population de
départ, en proportions égales, et la sélection tranche.

La grandeur qui décide de la survie est l'**énergie restante**, c'est-à-dire ce qui
reste après avoir payé ses recherches. Résoudre cher n'y vaut pas mieux que ne pas
résoudre — c'est ce qui donne enfin un enjeu à l'efficacité.

Prédiction écrite avant la mesure :

    La population convergera vers `budget`, seul mécanisme sans revers en régime
    stable dans M018, et vers des seuils d'absorption bas. `dissolution` disparaîtra.
    Si `none` domine, c'est que la rareté n'est pas assez mordante et le montage est
    à refaire avant d'en conclure quoi que ce soit.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import random
import statistics

from metamorphosis.m012b_dfa import DFA, exact_equivalence
from metamorphosis.m017_lab import BehavioralOracle, generate_episodes, make_environment
from metamorphosis.m019_engine import Case, Individual, Population
from metamorphosis.m019_selection import Genome, summarise_population

ROOT = Path(__file__).resolve().parents[1]

POPULATION = 10
GENERATIONS = 6
EPISODES = 6

# Dotation initiale, prime de résolution, plafond de recherche par épisode.
#
# Le plafond doit dépasser l'espace complet de profondeur 3 — 46 656 trajectoires —
# sans quoi un organisme sans macro applicable ne peut **jamais** achever une
# recherche. Un premier réglage à 45 000 rendait le montage dégénéré : dès que
# l'environnement changeait, la population entière s'abstenait et la sélection
# n'avait plus rien à trancher.
#
# La prime a dû être recalibrée après un premier essai où elle valait 25 000. La
# population y prospérait sans exception — zéro mort, énergie doublée — et `none`
# l'emportait 8/8. Une prime très supérieure au coût d'une résolution bon marché rend
# toute bibliothèque, même encombrée, sans conséquence : l'inefficacité ne coûte plus
# rien et l'oubli n'a rien à arbitrer.
#
# Ce recalibrage n'est pas un ajustement de confort. La condition qui l'impose était
# écrite avant la mesure, dans l'en-tête de ce fichier : « si `none` domine, c'est que
# la rareté n'est pas assez mordante et le montage est à refaire avant d'en conclure
# quoi que ce soit ». Le diagnostic est objectif — aucune mort, énergie doublée.
#
# À 6 000, l'arithmétique mord : une résolution en profondeur 3 coûte environ 23 000
# nœuds et fait perdre 17 000 ; une résolution par macro en rapporte près de 6 000 ;
# une abstention en coûte 60 000. Un organisme doit amortir chaque apprentissage
# coûteux par plusieurs résolutions bon marché, et une bibliothèque qui gonfle le
# facteur de branchement ampute réellement la prime.
ENERGY = 200_000
REWARD = 6_000
CEILING = 60_000

# L'environnement change une fois, à mi-parcours. Stable, l'absorption paierait
# toujours et l'oubli n'aurait aucun rôle ; changeant à chaque génération, aucune
# absorption ne paierait jamais. C'est entre les deux que la question a un sens.
GENERATIONS_PER_ENVIRONMENT = 3


def median(values: list[int]) -> int:
    return int(statistics.median(values)) if values else 0


def build_cases(seed: int, generation: int) -> list[Case]:
    """Traduit des épisodes du laboratoire en cas, oracle et vérification compris.

    C'est ici que le laboratoire entre, et nulle part ailleurs : le moteur de M019 ne
    connaît ni le générateur d'épisodes ni la cible.
    """
    era = generation // GENERATIONS_PER_ENVIRONMENT
    environment = make_environment(200_000 + seed * 7 + era)
    episodes = generate_episodes(
        environment, 201_000 + seed * 7 + generation, count=EPISODES
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


def run_lineage(seed: int) -> dict[str, object]:
    """Une lignée complète : population, générations, sélection. Tout dérive de `seed`."""
    rng = random.Random(seed)
    population = Population.seed(
        POPULATION, seed, energy=ENERGY, reward=REWARD, ceiling=CEILING
    )
    initial = summarise_population([i.genome for i in population.individuals])
    snapshots: list[dict[str, object]] = []

    for generation in range(GENERATIONS):
        population.live_generation(build_cases(seed, generation))
        snapshots.append(population.snapshot())
        if not population.alive:
            break
        population.select(rng, ENERGY)

    final = [i.genome for i in population.alive]
    return {
        "seed": seed,
        "initial_kinds": initial,
        "final_kinds": summarise_population(final),
        "final_genomes": [genome.to_dict() for genome in final],
        "survivors": len(final),
        "deaths_total": population.deaths,
        "median_final_threshold": median([g.abstraction_threshold for g in final]),
        "median_final_max_symbols": median([g.max_symbols for g in final]),
        "median_final_macros": median(
            [len(i.organism.library.macros) for i in population.alive]
        ),
        "snapshots": snapshots,
    }


def reference_lineage(seed: int) -> dict[str, object]:
    """Contrôle : un organisme seul, sans sélection, sous la même rareté.

    Il porte le génome par défaut de M017 — absorption au seuil 2, aucun oubli — et
    affronte exactement les mêmes épisodes. Sans lui, on ne saurait pas si la
    population gagne parce qu'elle sélectionne ou simplement parce qu'elle est douze.
    """
    genome = Genome(
        max_symbols=3, abstraction_threshold=2, forget_kind="none", forget_parameter=6
    )
    individual = Individual.born(
        genome, "reference", energy=ENERGY, reward=REWARD, ceiling=CEILING
    )
    for generation in range(GENERATIONS):
        for case in build_cases(seed, generation):
            individual.live(case)
        if not individual.ledger.alive:
            break
        individual.ledger.energy = ENERGY
    return {
        "seed": seed,
        "alive": individual.ledger.alive,
        "solved": individual.ledger.solved,
        "abstained": individual.ledger.abstained,
        "spent": individual.ledger.spent,
        "macros": len(individual.organism.library.macros),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lineages", type=int, default=4)
    parser.add_argument("--workers", type=int, default=None)
    arguments = parser.parse_args()

    seeds = list(range(arguments.lineages))
    with ProcessPoolExecutor(max_workers=arguments.workers) as pool:
        lineages = list(pool.map(run_lineage, seeds))
        references = list(pool.map(reference_lineage, seeds))

    for row in lineages:
        print(json.dumps({k: v for k, v in row.items() if k != "snapshots"}, ensure_ascii=False))

    kinds = {}
    for key in lineages[0]["initial_kinds"]:  # type: ignore[index]
        kinds[f"initial_{key}"] = sum(int(row["initial_kinds"][key]) for row in lineages)  # type: ignore[index]
        kinds[f"final_{key}"] = sum(int(row["final_kinds"][key]) for row in lineages)  # type: ignore[index]

    summary = {
        "development_only": True,
        "lineages": arguments.lineages,
        "population": POPULATION,
        "generations": GENERATIONS,
        "episodes_per_generation": EPISODES,
        **kinds,
        "survivors_total": sum(int(row["survivors"]) for row in lineages),
        "deaths_total": sum(int(row["deaths_total"]) for row in lineages),
        "median_final_threshold": median([int(row["median_final_threshold"]) for row in lineages]),
        "median_final_macros": median([int(row["median_final_macros"]) for row in lineages]),
        "population_solved_total": sum(
            int(row["snapshots"][-1]["solved_total"]) for row in lineages  # type: ignore[index]
        ),
        "reference_alive": sum(1 for row in references if row["alive"]),
        "reference_solved_total": sum(int(row["solved"]) for row in references),
        "reference_abstained_total": sum(int(row["abstained"]) for row in references),
        "reference_macros_median": median([int(row["macros"]) for row in references]),
        "trace_number_format": "integers_only",
    }

    path = ROOT / "results" / "M019_selection_development.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"summary": summary, "lineages": lineages, "references": references}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
