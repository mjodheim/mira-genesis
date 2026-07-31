"""M017 — Langage auto-extensible.

M014b et M014c partageaient une limite qu'aucun de leurs critères ne mesurait :
l'organisme ne pouvait exprimer que les douze programmes écrits à la main dans
`PROGRAM_LIBRARY`. Son « apprentissage » se réduisait à repondérer des compteurs
sur un catalogue fermé. Face à une cible hors de ce catalogue, il ne pouvait que
s'abstenir — jamais inventer.

M017 renverse la question. Le vocabulaire de départ ne contient que des atomes.
Tout ce qui dépasse l'atome doit être **construit** par composition, et ce que
l'organisme construit peut être **absorbé** dans sa bibliothèque sous forme de
macro-symbole, réutilisable et transportable.

Ce que ce module fournit :

- `Library` — un ensemble de symboles, atomes et macros mêlés, sérialisable ;
- `abstract` — la règle d'absorption : un motif qui se répète devient un symbole ;
- `description_length` — la longueur MDL d'une solution dans une bibliothèque donnée.

La longueur de description est la grandeur qui porte l'hypothèse. Elle a une plage
dynamique réelle, contrairement au coût en requêtes de M014b — 14 contre 14.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import itertools
import json
from typing import Iterator, Mapping, Sequence

from .structural import (
    Atom,
    all_atoms,
    atoms_from_json,
    atoms_to_json,
    canonical_atom_key,
    describe_atoms,
)


@dataclass(frozen=True)
class Symbol:
    """Une entrée de la bibliothèque : un nom, et les atomes qu'il déplie.

    Un atome est un symbole de longueur 1. Un macro-symbole en déplie plusieurs :
    c'est exactement là que se loge la compression.
    """

    name: str
    atoms: tuple[Atom, ...]
    origin: str  # "primitive" ou "abstracted"
    born_at_episode: int = 0

    @property
    def arity(self) -> int:
        return len(self.atoms)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "atoms": atoms_to_json(self.atoms),
            "origin": self.origin,
            "born_at_episode": self.born_at_episode,
        }

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "Symbol":
        return Symbol(
            name=str(data["name"]),
            atoms=atoms_from_json(data["atoms"]),  # type: ignore[arg-type]
            origin=str(data["origin"]),
            born_at_episode=int(data["born_at_episode"]),
        )


@dataclass
class Library:
    """Vocabulaire de l'organisme. Il grandit ; c'est tout l'objet de M017."""

    symbols: list[Symbol] = field(default_factory=list)

    @staticmethod
    def primitive() -> "Library":
        """Le plancher expressif : tous les atomes, aucun macro."""
        return Library([
            Symbol(f"a{index:03d}", (atom,), "primitive")
            for index, atom in enumerate(all_atoms())
        ])

    @staticmethod
    def closed(atoms: Sequence[Sequence[Atom]]) -> "Library":
        """Une bibliothèque fermée, façon M014c : des programmes tout faits, figés."""
        return Library([
            Symbol(f"p{index:03d}", tuple(group), "primitive")
            for index, group in enumerate(atoms)
        ])

    def __len__(self) -> int:
        return len(self.symbols)

    def __iter__(self) -> Iterator[Symbol]:
        return iter(self.symbols)

    @property
    def macros(self) -> tuple[Symbol, ...]:
        return tuple(symbol for symbol in self.symbols if symbol.origin == "abstracted")

    def keys(self) -> set[str]:
        return {canonical_atom_key(symbol.atoms) for symbol in self.symbols}

    def add(self, atoms: Sequence[Atom], episode: int) -> Symbol | None:
        """Absorbe un motif. None s'il est déjà exprimable en un seul symbole."""
        key = canonical_atom_key(atoms)
        if key in self.keys():
            return None
        symbol = Symbol(f"m{len(self.macros):03d}", tuple(atoms), "abstracted", episode)
        self.symbols.append(symbol)
        return symbol

    # Les symboles courts d'abord : la recherche doit rencontrer un macro avant les
    # compositions qu'il remplace, sinon l'abstraction ne rapporte rien.
    def search_order(self) -> tuple[Symbol, ...]:
        return tuple(sorted(self.symbols, key=lambda symbol: (symbol.arity, symbol.name)))

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": "m017-library/1",
                "symbols": [symbol.to_dict() for symbol in self.symbols],
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(raw: str) -> "Library":
        data = json.loads(raw)
        if data.get("version") != "m017-library/1":
            raise ValueError("unsupported M017 library")
        return Library([Symbol.from_dict(row) for row in data["symbols"]])

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def description_length(atoms: Sequence[Atom], library: Library) -> int:
    """Nombre minimal de symboles nécessaires pour écrire cette trajectoire.

    Segmentation optimale par programmation dynamique. La sémantique étant
    séquentielle, écrire un programme, c'est le découper en tranches contiguës que
    la bibliothèque sait nommer — et non choisir un sous-ensemble. Un macro de trois
    atomes fait donc tomber la longueur de trois à un, et c'est exactement la
    compression que M017 prétend mesurer.

    L'optimum est calculé, jamais approché : une heuristique gloutonne gonflerait la
    longueur des baselines et fabriquerait l'avantage qu'on cherche à mesurer.
    """
    count = len(atoms)
    if count == 0:
        return 0
    keys = [atom.to_list() for atom in atoms]
    unreachable = count + 1
    best = [0] + [unreachable] * count
    for start in range(count):
        if best[start] == unreachable:
            continue
        for symbol in library.symbols:
            end = start + symbol.arity
            if end > count:
                continue
            if keys[start:end] == [atom.to_list() for atom in symbol.atoms]:
                if best[start] + 1 < best[end]:
                    best[end] = best[start] + 1
    # Repli : sans couverture complète, les atomes seuls suffisent toujours.
    return best[count] if best[count] != unreachable else count


