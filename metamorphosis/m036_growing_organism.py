"""M036 — an organism that grows when its body is provably too small.

This is the complete loop, in one place:

1. it meets a task;
2. if it fails, it **proves** its body cannot express what it has already observed —
   from oracle answers alone, never seeing the target;
3. it **grows**, by a duplication that is neutral at the instant it happens;
4. it solves the task;
5. it **keeps** the acquisition, both the larger body and the absorbed macro.

Two measurements make this necessary rather than decorative:

- no composition of the existing atoms grows the state count. Across 53,280
  applications, 18,540 changed it and none increased it. A body could only shrink;
- an M017 macro already costs one symbol however many atoms it unfolds, so abstraction
  extends reach at fixed depth. That part of the language was already right, and this
  module does not touch it.

Growth is opt-in. `all_atoms()` is unchanged, so every recorded experiment keeps its
vocabulary, its reachable set and its digests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .m012b_dfa import DFA
from .m017_engine import BehavioralOracle, EpisodeResult, SelfExtendingOrganism
from .m017_language import Library, Symbol
from .structural import Word, all_atoms, enumerate_words, growth_atoms, normalize_dfa

OBSERVATION_WORDS: tuple[Word, ...] = enumerate_words(5)


def growing_library() -> Library:
    """The primitive vocabulary, widened by the capacity-increasing atoms.

    Growth belongs **inside** the search, not before it. Measured: with the eight growth
    atoms in the vocabulary the organism solves 2/8; applying growth as a separate phase
    and then searching each enlarged body solves 0/8.

    The reason is composition. In the vocabulary, a depth-3 trajectory can be
    edit → grow → edit, so the organism may enlarge itself *in the middle* of a repair.
    A grow-then-search phase can only ever produce grow → edit → edit, which is strictly
    less expressive.

    The price is honest: depth-3 enumeration widens from 36³ ≈ 46,000 nodes to
    44³ ≈ 85,000, so every episode costs nearly twice as much whether or not it needs to
    grow.
    """

    symbols = [
        Symbol(f"a{index:03d}", (atom,), "primitive")
        for index, atom in enumerate(all_atoms())
    ]
    symbols.extend(
        Symbol(f"g{index:03d}", (atom,), "primitive")
        for index, atom in enumerate(growth_atoms())
    )
    return Library(symbols)


def required_states_lower_bound(evidence: dict[Word, bool]) -> int:
    """Least states any automaton consistent with this evidence must have.

    Myhill–Nerode: two prefixes separated by an observed suffix cannot share a state, so
    a pairwise-distinguishable set of prefixes lower-bounds the state count.

    This is what the organism can establish **about itself**, from answers it already
    holds. The set is built greedily, so the bound may understate the true minimum. That
    keeps it sound in the direction that matters: it never claims growth is needed when it
    is not, and a silent diagnosis is not a proof that the body suffices.
    """

    prefixes = sorted({word[:k] for word in evidence for k in range(len(word) + 1)})

    def distinguishable(left: Word, right: Word) -> bool:
        for word, label in evidence.items():
            if word[: len(left)] != left:
                continue
            other = right + word[len(left) :]
            if other in evidence and evidence[other] != label:
                return True
        return False

    witnesses: list[Word] = []
    for prefix in prefixes:
        if all(distinguishable(prefix, kept) for kept in witnesses):
            witnesses.append(prefix)
    return max(1, len(witnesses))


@dataclass
class GrowthEvent:
    episode: int
    from_states: int
    to_states: int
    required_lower_bound: int

    def to_dict(self) -> dict[str, int]:
        return {
            "episode": self.episode,
            "from_states": self.from_states,
            "to_states": self.to_states,
            "required_lower_bound": self.required_lower_bound,
        }


@dataclass
class LifeRecord:
    """What the organism carries forward. Integers only, per M017 §9."""

    episodes: int = 0
    solved: int = 0
    abstained: int = 0
    growth_events: list[GrowthEvent] = field(default_factory=list)
    macros_absorbed: int = 0
    body_states: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "episodes": self.episodes,
            "solved": self.solved,
            "abstained": self.abstained,
            "growths": len(self.growth_events),
            "growth_events": [event.to_dict() for event in self.growth_events],
            "macros_absorbed": self.macros_absorbed,
            "body_states": self.body_states,
        }


class GrowingOrganism:
    """A lineage that carries one body across episodes and enlarges it when proved short.

    The organism keeps its body between tasks, unlike the M017 organisms which are handed
    a fresh base each episode. Without persistence there is no lineage to improve, and
    "self-improvement" would be a property of the harness rather than of the organism.
    """

    def __init__(self, body: DFA, *, search_budget: int = 200_000, max_symbols: int = 3):
        self.body = normalize_dfa(body)
        self.inner = SelfExtendingOrganism(
            max_symbols=max_symbols, search_budget=search_budget
        )
        self.inner.library = growing_library()
        self.record = LifeRecord(body_states=self.body.n_states)

    # -- diagnosis ---------------------------------------------------------------

    def observe(self, oracle: BehavioralOracle) -> dict[Word, bool]:
        """The organism's own evidence: what it asked, and what it was told."""

        return {word: bool(oracle.query(word)) for word in OBSERVATION_WORDS}

    def diagnose_insufficiency(self, evidence: dict[Word, bool]) -> int | None:
        """Return the proved required size when the body is too small, else None."""

        bound = required_states_lower_bound(evidence)
        return bound if bound > self.body.n_states else None

    # -- growth ------------------------------------------------------------------

    def grow_once(self, bodies: list[DFA]) -> list[DFA]:
        """Every distinct one-state-larger body reachable from `bodies`.

        The organism does not produce *a* child. A size bound says nothing about *where*
        the missing distinction lives, so it produces the whole set its vocabulary allows
        and keeps whichever solves the task.
        """

        from .structural import apply_atom, growth_atoms as _atoms

        grown: list[DFA] = []
        seen: set[tuple] = set()
        for body in bodies:
            for atom in _atoms():
                candidate = apply_atom(body, atom)
                if candidate is None or candidate.n_states <= body.n_states:
                    continue
                key = (candidate.transitions, candidate.accepting)
                if key in seen:
                    continue
                seen.add(key)
                grown.append(candidate)
        return grown

    def candidate_children(self, required: int) -> list[DFA]:
        """Every distinct body reachable by growing to `required` states.

        The diagnosis establishes *that* the body must grow, never *which* state to
        duplicate — a bound on size says nothing about where the missing distinction
        lives. A single deterministic growth therefore fails: measured 0/8, while growing
        and then searching each candidate succeeds.

        So the organism does not produce one child. It produces the whole set its
        vocabulary allows, and keeps whichever solves the task.
        """

        from .structural import apply_atom, growth_atoms as _atoms

        frontier = [self.body]
        while frontier and frontier[0].n_states < required:
            grown: list[DFA] = []
            seen: set[tuple] = set()
            for body in frontier:
                for atom in _atoms():
                    candidate = apply_atom(body, atom)
                    if candidate is None or candidate.n_states <= body.n_states:
                        continue
                    key = (candidate.transitions, candidate.accepting)
                    if key in seen:
                        continue
                    seen.add(key)
                    grown.append(candidate)
            if not grown:
                return []
            frontier = grown
        return frontier

    def adopt(self, child: DFA, required: int, episode: int) -> None:
        before = self.body.n_states
        self.body = child
        self.record.growth_events.append(
            GrowthEvent(episode, before, child.n_states, required)
        )
        self.record.body_states = child.n_states

    # -- one episode -------------------------------------------------------------

    def live(
        self, oracle: BehavioralOracle, *, max_growth: int = 2
    ) -> tuple[EpisodeResult, bool]:
        """Attempt a task; on failure, grow and retry, until it fits or growth is spent.

        Failure is the trigger, not the diagnosis. The Myhill–Nerode bound is sound but
        greedy, so it understates: measured on six cases it missed three that genuinely
        required growth. Gating growth behind it therefore suppressed the very cases the
        organism needed it for. An episode that could not be solved is itself sufficient
        evidence that a larger body is worth trying.

        The bound is still computed and recorded, because when it *does* fire it proves
        the limitation rather than guessing at it — but it no longer decides.
        """

        episode = self.record.episodes
        self.record.episodes += 1
        macros_before = len(self.inner.library.macros)

        result = self.inner.solve(self.body, oracle)
        grew = False

        if result.status != "success":
            proved = self.diagnose_insufficiency(self.observe(oracle))
            frontier = [self.body]
            for _ in range(max_growth):
                children = self.grow_once(frontier)
                if not children:
                    break
                solved = False
                for child in children:
                    attempt = self.inner.solve(child, oracle)
                    if attempt.status == "success":
                        self.adopt(child, proved or child.n_states, episode)
                        grew, result, solved = True, attempt, True
                        break
                if solved:
                    break
                frontier = children

        if result.status == "success" and result.solution is not None:
            # The acquisition is kept: the improved body becomes the lineage's body.
            self.body = normalize_dfa(result.solution)
            self.record.body_states = self.body.n_states
            self.record.solved += 1
        else:
            self.record.abstained += 1

        self.record.macros_absorbed += len(self.inner.library.macros) - macros_before
        return result, grew
