"""M026 — decidable metaproductivity guidance in bounded rewrite trees.

M026 does not reimplement DGM or HGM. It isolates one distinction between their
published parent-selection rules while holding expansion, evaluation and final-agent
selection fixed:

* ``dgm_immediate`` uses immediate development performance with a direct-child bonus;
* ``hgm_clade`` uses development evidence aggregated over the observed clade;
* ``uniform`` is an archive-search baseline;
* ``oracle_descendant`` is an evaluator-only ceiling with access to exact hidden
  descendant quality.

Each node is a serialisable extension of M017's rewrite language. Development and
hidden tasks are finite transformation sequences, and the minimum number of symbols
needed to express every sequence is computed exactly. Selection never receives hidden
cases, hidden scores or exact descendant potential.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from functools import lru_cache
import hashlib
import random
from statistics import median
from typing import Callable, Iterable, Sequence

from .m017_language import Library, description_length
from .structural import Atom, all_atoms, canonical_atom_key


State = tuple[str, ...]
Case = tuple[Atom, ...]
DEFAULT_BUDGET = 40
DEVELOPMENT_MIN_SEEDS = 64
POLICY_SEPARATION_FLOOR_PER_MILLE = 167
POLICY_WIN_FLOOR = 40
PROTOCOL_VERSION = "M026-development-v1"


@dataclass(frozen=True)
class RewriteAction:
    name: str
    atoms: tuple[Atom, ...]
    prerequisite: str | None = None


@dataclass(frozen=True)
class MetaproductivityRig:
    name: str
    development_cases: tuple[Case, ...]
    hidden_cases: tuple[Case, ...]
    fixed_macros: tuple[Case, ...]
    actions: tuple[RewriteAction, ...]
    max_symbols: int
    max_depth: int

    def __post_init__(self) -> None:
        if self.name not in {"mismatch", "aligned"}:
            raise ValueError("unknown M026 rig")
        if not self.development_cases or not self.hidden_cases:
            raise ValueError("both development and hidden cases are required")
        if len(self.development_cases) != len(self.hidden_cases):
            raise ValueError("development and hidden suites must have equal size")
        if type(self.max_symbols) is not int or self.max_symbols < 1:
            raise ValueError("max_symbols must be a positive integer")
        if type(self.max_depth) is not int or self.max_depth < 1:
            raise ValueError("max_depth must be a positive integer")
        names = [action.name for action in self.actions]
        if len(names) != len(set(names)):
            raise ValueError("rewrite action names must be unique")
        known = set(names)
        if any(
            action.prerequisite is not None and action.prerequisite not in known
            for action in self.actions
        ):
            raise ValueError("rewrite action prerequisite is unknown")

    @property
    def development_total(self) -> int:
        return len(self.development_cases)

    @property
    def hidden_total(self) -> int:
        return len(self.hidden_cases)

    def action(self, name: str) -> RewriteAction:
        for action in self.actions:
            if action.name == name:
                return action
        raise KeyError(name)

    def available_actions(self, state: State) -> tuple[RewriteAction, ...]:
        selected = set(state)
        return tuple(
            action
            for action in self.actions
            if action.name not in selected
            and (
                action.prerequisite is None
                or action.prerequisite in selected
            )
        )


def _shuffled_atoms(seed: int, salt: int) -> list[Atom]:
    atoms = list(all_atoms())
    random.Random(seed * 65_537 + salt).shuffle(atoms)
    return atoms


def build_mismatch_rig(seed: int) -> MetaproductivityRig:
    """Build a positive control with an explicit performance/potential reversal.

    Six development sequences contain every pair of four reusable generic motifs.
    Their hidden counterparts reverse each pair. A platform edit is immediately
    useless but unlocks the generic motifs; platform plus all four motifs solves both
    suites within depth five. Six shortcut edits each solve one visible case but no
    hidden case, and consuming one depth slot prevents the complete generic lineage.
    """

    atoms = _shuffled_atoms(seed, 26_001)
    generic = tuple(tuple(atoms[index : index + 2]) for index in range(0, 8, 2))
    platform_atoms = tuple(atoms[8:10])
    pairs = tuple((left, right) for left in range(4) for right in range(left + 1, 4))
    development = tuple(generic[left] + generic[right] for left, right in pairs)
    hidden = tuple(generic[right] + generic[left] for left, right in pairs)

    actions: list[RewriteAction] = [
        RewriteAction("platform", platform_atoms),
    ]
    actions.extend(
        RewriteAction(f"generic_{index}", motif, "platform")
        for index, motif in enumerate(generic)
    )
    actions.extend(
        RewriteAction(f"shortcut_{index}", case)
        for index, case in enumerate(development)
    )
    return MetaproductivityRig(
        name="mismatch",
        development_cases=development,
        hidden_cases=hidden,
        fixed_macros=(),
        actions=tuple(actions),
        max_symbols=2,
        max_depth=5,
    )


def build_aligned_rig(seed: int) -> MetaproductivityRig:
    """Build a negative control where visible and hidden quality are identical.

    Development and hidden sequences use different fixed context motifs but require
    the same six generic motifs. Every current-state development score therefore
    equals its hidden score exactly. The platform action is a harmless depth-consuming
    decoy and unlocks nothing.
    """

    atoms = _shuffled_atoms(seed, 26_002)
    generic = tuple(tuple(atoms[index : index + 2]) for index in range(0, 12, 2))
    development_context = tuple(atoms[12:14])
    hidden_context = tuple(atoms[14:16])
    platform_atoms = tuple(atoms[16:18])
    development = tuple(development_context + motif for motif in generic)
    hidden = tuple(hidden_context + motif for motif in generic)
    actions = (RewriteAction("platform", platform_atoms),) + tuple(
        RewriteAction(f"generic_{index}", motif)
        for index, motif in enumerate(generic)
    )
    return MetaproductivityRig(
        name="aligned",
        development_cases=development,
        hidden_cases=hidden,
        fixed_macros=(development_context, hidden_context),
        actions=actions,
        max_symbols=2,
        max_depth=5,
    )


def extend_state(state: State, action_name: str) -> State:
    if action_name in state:
        raise ValueError("rewrite action already present")
    return tuple(sorted((*state, action_name)))


@lru_cache(maxsize=None)
def score_state(
    rig: MetaproductivityRig,
    state: State,
    suite: str,
) -> int:
    """Return the exact number of expressible cases in one sealed suite."""

    if suite == "development":
        cases = rig.development_cases
    elif suite == "hidden":
        cases = rig.hidden_cases
    else:
        raise ValueError("suite must be development or hidden")

    known_names = {action.name for action in rig.actions}
    if tuple(sorted(state)) != state or len(state) != len(set(state)):
        raise ValueError("state must be sorted and unique")
    if any(name not in known_names for name in state):
        raise ValueError("state contains an unknown rewrite action")

    library = Library.primitive()
    for atoms in rig.fixed_macros:
        library.add(atoms, episode=-1)
    for name in state:
        library.add(rig.action(name).atoms, episode=-1)
    return sum(
        description_length(case, library) <= rig.max_symbols for case in cases
    )


@lru_cache(maxsize=None)
def exact_clade_hidden_successes(rig: MetaproductivityRig, state: State) -> int:
    """Return exact evaluator-only hidden quality for the reachable rooted clade.

    The rooted clade includes ``state`` itself, matching HGM's theoretical CMP
    definition. M026 uses the sealed hidden suite for utility, whereas selectors see
    only development-suite observations.
    """

    best = score_state(rig, state, "hidden")
    if len(state) >= rig.max_depth:
        return best
    for action in rig.available_actions(state):
        best = max(
            best,
            exact_clade_hidden_successes(rig, extend_state(state, action.name)),
        )
    return best


@dataclass(frozen=True)
class PublicNode:
    """The complete information boundary visible to a parent selector."""

    node_id: int
    parent_id: int | None
    depth: int
    development_successes: int
    development_total: int
    children: tuple[int, ...]
    can_expand: bool


@dataclass(frozen=True)
class PublicArchive:
    nodes: tuple[PublicNode, ...]
    step: int
    budget: int

    def eligible(self) -> tuple[PublicNode, ...]:
        return tuple(
            node
            for node in self.nodes
            if node.can_expand
            and node.development_successes < node.development_total
        )

    def clade(self, root_id: int) -> tuple[PublicNode, ...]:
        by_id = {node.node_id: node for node in self.nodes}
        found: list[PublicNode] = []
        pending = [root_id]
        while pending:
            node_id = pending.pop()
            node = by_id[node_id]
            found.append(node)
            pending.extend(reversed(node.children))
        return tuple(found)


def clade_development_counts(
    archive: PublicArchive,
    root_id: int,
) -> tuple[int, int]:
    clade = archive.clade(root_id)
    successes = sum(node.development_successes for node in clade)
    total = sum(node.development_total for node in clade)
    return successes, total - successes


@lru_cache(maxsize=None)
def _fixed_sigmoid_weight(successes: int, total: int) -> int:
    """DGM's λ=10, midpoint=.5 sigmoid rounded to a fixed integer scale."""

    if type(successes) is not int or type(total) is not int:
        raise TypeError("scores must be exact integers")
    if total < 1 or not 0 <= successes <= total:
        raise ValueError("invalid development score")
    with localcontext() as context:
        context.prec = 50
        score = Decimal(successes) / Decimal(total)
        exponent = -(Decimal(10) * (score - Decimal("0.5")))
        sigmoid = Decimal(1) / (Decimal(1) + exponent.exp())
        scaled = (sigmoid * Decimal(1_000_000)).to_integral_value(
            rounding=ROUND_HALF_EVEN
        )
    return max(1, int(scaled))