@dataclass
class AbstractionRule:
    """Quand un motif mérite-t-il de devenir un symbole ?

    Règle : une **tranche contiguë** d'au moins deux atomes, observée dans au moins
    `threshold` solutions distinctes, est absorbée. Contiguë, parce que la sémantique
    est séquentielle : seule une tranche a un effet indépendant de son contexte et
    peut donc être nommée sans changer ce qu'elle fait.

    Uniquement des entiers — M014b a montré qu'un hash de décision incorporant des
    flottants n'est pas reproductible d'un environnement à l'autre.
    """

    threshold: int = 2
    max_pattern_size: int = 4
    counts: dict[str, int] = field(default_factory=dict)
    solved_episodes: int = 0

    def _patterns(self, atoms: Sequence[Atom]) -> Iterator[tuple[Atom, ...]]:
        for size in range(2, min(len(atoms), self.max_pattern_size) + 1):
            for start in range(len(atoms) - size + 1):
                yield tuple(atoms[start : start + size])

    def observe(self, atoms: Sequence[Atom], library: Library, episode: int) -> tuple[Symbol, ...]:
        """Enregistre une solution et rend les symboles nouvellement absorbés.

        Chaque épisode résolu compte, y compris lorsqu'il redonne une trajectoire
        déjà vue. Une première version ignorait les solutions déjà rencontrées, pour
        éviter de gonfler les comptes ; c'était précisément supprimer le signal —
        la récurrence d'un motif à travers les épisodes **est** ce que la règle doit
        détecter. Aucun macro ne naissait jamais.
        """
        if len(atoms) < 2:
            return ()
        self.solved_episodes += 1

        known = library.keys()
        born: list[Symbol] = []
        for pattern in self._patterns(atoms):
            key = canonical_atom_key(pattern)
            self.counts[key] = self.counts.get(key, 0) + 1
            if self.counts[key] >= self.threshold and key not in known:
                symbol = library.add(pattern, episode)
                if symbol is not None:
                    born.append(symbol)
                    known.add(key)
        return tuple(born)

    def state_digest(self) -> str:
        return hashlib.sha256(
            json.dumps(sorted(self.counts.items()), separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def explain(atoms: Sequence[Atom], library: Library) -> str:
    return f"{describe_atoms(atoms)} [{description_length(atoms, library)} symbole(s)]"
