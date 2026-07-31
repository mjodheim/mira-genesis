"""M017 — banc d'essai. Propriété du laboratoire, jamais visible de l'organisme.

Hypothèse testée, énoncée sans détour :

    Un environnement réel n'est pas un tirage uniforme de transformations. Il a une
    structure compositionnelle qui **se répète**. Un organisme qui absorbe ses motifs
    récurrents dans son vocabulaire acquiert un pouvoir expressif qu'il n'avait pas,
    et voit son coût de recherche s'effondrer. Un organisme à catalogue fermé, lui,
    ne peut que s'abstenir.

La récurrence des motifs n'est donc pas un artefact commode : c'est la prémisse de
l'hypothèse, et elle est déclarée ici plutôt que dissimulée dans un générateur.

Le générateur ne connaît pas l'organisme, ne lui transmet rien, et refuse tout
épisode dont la cible serait comportementalement indistinguable de la source.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Sequence

from .m012b_dfa import DFA, exact_equivalence, random_minimal_dfa
from .structural import (
    Atom,
    ROLES,
    Word,
    all_atoms,
    apply_atoms,
    canonical_atom_key,
    enumerate_words,
    fingerprint,
    flip,
    normalize_dfa,
    redirect,
    walk,
)

_A = "deepest_accepting"
_R = "deepest_rejecting"
_H = "max_indegree_rejecting"
_I = "initial"

# Même jeu de filtrage que l'organisme : le laboratoire vérifie l'unicité dans le
# régime d'observation où l'organisme cherchera, pas dans un autre.
EPISODE_FILTER_WORDS: tuple[Word, ...] = enumerate_words(5)


@dataclass
class BehavioralOracle:
    """Surface comportementale. La cible n'est jamais exposée à l'organisme."""

    target: DFA
    mode: str = "stable"
    calls: int = 0

    def __post_init__(self) -> None:
        self._per_word: dict[Word, int] = {}

    def query(self, word: Word) -> bool:
        frozen = tuple(int(value) for value in word)
        self.calls += 1
        self._per_word[frozen] = self._per_word.get(frozen, 0) + 1
        value = self.target.accepts(frozen)
        if self.mode == "alternating" and self._per_word[frozen] % 2 == 0:
            return not value
        if self.mode == "periodic_three" and self._per_word[frozen] % 3 == 0:
            return not value
        return value

    # Réservé à l'évaluateur. Les audits d'isolation vérifient ce nom.
    def _audit_target(self) -> DFA:
        return self.target


# La bibliothèque fermée que M014c emportait : des programmes tout faits, jamais
# étendus. Reproduite ici pour que la baseline soit celle de l'expérience réelle,
# et non un homme de paille.
CLOSED_LIBRARY_PROGRAMS: tuple[tuple[Atom, ...], ...] = (
    (flip(_A),),
    (flip(_R),),
    (flip(_H),),
    (flip(_I),),
    (redirect(_A, 0, _I),),
    (redirect(_R, 1, _I),),
    (redirect(_H, 1, _R),),
    (redirect(_H, 0, _A),),
    (redirect(_I, 0, _A),),
    (redirect(_I, 1, _R),),
    (flip(_A), redirect(_H, 1, _I)),
    (flip(_R), redirect(_I, 0, _A)),
)


@dataclass(frozen=True)
class Environment:
    """Un environnement : ses motifs récurrents et son bruit."""

    environment_id: str
    motifs: tuple[tuple[Atom, ...], ...]
    noise: tuple[Atom, ...]

    def motif_keys(self) -> tuple[str, ...]:
        return tuple(sorted(canonical_atom_key(motif) for motif in self.motifs))


@dataclass(frozen=True)
class Episode:
    index: int
    base: DFA
    target: DFA
    program: tuple[Atom, ...]
    motif_index: int
    has_noise: bool


def is_irreducible_motif(motif: Sequence[Atom], sample_seeds: Sequence[int]) -> bool:
    """Le motif survit-il à une recherche de référence sur des sources indépendantes ?

    Mesure décisive : sur des motifs tirés au hasard, **35 épisodes sur 40** avaient
    une trajectoire plus courte menant à la même cible, et le motif n'était jamais
    retrouvé. La réductibilité est une propriété du motif, pas de la source — un
    motif dont l'effet net s'écrit en deux atomes s'écrira en deux atomes partout.

    Le filtre est donc posé ici, à la construction de l'environnement, et non à
    chaque épisode : c'est là qu'il est efficace, et c'est là qu'il se déclare.
    """
    for seed in sample_seeds:
        base = _usable_base(seed, 6, 9)
        raw = apply_atoms(base, motif)
        if raw is None:
            return False
        target = normalize_dfa(raw)
        if exact_equivalence(base, target)[0]:
            return False
        if not _recovers_motif(base, target, motif, fingerprint(target, EPISODE_FILTER_WORDS)):
            return False
    return True


def make_environment(
    seed: int,
    motif_count: int = 3,
    motif_size: int = 3,
    sample_bases: int = 2,
) -> Environment:
    """Tire des motifs irréductibles et distincts, hors de portée du catalogue fermé."""
    rng = random.Random(seed)
    atoms = list(all_atoms())
    sample_seeds = tuple(seed * 31 + offset * 7919 for offset in range(1, sample_bases + 1))
    motifs: list[tuple[Atom, ...]] = []
    seen: set[str] = set()
    for _ in range(4096):
        if len(motifs) == motif_count:
            break
        motif = tuple(rng.sample(atoms, motif_size))
        key = canonical_atom_key(motif)
        if key in seen:
            continue
        seen.add(key)
        if is_irreducible_motif(motif, sample_seeds):
            motifs.append(motif)
    if len(motifs) < motif_count:
        raise RuntimeError(f"unable to draw {motif_count} irreducible motifs for seed {seed}")
    noise = tuple(rng.sample(atoms, 6))
    return Environment(f"env-{seed}", tuple(motifs), noise)


def _usable_base(seed: int, min_states: int, max_states: int) -> DFA:
    """Une source dont tous les rôles sont occupés : sinon les atomes sont vides."""
    for attempt in range(64):
        base = normalize_dfa(random_minimal_dfa(seed + attempt * 7919, min_states, max_states))
        if any(base.accepting) and not all(base.accepting) and base.n_states >= min_states:
            return base
    raise RuntimeError("unable to draw a base DFA with every structural role occupied")


def _recovers_motif(
    base: DFA,
    target: DFA,
    program: Sequence[Atom],
    observed: tuple[bool, ...],
) -> bool:
    """Une recherche de référence retrouve-t-elle exactement ce motif ?

    Ce filtre est indispensable, et il a été ajouté après mesure. Sans lui, la
    recherche retrouve *une* solution exacte, jamais *le* motif : chaque épisode
    partant d'une source différente, les solutions trouvées ne se répètent pas, et
    un organisme qui absorbe les motifs récurrents n'a jamais rien à absorber.
    L'expérience mesurerait alors une abstraction qui ne se déclenche jamais — ce
    qui ne réfute rien du tout.

    Une première version exigeait que le motif soit l'unique trajectoire minimale.
    Trop stricte : presque aucun épisode ne passait, les permutations d'atomes non
    interactifs produisant couramment le même automate. La condition retenue est
    celle qui porte réellement la mesure — que la recherche débouche sur le motif —
    et non une propriété plus forte dont l'expérience n'a pas besoin.

    M014c rejetait déjà ses cibles à étiquette latente ambiguë. C'est la même
    exigence, portée au langage compositionnel.
    """
    blocks = [(atom,) for atom in all_atoms()]
    expected = tuple(atom.to_list() for atom in program)
    for depth in range(1, len(program) + 1):
        for indices, candidate in walk(base, blocks, depth):
            if fingerprint(candidate, EPISODE_FILTER_WORDS) != observed:
                continue
            if not exact_equivalence(normalize_dfa(candidate), target)[0]:
                continue
            found = tuple(blocks[index][0].to_list() for index in indices)
            return found == expected
    return False


def generate_episodes(
    environment: Environment,
    seed: int,
    *,
    count: int = 12,
    min_states: int = 6,
    max_states: int = 9,
    noise_probability: int = 3,
) -> tuple[Episode, ...]:
    """Suite d'épisodes d'un même environnement.

    `noise_probability` est un dénominateur entier : un épisode sur trois porte un
    atome de bruit en plus de son motif. Aucun flottant n'entre dans la génération.
    """
    rng = random.Random(seed)
    episodes: list[Episode] = []
    attempt = 0
    while len(episodes) < count and attempt < count * 40:
        attempt += 1
        base = _usable_base(seed + attempt * 104_729, min_states, max_states)
        motif_index = rng.randrange(len(environment.motifs))
        program = list(environment.motifs[motif_index])
        has_noise = rng.randrange(noise_probability) == 0
        if has_noise:
            extra = rng.choice(environment.noise)
            if canonical_atom_key([extra]) not in {canonical_atom_key([a]) for a in program}:
                program.append(extra)
            else:
                has_noise = False
        raw = apply_atoms(base, program)
        if raw is None:
            continue
        target = normalize_dfa(raw)
        if exact_equivalence(base, target)[0]:
            continue
        if not _recovers_motif(base, target, program, fingerprint(target, EPISODE_FILTER_WORDS)):
            continue
        episodes.append(
            Episode(len(episodes), base, target, tuple(program), motif_index, has_noise)
        )
    if len(episodes) < count:
        raise RuntimeError("unable to generate the requested episode count")
    return tuple(episodes)


def make_out_of_language_target(base: DFA, seed: int) -> DFA:
    """Cible qu'aucune composition d'atomes ne peut produire : elle ajoute un état.

    Le langage structurel réécrit un automate à nombre d'états constant. Une cible
    qui en gagne un est hors langage par construction, quelle que soit la profondeur
    de recherche — c'est le contrôle négatif que M017 doit rejeter, pas résoudre.
    """
    source = normalize_dfa(base)
    rng = random.Random(seed)
    count = source.n_states
    for _ in range(4096):
        transitions = [list(row) for row in source.transitions]
        accepting = list(source.accepting)
        transitions.append([rng.randrange(count + 1), rng.randrange(count + 1)])
        accepting.append(bool(rng.randrange(2)))
        transitions[rng.randrange(count)][rng.randrange(2)] = count
        candidate = normalize_dfa(
            DFA(
                source.alphabet,
                tuple(tuple(row) for row in transitions),
                tuple(accepting),
                source.initial,
            )
        )
        if candidate.n_states > source.n_states:
            return candidate
    raise RuntimeError("unable to construct a state-adding out-of-language target")


def environment_profile(environment: Environment) -> dict[str, object]:
    return {
        "environment_id": environment.environment_id,
        "motif_count": len(environment.motifs),
        "motif_sizes": [len(motif) for motif in environment.motifs],
        "roles": list(ROLES),
    }


def hidden_words(seed: int, count: int = 4_000) -> tuple[Word, ...]:
    rng = random.Random(seed)
    return tuple(
        tuple(rng.randrange(2) for _ in range(rng.randint(0, 24))) for _ in range(count)
    )


def hidden_accuracy(target: DFA, candidate: DFA, words: Sequence[Word]) -> int:
    """Nombre de désaccords sur un jeu de mots caché. Entier, donc portable."""
    return sum(1 for word in words if target.accepts(word) != candidate.accepts(word))
