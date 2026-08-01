"""M017 — les trois organismes comparés.

`ClosedLibraryOrganism`  — exactement la capacité de M014c : un catalogue figé,
                            aucune composition. Hors catalogue, il ne peut que
                            s'abstenir. C'est une incapacité structurelle, pas une
                            lenteur.
`OpenSearchOrganism`     — compose librement, n'absorbe jamais rien. Capable, mais
                            il repaye le prix fort à chaque épisode.
`SelfExtendingOrganism`  — compose et **absorbe**. Son vocabulaire grandit.

La grandeur mesurée est le nombre de programmes évalués avant de trouver. Elle va de
l'unité à la centaine de milliers. M014b comparait 14 requêtes à 14 requêtes : c'est
cette absence de plage dynamique qui rendait son critère indécidable, et c'est ce que
M017 corrige d'abord.

Le coût d'oracle, lui, est délibérément **constant** entre les trois organismes : même
jeu de sondage, même confirmation. Il ne peut donc pas confondre la comparaison.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterator, Protocol, Sequence

from .m012b_dfa import DFA, exact_equivalence
from .m013e_engine import UnknownSubstrateMigrator
from .m013e_lab import OpaqueBooleanMachine
from .m013e_runtime import opaque_body_to_dfa
from .m017_language import AbstractionRule, Library, Symbol, description_length
from .structural import (
    Atom,
    Word,
    enumerate_words,
    fingerprint,
    normalize_dfa,
    walk,
)

# Sondage à deux étages. Presque tous les candidats meurent sur les sept mots courts ;
# seuls les survivants payent l'empreinte complète. C'est ce qui rend une recherche
# exhaustive de profondeur 3 tenable en Python.
FILTER_WORDS: tuple[Word, ...] = enumerate_words(5)
SHORT_WORDS: tuple[Word, ...] = enumerate_words(2)


def _confirmation_words() -> tuple[Word, ...]:
    """Jeu de confirmation strict, fixe et déterministe.

    Une première version ne confirmait que sur des mots de longueur 6. Sur des
    automates de six à neuf états, cela laissait passer des trajectoires de deux
    atomes qui approchent la cible sans l'égaler : la recherche s'arrêtait sur une
    approximation bon marché, et aucun motif ne se répétait jamais — l'abstraction
    n'avait alors rien à absorber.

    Deux automates de n et m états qui diffèrent le font sur un mot de longueur au
    plus n+m−1. Les mots longs tirés ici couvrent cette borne pour le domaine visé.
    """
    words = [word for word in enumerate_words(6) if len(word) == 6]
    rng = random.Random(0x17C0_FFEE)
    words.extend(
        tuple(rng.randrange(2) for _ in range(rng.randint(7, 20))) for _ in range(96)
    )
    return tuple(words)


CONFIRMATION_WORDS: tuple[Word, ...] = _confirmation_words()


class BehavioralOracle(Protocol):
    """Tout ce que l'organisme voit du monde : poser un mot, recevoir un booléen.

    Déclaré ici comme protocole, et non importé de `m017_lab`. Un organisme qui
    importe son laboratoire n'est pas isolé de lui : la dépendance rendait techniquement
    atteignables, depuis le code de l'organisme, le générateur d'épisodes, les motifs
    de l'environnement et la méthode `_audit_target`. `scripts/audit_m017_isolation.py`
    vérifie désormais que cette frontière tient.
    """

    def query(self, word: Word) -> bool: ...


@dataclass(frozen=True)
class EpisodeResult:
    status: str
    reason: str
    episode: int
    program: tuple[Atom, ...] | None
    symbols_used: tuple[str, ...]
    search_nodes: int
    oracle_calls: int
    false_matches: int
    library_size: int
    macro_count: int
    program_atoms: int
    program_symbols: int
    born_symbols: tuple[str, ...]
    solution: DFA | None


class _Organism:
    """Partie commune : sonder, chercher, confirmer."""

    def __init__(
        self,
        library: Library,
        max_symbols: int,
        search_budget: int,
        repeat_queries: int = 2,
    ) -> None:
        self.library = library
        self.max_symbols = max_symbols
        self.search_budget = search_budget
        self.repeat_queries = repeat_queries
        self.episode = 0

    # -- oracle ---------------------------------------------------------------

    def _probe(self, oracle: BehavioralOracle) -> tuple[tuple[bool, ...] | None, int, str]:
        observed: list[bool] = []
        calls = 0
        for word in FILTER_WORDS:
            answers = [bool(oracle.query(word)) for _ in range(self.repeat_queries)]
            calls += self.repeat_queries
            if len(set(answers)) != 1:
                return None, calls, "oracle_inconsistent"
            observed.append(answers[0])
        return tuple(observed), calls, ""

    def _confirm(self, candidate: DFA, oracle: BehavioralOracle) -> tuple[str, int]:
        calls = 0
        for word in CONFIRMATION_WORDS:
            answers = [bool(oracle.query(word)) for _ in range(self.repeat_queries)]
            calls += self.repeat_queries
            if len(set(answers)) != 1:
                return "oracle_changed_during_confirmation", calls
            if answers[0] != candidate.accepts(word):
                return "mismatch", calls
        return "confirmed", calls

    # -- recherche ------------------------------------------------------------

    def _candidates(
        self, base: DFA
    ) -> Iterator[tuple[tuple[Symbol, ...], tuple[Atom, ...], DFA]]:
        """Approfondissement itératif : une solution courte est trouvée en premier.

        C'est ici que l'abstraction se paye. Un motif absorbé est un symbole : il est
        atteint dès la profondeur 1, là où sa version dépliée demande d'explorer
        toutes les trajectoires de trois atomes.
        """
        order = self.library.search_order()
        blocks = [symbol.atoms for symbol in order]
        for depth in range(1, self.max_symbols + 1):
            for indices, candidate in walk(base, blocks, depth):
                symbols = tuple(order[index] for index in indices)
                atoms = tuple(atom for symbol in symbols for atom in symbol.atoms)
                yield symbols, atoms, candidate

    # -- épisode --------------------------------------------------------------

    def _absorb(
        self, atoms: Sequence[Atom], symbols: Sequence[Symbol]
    ) -> tuple[str, ...]:
        """Crochet d'après-épisode. `symbols` est ce que l'organisme a réellement
        employé : M018 en a besoin pour créditer ses symboles et jeter les inutiles."""
        return ()

    def solve(self, base: DFA, oracle: BehavioralOracle) -> EpisodeResult:
        episode = self.episode
        self.episode += 1
        source = normalize_dfa(base)
        library_size = len(self.library)
        macro_count = len(self.library.macros)

        def abstain(reason: str, nodes: int, calls: int, false_matches: int) -> EpisodeResult:
            return EpisodeResult(
                "abstained", reason, episode, None, (), nodes, calls, false_matches,
                library_size, macro_count, 0, 0, (), None,
            )

        observed, calls, reason = self._probe(oracle)
        if observed is None:
            return abstain(reason, 0, calls, 0)
        observed_short = observed[: len(SHORT_WORDS)]

        nodes = 0
        false_matches = 0
        for symbols, atoms, candidate in self._candidates(source):
            if nodes >= self.search_budget:
                return abstain("search_budget_exhausted", nodes, calls, false_matches)
            nodes += 1
            if fingerprint(candidate, SHORT_WORDS) != observed_short:
                continue
            if fingerprint(candidate, FILTER_WORDS) != observed:
                continue

            verdict, confirm_calls = self._confirm(candidate, oracle)
            calls += confirm_calls
            if verdict == "oracle_changed_during_confirmation":
                return abstain(verdict, nodes, calls, false_matches)
            if verdict == "mismatch":
                # Une empreinte peut coïncider sans que le comportement le fasse.
                # La recherche reprend là où elle en était plutôt que d'abandonner.
                false_matches += 1
                continue

            symbols_needed = description_length(atoms, self.library)
            born = self._absorb(atoms, symbols)
            return EpisodeResult(
                "success", "program_identified", episode, atoms,
                tuple(symbol.name for symbol in symbols), nodes, calls, false_matches,
                len(self.library), len(self.library.macros), len(atoms),
                symbols_needed, born, normalize_dfa(candidate),
            )

        return abstain("no_expressible_program_within_budget", nodes, calls, false_matches)


class ClosedLibraryOrganism(_Organism):
    """La capacité de M014c, reproduite telle quelle."""

    def __init__(self, programs: Sequence[Sequence[Atom]], search_budget: int = 200_000) -> None:
        super().__init__(Library.closed(programs), max_symbols=1, search_budget=search_budget)


class OpenSearchOrganism(_Organism):
    """Compose, mais n'apprend jamais de nouveau symbole."""

    def __init__(self, max_symbols: int = 3, search_budget: int = 200_000) -> None:
        super().__init__(Library.primitive(), max_symbols=max_symbols, search_budget=search_budget)


