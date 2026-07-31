"""M017 — étude de dispersion. **Aucun résultat canonique.**

Porte de gel n°2. M014b a préenregistré une marge de 25 % sans jamais établir que la
dispersion entre environnements était plus petite qu'elle. Le critère mesurait du
bruit d'échantillonnage, et l'expérience était indécidable avant même d'être lancée.

Ce script ne cherche pas à montrer que Genesis gagne. Il mesure **de combien la
comparaison décisive varie d'un environnement à l'autre**, afin qu'un seuil puisse
ensuite être choisi en connaissance de cause — ou que l'on constate qu'aucun seuil
n'est défendable.

La comparaison décisive est désignée dans `experiments/M017/PRE_REGISTRATION_DRAFT.md`
et n'est pas rediscutée ici : coût de recherche médian sur la seconde moitié des
épisodes, organisme auto-extensible contre recherche ouverte, par environnement.

Le catalogue fermé est exécuté comme **contrôle**, jamais comme critère : il est
structurellement incapable, et un seuil calé sur lui passerait trivialement.
"""

from __future__ import annotations

import json
from pathlib import Path
import statistics
import time

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m017_engine import (
    ClosedLibraryOrganism,
    OpenSearchOrganism,
    SelfExtendingOrganism,
)
from metamorphosis.m017_lab import (
    CLOSED_LIBRARY_PROGRAMS,
    BehavioralOracle,
    generate_episodes,
    make_environment,
)

ROOT = Path(__file__).resolve().parents[1]

ENVIRONMENTS = 8
EPISODES = 14
SECOND_HALF_FROM = EPISODES // 2


def median(values: list[int]) -> int:
    return int(statistics.median(values)) if values else 0


def main() -> None:
    started = time.perf_counter()
    rows: list[dict[str, object]] = []

    for index in range(ENVIRONMENTS):
        environment = make_environment(90_000 + index * 137)
        episodes = generate_episodes(environment, 91_000 + index * 137, count=EPISODES)
        systems = {
            "closed": ClosedLibraryOrganism(CLOSED_LIBRARY_PROGRAMS),
            "open": OpenSearchOrganism(),
            "genesis": SelfExtendingOrganism(),
        }
        late: dict[str, list[int]] = {name: [] for name in systems}
        early: dict[str, list[int]] = {name: [] for name in systems}
        solved: dict[str, int] = {name: 0 for name in systems}
        paired: list[int] = []
        genesis_slower = 0
        capability_wins = 0

        for episode in episodes:
            nodes: dict[str, int | None] = {}
            for name, organism in systems.items():
                result = organism.solve(episode.base, BehavioralOracle(episode.target))
                if result.status != "success":
                    nodes[name] = None
                    continue
                assert result.solution is not None
                assert exact_equivalence(result.solution, episode.target)[0], "faux succès"
                solved[name] += 1
                nodes[name] = result.search_nodes
                bucket = late if episode.index >= SECOND_HALF_FROM else early
                bucket[name].append(result.search_nodes)

            if episode.index < SECOND_HALF_FROM:
                continue
            # Comparaison appariée : les deux organismes sur **le même** épisode.
            # La médiane par environnement était bimodale — 42 nœuds pour un motif
            # pur, environ 1 800 lorsque l'épisode porte un atome de bruit — et
            # basculait selon le tirage. L'appariement supprime ce facteur de
            # confusion au lieu de l'espérer négligeable.
            if nodes["genesis"] is not None and nodes["open"] is not None:
                paired.append(int(nodes["open"] * 100 // nodes["genesis"]))
                if nodes["open"] < nodes["genesis"]:
                    genesis_slower += 1
            elif nodes["genesis"] is not None and nodes["open"] is None:
                capability_wins += 1

        row = {
            "environment": index,
            "environment_id": environment.environment_id,
            "macros": len(systems["genesis"].library.macros),
            **{f"{name}_solved": solved[name] for name in systems},
            **{f"{name}_early_median": median(early[name]) for name in systems},
            **{f"{name}_late_median": median(late[name]) for name in systems},
            "paired_ratio_x100_median": median(paired),
            "paired_ratio_x100_min": min(paired) if paired else 0,
            "paired_episodes": len(paired),
            "genesis_slower_episodes": genesis_slower,
            "capability_wins": capability_wins,
        }
        # Rapports entiers, arrondis vers le bas : aucun flottant n'entre dans une
        # grandeur qui servira à fixer un seuil. C'est la correction imposée par le
        # défaut de traçabilité de M014b.
        genesis_late = row["genesis_late_median"]
        open_late = row["open_late_median"]
        row["unpaired_ratio_x100"] = (
            int(open_late * 100 // genesis_late) if genesis_late else 0
        )
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

    paired_medians = [int(row["paired_ratio_x100_median"]) for row in rows]
    unpaired = [int(row["unpaired_ratio_x100"]) for row in rows]

    summary = {
        "development_only": True,
        "environments": ENVIRONMENTS,
        "episodes_per_environment": EPISODES,
        "decisive_comparison": "median paired per-episode ratio of open to self-extending search nodes, late episodes, per environment",
        "paired_ratio_x100_min": min(paired_medians),
        "paired_ratio_x100_median": median(paired_medians),
        "paired_ratio_x100_max": max(paired_medians),
        "worst_single_episode_ratio_x100": min(int(row["paired_ratio_x100_min"]) for row in rows),
        "genesis_slower_episodes_total": sum(int(row["genesis_slower_episodes"]) for row in rows),
        "capability_wins_total": sum(int(row["capability_wins"]) for row in rows),
        # Statistique rejetée, conservée pour que le motif du rejet reste vérifiable.
        "rejected_unpaired_ratio_x100_min": min(unpaired),
        "rejected_unpaired_ratio_x100_max": max(unpaired),
        "environments_favouring_genesis": sum(1 for ratio in paired_medians if ratio > 100),
        "environments_favouring_open": sum(1 for ratio in paired_medians if ratio < 100),
        "closed_solved_total": sum(int(row["closed_solved"]) for row in rows),
        "open_solved_total": sum(int(row["open_solved"]) for row in rows),
        "genesis_solved_total": sum(int(row["genesis_solved"]) for row in rows),
        "macros_total": sum(int(row["macros"]) for row in rows),
        "elapsed_seconds": int(time.perf_counter() - started),
        "trace_number_format": "integers_only",
    }

    path = ROOT / "results" / "M017_dispersion_development.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"summary": summary, "environments": rows}, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