def _weighted_choice(
    candidates: Sequence[PublicNode],
    weights: Sequence[int],
    rng: random.Random,
) -> int:
    if len(candidates) != len(weights) or not candidates:
        raise ValueError("weighted choice requires matching non-empty inputs")
    if any(type(weight) is not int or weight < 1 for weight in weights):
        raise ValueError("weights must be positive integers")
    ticket = rng.randrange(sum(weights))
    cumulative = 0
    for candidate, weight in zip(candidates, weights, strict=True):
        cumulative += weight
        if ticket < cumulative:
            return candidate.node_id
    raise AssertionError("weighted choice fell through")


def select_dgm_immediate(archive: PublicArchive, rng: random.Random) -> int:
    """Fixed-point adaptation of DGM's published parent-selection equation."""

    eligible = archive.eligible()
    weights = [
        max(
            1,
            _fixed_sigmoid_weight(
                node.development_successes,
                node.development_total,
            )
            // (1 + len(node.children)),
        )
        for node in eligible
    ]
    return _weighted_choice(eligible, weights, rng)


def _integer_beta_order_statistic(
    alpha: int,
    beta: int,
    rng: random.Random,
) -> int:
    """Sample a discrete 64-bit order-statistic analogue of Beta(alpha, beta).

    For integer parameters, a continuous Beta variate is the ``alpha``-th order
    statistic of ``alpha + beta - 1`` independent uniform variates. Using 64-bit
    integer uniforms keeps every selection decision integer and reproducible while
    preserving that construction up to the finite grid.
    """

    if type(alpha) is not int or type(beta) is not int or alpha < 1 or beta < 1:
        raise ValueError("beta parameters must be positive integers")
    draws = sorted(rng.getrandbits(64) for _ in range(alpha + beta - 1))
    return draws[alpha - 1]


