"""M035 — variation with a capacity-increasing operator, under selection.

Two results bound what the existing stack can do:

- a learned tool adds nothing to the reachable set, because it is a composition of
  primitives charged what those primitives cost (M034);
- no composition of structural atoms grows the state count. Over 53,280 applications,
  18,540 changed it and *none* grew it.

So an organism can rearrange or shrink, never gain capacity. Its expressive ceiling is
fixed at birth, and no descendant can be structurally novel.

This module adds the operation biology uses for exactly this problem: duplication.
A duplicated state is redundant at birth — the language is unchanged, so selection cannot
see it — and then free to diverge under the atoms that already exist.

Nothing here is a claim about general self-improvement. It is a bounded, decidable
mechanism in a finite automaton domain, where "novel" has an exact meaning: outside the
founder's reachable set.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import random
from typing import Sequence

from .m012b_dfa import DFA, exact_equivalence, minimize_dfa
from .structural import Atom, all_atoms, apply_atoms, normalize_dfa

ATOMS = all_atoms()


# --------------------------------------------------------------------------------------
# The capacity-increasing operator
# --------------------------------------------------------------------------------------


def duplicable_states(dfa: DFA) -> tuple[int, ...]:
    """States that can be duplicated into a *reachable* twin.

    A state with no incoming edge cannot: its twin would be unreachable, normalisation
    would strip it, and the duplication would add no capacity. Exposed so callers pick a
    usable state instead of discovering the failure by getting `None` back.
    """

    incoming = {
        dfa.transitions[state][symbol]
        for state in range(dfa.n_states)
        for symbol in (0, 1)
    }
    return tuple(sorted(incoming))


def duplicate_state(dfa: DFA, index: int, incoming: int = 0) -> DFA | None:
    """Append a behaviourally identical twin of `index` and route one edge to it.

    Neutral by construction: the twin carries the same outgoing transitions and the same
    acceptance, so at the instant of duplication the two are indistinguishable and the
    language is unchanged. That is the point — a mutation selection cannot see is free to
    drift, which is how duplication creates novelty in biology rather than damage.

    `incoming` selects which edge pointing at `index` is redirected, so the operator is
    deterministic and enumerable rather than random.
    """

    if not 0 <= index < dfa.n_states:
        return None

    size = dfa.n_states
    transitions = [list(row) for row in dfa.transitions]
    accepting = list(dfa.accepting)
    transitions.append(list(dfa.transitions[index]))
    accepting.append(bool(dfa.accepting[index]))

    edges = [
        (state, symbol)
        for state in range(size)
        for symbol in (0, 1)
        if transitions[state][symbol] == index
    ]
    if not edges:
        return None
    state, symbol = edges[incoming % len(edges)]
    transitions[state][symbol] = size

    return DFA(
        dfa.alphabet,
        tuple(tuple(row) for row in transitions),
        tuple(accepting),
        dfa.initial,
    )


# --------------------------------------------------------------------------------------
# Organisms and lineage
# --------------------------------------------------------------------------------------


def required_states_lower_bound(evidence: dict[tuple[int, ...], bool]) -> int:
    """Least number of states any automaton consistent with this evidence must have.

    Myhill–Nerode: two prefixes are distinguishable when some observed suffix sends them
    to opposite answers, and distinguishable prefixes cannot share a state. A set of
    pairwise-distinguishable prefixes is therefore a lower bound on the state count.

    This is the diagnosis an organism can make **about itself**, from the oracle answers
    it already holds and without ever seeing the target. When the bound exceeds its own
    size, growth is not one option among several: no rearrangement of its current states
    can express what it has already observed.

    A greedy pairwise-distinguishable set is used. It may understate the true minimum,
    which keeps the bound sound: it never claims growth is needed when it is not.
    """

    prefixes = sorted({word[:k] for word in evidence for k in range(len(word) + 1)})

    def distinguishable(left: tuple[int, ...], right: tuple[int, ...]) -> bool:
        for word, label in evidence.items():
            if not word[: len(left)] == left:
                continue
            suffix = word[len(left) :]
            other = right + suffix
            if other in evidence and evidence[other] != label:
                return True
        return False

    witnesses: list[tuple[int, ...]] = []
    for prefix in prefixes:
        if all(distinguishable(prefix, kept) for kept in witnesses):
            witnesses.append(prefix)
    return max(1, len(witnesses))


def growth_is_necessary(organism: "Organism", evidence: dict[tuple[int, ...], bool]) -> bool:
    """Has this body run out of room for what it has already seen?"""

    return required_states_lower_bound(evidence) > organism.size


@dataclass(frozen=True)
class Mutation:
    """One recorded step of a lineage, sufficient to reproduce it exactly.

    A `parent_digest` alone identifies the previous body but cannot rebuild it. Gate 9
    requires the full lineage to remain replayable from the founder and immutable inputs,
    so the operation itself is stored rather than a pointer to its outcome.
    """

    kind: str            # "atom" or "duplication"
    atom_index: int      # index into ATOMS for an atom, -1 otherwise
    state: int           # duplicated state, -1 otherwise
    incoming: int        # which in-edge was rerouted, -1 otherwise

    def to_dict(self) -> dict[str, int | str]:
        return {
            "kind": self.kind,
            "atom_index": self.atom_index,
            "state": self.state,
            "incoming": self.incoming,
        }


def replay(founder: DFA, ancestry: Sequence[Mutation]) -> DFA | None:
    """Rebuild a descendant from its founder and its recorded mutations.

    Deterministic and total: every step is either an indexed atom or an indexed
    duplication, so the chain reproduces the body exactly or fails loudly. Nothing about
    the search, the population or the seeds is needed.
    """

    current = founder
    for step in ancestry:
        if step.kind == "atom":
            nxt = apply_atoms(current, [ATOMS[step.atom_index]])
        elif step.kind == "duplication":
            nxt = duplicate_state(current, step.state, step.incoming)
        else:
            return None
        if nxt is None:
            return None
        current = nxt
    return current


@dataclass(frozen=True)
class Organism:
    body: DFA
    generation: int = 0
    duplications: int = 0
    edits: int = 0
    parent_digest: str | None = None
    ancestry: tuple[Mutation, ...] = ()

    @property
    def size(self) -> int:
        return self.body.n_states

    def digest(self) -> str:
        payload = json.dumps(
            {
                "transitions": [list(row) for row in self.body.transitions],
                "accepting": [bool(a) for a in self.body.accepting],
                "initial": self.body.initial,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def structural_cost(self) -> int:
        """Growth is not free. An organism pays for the capacity it carries.

        Without this an unbounded duplicator wins trivially by bloating until some
        behaviour falls out. The cost is the whole reason a capacity increase has to be
        earned rather than taken.
        """

        return self.size


@dataclass
class VariationBudget:
    """Deterministic accounting. No float enters any decision."""

    bodies_evaluated: int = 0
    duplications_applied: int = 0
    atoms_applied: int = 0
    structural_cost_paid: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "bodies_evaluated": self.bodies_evaluated,
            "duplications_applied": self.duplications_applied,
            "atoms_applied": self.atoms_applied,
            "structural_cost_paid": self.structural_cost_paid,
        }


# --------------------------------------------------------------------------------------
# Variation
# --------------------------------------------------------------------------------------


def offspring(
    parent: Organism,
    rng: random.Random,
    *,
    allow_duplication: bool,
    max_size: int,
    evidence: dict[tuple[int, ...], bool] | None = None,
) -> Organism | None:
    """One child from one parent, by a single variation event.

    With `evidence`, duplication stops being a coin flip and becomes a response to a
    diagnosis: the parent grows exactly when the observations it already holds cannot fit
    in a body its size. That is the difference between blind variation and building a
    child for a task the parent has proved it cannot solve.

    The bound is sound but not tight, so a diagnosis of "no growth needed" is not a
    guarantee that none is; it only guarantees that a demanded growth was warranted.
    """

    wants_growth = allow_duplication and parent.size < max_size and (
        growth_is_necessary(parent, evidence)
        if evidence is not None
        else rng.randrange(4) == 0
    )

    if wants_growth:
        usable = duplicable_states(parent.body)
        if not usable:
            return None
        state = usable[rng.randrange(len(usable))]
        incoming = rng.randrange(4)
        child_body = duplicate_state(parent.body, index=state, incoming=incoming)
        if child_body is None:
            return None
        step = Mutation("duplication", -1, state, incoming)
        return Organism(
            body=child_body,
            generation=parent.generation + 1,
            duplications=parent.duplications + 1,
            edits=parent.edits,
            parent_digest=parent.digest(),
            ancestry=parent.ancestry + (step,),
        )

    atom_index = rng.randrange(len(ATOMS))
    atom: Atom = ATOMS[atom_index]
    child_body = apply_atoms(parent.body, [atom])
    if child_body is None:
        return None
    return Organism(
        body=child_body,
        generation=parent.generation + 1,
        duplications=parent.duplications,
        edits=parent.edits + 1,
        parent_digest=parent.digest(),
        ancestry=parent.ancestry + (Mutation("atom", atom_index, -1, -1),),
    )


# --------------------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------------------


def agreement(candidate: DFA, target: DFA, words: Sequence[tuple[int, ...]]) -> int:
    """Integer agreement over a fixed word set. The environment's only feedback."""

    return sum(1 for word in words if candidate.accepts(word) == target.accepts(word))


