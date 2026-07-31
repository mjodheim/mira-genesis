# M017 — Protocole de développement (brouillon)

**Statut : BROUILLON — évaluation canonique interdite.**

## Hypothèse

Dans un environnement dont la structure compositionnelle se répète, un organisme qui
absorbe ses motifs récurrents dans son vocabulaire acquiert un pouvoir expressif qu'il
n'avait pas, et voit son coût de recherche s'effondrer. Un organisme à catalogue fermé
ne peut pas le suivre, et un organisme qui compose sans jamais absorber ne s'améliore
pas avec le temps.

La récurrence des motifs est la **prémisse déclarée** de l'hypothèse, pas un artefact
commode : elle est posée dans `m017_lab.py`, pas dissimulée dans un générateur.

## Le langage

- 4 rôles structurels, 36 atomes : `flip <rôle>` et `redirect <rôle> <symbole> <rôle>` ;
- sémantique **séquentielle** : chaque atome résout ses rôles sur l'automate laissé
  par le précédent ;
- un programme est une trajectoire ; un macro-symbole est une tranche contiguë ;
- profondeur 3 : 46 656 trajectoires. Profondeur 4 : 1,7 million, hors budget.

## Quatre décisions de conception, et la mesure qui les impose

Chacune a été prise après échec mesuré. Elles sont consignées ici pour qu'aucune ne
puisse être défaite sans refaire la mesure.

1. **Sémantique séquentielle plutôt que rôles résolus sur la source.**
   En résolution unique, un programme se réduit à des éditions indépendantes sur
   quelques états : **5 motifs de 3 atomes sur 8 avaient un équivalent exact en
   ≤ 2 atomes**, 3 d'entre eux en un seul. La composition n'apportait rien.
   En séquentiel : **1 sur 8**.

2. **Confirmation stricte, sur des mots longs.**
   Une confirmation limitée aux mots de longueur 6 laissait passer, sur des automates
   de 6 à 9 états, des trajectoires de 2 atomes qui approchent la cible sans l'égaler.
   La recherche s'arrêtait sur une approximation, aucun motif ne se répétait, et
   l'abstraction n'avait rien à absorber.

3. **Motifs irréductibles, filtrés à la construction de l'environnement.**
   Sur des motifs tirés au hasard, **35 épisodes sur 40** admettaient une trajectoire
   plus courte et le motif n'était jamais retrouvé. La réductibilité est une propriété
   du motif, pas de la source. Une première version filtrait chaque épisode en exigeant
   l'unicité de la trajectoire minimale : trop stricte, presque aucun épisode ne
   passait. La condition retenue est celle qui porte la mesure — qu'une recherche de
   référence retrouve le motif — et non une propriété plus forte dont l'expérience
   n'a pas besoin.

4. **Chaque épisode résolu compte, même s'il redonne une trajectoire déjà vue.**
   Une première règle d'abstraction ignorait les solutions déjà rencontrées pour ne pas
   gonfler ses compteurs. C'était supprimer le signal : la récurrence d'un motif à
   travers les épisodes **est** ce que la règle doit détecter. Aucun macro ne naissait.

## Baselines

- catalogue fermé — la capacité de M014c, reproduite telle quelle ;
- recherche ouverte sans absorption — capable, mais son coût ne décroît pas ;
- plafond oracle : le motif vrai, fourni au même moteur de réincarnation.

## Résultat de développement observé

Trois environnements, 14 épisodes chacun, 42 au total :

| | résolus | nœuds médians, 1re moitié | 2de moitié |
|---|---|---|---|
| catalogue fermé | **0 / 42** | — | — |
| recherche ouverte | 34 / 42 | 7 154 | 8 545 |
| auto-extensible | **37 / 42** | 4 222 | **43** |

- 3 épisodes résolus par le seul organisme auto-extensible, 0 dans l'autre sens ;
- 24 macro-symboles absorbés ; longueur de description médiane 2 contre 3 ;
- 9/9 réincarnations exactes sur trois familles de machines opaques, archive intacte ;
- 4/4 abstentions sur les contrôles négatifs ;
- **0 faux succès** : toute solution annoncée est exactement équivalente.

Le coût de recherche s'effondre d'un facteur cent pour l'organisme qui étend son
langage, et reste plat pour celui qui ne l'étend pas. C'est la comparaison qui porte
l'hypothèse, et elle est mesurée sur une plage de quatre ordres de grandeur.

## Portes de gel

Le protocole ne pourra être figé qu'après :

1. ~~la désignation de la comparaison unique qui décide de l'expérience~~ —
   **franchie**, voir [`PRE_REGISTRATION_DRAFT.md`](PRE_REGISTRATION_DRAFT.md) :
   coût de recherche médian sur la seconde moitié des épisodes, auto-extensible
   contre recherche ouverte, par environnement. Le statut simplement rapporté des
   autres grandeurs y est justifié, et la condition d'échec y est écrite d'avance ;
2. l'établissement que la marge retenue dépasse la dispersion entre environnements,
   au lieu de le supposer. **M014b a échoué exactement là.** Mesure en cours via
   `scripts/run_m017_dispersion.py` ;
3. la vérification que le budget de recherche et la profondeur maximale découlent de
   l'hypothèse, et non de la marge qu'ils produisent ;
4. le transport de la bibliothèque étendue vers un environnement scellé aux motifs
   inédits, pour vérifier qu'elle confère encore un avantage — la leçon de M014b ;
5. l'extension des contrôles négatifs aux motifs adverses et aux environnements dont
   la distribution change brutalement après absorption ;
6. un audit d'isolation des sources et une trace de décision entièrement entière.

Les cas canoniques ne seront engendrés qu'après l'existence du head scellé immuable.

## Ce que M017 ne prétendra pas

Le langage reste borné : quatre rôles, deux formes d'atome, un domaine booléen fini.
Un organisme qui absorbe des tranches de son propre langage n'invente pas de rôle
nouveau, ne change pas de domaine et ne se choisit pas un corps. M017 est la première
marche vers H6, pas H6.
