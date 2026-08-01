"""M019 — pression de sélection.

Ce que l'évolution a et que Genesis n'avait pas : **la rareté**.

Jusqu'ici, un épisode était posé, l'organisme le résolvait ou s'abstenait, et rien ne
s'ensuivait. Le budget de recherche valait 200 000 nœuds, délibérément généreux, et le
dépasser coûtait une abstention sans conséquence. C'est pourquoi les trois mécanismes
d'oubli de M018 n'ont rien rapporté : **il n'y avait rien pour quoi être efficace.**
Un organisme qui ne peut pas mourir de son inefficacité n'a aucune raison de devenir
efficace. L'évolution n'est pas un moteur de variation, c'est un moteur de filtrage
sous contrainte ; sans la contrainte, la variation est de la dérive.

Deuxième absence, révélée par l'échec de la dissolution : **la population**. La chenille
se dissout une fois, et si cela échoue, cette chenille meurt — pas l'espèce. Notre
organisme était seul, donc une stratégie ruineuse dans neuf cas sur dix et géniale dans
le dixième lui était interdite. Le résultat négatif de M018 ne dit pas que détruire est
inutile : il dit que **détruire est intenable pour un individu isolé**.

Troisième absence : la variation ne portait jamais sur l'**encodage**. L'évolution
duplique un gène puis en laisse diverger la copie ; Genesis absorbait des motifs sans
jamais dupliquer un symbole pour en faire dériver une variante.

Ici, l'énergie **est** le budget de recherche. Un organisme appauvri cherche moins
loin, résout moins, s'appauvrit davantage. C'est une spirale de famine, et c'est
exactement ce qui donne un enjeu à l'efficacité.

Tout est entier. D010 : aucun flottant n'entre dans une décision.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import random
from typing import Sequence

from .m017_language import Library, Symbol
from .m018_forgetting import (
    BudgetForgetting,
    DissolutionForgetting,
    ForgettingPolicy,
    NoForgetting,
    UtilityForgetting,
)
from .structural import Atom, all_atoms, canonical_atom_key

FORGET_KINDS: tuple[str, ...] = ("none", "utility", "budget", "dissolution")


@dataclass(frozen=True)
class Genome:
    """Ce qui se transmet et ce qui mute. Rien d'autre n'est héritable.

    Le vocabulaire atomique n'y figure pas : M019 ne teste pas l'invention de
    primitives, mais la sélection sur la manière de s'en servir.
    """

    max_symbols: int
    abstraction_threshold: int
    forget_kind: str
    forget_parameter: int

    @staticmethod
    def seed(rng: random.Random) -> "Genome":
        return Genome(
            max_symbols=rng.choice((2, 3)),
            abstraction_threshold=rng.choice((2, 3, 4)),
            forget_kind=rng.choice(FORGET_KINDS),
            forget_parameter=rng.choice((3, 4, 6, 8)),
        )

    def policy(self) -> ForgettingPolicy:
        if self.forget_kind == "utility":
            return UtilityForgetting(grace_period=self.forget_parameter)
        if self.forget_kind == "budget":
            return BudgetForgetting(max_macros=self.forget_parameter)
        if self.forget_kind == "dissolution":
            return DissolutionForgetting(period=self.forget_parameter)
        return NoForgetting()

    def mutate(self, rng: random.Random) -> "Genome":
        field = rng.choice(("max_symbols", "abstraction_threshold", "forget_kind", "forget_parameter"))
        if field == "max_symbols":
            return replace(self, max_symbols=max(2, min(3, self.max_symbols + rng.choice((-1, 1)))))
        if field == "abstraction_threshold":
            return replace(
                self,
                abstraction_threshold=max(2, min(5, self.abstraction_threshold + rng.choice((-1, 1)))),
            )
        if field == "forget_kind":
            return replace(self, forget_kind=rng.choice(FORGET_KINDS))
        return replace(
            self, forget_parameter=max(2, min(12, self.forget_parameter + rng.choice((-2, -1, 1, 2))))
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "max_symbols": self.max_symbols,
            "abstraction_threshold": self.abstraction_threshold,
            "forget_kind": self.forget_kind,
            "forget_parameter": self.forget_parameter,
        }


def duplicate_and_diverge(library: Library, rng: random.Random) -> Symbol | None:
    """Duplication puis divergence — l'opérateur que Genesis n'avait pas.

    L'évolution copie un gène et laisse la copie dériver, ce qui produit une structure
    nouvelle sans détruire l'ancienne. Genesis absorbait des motifs récurrents mais ne
    dupliquait jamais un symbole pour en faire varier une version.

    Un atome de la copie est remplacé ; si la variante existe déjà, rien n'est ajouté.
    """
    macros = library.macros
    if not macros:
        return None
    source = macros[rng.randrange(len(macros))]
    atoms: list[Atom] = list(source.atoms)
    atoms[rng.randrange(len(atoms))] = rng.choice(all_atoms())
    if canonical_atom_key(atoms) in library.keys():
        return None
    return library.add(atoms, episode=-1)


@dataclass
class Ledger:
    """Comptabilité vitale d'un organisme. Énergie et budget de recherche confondus.

    Un organisme appauvri cherche moins loin, donc résout moins, donc s'appauvrit
    davantage. La spirale est voulue : c'est elle qui fait de l'efficacité un enjeu de
    survie plutôt qu'une élégance.
    """

    energy: int
    reward: int
    ceiling: int
    solved: int = 0
    abstained: int = 0
    spent: int = 0
    born_at_generation: int = 0

    @property
    def alive(self) -> bool:
        return self.energy > 0

    def budget(self) -> int:
        return max(1, min(self.ceiling, self.energy))

    def settle(self, nodes: int, solved: bool) -> None:
        self.spent += nodes
        self.energy -= nodes
        if solved:
            self.energy += self.reward
            self.solved += 1
        else:
            self.abstained += 1


def summarise_population(genomes: Sequence[Genome]) -> dict[str, int]:
    """Ce que la sélection a retenu, lisible d'un coup d'œil."""
    counts = {f"kind_{kind}": 0 for kind in FORGET_KINDS}
    for genome in genomes:
        counts[f"kind_{genome.forget_kind}"] += 1
    return counts