def select_hgm_clade(archive: PublicArchive, rng: random.Random) -> int:
    """Select by a clade-aggregated integer Thompson-sampling analogue."""

    samples: list[tuple[int, int]] = []
    for node in archive.eligible():
        successes, failures = clade_development_counts(archive, node.node_id)
        sample = _integer_beta_order_statistic(
            1 + successes,
            1 + failures,
            rng,
        )
        samples.append((sample, -node.node_id))
    if not samples:
        raise ValueError("no eligible parent")
    best_sample, negative_id = max(samples)
    del best_sample
    return -negative_id


def select_uniform(archive: PublicArchive, rng: random.Random) -> int:
    eligible = archive.eligible()
    if not eligible:
        raise ValueError("no eligible parent")
    return eligible[rng.randrange(len(eligible))].node_id


Selector = Callable[[PublicArchive, random.Random], int]
PUBLIC_SELECTORS: dict[str, Selector] = {
    "dgm_immediate": select_dgm_immediate,
    "hgm_clade": select_hgm_clade,
    "uniform": select_uniform,
}
STRATEGIES = (*PUBLIC_SELECTORS, "oracle_descendant")


@dataclass
class _NodeRecord:
    node_id: int
    parent_id: int | None
    state: State
    development_successes: int
    hidden_successes: int
    action_order: tuple[str, ...]
    cursor: int = 0
    children: list[int] = field(default_factory=list)