# Two independent decisions, two domain separators. Sharing one would make the choice of
# which bodies survive and the choice of which lineage represents each body correlated
# through the same hash.
BODY_SELECTION_DOMAIN = "m037-body-selection-v1"
REPRESENTATIVE_DOMAIN = "m037-body-representative-v1"


def thresholded_elitist_truncation(
    population: Sequence[tuple[Organism, int]],
    threshold: int,
    capacity: int,
) -> list[Organism]:
    """The selector M035 actually used. Preserved unchanged, under its true name.

    It admits on a threshold, then ranks the admitted by descending agreement, favours
    the smaller body on a tie, and truncates. That is elitist truncation, not a minimal
    criterion, and M035's historical 6/12 belongs to *this* implementation.

    It was previously documented as "chosen from M021's measurement". That attribution
    was wrong. `rank_by_minimal_criterion` in `m021_measures.py` filters on viability
    (`ledger.solved > 0`), ranks the viable by **novelty**, ranks the rejected by energy,
    and lets `Population.select` truncate. M021's 750 per mille belongs to that composite
    — viability, then novelty, then truncation — and to its own domain. Nothing here
    inherits it.
    """

    qualified = [(org, score) for org, score in population if score >= threshold]
    qualified.sort(key=lambda pair: (-pair[1], pair[0].structural_cost(), pair[0].digest()))
    return [org for org, _ in qualified[:capacity]]


