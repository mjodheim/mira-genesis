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


def minimal_criterion_survivors(
    population: Sequence[tuple[Organism, int]],
    threshold: int,
    capacity: int,
) -> list[Organism]:
    """Keep everyone who clears a bar, not the best few.

    M021 measured four selection rules against exact hidden quality and minimal criterion
    preserved the most: 750 per mille against 416 for novelty, 312 for a
    quality-diversity approximation and 0 for the direct objective. Selecting the best
    collapses the population onto one lineage and destroys the redundancy duplication
    needs in order to drift.

    Ties are broken by structural cost, so a smaller organism survives a larger one at
    equal agreement. That is what stops growth from being free.
    """

    qualified = [(org, score) for org, score in population if score >= threshold]
    if len(qualified) <= capacity:
        return [org for org, _ in qualified]

    # Sorting by score and truncating is elitist selection wearing a minimal criterion's
    # name. It collapses the population onto the best few, and the measurement shows the
    # cost: with truncation, raising generations from 60 to 150 changed nothing at all,
    # on every configuration swept. The population reached a fixed point and stopped
    # exploring.
    #
    # A minimal criterion holds that everyone above the bar is equally admissible. When
    # more qualify than there is room for, the cut must therefore preserve variety rather
    # than rank. Distinct bodies are kept first, and only then is the remainder filled.
    by_body: dict[str, tuple[Organism, int]] = {}
    for org, score in qualified:
        key = org.digest()
        kept = by_body.get(key)
        if kept is None or org.structural_cost() < kept[0].structural_cost():
            by_body[key] = (org, score)

    # Ordering the distinct bodies by structural cost was measured at 0/12 on every swept
    # configuration: cost rises with size, so a size-ordered cut discards precisely the
    # organisms that have grown. Diversity must be preserved without selecting against
    # the capacity increase the experiment exists to test.
    distinct = sorted(
        by_body.values(),
        key=lambda pair: (-pair[1], pair[0].structural_cost(), pair[0].digest()),
    )
    return [org for org, _ in distinct[:capacity]]


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