class _Archive:
    def __init__(self, rig: MetaproductivityRig, seed: int, budget: int) -> None:
        self.rig = rig
        self.seed = seed
        self.budget = budget
        self.records: list[_NodeRecord] = []
        self.state_ids: dict[State, int] = {}
        self._add_record((), None)

    def _action_order(self, state: State) -> tuple[str, ...]:
        def key(action: RewriteAction) -> str:
            payload = f"m026|{self.seed}|{'/'.join(state)}|{action.name}"
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()

        return tuple(
            action.name
            for action in sorted(self.rig.available_actions(state), key=key)
        )

    def _add_record(self, state: State, parent_id: int | None) -> _NodeRecord:
        record = _NodeRecord(
            node_id=len(self.records),
            parent_id=parent_id,
            state=state,
            development_successes=score_state(self.rig, state, "development"),
            hidden_successes=score_state(self.rig, state, "hidden"),
            action_order=self._action_order(state),
        )
        self.records.append(record)
        self.state_ids[state] = record.node_id
        if parent_id is not None:
            self.records[parent_id].children.append(record.node_id)
        return record

    def _next_unique_action(self, record: _NodeRecord, *, consume: bool) -> str | None:
        cursor = record.cursor
        while cursor < len(record.action_order):
            action_name = record.action_order[cursor]
            next_state = extend_state(record.state, action_name)
            if next_state not in self.state_ids:
                if consume:
                    record.cursor = cursor + 1
                return action_name
            cursor += 1
            if consume:
                record.cursor = cursor
        return None

    def public(self, step: int) -> PublicArchive:
        return PublicArchive(
            nodes=tuple(
                PublicNode(
                    node_id=record.node_id,
                    parent_id=record.parent_id,
                    depth=len(record.state),
                    development_successes=record.development_successes,
                    development_total=self.rig.development_total,
                    children=tuple(record.children),
                    can_expand=(
                        len(record.state) < self.rig.max_depth
                        and self._next_unique_action(record, consume=False) is not None
                    ),
                )
                for record in self.records
            ),
            step=step,
            budget=self.budget,
        )

    def expand(self, parent_id: int) -> tuple[_NodeRecord, str]:
        parent = self.records[parent_id]
        action_name = self._next_unique_action(parent, consume=True)
        if action_name is None:
            raise ValueError("selected parent has no unique untried action")
        state = extend_state(parent.state, action_name)
        return self._add_record(state, parent_id), action_name


def _select_oracle_descendant(
    archive: _Archive,
    public: PublicArchive,
) -> int:
    eligible = public.eligible()
    if not eligible:
        raise ValueError("no eligible parent")
    return min(
        eligible,
        key=lambda node: (
            -exact_clade_hidden_successes(
                archive.rig,
                archive.records[node.node_id].state,
            ),
            len(node.children),
            node.node_id,
        ),
    ).node_id


def _per_mille(value: int, total: int) -> int:
    return value * 1000 // total


def _pairwise_concordance_per_mille(
    estimates: Sequence[int],
    targets: Sequence[int],
) -> int:
    if len(estimates) != len(targets):
        raise ValueError("estimate and target lengths differ")
    concordant = 0
    discordant = 0
    for left in range(len(estimates)):
        for right in range(left + 1, len(estimates)):
            estimate_delta = estimates[left] - estimates[right]
            target_delta = targets[left] - targets[right]
            if estimate_delta == 0 or target_delta == 0:
                continue
            if (estimate_delta > 0) == (target_delta > 0):
                concordant += 1
            else:
                discordant += 1
    comparable = concordant + discordant
    return (concordant - discordant) * 1000 // comparable if comparable else 0


def _calibration(archive: _Archive, public: PublicArchive) -> tuple[int, int]:
    immediate: list[int] = []
    clade_estimate: list[int] = []
    exact_target: list[int] = []
    for node in public.nodes:
        record = archive.records[node.node_id]
        immediate.append(
            _per_mille(node.development_successes, node.development_total)
        )
        successes, failures = clade_development_counts(public, node.node_id)
        clade_estimate.append(_per_mille(successes, successes + failures))
        exact_target.append(
            _per_mille(
                exact_clade_hidden_successes(archive.rig, record.state),
                archive.rig.hidden_total,
            )
        )
    return (
        _pairwise_concordance_per_mille(immediate, exact_target),
        _pairwise_concordance_per_mille(clade_estimate, exact_target),
    )


