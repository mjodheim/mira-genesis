"""M022 — an explicit stress test for post-selection adaptation.

M021 separated selection measures on exact held-out quality, but its adaptive and frozen
audits were almost identical. M022 does not reinterpret that result. It builds a new,
separately named rig whose held-out sequence repeats irreducible motifs often enough for
M017-style abstraction to become useful after the audit has started.

The evaluator always runs two copies from the same pre-audit state:

- the adaptive copy persists across the complete sequence;
- the frozen copy is reset before every episode.

Both copies receive the same episode, oracle contract and search budget. Any late cost
advantage can therefore come only from state acquired during the held-out sequence.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import statistics
from typing import Sequence

from .m012b_dfa import exact_equivalence
from .m017_engine import BehavioralOracle as OracleProtocol
from .m017_lab import BehavioralOracle, Episode, generate_episodes, make_environment
from .m019_engine import Case


@dataclass(frozen=True)
class StagedCase:
    """One held-out case with its declared motif round for later diagnostics."""

    case: Case
    motif_index: int
    round_index: int


@dataclass(frozen=True)
class PairedEpisode:
    motif_index: int
    round_index: int
    adaptive_status: str
    frozen_status: str
    adaptive_nodes: int
    frozen_nodes: int
    adaptive_macros_after: int

    @property
    def both_solved(self) -> bool:
        return self.adaptive_status == "success" and self.frozen_status == "success"


@dataclass(frozen=True)
class AdaptationAudit:
    rows: tuple[PairedEpisode, ...]
    late_round_start: int
    adaptive_solved: int
    frozen_solved: int
    adaptive_late_solved: int
    frozen_late_solved: int
    common_late_pairs: int
    adaptive_late_nodes: int
    frozen_late_nodes: int
    late_cost_ratio_per_mille: int
    adaptive_late_not_worse: bool


def _median(values: Sequence[int]) -> int:
    return int(statistics.median(values)) if values else 0


def _as_case(episode: Episode) -> Case:
    return Case(
        base=episode.base,
        make_oracle=(
            lambda target=episode.target: BehavioralOracle(target)
        ),
        verify=(
            lambda solution, target=episode.target: bool(
                exact_equivalence(solution, target)[0]
            )
        ),
    )


def build_repeated_motif_sequence(
    seed: int,
    *,
    motif_count: int = 3,
    repetitions: int = 4,
    candidate_episodes: int = 36,
) -> tuple[StagedCase, ...]:
    """Build a deterministic sequence with each held-out motif repeated in rounds.

    Only noise-free episodes are admitted. Different source automata are retained, so
    the organism cannot memorise one complete input/output instance; it must reuse the
    recurring transformation motif.
    """
    if motif_count < 1:
        raise ValueError("motif_count must be positive")
    if repetitions < 3:
        raise ValueError("repetitions must leave at least one late round")
    if candidate_episodes < motif_count * repetitions:
        raise ValueError("candidate_episodes is too small for the requested sequence")

    environment = make_environment(400_000 + seed, motif_count=motif_count)
    for attempt in range(32):
        episodes = generate_episodes(
            environment,
            410_000 + seed * 101 + attempt * 7_919,
            count=candidate_episodes,
            noise_probability=4,
        )
        by_motif: dict[int, list[Episode]] = {
            index: [] for index in range(motif_count)
        }
        seen_bases: set[object] = set()
        for episode in episodes:
            if not episode.has_noise and episode.base not in seen_bases:
                by_motif[episode.motif_index].append(episode)
                seen_bases.add(episode.base)
        if not all(len(group) >= repetitions for group in by_motif.values()):
            continue

        staged: list[StagedCase] = []
        for round_index in range(repetitions):
            for motif_index in range(motif_count):
                episode = by_motif[motif_index][round_index]
                staged.append(
                    StagedCase(_as_case(episode), motif_index, round_index)
                )
        return tuple(staged)

    raise RuntimeError("unable to build a balanced repeated-motif sequence")


def _run_one(
    organism: object,
    case: Case,
    *,
    search_budget: int,
) -> tuple[str, int, int]:
    organism.search_budget = search_budget
    oracle: OracleProtocol = case.make_oracle()
    result = organism.solve(case.base, oracle)
    if result.status == "success":
        if result.solution is None or not case.verify(result.solution):
            raise AssertionError("false success during M022 audit")
    macro_count = len(organism.library.macros)
    return result.status, result.search_nodes, macro_count


def compare_adaptive_to_frozen(
    organism: object,
    staged_cases: Sequence[StagedCase],
    *,
    late_round_start: int = 2,
    search_budget: int = 200_000,
) -> AdaptationAudit:
    """Compare persistent adaptation with an episode-reset control on identical cases."""
    if late_round_start < 1:
        raise ValueError("late_round_start must be positive")
    if not staged_cases:
        raise ValueError("staged_cases must not be empty")

    template = copy.deepcopy(organism)
    adaptive = copy.deepcopy(template)
    rows: list[PairedEpisode] = []

    for staged in staged_cases:
        frozen = copy.deepcopy(template)
        adaptive_status, adaptive_nodes, adaptive_macros = _run_one(
            adaptive,
            staged.case,
            search_budget=search_budget,
        )
        frozen_status, frozen_nodes, _ = _run_one(
            frozen,
            staged.case,
            search_budget=search_budget,
        )
        rows.append(
            PairedEpisode(
                motif_index=staged.motif_index,
                round_index=staged.round_index,
                adaptive_status=adaptive_status,
                frozen_status=frozen_status,
                adaptive_nodes=adaptive_nodes,
                frozen_nodes=frozen_nodes,
                adaptive_macros_after=adaptive_macros,
            )
        )

    late = [row for row in rows if row.round_index >= late_round_start]
    common = [row for row in late if row.both_solved]
    adaptive_late_nodes = sum(row.adaptive_nodes for row in common)
    frozen_late_nodes = sum(row.frozen_nodes for row in common)
    ratio = (
        frozen_late_nodes * 1000 // adaptive_late_nodes
        if adaptive_late_nodes > 0
        else 0
    )

    adaptive_solved = sum(row.adaptive_status == "success" for row in rows)
    frozen_solved = sum(row.frozen_status == "success" for row in rows)
    adaptive_late_solved = sum(row.adaptive_status == "success" for row in late)
    frozen_late_solved = sum(row.frozen_status == "success" for row in late)

    return AdaptationAudit(
        rows=tuple(rows),
        late_round_start=late_round_start,
        adaptive_solved=adaptive_solved,
        frozen_solved=frozen_solved,
        adaptive_late_solved=adaptive_late_solved,
        frozen_late_solved=frozen_late_solved,
        common_late_pairs=len(common),
        adaptive_late_nodes=adaptive_late_nodes,
        frozen_late_nodes=frozen_late_nodes,
        late_cost_ratio_per_mille=ratio,
        adaptive_late_not_worse=adaptive_late_solved >= frozen_late_solved,
    )


def audit_summary(audit: AdaptationAudit) -> dict[str, int | bool]:
    """Return an integer-only summary suitable for reproducible JSON traces."""
    late_ratios = [
        row.frozen_nodes * 1000 // row.adaptive_nodes
        for row in audit.rows
        if row.round_index >= audit.late_round_start
        and row.both_solved
        and row.adaptive_nodes > 0
    ]
    return {
        "adaptive_solved": audit.adaptive_solved,
        "frozen_solved": audit.frozen_solved,
        "adaptive_late_solved": audit.adaptive_late_solved,
        "frozen_late_solved": audit.frozen_late_solved,
        "common_late_pairs": audit.common_late_pairs,
        "adaptive_late_nodes": audit.adaptive_late_nodes,
        "frozen_late_nodes": audit.frozen_late_nodes,
        "late_cost_ratio_per_mille": audit.late_cost_ratio_per_mille,
        "median_late_pair_ratio_per_mille": _median(late_ratios),
        "adaptive_late_not_worse": audit.adaptive_late_not_worse,
        "macros_after_sequence": audit.rows[-1].adaptive_macros_after,
    }
