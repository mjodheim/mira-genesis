"""M019 — la population et sa sélection.

Un organisme n'est plus seul et n'a plus de budget garanti. Il dispose d'une énergie
qui est aussi son budget de recherche, la dépense à chaque épisode, en regagne en
résolvant, et meurt quand elle s'épuise.

À la fin d'une génération, la moitié la moins riche est remplacée par des copies mutées
de la moitié la plus riche. C'est le seul endroit du projet où quelque chose est
véritablement sélectionné plutôt que conçu.

La question que cela permet enfin de poser : **une population sous sélection
découvre-t-elle ce que je n'ai pas su concevoir ?** M018 a montré que trois mécanismes
d'oubli écrits à la main ne payaient pas. Si la sélection converge d'elle-même vers l'un
d'eux, ou vers un réglage qu'aucune de mes heuristiques n'atteignait, alors le projet
tient pour la première fois une amélioration que personne n'a écrite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Callable, Sequence

from .m012b_dfa import DFA
from .m017_engine import BehavioralOracle
from .m017_language import Library
from .m018_engine import ForgettingOrganism
from .m019_selection import Genome, Ledger, duplicate_and_diverge


@dataclass(frozen=True)
class Case:
    """Un épisode tel que l'organisme le rencontre, et la vérification de l'évaluateur.

    L'oracle est **fourni**, jamais fabriqué ici : `BehavioralOracle` est un protocole,
    et un moteur qui instancierait celui du laboratoire ne serait plus isolé de lui.
    Chaque organisme reçoit son propre oracle, sans quoi ils partageraient un compteur
    d'appels.

    `verify` appartient à l'évaluateur : elle décide si une solution annoncée est
    exactement équivalente. Un faux succès y est fatal, comme partout ailleurs.
    """

    base: DFA
    make_oracle: Callable[[], BehavioralOracle]
    verify: Callable[[DFA], bool]


@dataclass
class Individual:
    """Un organisme, son génome et sa comptabilité vitale."""

    genome: Genome
    ledger: Ledger
    organism: ForgettingOrganism
    lineage: str

    @staticmethod
    def born(
        genome: Genome,
        lineage: str,
        *,
        energy: int,
        reward: int,
        ceiling: int,
        generation: int = 0,
        library: Library | None = None,
    ) -> "Individual":
        organism = ForgettingOrganism(
            policy=genome.policy(),
            max_symbols=genome.max_symbols,
            search_budget=ceiling,
            threshold=genome.abstraction_threshold,
            library=library,
        )
        ledger = Ledger(
            energy=energy, reward=reward, ceiling=ceiling, born_at_generation=generation
        )
        return Individual(genome, ledger, organism, lineage)

    def live(self, case: Case) -> int:
        """Un épisode. Rend les nœuds dépensés. La mort n'est pas rattrapable."""
        if not self.ledger.alive:
            return 0
        # Le budget de recherche est l'énergie : un organisme appauvri cherche moins loin.
        self.organism.search_budget = self.ledger.budget()
        result = self.organism.solve(case.base, case.make_oracle())
        solved = result.status == "success"
        if solved:
            assert result.solution is not None
            assert case.verify(result.solution), "faux succès"
        self.ledger.settle(result.search_nodes, solved)
        return result.search_nodes

    def offspring(
        self, lineage: str, rng: random.Random, generation: int, energy: int
    ) -> "Individual":
        """Descendant : génome muté, bibliothèque héritée puis divergée.

        La bibliothèque se transmet, ce qui rend l'hérédité culturelle possible ; mais
        M017 a mesuré qu'une bibliothèque inadaptée est un passif de 0,69×. La
        transmettre est donc un pari, et c'est précisément ce que la sélection doit
        arbitrer plutôt que moi.
        """
        inherited = Library.from_json(self.organism.export_library())
        duplicate_and_diverge(inherited, rng)
        return Individual.born(
            self.genome.mutate(rng),
            lineage,
            energy=energy,
            reward=self.ledger.reward,
            ceiling=self.ledger.ceiling,
            generation=generation,
            library=inherited,
        )


@dataclass
class Population:
    individuals: list[Individual] = field(default_factory=list)
    generation: int = 0
    deaths: int = 0
    history: list[dict[str, object]] = field(default_factory=list)

    @staticmethod
    def seed(
        size: int, seed: int, *, energy: int, reward: int, ceiling: int
    ) -> "Population":
        rng = random.Random(seed)
        return Population(
            [
                Individual.born(
                    Genome.seed(rng), f"g0-{index}", energy=energy, reward=reward, ceiling=ceiling
                )
                for index in range(size)
            ]
        )

    @property
    def alive(self) -> list[Individual]:
        return [individual for individual in self.individuals if individual.ledger.alive]

    def live_generation(self, cases: Sequence[Case]) -> None:
        for case in cases:
            for individual in self.individuals:
                individual.live(case)

    def select(self, rng: random.Random, starting_energy: int) -> None:
        """Les riches se reproduisent, les pauvres sont remplacés.

        Le classement est par énergie restante, c'est-à-dire par ce qu'il reste après
        avoir payé ses recherches — donc par efficacité réelle, pas par nombre de
        succès. Résoudre cher ne vaut pas mieux que ne pas résoudre.

        **L'énergie n'est pas remise à niveau entre générations**, et cette décision a
        été renversée après mesure. Une première version la réinitialisait, au motif
        raisonnable qu'on sélectionne une stratégie et non une avance accumulée. C'était
        rendre tout investissement invisible : apprendre coûte cher immédiatement et ne
        rapporte qu'aux épisodes suivants, si bien que l'apprenti était classé sous le
        prudent et éliminé avant d'avoir pu transmettre sa bibliothèque. La population
        convergeait vers une profondeur de recherche de 2 et zéro macro — la sélection
        avait découvert que **ne pas essayer coûte moins cher qu'essayer**.

        L'énergie est donc reportée, mais plafonnée : sans plafond, la richesse
        composerait et le classement ne mesurerait plus qu'une chance initiale.
        """
        survivors = sorted(self.alive, key=lambda i: (-i.ledger.energy, i.lineage))
        self.deaths += len(self.individuals) - len(survivors)
        if not survivors:
            self.individuals = []
            return

        keep = survivors[: max(1, len(self.individuals) // 2)]
        self.generation += 1
        children = [
            keep[index % len(keep)].offspring(
                f"g{self.generation}-{index}", rng, self.generation, starting_energy
            )
            for index in range(len(self.individuals) - len(keep))
        ]
        # Les survivants gardent leur énergie, plafonnée au double de la dotation :
        # un investissement reste visible d'une génération à l'autre, sans que la
        # richesse compose indéfiniment.
        for individual in keep:
            individual.ledger.energy = min(individual.ledger.energy, 2 * starting_energy)
        self.individuals = keep + children

    def snapshot(self) -> dict[str, object]:
        living = self.alive
        return {
            "generation": self.generation,
            "alive": len(living),
            "deaths_total": self.deaths,
            "solved_total": sum(i.ledger.solved for i in self.individuals),
            "abstained_total": sum(i.ledger.abstained for i in self.individuals),
            "spent_total": sum(i.ledger.spent for i in self.individuals),
            "best_energy": max((i.ledger.energy for i in living), default=0),
            "genomes": [i.genome.to_dict() for i in living],
            "macros": [len(i.organism.library.macros) for i in living],
        }