def run_trial(
    rig_name: str,
    strategy: str,
    seed: int,
    *,
    budget: int = DEFAULT_BUDGET,
) -> dict[str, object]:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    if type(budget) is not int or budget < 1:
        raise ValueError("budget must be a positive integer")
    if strategy not in STRATEGIES:
        raise ValueError("unknown M026 strategy")
    if rig_name == "mismatch":
        rig = build_mismatch_rig(seed)
    elif rig_name == "aligned":
        rig = build_aligned_rig(seed)
    else:
        raise ValueError("unknown M026 rig")

    archive = _Archive(rig, seed, budget)
    rng = random.Random(seed * 104_729 + 26)
    trace: list[dict[str, object]] = []

    for step in range(budget):
        public = archive.public(step)
        if not public.eligible():
            break
        if strategy == "oracle_descendant":
            parent_id = _select_oracle_descendant(archive, public)
        else:
            parent_id = PUBLIC_SELECTORS[strategy](public, rng)
        child, action_name = archive.expand(parent_id)
        trace.append(
            {
                "step": step,
                "parent_id": parent_id,
                "child_id": child.node_id,
                "action": action_name,
                "child_development_successes": child.development_successes,
            }
        )

    public = archive.public(len(trace))
    final = min(
        archive.records,
        key=lambda record: (-record.development_successes, record.node_id),
    )
    best_hidden = max(
        archive.records,
        key=lambda record: (record.hidden_successes, -record.node_id),
    )
    dgm_calibration, hgm_calibration = _calibration(archive, public)

    return {
        "rig": rig.name,
        "strategy": strategy,
        "seed": seed,
        "budget": budget,
        "archive_nodes": len(archive.records),
        "expansions": len(trace),
        "final_node_id": final.node_id,
        "final_state": list(final.state),
        "final_development_successes": final.development_successes,
        "final_development_per_mille": _per_mille(
            final.development_successes,
            rig.development_total,
        ),
        "final_hidden_successes": final.hidden_successes,
        "final_hidden_per_mille": _per_mille(
            final.hidden_successes,
            rig.hidden_total,
        ),
        "best_hidden_node_id": best_hidden.node_id,
        "best_hidden_per_mille": _per_mille(
            best_hidden.hidden_successes,
            rig.hidden_total,
        ),
        "dgm_exact_cmp_concordance_per_mille": dgm_calibration,
        "hgm_exact_cmp_concordance_per_mille": hgm_calibration,
        "integer_only_selection_trace": True,
        "hidden_fields_visible_to_selector": False,
        "trace": trace,
    }


def _integer_median(values: Iterable[int]) -> int:
    rows = list(values)
    if not rows:
        return 0
    return int(median(rows))


def _reachable_states(rig: MetaproductivityRig) -> tuple[State, ...]:
    """Enumerate every valid state in the finite depth-bounded rewrite domain."""

    seen: set[State] = {()}
    pending = [()]
    while pending:
        state = pending.pop()
        if len(state) >= rig.max_depth:
            continue
        for action in rig.available_actions(state):
            child = extend_state(state, action.name)
            if child not in seen:
                seen.add(child)
                pending.append(child)
    return tuple(sorted(seen, key=lambda state: (len(state), state)))


