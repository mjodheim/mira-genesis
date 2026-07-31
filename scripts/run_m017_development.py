"""Banc de développement M017. **Aucun résultat canonique.**

Trois organismes, trois environnements, une seule question : un organisme qui absorbe
les motifs récurrents de son environnement acquiert-il un pouvoir expressif et un
coût de recherche que ses jumeaux n'ont pas ?

Les grandeurs rapportées sont des entiers. M014b a montré qu'un hash de décision
incorporant des flottants n'est pas reproductible d'un environnement à l'autre.
"""

from __future__ import annotations

import json
from pathlib import Path
import statistics

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m017_engine import (
    ClosedLibraryOrganism,
    OpenSearchOrganism,
    SelfExtendingOrganism,
    embody,
)
from metamorphosis.m017_lab import (
    CLOSED_LIBRARY_PROGRAMS,
    BehavioralOracle,
    environment_profile,
    generate_episodes,
    make_environment,
    make_out_of_language_target,
)

ROOT = Path(__file__).resolve().parents[1]

ENVIRONMENTS = 3
EPISODES = 14


def median(values: list[int]) -> int:
    return int(statistics.median(values)) if values else 0


def main() -> None:
    per_episode: list[dict[str, object]] = []
    environments: list[dict[str, object]] = []
    macro_totals: list[int] = []

    for index in range(ENVIRONMENTS):
        environment = make_environment(70_000 + index * 101)
        episodes = generate_episodes(environment, 71_000 + index * 101, count=EPISODES)
        systems = {
            "closed": ClosedLibraryOrganism(CLOSED_LIBRARY_PROGRAMS),
            "open": OpenSearchOrganism(),
            "genesis": SelfExtendingOrganism(),
        }
        rows: dict[str, list[dict[str, object]]] = {name: [] for name in systems}

        for episode in episodes:
            for name, organism in systems.items():
                result = organism.solve(episode.base, BehavioralOracle(episode.target))
                exact = (
                    result.solution is not None
                    and exact_equivalence(result.solution, episode.target)[0]
                )
                # Une solution annoncée mais inexacte serait un faux succès. Aucun
                # n'est toléré : le critère est l'équivalence, pas la ressemblance.
                assert result.status != "success" or exact, "faux succès"
                record = {
                    "environment": index,
                    "episode": episode.index,
                    "system": name,
                    "motif_index": episode.motif_index,
                    "target_atoms": len(episode.program),
                    "status": result.status,
                    "reason": result.reason,
                    "search_nodes": result.search_nodes,
                    "oracle_calls": result.oracle_calls,
                    "false_matches": result.false_matches,
                    "program_symbols": result.program_symbols,
                    "macro_count": result.macro_count,
                    "exact": bool(exact),
                }
                rows[name].append(record)
                per_episode.append(record)

        macro_totals.append(len(systems["genesis"].library.macros))
        environments.append({
            "environment": index,
            "profile": environment_profile(environment),
            "genesis_macros": len(systems["genesis"].library.macros),
            "genesis_library_sha256": systems["genesis"].library.sha256(),
            **{
                f"{name}_solved": sum(1 for row in rows[name] if row["status"] == "success")
                for name in systems
            },
        })

    def solved(system: str) -> list[dict[str, object]]:
        return [
            row for row in per_episode
            if row["system"] == system and row["status"] == "success"
        ]

    def nodes(system: str) -> list[int]:
        return [int(row["search_nodes"]) for row in solved(system)]

    # Courbe d'apprentissage : le coût de recherche doit s'effondrer pour Genesis
    # au fil des épisodes, et rester plat pour la recherche ouverte.
    def half_nodes(system: str, second: bool) -> list[int]:
        return [
            int(row["search_nodes"])
            for row in solved(system)
            if (int(row["episode"]) >= EPISODES // 2) is second
        ]

    open_solved = {(row["environment"], row["episode"]) for row in solved("open")}
    genesis_solved = {(row["environment"], row["episode"]) for row in solved("genesis")}

    total = ENVIRONMENTS * EPISODES
    summary = {
        "development_only": True,
        "environments": ENVIRONMENTS,
        "episodes_per_environment": EPISODES,
        "total_episodes": total,
        "closed_solved": len(solved("closed")),
        "open_solved": len(solved("open")),
        "genesis_solved": len(solved("genesis")),
        "genesis_only_solved": len(genesis_solved - open_solved),
        "open_only_solved": len(open_solved - genesis_solved),
        "false_successes": 0,
        "open_nodes_total": sum(nodes("open")),
        "genesis_nodes_total": sum(nodes("genesis")),
        "open_nodes_median": median(nodes("open")),
        "genesis_nodes_median": median(nodes("genesis")),
        "open_nodes_first_half_median": median(half_nodes("open", False)),
        "open_nodes_second_half_median": median(half_nodes("open", True)),
        "genesis_nodes_first_half_median": median(half_nodes("genesis", False)),
        "genesis_nodes_second_half_median": median(half_nodes("genesis", True)),
        "genesis_macros_total": sum(macro_totals),
        "genesis_symbols_median": median(
            [int(row["program_symbols"]) for row in solved("genesis")]
        ),
        "open_symbols_median": median(
            [int(row["program_symbols"]) for row in solved("open")]
        ),
        "trace_number_format": "integers_only",
    }

    # --- réincarnation : le programme trouvé se traduit-il en un corps natif ? ----
    embodiment: list[dict[str, object]] = []
    environment = make_environment(72_500)
    episodes = generate_episodes(environment, 72_600, count=3, min_states=5, max_states=7)
    for family in range(3):
        machine = make_development_positive_machine(family)
        organism = SelfExtendingOrganism()
        for episode in episodes:
            result = organism.solve(episode.base, BehavioralOracle(episode.target))
            if result.status != "success" or result.solution is None:
                embodiment.append({"family": family, "episode": episode.index, "status": "skipped"})
                continue
            certificate = embody(machine, episode.base, result.solution, 73_000 + family)
            embodiment.append({
                "family": family,
                "episode": episode.index,
                "status": certificate.status,
                "reason": certificate.reason,
                "old_body_exact": certificate.old_body_exact,
                "new_body_exact": certificate.new_body_exact,
                "archive_bit_exact": certificate.archive_bit_exact,
            })

    summary["embodiment_exact"] = sum(
        1 for row in embodiment
        if row.get("old_body_exact") and row.get("new_body_exact") and row.get("archive_bit_exact")
    )
    summary["embodiment_attempted"] = sum(1 for row in embodiment if row["status"] != "skipped")

    # --- contrôles négatifs : hors langage et oracle instable --------------------
    negative: list[dict[str, object]] = []
    control_environment = make_environment(74_000)
    control_episodes = generate_episodes(control_environment, 74_100, count=4)
    for position, episode in enumerate(control_episodes):
        if position % 2 == 0:
            oracle = BehavioralOracle(make_out_of_language_target(episode.base, 74_500 + position))
            label = "out_of_language"
        else:
            oracle = BehavioralOracle(episode.target, mode="alternating")
            label = "unstable_oracle"
        result = SelfExtendingOrganism().solve(episode.base, oracle)
        negative.append({"kind": label, "status": result.status, "reason": result.reason})

    summary["negative_abstentions"] = sum(1 for row in negative if row["status"] == "abstained")
    summary["negative_total"] = len(negative)

    output = {
        "summary": summary,
        "environments": environments,
        "episodes": per_episode,
        "embodiment": embodiment,
        "negative_controls": negative,
    }
    path = ROOT / "results" / "M017_development.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