class SelfExtendingOrganism(_Organism):
    """Compose et absorbe. C'est l'organisme dont M017 teste l'hypothèse."""

    def __init__(
        self,
        max_symbols: int = 3,
        search_budget: int = 200_000,
        threshold: int = 2,
        library: Library | None = None,
    ) -> None:
        super().__init__(
            library or Library.primitive(),
            max_symbols=max_symbols,
            search_budget=search_budget,
        )
        self.rule = AbstractionRule(threshold=threshold)

    def _absorb(
        self, atoms: Sequence[Atom], symbols: Sequence[Symbol]
    ) -> tuple[str, ...]:
        return tuple(
            symbol.name
            for symbol in self.rule.observe(atoms, self.library, self.episode)
        )

    def export_library(self) -> str:
        return self.library.to_json()


@dataclass(frozen=True)
class EmbodimentResult:
    status: str
    reason: str
    old_body_exact: bool
    new_body_exact: bool
    archive_bit_exact: bool
    used_opcodes: tuple[str, ...]


def embody(
    machine: OpaqueBooleanMachine,
    base: DFA,
    solution: DFA,
    search_seed: int,
    migrator: UnknownSubstrateMigrator | None = None,
) -> EmbodimentResult:
    """Reconstruit l'ancien et le nouveau corps sur un substrat opaque.

    M014b avait raison sur un point : une compétence qui ne se réincarne pas n'a rien
    prouvé. Ce contrôle vérifie qu'un programme trouvé par le langage étendu se
    traduit en un corps natif exact, et que l'archive reste intacte octet pour octet.
    """
    engine = migrator or UnknownSubstrateMigrator(native_component_budget=360)
    old = engine.migrate(base, machine, search_seed)
    if old.status != "success" or old.body is None:
        return EmbodimentResult("failed", f"old_body:{old.reason}", False, False, False, ())

    archived = old.body.to_json()
    new = engine.migrate(
        solution, machine, search_seed ^ 0x1701_1701, supplied_substrate=old.substrate
    )
    if new.status != "success" or new.body is None:
        return EmbodimentResult("failed", f"new_body:{new.reason}", False, False, False, ())

    return EmbodimentResult(
        "success",
        "bodies_reconstructed",
        exact_equivalence(base, opaque_body_to_dfa(old.body, machine))[0],
        exact_equivalence(solution, opaque_body_to_dfa(new.body, machine))[0],
        archived == old.body.to_json(),
        tuple(sorted(set(old.used_opcodes) | set(new.used_opcodes))),
    )
