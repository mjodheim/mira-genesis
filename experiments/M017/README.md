# M017 — Langage auto-extensible

## Pourquoi cette expérience passe devant les autres

La feuille de route plaçait M017 en sixième position, après la mémoire (M015) et la
compétence sensorimotrice (M016). **L'ordre était faux, pas les noms.**

M012b, M013e, M014b et M014c partagent une limite qu'aucun de leurs critères ne
mesurait : l'organisme ne peut exprimer que ce qui lui a été écrit à la main. Dans
`m014c_meta.py`, `MetaPlasticitySession.identify` énumère strictement
`passport.programs` — douze programmes. Tout l'« apprentissage » consiste à
repondérer des compteurs de groupe sur ce catalogue fermé. Face à une cible qui n'y
figure pas, l'organisme ne peut que s'abstenir : jamais inventer.

Ajouter la mémoire ou la sensorimotricité à cet organisme aurait étendu latéralement
un paradigme dont le cœur n'est pas établi. M017 attaque ce cœur.

## La question

Un organisme dont le vocabulaire de départ ne contient que des atomes peut-il
**absorber** les compositions récurrentes de son environnement, et en tirer un
pouvoir expressif et un coût de recherche que ses jumeaux n'ont pas ?

## Les trois organismes

| | Catalogue | Compose | Absorbe |
|---|---|---|---|
| `ClosedLibraryOrganism` | 12 programmes figés | non | non |
| `OpenSearchOrganism` | 36 atomes | jusqu'à 3 | non |
| `SelfExtendingOrganism` | 36 atomes, puis davantage | jusqu'à 3 | **oui** |

Le premier reproduit exactement la capacité de M014c. Son incapacité est
**structurelle**, pas une lenteur : c'est ce qui donne à M017 une taille d'effet que
M014b n'a jamais pu obtenir.

## Ce que M017 corrige dans la méthode

M014b comparait 14 requêtes à 14 requêtes, sur une fenêtre large de quatre requêtes.
Aucun critère ne pouvait y séparer le signal du bruit d'échantillonnage.

M017 mesure le **nombre de programmes évalués avant de trouver**, qui va de l'unité à
la centaine de milliers. Le coût d'oracle, lui, est rendu délibérément constant entre
les trois organismes : même sondage, même confirmation. Il ne peut donc pas confondre
la comparaison.

## Statut

Développement. Aucune évaluation canonique n'est autorisée : voir
[`STATUS.md`](STATUS.md) et [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md).
