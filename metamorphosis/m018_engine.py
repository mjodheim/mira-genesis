"""M018 — l'organisme qui peut se défaire de ce qu'il a appris.

Un seul ajout par rapport à M017 : après chaque épisode résolu, l'organisme crédite
les symboles qu'il vient d'employer, puis laisse sa politique d'oubli jeter ce qui ne
porte plus.

Il ne lit jamais ce que fait un macro. Il ne connaît que son usage et son âge — la
contrainte exacte d'un organisme qui manipule du code que personne ne comprend.
"""

from __future__ import annotations

from typing import Sequence

from .m017_engine import SelfExtendingOrganism
from .m017_language import Library, Symbol
from .m018_forgetting import ForgettingPolicy, NoForgetting, SymbolLedger
from .structural import Atom


class ForgettingOrganism(SelfExtendingOrganism):
    def __init__(
        self,
        policy: ForgettingPolicy | None = None,
        max_symbols: int = 3,
        search_budget: int = 200_000,
        threshold: int = 2,
        library: Library | None = None,
    ) -> None:
        super().__init__(
            max_symbols=max_symbols,
            search_budget=search_budget,
            threshold=threshold,
            library=library,
        )
        self.policy: ForgettingPolicy = policy or NoForgetting()
        self.ledger = SymbolLedger()
        self.discarded: list[str] = []
        # Une bibliothèque héritée entre au registre comme si elle venait de naître :
        # ses symboles n'ont encore rien prouvé ici, et c'est précisément la situation
        # où M017 a mesuré un passif de 0,69×.
        for symbol in self.library.macros:
            self.ledger.register(symbol, 0)

    def _absorb(
        self, atoms: Sequence[Atom], symbols: Sequence[Symbol]
    ) -> tuple[str, ...]:
        born = super()._absorb(atoms, symbols)
        for symbol in self.library.macros:
            self.ledger.register(symbol, self.episode)
        self.ledger.credit([symbol.name for symbol in symbols if symbol.arity > 1])
        dropped = self.policy.after_episode(
            self.library, self.rule, self.ledger, self.episode
        )
        self.discarded.extend(dropped)
        return born

    @property
    def macro_count(self) -> int:
        return len(self.library.macros)