def summarize_runs(runs: Sequence[dict[str, object]]) -> dict[str, object]:
    expected_rigs = {"mismatch", "aligned"}
    expected_strategies = set(STRATEGIES)
    seed_sets: dict[tuple[str, str], set[int]] = {}
    for rig in expected_rigs:
        for strategy in expected_strategies:
            seed_sets[(rig, strategy)] = {
                int(row["seed"])
                for row in runs
                if row["rig"] == rig and row["strategy"] == strategy
            }
    if any(not seeds for seeds in seed_sets.values()):
        raise ValueError("every rig and strategy requires at least one seed")
    reference = seed_sets[("mismatch", "dgm_immediate")]
    if any(seeds != reference for seeds in seed_sets.values()):
        raise ValueError("M026 runs are not paired across rigs and strategies")
    expected_rows = len(reference) * len(expected_rigs) * len(expected_strategies)
    if len(runs) != expected_rows:
        raise ValueError("M026 runs contain missing or duplicate rows")

    summary: dict[str, object] = {
        "development_only": True,
        "paired_seeds": len(reference),
        "paired_seed_values": sorted(reference),
        "development_min_seeds": DEVELOPMENT_MIN_SEEDS,
        "common_task_families": True,
        "common_expansion_orders": True,
        "integer_only_selection_traces": all(
            bool(row["integer_only_selection_trace"]) for row in runs
        ),
        "hidden_fields_visible_to_selectors": any(
            bool(row["hidden_fields_visible_to_selector"]) for row in runs
        ),
        "primary_metric": "final hidden exact quality per mille",
        "policy_separation_floor_per_mille": POLICY_SEPARATION_FLOOR_PER_MILLE,
        "policy_win_floor": POLICY_WIN_FLOOR,
    }

    for rig in sorted(expected_rigs):
        for strategy in STRATEGIES:
            selected = [
                row
                for row in runs
                if row["rig"] == rig and row["strategy"] == strategy
            ]
            prefix = f"{rig}_{strategy}"
            for metric in (
                "final_development_per_mille",
                "final_hidden_per_mille",
                "best_hidden_per_mille",
                "dgm_exact_cmp_concordance_per_mille",
                "hgm_exact_cmp_concordance_per_mille",
            ):
                summary[f"{prefix}_{metric}_median"] = _integer_median(
                    int(row[metric]) for row in selected
                )

    hgm_by_seed = {
        int(row["seed"]): int(row["final_hidden_per_mille"])
        for row in runs
        if row["rig"] == "mismatch" and row["strategy"] == "hgm_clade"
    }
    dgm_by_seed = {
        int(row["seed"]): int(row["final_hidden_per_mille"])
        for row in runs
        if row["rig"] == "mismatch" and row["strategy"] == "dgm_immediate"
    }
    differences = [hgm_by_seed[seed] - dgm_by_seed[seed] for seed in sorted(reference)]
    summary["mismatch_hgm_minus_dgm_median_per_mille"] = _integer_median(differences)
    summary["mismatch_hgm_wins"] = sum(value > 0 for value in differences)
    summary["mismatch_hgm_ties"] = sum(value == 0 for value in differences)
    summary["mismatch_hgm_losses"] = sum(value < 0 for value in differences)

    enough = len(reference) >= DEVELOPMENT_MIN_SEEDS
    summary["enough_seeds_for_comparison"] = enough
    summary["hgm_policy_advantage_supported"] = (
        enough
        and int(summary["mismatch_hgm_minus_dgm_median_per_mille"])
        >= POLICY_SEPARATION_FLOOR_PER_MILLE
        and int(summary["mismatch_hgm_wins"]) >= POLICY_WIN_FLOOR
    )
    summary["aligned_control_exact"] = all(
        int(row["final_development_per_mille"])
        == int(row["final_hidden_per_mille"])
        for row in runs
        if row["rig"] == "aligned"
    )
    if not enough:
        summary["comparison_status"] = "insufficient_paired_seeds"
    elif not bool(summary["aligned_control_exact"]):
        summary["comparison_status"] = "aligned_control_failed"
    elif bool(summary["hgm_policy_advantage_supported"]):
        summary["comparison_status"] = "hgm_policy_advantage_supported"
    else:
        summary["comparison_status"] = "predicted_hgm_advantage_not_supported"
    return summary


def verify_structural_controls(seed: int = 0) -> dict[str, bool]:
    mismatch = build_mismatch_rig(seed)
    platform = ("platform",)
    shortcut = ("shortcut_0",)
    aligned = build_aligned_rig(seed)
    aligned_states = _reachable_states(aligned)
    return {
        "platform_has_lower_immediate_score": (
            score_state(mismatch, platform, "development")
            < score_state(mismatch, shortcut, "development")
        ),
        "platform_has_higher_exact_descendant_quality": (
            exact_clade_hidden_successes(mismatch, platform)
            > exact_clade_hidden_successes(mismatch, shortcut)
        ),
        "aligned_current_quality_is_exact": all(
            score_state(aligned, state, "development")
            == score_state(aligned, state, "hidden")
            for state in aligned_states
        ),
    }
