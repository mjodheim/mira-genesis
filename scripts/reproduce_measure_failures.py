"""Reproduit, à la demande, les décrochages de mesure catalogués dans `MEASURES.md`.

Chaque cas suit la même forme :

    une mesure qui a l'air saine → une pression d'optimisation → l'endroit exact où
    elle cesse de suivre ce qu'elle prétend suivre, **prouvé** par la vérité terrain.

Ce que ce script n'apporte pas : les phénomènes. Goodhart, le *reward hacking*, le
*specification gaming* et la littérature qualité-diversité les décrivent depuis
longtemps.

Ce qu'il apporte : ils sont ici **exhibés dans un domaine décidable**. L'équivalence
comportementale de deux automates finis se prouve, donc on montre *où* la mesure
décroche au lieu de constater qu'un résultat a l'air faux. C'est ce que la plupart des
bancs d'essai ne peuvent pas faire.

    python scripts/reproduce_measure_failures.py              # cas rapides
    python scripts/reproduce_measure_failures.py --case R004
    python scripts/reproduce_measure_failures.py --full       # ajoute les cas coûteux
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import random
import statistics
from typing import Callable

from metamorphosis.conformance import w_method_suite
from metamorphosis.m012b_dfa import DFA, exact_equivalence, random_minimal_dfa
from metamorphosis.m017_engine import (
    ClosedLibraryOrganism,
    OpenSearchOrganism,
    SelfExtendingOrganism,
    enumerate_words,
)
from metamorphosis.m017_lab import (
    CLOSED_LIBRARY_PROGRAMS,
    BehavioralOracle,
    generate_episodes,
    make_environment,
)
from metamorphosis.m018_engine import ForgettingOrganism
from metamorphosis.m018_forgetting import NoForgetting, UtilityForgetting
from metamorphosis.m019_selection import Ledger
from metamorphosis.structural import all_atoms, apply_atoms, normalize_dfa


# --------------------------------------------------------------------------------
# R002 — une baseline structurellement incapable prise pour critère
# --------------------------------------------------------------------------------

def case_R002() -> dict[str, object]:
    """Un seuil calé sur une baseline incapable passe sans rien mesurer.

    Le catalogue fermé ne résout aucun épisode composé. N'importe quel système, même
    trivial, le bat donc d'un facteur infini — et le critère ne dit rien de plus que
    l'incapacité, déjà connue, de la baseline.
    """
    episodes = generate_episodes(make_environment(70_000), 70_100, count=6)
    closed = ClosedLibraryOrganism(CLOSED_LIBRARY_PROGRAMS)
    openly = OpenSearchOrganism()

    closed_solved = sum(
        1
        for episode in episodes
        if closed.solve(episode.base, BehavioralOracle(episode.target)).status == "success"
    )
    open_solved = sum(
        1
        for episode in episodes
        if openly.solve(episode.base, BehavioralOracle(episode.target)).status == "success"
    )
    return {
        "case": "R002",
        "claim": "un rapport au catalogue fermé mesure l'avantage du mécanisme testé",
        "closed_solved": f"{closed_solved}/{len(episodes)}",
        "open_solved": f"{open_solved}/{len(episodes)}",
        "diverged": closed_solved == 0 and open_solved > 0,
        "why": "la baseline résout zéro : tout seuil contre elle passe trivialement "
               "et ne mesure que son incapacité, qui était déjà connue",
        "rule": "une baseline incapable est un contrôle, jamais un critère",
    }


# --------------------------------------------------------------------------------
# R004 — une vérification incapable de garantir ce qu'elle affirmait
# --------------------------------------------------------------------------------

def _probabilistic_confirmation_words() -> tuple[tuple[int, ...], ...]:
    """Le jeu de confirmation d'origine, reconstruit pour la démonstration.

    Tous les mots jusqu'à la longueur 6, plus 96 mots tirés au hasard entre 7 et 20.
    Sa docstring affirmait couvrir la borne de distinction de deux automates.
    """
    words = [word for word in enumerate_words(6) if len(word) == 6]
    rng = random.Random(0x17C0_FFEE)
    words.extend(
        tuple(rng.randrange(2) for _ in range(rng.randint(7, 20))) for _ in range(96)
    )
    return tuple(words)


def case_R004() -> dict[str, object]:
    """« Zéro faux succès » rapporté par une procédure incapable de le garantir.

    On engendre de vraies différences avec le jeu d'atomes de l'organisme, puis on
    demande aux deux procédures de les détecter. La vérité terrain est
    `exact_equivalence`, décidable.
    """
    filtering = enumerate_words(5)
    probabilistic = set(filtering) | set(_probabilistic_confirmation_words())

    atoms = all_atoms()
    checked = missed_by_probabilistic = missed_by_conformance = 0
    first_witness: list[int] | None = None

    for seed in range(60):
        left = normalize_dfa(random_minimal_dfa(seed, 8, 9))
        for offset in range(0, len(atoms), 5):
            edited = apply_atoms(left, (atoms[offset],))
            if edited is None:
                continue
            right = normalize_dfa(edited)
            equivalent, witness = exact_equivalence(left, right)
            if equivalent:
                continue
            checked += 1

            if not any(left.accepts(w) != right.accepts(w) for w in probabilistic):
                missed_by_probabilistic += 1
                if first_witness is None and witness is not None:
                    first_witness = list(witness)

            suite = w_method_suite(left, max_target_states=left.n_states)
            if not any(left.accepts(w) != right.accepts(w) for w in suite):
                missed_by_conformance += 1

    return {
        "case": "R004",
        "claim": "la confirmation garantit zéro faux succès",
        "real_differences": checked,
        "missed_by_probabilistic_set": missed_by_probabilistic,
        "missed_by_conformance_suite": missed_by_conformance,
        "first_missed_witness": first_witness,
        "diverged": missed_by_probabilistic > 0 and missed_by_conformance == 0,
        "why": "96 tirages ne couvrent pas 2^7+...+2^20 ; la procédure rapportait une "
               "garantie qu'elle ne pouvait pas donner, et le résultat juste tenait au tirage",
        "rule": "une condition d'admission vaut ce que vaut la complétude de sa vérification",
    }


# --------------------------------------------------------------------------------
# R006 — un horizon plus court que le délai de rendement
# --------------------------------------------------------------------------------

def case_R006() -> dict[str, object]:
    """Une sélection impatiente élimine l'investisseur avant tout remboursement.

    Deux stratégies, la comptabilité réelle de M019, et des coûts tirés des mesures :
    apprendre coûte ~23 000 nœuds puis ~43, ne pas essayer en coûte 1 296 pour rien.
    """
    reward, endowment, ceiling = 6_000, 200_000, 60_000

    def simulate(costs: list[int], solves: list[bool]) -> list[int]:
        ledger = Ledger(energy=endowment, reward=reward, ceiling=ceiling)
        trace = []
        for cost, solved in zip(costs, solves):
            ledger.settle(cost, solved)
            trace.append(ledger.energy)
        return trace

    horizon = 6
    # L'apprenti paye trois recherches profondes — une par motif — puis récolte.
    learner_costs = [23_000, 23_000, 23_000] + [43] * 9
    learner_solves = [True] * 12
    # Le prudent cherche en profondeur 2, échoue vite, ne dépense presque rien.
    coward_costs = [1_296] * 12
    coward_solves = [False] * 12

    learner = simulate(learner_costs, learner_solves)
    coward = simulate(coward_costs, coward_solves)

    return {
        "case": "R006",
        "claim": "classer sur l'énergie restante sélectionne l'efficacité",
        "horizon_generations": horizon,
        "learner_energy_at_horizon": learner[horizon - 1],
        "coward_energy_at_horizon": coward[horizon - 1],
        "learner_energy_at_end": learner[-1],
        "coward_energy_at_end": coward[-1],
        "diverged": learner[horizon - 1] < coward[horizon - 1] and learner[-1] > coward[-1],
        "why": "à l'horizon de coupe l'apprenti est derrière et se fait éliminer ; "
               "au terme il est devant. La mesure est juste, l'horizon la retourne",
        "rule": "l'horizon d'évaluation prime sur l'intensité de la pression",
    }


# --------------------------------------------------------------------------------
# R005 — une grandeur sans conséquence
# --------------------------------------------------------------------------------

def case_R005() -> dict[str, object]:
    """Optimiser une grandeur qui ne coûte rien n'exerce aucune pression.

    Même organisme, même épisodes, avec et sans oubli. Sous un budget généreux, les
    deux survivent identiquement : la mesure ne les sépare pas.
    """
    budget = 200_000
    episodes = generate_episodes(make_environment(70_000), 70_100, count=10)
    results = {}
    for label, policy in (("sans_oubli", NoForgetting()), ("avec_oubli", UtilityForgetting())):
        organism = ForgettingOrganism(policy=policy, search_budget=budget)
        solved = nodes = worst = 0
        for episode in episodes:
            outcome = organism.solve(episode.base, BehavioralOracle(episode.target))
            nodes += outcome.search_nodes
            worst = max(worst, outcome.search_nodes)
            solved += outcome.status == "success"
        results[label] = {"solved": solved, "nodes": nodes, "worst_episode": worst}

    # La mesure ne sépare rien si l'écart de coût est négligeable **et** si aucun
    # organisme ne peut être puni pour ce coût. Les deux conditions sont mesurées.
    costs = [int(row["nodes"]) for row in results.values()]
    gap_per_mille = abs(costs[0] - costs[1]) * 1000 // max(costs)
    worst_episode = max(int(row["worst_episode"]) for row in results.values())
    budget_ever_binding = worst_episode >= budget
    outcomes_identical = len({int(row["solved"]) for row in results.values()}) == 1

    return {
        "case": "R005",
        "claim": "le coût de recherche mesure l'efficacité d'un mécanisme d'oubli",
        **{f"{label}_{k}": v for label, row in results.items() for k, v in row.items()},
        "cost_gap_per_mille": gap_per_mille,
        "worst_episode_nodes": worst_episode,
        "budget": budget,
        "budget_ever_binding": budget_ever_binding,
        "diverged": outcomes_identical and not budget_ever_binding and gap_per_mille < 50,
        "why": "l'écart de coût est de quelques pour mille et le budget n'est jamais "
               "atteint : aucune différence de coût ne change le sort d'un organisme, "
               "il n'y a rien pour quoi être efficace",
        "rule": "une grandeur qu'on optimise sans qu'elle coûte n'exerce aucune pression",
    }


# --------------------------------------------------------------------------------
# R001 / R003 — plage dynamique et taille d'échantillon
# --------------------------------------------------------------------------------

def _paired_ratio(index: int) -> int:
    """Rapport apparié médian d'un environnement, la grandeur décisive de M017."""
    environment = make_environment(90_000 + index * 137)
    episodes = generate_episodes(environment, 91_000 + index * 137, count=14)
    openly, genesis = OpenSearchOrganism(), SelfExtendingOrganism()
    ratios: list[int] = []
    for episode in episodes:
        open_result = openly.solve(episode.base, BehavioralOracle(episode.target))
        genesis_result = genesis.solve(episode.base, BehavioralOracle(episode.target))
        if episode.index < 7:
            continue
        if open_result.status == "success" and genesis_result.status == "success":
            ratios.append(int(open_result.search_nodes * 100 // genesis_result.search_nodes))
    return int(statistics.median(ratios)) if ratios else 0


def case_R003(environments: int, workers: int | None) -> dict[str, object]:
    """Un minimum d'échantillon optimiste, et un seuil qui n'y survit pas.

    Reproduction réduite : `MEASURES.md` rapporte 8 puis 50 environnements, minimum
    95,3× puis **9,0×**. Ici on compare un petit et un grand tirage du même processus.
    """
    small = max(4, environments // 4)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        ratios = list(pool.map(_paired_ratio, range(environments)))
    live = [ratio for ratio in ratios if ratio]

    return {
        "case": "R003",
        "claim": "un seuil dérivé du cas typique borne le cas le pire",
        "environments": environments,
        "small_sample_min_x100": min(live[:small]) if live[:small] else 0,
        "full_sample_min_x100": min(live) if live else 0,
        "full_sample_median_x100": int(statistics.median(live)) if live else 0,
        "diverged": bool(live) and min(live) < min(live[:small]),
        "why": "le minimum d'un petit échantillon est optimiste ; à pleine échelle "
               "MEASURES.md rapporte 95,3x puis 9,0x, sous le seuil de 10x proposé",
        "rule": "établir la plage dynamique avant de fixer une marge",
    }


CHEAP: dict[str, Callable[[], dict[str, object]]] = {
    "R002": case_R002,
    "R004": case_R004,
    "R005": case_R005,
    "R006": case_R006,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=sorted(set(CHEAP) | {"R003"}))
    parser.add_argument("--full", action="store_true", help="ajoute les cas coûteux (R003)")
    parser.add_argument("--environments", type=int, default=16)
    parser.add_argument("--workers", type=int, default=None)
    arguments = parser.parse_args()

    findings: list[dict[str, object]] = []
    if arguments.case == "R003":
        findings.append(case_R003(arguments.environments, arguments.workers))
    elif arguments.case:
        findings.append(CHEAP[arguments.case]())
    else:
        findings.extend(CHEAP[name]() for name in sorted(CHEAP))
        if arguments.full:
            findings.append(case_R003(arguments.environments, arguments.workers))

    for finding in findings:
        print(json.dumps(finding, indent=2, ensure_ascii=False))

    reproduced = sum(1 for finding in findings if finding["diverged"])
    print(f"\n{reproduced}/{len(findings)} décrochages reproduits, vérité terrain à l'appui")
    return 0 if reproduced == len(findings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
