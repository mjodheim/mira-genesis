# M019 — Statut

- Protocole : **BROUILLON DE DÉVELOPPEMENT**
- Résultats canoniques autorisés : **NON**
- Statut scientifique : `DEVELOPMENT — RIG NOT VALID, STRUCTURAL CAUSE IDENTIFIED`
- Tests de développement : **9 passants**, dans une suite de 48

## Le montage ne teste pas ce qu'il prétend tester

Trois calibrages, trois dégénérescences. La porte de gel n°1 — « la rareté doit
mordre » — n'est franchie dans aucun. Aucune conclusion n'est tirée sur l'hypothèse H8.

| Calibrage | Résultat | Morts |
|---|---|---|
| prime 25 000 | énergie doublée, `none` 8/8 | 0 |
| prime 6 000 | profondeur → 2, macros → 0 | 0 |
| prime 6 000 + report d'énergie | profondeur → 2, macros → 0 | 0 |

Population : 11 épisodes résolus. Organisme de contrôle, seul, sans sélection : **103**,
avec 18 macros.

## La cause est structurelle, pas numérique

L'invariant des trois essais : **une sélection à horizon court ne peut pas valoriser un
investissement dont le rendement est différé.**

Apprendre coûte ~23 000 nœuds pour une prime de 6 000, soit −17 000 immédiats. Ne pas
essayer coûte 1 296. À la première sélection, l'apprenti est classé sous le prudent et
éliminé — avant d'avoir résolu les trois motifs de son environnement, seul moment où
sa bibliothèque commencerait à rembourser.

Le report d'énergie ne corrige rien, parce qu'il suppose que l'investisseur survive
jusqu'à la génération suivante. Il est éliminé avant.

**La sélection a découvert que ne pas essayer coûte moins cher qu'essayer**, et elle
avait raison sur l'horizon qu'on lui a donné.

## Un garde-fou mal choisi

« Mortalité non nulle » était une mauvaise porte. Zéro mort n'y signalait pas une
rareté trop faible mais l'inverse : **elle mordait assez pour que la stratégie
gagnante soit de ne rien dépenser.** Un organisme qui cherche en profondeur 2 dépense
1 296 nœuds et ne meurt jamais.

Un garde-fou correct aurait été : *la population apprend-elle quelque chose ?*, mesuré
par le nombre de macros. Il valait zéro dans les trois essais.

## Pourquoi je m'arrête ici

Un quatrième calibrage serait de l'ajustement jusqu'à obtenir la réponse voulue —
exactement ce contre quoi la discipline du dépôt existe. Trois essais, un invariant
identifié et une cause nommée suffisent pour conclure que **le montage est faux**, et
non que l'hypothèse est réfutée.

## Ce que M019b devra changer

L'horizon d'évaluation doit dépasser la période de remboursement de l'apprentissage :

1. sélection toutes les **N générations**, pas à chaque génération ;
2. ou fitness intégrée sur la vie entière de la lignée plutôt que sur une génération ;
3. ou coût d'apprentissage amorti — la première résolution d'un motif inaugure une
   série, et une fitness qui n'en voit que le premier terme se trompe de grandeur.

La leçon dépasse ce projet : **une pression de sélection mal formée sélectionne la
stagnation.** Trop faible, elle ne trie rien ; trop impatiente, elle élimine
l'exploration avant qu'elle ne rapporte. L'horizon compte davantage que l'intensité.

C'est le même piège que M014b sous une autre forme — un critère qui mesure la mauvaise
chose ne devient pas juste en changeant ses seuils.
