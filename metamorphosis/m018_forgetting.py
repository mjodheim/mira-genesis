"""M018 — détruire pour continuer à s'améliorer.

M017 a mesuré que l'accumulation seule finit par coûter. Une bibliothèque héritée d'un
environnement aux motifs disjoints donne **0,69×** — strictement pire que pas de
bibliothèque du tout, quatre paires sur quatre. Ses macros ne s'appliquent jamais et
gonflent pourtant le facteur de branchement à chaque épisode.

Ce n'est pas propre à ce projet. C'est le **problème d'utilité**, établi dans les
années 80–90 sur les systèmes qui apprennent des macro-opérateurs : à force
d'accumuler, le système devient plus lent que s'il n'avait rien appris. Markovitch et
Scott ont montré que l'oubli sélectif n'en était pas un raffinement mais une
nécessité. La perte de plasticité en apprentissage continu raconte la même chose, et
son remède connu est de réinitialiser périodiquement les unités les moins utiles.

La chenille ne devient pas papillon en grossissant. Dans la chrysalide, l'essentiel de
son corps est dissous ; ce qui survit tient dans quelques disques imaginaux.

Trois mécanismes, du plus prudent au plus radical :

`UtilityForgetting`     — comptabilité par symbole ; on jette ceux qui n'ont jamais
                          servi passé un délai de grâce. Réactif : il faut avoir déjà
                          payé pour savoir.
`BudgetForgetting`      — plafond dur sur la bibliothèque ; admettre un symbole oblige
                          à en expulser un. La contrepartie est payée à chaque instant.
`DissolutionForgetting` — on jette périodiquement **tous** les macros et l'on affaiblit
                          de moitié les compteurs de motifs. Seul ce qui récurre encore
                          revient. Les compteurs sont les disques imaginaux : le plan
                          survit, le corps non.

Le coût d'un symbole est **uniforme** : il multiplie le facteur de branchement, quelle
que soit son utilité. C'est ce qui rend la comptabilité honnête et entière — un
symbole jamais employé est du coût pur, sans qu'aucune pondération soit nécessaire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

from .m017_language import AbstractionRule, Library, Symbol


@dataclass
class SymbolLedger:
    """Ce que l'organisme sait de ses propres symboles, sans les inspecter.

    Il ne lit pas ce que fait un macro. Il sait seulement combien de fois il a servi et
    depuis combien d'épisodes il est là. C'est exactement la contrainte du code qu'on
    ne peut pas comprendre : juger sur l'usage, jamais sur la sémantique.
    """

    uses: dict[str, int] = field(default_factory=dict)
    present_since: dict[str, int] = field(default_factory=dict)

    def register(self, symbol: Symbol, episode: int) -> None:
        self.uses.setdefault(symbol.name, 0)
        self.present_since.setdefault(symbol.name, episode)

    def credit(self, names: Sequence[str]) -> None:
        for name in names:
            self.uses[name] = self.uses.get(name, 0) + 1

    def forget(self, name: str) -> None:
        self.uses.pop(name, None)
        self.present_since.pop(name, None)

    def age(self, name: str, episode: int) -> int:
        return episode - self.present_since.get(name, episode)


class ForgettingPolicy(Protocol):
    name: str

    def after_episode(
        self, library: Library, rule: AbstractionRule, ledger: SymbolLedger, episode: int
    ) -> tuple[str, ...]: ...


def _drop(library: Library, ledger: SymbolLedger, names: set[str]) -> tuple[str, ...]:
    if not names:
        return ()
    library.symbols = [symbol for symbol in library.symbols if symbol.name not in names]
    for name in names:
        ledger.forget(name)
    return tuple(sorted(names))


@dataclass
class NoForgetting:
    """Le contrôle : l'organisme de M017, qui accumule et ne jette jamais."""

    name: str = "none"

    def after_episode(
        self, library: Library, rule: AbstractionRule, ledger: SymbolLedger, episode: int
    ) -> tuple[str, ...]:
        return ()


@dataclass
class UtilityForgetting:
    """Jeter ce qui n'a jamais servi, passé un délai de grâce.

    Le délai existe parce qu'un symbole absorbé à l'épisode n ne peut pas avoir servi
    avant. Sans lui, la règle détruirait tout ce qu'elle vient d'apprendre.
    """

    grace_period: int = 4
    name: str = "utility"

    def after_episode(
        self, library: Library, rule: AbstractionRule, ledger: SymbolLedger, episode: int
    ) -> tuple[str, ...]:
        doomed = {
            symbol.name
            for symbol in library.macros
            if ledger.age(symbol.name, episode) >= self.grace_period
            and ledger.uses.get(symbol.name, 0) == 0
        }
        return _drop(library, ledger, doomed)


@dataclass
class BudgetForgetting:
    """Plafond dur : au-delà, admettre un symbole oblige à en expulser un.

    Expulsion par usage croissant, puis par ancienneté. La contrepartie du branchement
    est ainsi payée à chaque instant plutôt que différée jusqu'à devenir un passif.
    """

    max_macros: int = 6
    name: str = "budget"

    def after_episode(
        self, library: Library, rule: AbstractionRule, ledger: SymbolLedger, episode: int
    ) -> tuple[str, ...]:
        macros = list(library.macros)
        if len(macros) <= self.max_macros:
            return ()
        ranked = sorted(
            macros,
            key=lambda symbol: (
                ledger.uses.get(symbol.name, 0),
                -ledger.age(symbol.name, episode),
                symbol.name,
            ),
        )
        doomed = {symbol.name for symbol in ranked[: len(macros) - self.max_macros]}
        return _drop(library, ledger, doomed)


@dataclass
class DissolutionForgetting:
    """La chrysalide : jeter tout le corps, garder le plan affaibli.

    Tous les macros partent. Les compteurs de motifs sont divisés par deux — division
    entière, aucun flottant n'entre dans une décision. Ce qui récurre encore repassera
    le seuil et renaîtra ; ce qui ne récurre plus ne reviendra pas.

    C'est le seul des trois mécanismes qui teste l'hypothèse dans sa forme forte, et le
    seul dont on attend qu'il **coûte** en environnement stable.
    """

    period: int = 6
    name: str = "dissolution"

    def after_episode(
        self, library: Library, rule: AbstractionRule, ledger: SymbolLedger, episode: int
    ) -> tuple[str, ...]:
        if episode == 0 or (episode + 1) % self.period != 0:
            return ()
        doomed = {symbol.name for symbol in library.macros}
        for key in list(rule.counts):
            rule.counts[key] //= 2
            if rule.counts[key] == 0:
                del rule.counts[key]
        return _drop(library, ledger, doomed)


POLICIES: tuple[ForgettingPolicy, ...] = (
    NoForgetting(),
    UtilityForgetting(),
    BudgetForgetting(),
    DissolutionForgetting(),
)
