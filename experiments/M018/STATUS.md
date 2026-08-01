# M018 — Statut

- Protocole : **BROUILLON DE DÉVELOPPEMENT**
- Résultats canoniques autorisés : **NON**
- Statut scientifique : `DEVELOPMENT — HYPOTHESIS NOT SUPPORTED`
- Tests de développement : **7 passants**

## La prédiction était fausse

Elle avait été écrite avant la mesure, dans `PROTOCOL_DRAFT.md` :

> `(1)` et `(2)` réduiront le passif sans l'annuler, `(3)` l'annulera mais coûtera cher
> sur les environnements stables.

La seconde moitié tient. **La première est fausse, et c'est celle qui portait
l'hypothèse.** Aucun des trois mécanismes n'annule le passif de transport.

## Ce que la mesure dit

Trois paires d'environnements, quatre politiques. La référence est `NoForgetting`,
c'est-à-dire l'organisme de M017 qui accumule sans jamais jeter.

| | stable | décalage | transport |
|---|---|---|---|
| `budget` | **identique** | +3 % | +6 % |
| `utility` | jusqu'à 177× pire | +2 % | +4 % |
| `dissolution` | **350× pire** | −18 % | 0 % |

- **La dissolution est un désastre.** 14 898 nœuds contre 42 en environnement stable.
  Elle jette le bon avec le mauvais et ne gagne nulle part.
- **Le budget fixe est le seul sans revers** : coût strictement identique en stable, et
  quelques pour cent ailleurs. Son bénéfice reste marginal.
- **Aucun ne restaure l'amélioration.** Le passif de 0,69× mesuré par M017 survit.

## Pourquoi, et c'est le résultat utile

Trois raisons, dans l'ordre d'importance :

1. **L'oubli est réactif.** Le coût d'un symbole inutile est payé d'avance, à chaque
   épisode, sur chaque nœud de recherche. Quand l'organisme sait enfin qu'un macro ne
   sert pas, il l'a déjà financé. Jeter ensuite ne rembourse rien.
2. **La destruction est indiscriminée.** La dissolution ne distingue pas ce qui a cessé
   de servir de ce qui va resservir, et paye 350× pour cette ignorance.
3. **Le coût d'un macro inutile est réel mais modeste.** Le facteur de branchement
   passe de 36 à environ 48 symboles ; les recherches s'arrêtent souvent tôt. Il n'y a
   pas 45 % à récupérer par simple suppression.

## Ce que ça réoriente

Le problème n'est pas que l'organisme ne sait pas détruire. C'est que **chaque symbole
est disponible sans condition, à chaque pas**.

Le remède indiqué par la mesure n'est pas la suppression mais la **sélection au moment
de l'emploi** : prédire à bas coût si un macro peut s'appliquer à cette source-ci avant
de l'étendre. Ce n'est pas de l'oubli, c'est de l'activation conditionnelle — et cela
ne détruit rien, donc cela ne coûte rien en régime stable.

C'est aussi là que la métaphore de la chenille montre sa limite. Elle se dissout parce
qu'elle construit un autre corps **une fois**. Un organisme qui affronte des
distributions changeantes à répétition ne peut pas se dissoudre à chaque fois : il doit
contextualiser, pas détruire.

## Prochaine porte

Implémenter le mécanisme de garde et le mesurer sur les trois mêmes régimes, contre les
quatre politiques déjà en place. Le banc existe, il suffit d'y ajouter une cinquième
colonne.