def _key(domain: str, *parts: object) -> str:
    payload = "|".join([domain, *(str(part) for part in parts)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def body_selection_key(
    body_digest: str, *, commitment: str, reduction_seed: int, generation: int
) -> str:
    """Which bodies survive. Sees no score, no size, no input position."""

    return _key(BODY_SELECTION_DOMAIN, commitment, reduction_seed, generation, body_digest)


def representative_key(
    body_digest: str,
    ancestry_digest: str,
    *,
    commitment: str,
    reduction_seed: int,
    generation: int,
) -> str:
    """Which lineage represents a body when several converged on it.

    Two organisms can share a body and differ in ancestry, generation, edit and
    duplication counts. Keeping whichever the loop met first makes the surviving *lineage*
    depend on input order even when the surviving *bodies* do not — and that leaks into
    replayability, genealogical depth and every count reported for the winner.

    Separate domain from `body_selection_key`, so the two decisions cannot correlate.
    """

    return _key(
        REPRESENTATIVE_DOMAIN,
        commitment,
        reduction_seed,
        generation,
        body_digest,
        ancestry_digest,
    )


def ancestry_digest(organism: Organism) -> str:
    """Identity of a lineage, independent of the body it arrived at."""

    payload = json.dumps(
        [step.to_dict() for step in organism.ancestry],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def positive_population_floor_admission_with_body_diversity(
    population: Sequence[tuple[Organism, int]],
    threshold: int,
    capacity: int,
    *,
    commitment: str,
    reduction_seed: int,
    generation: int,
) -> list[Organism]:
    """Admit above a positive population floor; reduce uniformly over **distinct bodies**.

    Named for the whole rule, including the part that is easy to overlook. The runner
    supplies `max(1, min(score))`, so admission carries a **viability condition** on top
    of the population floor: an organism agreeing with nothing is rejected outright.

    That condition is chosen, not inherited. A minimal criterion is defined by a viability
    bar rather than by no bar at all; removing it entirely would leave a pure diversity
    sampler with no selection pressure, which is a different object. Here a zero score
    means disagreeing on every observed word, which is a defensible reading of non-viable.

    **Its cost is stated rather than hidden.** The justification for keeping admission
    otherwise near-vacuous is that a neutral duplication carries *exactly its parent's
    score*, so a rising bar would exclude duplicates before they could drift. That
    protection applies only once a lineage is viable. A neutral duplicate of a parent that
    has never scored receives no protection at all: both sit below 1 and both are rejected.
    If the entire population scores zero, nothing is admitted and the caller must decide
    what to do with an empty result.

    The work is therefore done by the reduction, and its unit is the **distinct body**.
    That is a declared diversity policy, not neutrality between organisms: ten clones
    present one candidacy. Chosen on mechanism before any measurement — the property under
    test is *structural* drift, and per-individual reduction would let a heavily
    replicated clone crowd out rare structures by multiplicity alone.

    Three decisions, kept apart:

    1. **admission** — score reaches the threshold; its exact value then has no influence;
    2. **which bodies survive** — `body_selection_key`;
    3. **which lineage represents each body** — `representative_key`, a separate domain.

    Neither key sees score, size, structural cost or input position, and both derive from
    an explicit `commitment` rather than the mutation generator: drawing from that stream
    would make the count of admitted organisms shift every later variation, coupling
    selection to variation through the random state.

    Growth's cost stays in `VariationBudget` and in the reported result. It is deliberately
    not reintroduced here as a survival pressure.
    """

    qualified = [org for org, score in population if score >= threshold]
    if not qualified:
        return []

    groups: dict[str, list[Organism]] = {}
    for org in qualified:
        groups.setdefault(org.digest(), []).append(org)

    chosen: dict[str, Organism] = {}
    for digest, members in groups.items():
        chosen[digest] = min(
            members,
            key=lambda org: representative_key(
                digest,
                ancestry_digest(org),
                commitment=commitment,
                reduction_seed=reduction_seed,
                generation=generation,
            ),
        )

    if len(chosen) <= capacity:
        return [chosen[digest] for digest in sorted(chosen)]

    ordered = sorted(
        chosen.items(),
        key=lambda item: body_selection_key(
            item[0],
            commitment=commitment,
            reduction_seed=reduction_seed,
            generation=generation,
        ),
    )
    return [org for _, org in ordered[:capacity]]


# Names used while the rule was still described as a minimal criterion, and before the
# viability condition in `max(1, ...)` was acknowledged. Kept as aliases so the two
# corrections stay visible rather than becoming silent renames.
population_floor_admission_with_body_diversity = (
    positive_population_floor_admission_with_body_diversity
)
minimal_admission_with_body_diversity = (
    positive_population_floor_admission_with_body_diversity
)


# Historical alias. `minimal_criterion_survivors` named a selector that was not a minimal
# criterion; the name is kept pointing at the implementation that produced M035's result
# so that record stays reproducible.
minimal_criterion_survivors = thresholded_elitist_truncation


def speciated_survivors(
    population: Sequence[tuple[Organism, int]],
    threshold: int,
    capacity: int,
) -> list[Organism]:
    """Selection within structural niches, so new capacity is not culled on arrival.

    A duplication is neutral in behaviour but not in competition: the twin arrives with
    the parent's score and a larger structural cost, so a plain tie-break on size removes
    it immediately. Growth then never survives long enough to diverge, which is the whole
    point of duplicating.

    This is the failure mode neuroevolution documents: a topological innovation is born
    less fit than the incumbents and is eliminated before it can be optimised. NEAT's
    answer is speciation — innovations compete inside their own niche.

    The niche here is the state count, the only structural axis this organism has. Each
    size is allotted a share of the population, so a larger organism is judged against
    other large ones rather than against the whole field.
    """

    qualified = [(org, score) for org, score in population if score >= threshold]
    if not qualified:
        return []

    species: dict[int, list[tuple[Organism, int]]] = {}
    for org, score in qualified:
        species.setdefault(org.size, []).append((org, score))

    share = max(1, capacity // len(species))
    survivors: list[Organism] = []
    for size in sorted(species):
        members = sorted(
            species[size],
            key=lambda pair: (-pair[1], pair[0].digest()),
        )
        survivors.extend(org for org, _ in members[:share])

    # Any remaining capacity goes to the strongest overall, so speciation widens the
    # search without shrinking it.
    if len(survivors) < capacity:
        held = {org.digest() for org in survivors}
        rest = sorted(
            (pair for pair in qualified if pair[0].digest() not in held),
            key=lambda pair: (-pair[1], pair[0].structural_cost(), pair[0].digest()),
        )
        survivors.extend(org for org, _ in rest[: capacity - len(survivors)])

    return survivors[:capacity]
