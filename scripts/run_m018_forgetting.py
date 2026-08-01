"""M018 — les trois mécanismes de dissolution, mesurés. **Aucun résultat canonique.**

Trois régimes, parce que l'hypothèse prédit des signes opposés selon le régime :

1. **stable** — l'organisme vit dans un environnement dont les motifs ne changent pas.
   L'oubli ne peut qu'y coûter : il jette des symboles qui allaient resservir.
2. **décalage** — la distribution bascule sur des motifs disjoints. L'oubli devrait
   y gagner : les anciens macros sont devenus du coût pur.
3. **transport** — l'organisme démarre avec une bibliothèque héritée d'un environnement
   étranger. C'est le passif de 0,69× mesuré par M017. Un mécanisme d'oubli qui
   fonctionne doit l'annuler.

Prédiction écrite avant la mesure, dans ces termes :

    (1) et (2) réduiront le passif sans l'annuler, (3) l'annulera mais coûtera cher
    sur les environnements stables. S'il n'y a pas de coût à la dissolution, c'est que
    la mesure est mal construite.
"""

from __future__ import annotations

import json
from pathlib import Path
import statistics

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m017_lab import (
    BehavioralOracle,
    generate_episodes,
    make_environment,
)
from metamorphosis.m017_language import Library
from metamorphosis.m018_engine import ForgettingOrganism
from metamorphosis.m018_forgetting import (
    BudgetForgetting,
    DissolutionForgetting,
    NoForgetting,
    UtilityForgetting,
)

ROOT = Path(__file__).resolve().parents[1]

PAIRS = 3
STABLE_EPISODES = 12
SHIFTED_EPISODES = 8
TRANSPORT_EPISODES = 8


def median(values: list[int]) -> int:
    return int(statistics.median(values)) if values else 0


def policies() -> dict[str, object]:
    return {
        "none": NoForgetting(),
        "utility": UtilityForgetting(),
        "budget": BudgetForgetting(),
        "dissolution": DissolutionForgetting(),
    }


def run(organism: ForgettingOrganism, episodes) -> tuple[list[int], int]:
    costs: list[int] = []
    abstentions = 0
    for episode in episodes:
        result = organism.solve(episode.base, BehavioralOracle(episode.target))
        if result.status != "success":
            abstentions += 1
            continue
        assert result.solution is not None
        assert exact_equivalence(result.solution, episode.target)[0], "faux succès"
        costs.append(result.search_nodes)
    return costs, abstentions


def train_foreign_library(seed: int) -> str:
    """Bibliothèque apprise ailleurs — la source exacte du passif de M017."""
    environment = make_environment(seed)
    organism = ForgettingOrganism()
    run(organism, generate_episodes(environment, seed + 500, count=10))
    return organism.export_library()


def main() -> None:
    rows: list[dict[str, object]] = []

    for pair in range(PAIRS):
        home = make_environment(120_000 + pair * 173)
        away = make_environment(121_000 + pair * 173)
        home_episodes = generate_episodes(home, 122_000 + pair * 173, count=STABLE_EPISODES)
        away_episodes = generate_episodes(away, 123_000 + pair * 173, count=SHIFTED_EPISODES)
        transport_episodes = generate_episodes(
            home, 124_000 + pair * 173, count=TRANSPORT_EPISODES
        )
        foreign = train_foreign_library(125_000 + pair * 173)

        for name, policy in policies().items():
            # Régimes 1 et 2 : même organisme, la distribution bascule au milieu.
            resident = ForgettingOrganism(policy=policy)
            stable_costs, stable_abstentions = run(resident, home_episodes)
            shifted_costs, shifted_abstentions = run(resident, away_episodes)

            # Régime 3 : organisme neuf, bibliothèque étrangère au départ.
            migrant = ForgettingOrganism(
                policy=policy, library=Library.from_json(foreign)
            )
            transport_costs, transport_abstentions = run(migrant, transport_episodes)

            rows.append({
                "pair": pair,
                "policy": name,
                "stable_median": median(stable_costs),
                "stable_solved": len(stable_costs),
                "stable_abstentions": stable_abstentions,
                "shifted_median": median(shifted_costs),
                "shifted_solved": len(shifted_costs),
                "shifted_abstentions": shifted_abstentions,
                "transport_median": median(transport_costs),
                "transport_solved": len(transport_costs),
                "transport_abstentions": transport_abstentions,
                "macros_at_end": resident.macro_count,
                "discarded": len(resident.discarded),
                "migrant_macros_at_end": migrant.macro_count,
                "migrant_discarded": len(migrant.discarded),
            })
            print(json.dumps(rows[-1], ensure_ascii=False))

    def gather(policy: str, field: str) -> list[int]:
        return [int(row[field]) for row in rows if row["policy"] == policy]

    # Rapports entiers en centièmes : la référence est toujours `none`, l'organisme
    # de M017 qui accumule sans jamais jeter. Au-dessus de 100, l'oubli gagne.
    summary: dict[str, object] = {"development_only": True, "pairs": PAIRS}
    for regime in ("stable", "shifted", "transport"):
        reference = gather("none", f"{regime}_median")
        for name in policies():
            values = gather(name, f"{regime}_median")
            ratios = [
                int(base * 100 // value) if value else 0
                for base, value in zip(reference, values)
            ]
            summary[f"{regime}_{name}_median"] = median(values)
            summary[f"{regime}_{name}_vs_none_x100"] = median(ratios)

    summary["discarded_total"] = sum(int(row["discarded"]) for row in rows)
    summary["trace_number_format"] = "integers_only"

    path = ROOT / "results" / "M018_forgetting_development.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"summary": summary, "runs": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
