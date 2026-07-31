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

## Budget et profondeur — porte de gel n°3

Ces deux paramètres décident silencieusement du résultat. Ils sont donc justifiés ici
par l'hypothèse, et fixés avant toute mesure de marge.

### Le budget porte sur les pas de composition, pas sur les atomes

`max_symbols = 3` borne le nombre de **symboles composés**, non le nombre d'atomes
produits. Pour la recherche ouverte, trois symboles font trois atomes. Pour
l'organisme auto-extensible, trois symboles peuvent en faire neuf.

Cette asymétrie **est** l'hypothèse, pas un avantage concédé. Ce qu'un raisonneur
borné dépense, c'est le pas de décision : absorber un motif signifie qu'un seul pas
porte désormais plus loin. C'est l'argument classique du *chunking*. Borner les atomes
plutôt que les pas réduirait l'absorption à un simple réordonnancement de la
recherche, et l'expérience ne testerait plus la croissance du langage.

Conséquence à énoncer sans détour : sur une cible de quatre atomes, la recherche
ouverte échoue — par profondeur si on la borne à trois pas, par budget si on lui en
accorde quatre, car 36⁴ = 1 679 616 dépasse tout budget tenable. L'organisme
auto-extensible réussit parce qu'un macro comprime trois atomes en un pas. C'est
exactement l'effet mesuré, et il ne doit pas être présenté comme autre chose.

### Profondeur 3, parce que les motifs font trois atomes

La profondeur maximale est fixée à la taille des motifs de l'environnement, qui est
une propriété du banc et non un bouton de réglage.

- En deçà, la recherche ouverte serait structurellement incapable **même sur un motif
  pur** : elle deviendrait un second contrôle, et la comparaison décisive n'aurait
  plus de terme de comparaison.
- Au-delà, l'espace de profondeur 4 dépasse tout budget praticable en Python.

### Budget 200 000, choisi pour favoriser la baseline

L'espace complet de profondeur 3 sur 36 atomes compte 46 656 trajectoires. Le budget
est fixé à plus de quatre fois ce nombre, afin que la recherche ouverte ne soit
**jamais** limitée par le budget sur un motif pur : elle peut toujours achever son
balayage.

Le budget est donc réglé contre l'hypothèse testée, non pour elle. Toute abstention de
la baseline sur un motif pur signalerait une erreur d'implémentation, pas un manque de
ressources.

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

## Portes n°4 et n°5 — le transport, et ce qu'il oblige à retirer

La prédiction avait été écrite avant la mesure, dans l'en-tête de
`scripts/run_m017_transport.py`. Elle est confirmée, y compris dans sa partie
défavorable.

| Bibliothèque héritée | Gain médian sur les épisodes précoces | Paires |
|---|---|---|
| motifs **partagés** avec la cible | **118,7×** (0,90× à 261×) | 3 / 4 aident |
| motifs **disjoints** de la cible | **0,69×** (0,65× à 0,75×) | **4 / 4 nuisent** |

Une bibliothèque héritée d'un environnement aux motifs différents est **strictement
pire que pas de bibliothèque du tout**, et la mesure est serrée : 0,65 à 0,75 sur les
quatre paires. Ce n'est pas du bruit, c'est un mécanisme. Ses macros ne s'appliquent
jamais et gonflent pourtant le facteur de branchement à chaque épisode.

### Ce que M017 ne pourra donc pas revendiquer

**Le langage étendu ne se transporte pas.** Il croît *à l'intérieur* d'une
distribution de transformations, et son avantage ne suit que dans la mesure où
l'environnement d'arrivée partage cette structure. Sans structure partagée,
l'absorption est un passif net.

C'est exactement la leçon de M014b — transporter un mécanisme ne transporte pas son
avantage — retrouvée un niveau au-dessus. Elle est portée ici dans le protocole avant
tout gel, et non découverte après une évaluation canonique.

Le transport est donc **rapporté**, jamais décisif. La comparaison qui décide reste
intra-environnement, ce qui était déjà sa désignation.

### Décalage brutal de distribution — porte n°5

Un organisme ayant vécu dans un environnement reçoit ensuite les motifs d'un autre :

- coût médian avant décalage : 744 à 11 492 nœuds ;
- coût médian après décalage : 3 630 à 20 572 nœuds ;
- abstentions : **3 sur 24** ;
- faux succès : **0**.

L'organisme se dégrade sans jamais mentir : il revient au coût d'une recherche sans
macro utile, s'abstient quand le budget ne suffit plus, et n'annonce aucune solution
inexacte.

### Ce que cela ouvre pour M018

Le passif du transport a une cause nommable : l'organisme ne peut ni oublier ses
macros, ni juger qu'ils ne s'appliquent plus. Un organisme capable de diagnostiquer
que son propre langage est inadapté et de s'en défaire annulerait ce passif — c'est
précisément H6, l'auto-métamorphose, et M017 vient de produire la première mesure qui
la rend nécessaire plutôt que souhaitable.

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
