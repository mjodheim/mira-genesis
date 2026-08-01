"""M017 — transport et décalage de distribution. **Aucun résultat canonique.**

Portes de gel n°4 et n°5. M014b a transporté un mécanisme de plasticité parfaitement
et découvert que **son avantage ne survivait pas au changement de distribution**. La
leçon vaut au niveau du langage, et il serait malhonnête de ne pas la tester : une
bibliothèque de macro-symboles absorbés dans un environnement conserve-t-elle son
avantage ailleurs ?

Trois conditions sur un même environnement cible, comparées épisode par épisode :

- `fresh`     — bibliothèque primitive, aucun héritage ;
- `shared`    — bibliothèque héritée d'un environnement aux **mêmes** motifs ;
- `disjoint`  — bibliothèque héritée d'un environnement aux motifs **différents**.

Prédiction écrite avant la mesure : `shared` bat `fresh` sur les épisodes précoces,
puisqu'il possède déjà les motifs de la cible. `disjoint` est **attendu plus mauvais
que `fresh`** : ses macros n'aideront pas et gonfleront le facteur de branchement,
comme observé à `env-90274` épisode 9 où douze macros inutiles coûtaient 2 245 nœuds
contre 1 711 à un organisme sans macro.

Si `disjoint` est effectivement plus mauvais, la portée de M017 devra être resserrée :
le langage grandit **dans** un environnement, il ne se transporte pas gratuitement
vers un autre. Ce serait la leçon de M014b, retrouvée un cran plus haut.

La bibliothèque passe par sa forme sérialisée entre les deux environnements : un
langage qui ne se transporte pas ne se réincarne pas.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m017_engine import SelfExtendingOrganism
from metamorphosis.m017_lab import (
    BehavioralOracle,
    Environment,
    generate_episodes,
    make_environment,
)
from metamorphosis.m017_language import Library

ROOT = Path(__file__).resolve().parents[1]

PAIRS = 4
SOURCE_EPISODES = 12
TARGET_EPISODES = 10


def median(values: list[int]) -> int:
    return int(statistics.median(values)) if values else 0


def train_library(environment: Environment, seed: int) -> tuple[str, int]:
    """Fait vivre un organisme dans un environnement et exporte son langage."""
    organism = SelfExtendingOrganism()
    for episode in generate_episodes(environment, seed, count=SOURCE_EPISODES):
        organism.solve(episode.base, BehavioralOracle(episode.target))
    return organism.export_library(), len(organism.library.macros)


def measure_pair(pair: int) -> tuple[dict[str, object], dict[str, object]]:
    """Une paire d'environnements : transport puis décalage. Tout dérive de `pair`.

    Fonction de premier niveau pour être exécutable dans un processus séparé : les
    paires sont indépendantes et entièrement déterminées par leurs graines, donc le
    parallélisme ne change aucun chiffre.
    """
    target_env = make_environment(95_000 + pair * 211)
    other_env = make_environment(96_000 + pair * 211)

    # Même environnement-source que la cible : motifs partagés à l'identique.
    shared_env = Environment(
        f"{target_env.environment_id}-shared", target_env.motifs, other_env.noise
    )
    shared_json, shared_macros = train_library(shared_env, 97_000 + pair * 211)
    disjoint_json, disjoint_macros = train_library(other_env, 97_500 + pair * 211)

    episodes = generate_episodes(target_env, 98_000 + pair * 211, count=TARGET_EPISODES)
    organisms = {
        "fresh": SelfExtendingOrganism(),
        "shared": SelfExtendingOrganism(library=Library.from_json(shared_json)),
        "disjoint": SelfExtendingOrganism(library=Library.from_json(disjoint_json)),
    }

    early: dict[str, list[int]] = {name: [] for name in organisms}
    solved: dict[str, int] = {name: 0 for name in organisms}
    paired_shared: list[int] = []
    paired_disjoint: list[int] = []

    for episode in episodes:
        nodes: dict[str, int | None] = {}
        for name, organism in organisms.items():
            result = organism.solve(episode.base, BehavioralOracle(episode.target))
            if result.status != "success":
                nodes[name] = None
                continue
            assert result.solution is not None
            assert exact_equivalence(result.solution, episode.target)[0], "faux succès"
            solved[name] += 1
            nodes[name] = result.search_nodes
            if episode.index < TARGET_EPISODES // 2:
                early[name].append(result.search_nodes)

        # Les épisodes précoces sont les seuls où l'héritage peut se voir : au-delà,
        # l'organisme `fresh` a absorbé les motifs de la cible par lui-même.
        if episode.index >= TARGET_EPISODES // 2:
            continue
        base_nodes = nodes["fresh"]
        if base_nodes is None:
            continue
        if nodes["shared"] is not None:
            paired_shared.append(int(base_nodes * 100 // nodes["shared"]))
        if nodes["disjoint"] is not None:
            paired_disjoint.append(int(base_nodes * 100 // nodes["disjoint"]))

    transport_row = {
        "pair": pair,
        "target": target_env.environment_id,
        "shared_source_macros": shared_macros,
        "disjoint_source_macros": disjoint_macros,
        **{f"{name}_solved": solved[name] for name in organisms},
        **{f"{name}_early_median": median(early[name]) for name in organisms},
        "shared_gain_x100_median": median(paired_shared),
        "disjoint_gain_x100_median": median(paired_disjoint),
    }

    # Porte n°5 — décalage brutal de distribution après absorption. L'organisme a
    # vécu dans la cible ; on lui impose ensuite les motifs d'un autre environnement.
    veteran = organisms["fresh"]
    after: list[int] = []
    abstentions = 0
    for episode in generate_episodes(other_env, 99_000 + pair * 211, count=6):
        result = veteran.solve(episode.base, BehavioralOracle(episode.target))
        if result.status != "success":
            abstentions += 1
            continue
        assert result.solution is not None
        assert exact_equivalence(result.solution, episode.target)[0], "faux succès"
        after.append(result.search_nodes)
    shift_row = {
        "pair": pair,
        "macros_at_shift": len(veteran.library.macros),
        "before_shift_early_median": median(early["fresh"]),
        "after_shift_median": median(after),
        "after_shift_solved": len(after),
        "after_shift_abstentions": abstentions,
    }
    return transport_row, shift_row


def main() -> None:
    # `map` conserve l'ordre des paires, donc le fichier de résultats est identique
    # au bit près qu'on tourne sur un cœur ou sur seize.
    with ProcessPoolExecutor() as pool:
        measured = list(pool.map(measure_pair, range(PAIRS)))
    rows = [transport for transport, _ in measured]
    shift_rows = [shift for _, shift in measured]
    for transport, shift in measured:
        print(json.dumps(transport, ensure_ascii=False))
        print(json.dumps(shift, ensure_ascii=False))

    shared_gains = [int(row["shared_gain_x100_median"]) for row in rows]
    disjoint_gains = [int(row["disjoint_gain_x100_median"]) for row in rows]

    summary = {
        "development_only": True,
        "pairs": PAIRS,
        "shared_gain_x100_min": min(shared_gains),
        "shared_gain_x100_median": median(shared_gains),
        "shared_gain_x100_max": max(shared_gains),
        "disjoint_gain_x100_min": min(disjoint_gains),
        "disjoint_gain_x100_median": median(disjoint_gains),
        "disjoint_gain_x100_max": max(disjoint_gains),
        "pairs_where_shared_helps": sum(1 for gain in shared_gains if gain > 100),
        "pairs_where_disjoint_hurts": sum(1 for gain in disjoint_gains if gain < 100),
        "shift_abstentions_total": sum(int(row["after_shift_abstentions"]) for row in shift_rows),
        "trace_number_format": "integers_only",
    }

    path = ROOT / "results" / "M017_transport_development.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"summary": summary, "transport": rows, "distribution_shift": shift_rows},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
