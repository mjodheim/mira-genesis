# M019 — Statut

- Protocole : **BROUILLON DE DÉVELOPPEMENT**
- Résultats canoniques autorisés : **NON**
- Statut scientifique : `DEVELOPMENT — RIG CALIBRATION`
- Tests de développement : **9 passants**

## Deux dégénérescences opposées, et ce qu'elles apprennent

Concevoir une pression de sélection s'est révélé plus difficile que concevoir
l'organisme. Deux montages ont échoué, dans des directions contraires, et chacun a été
diagnostiqué par une condition écrite avant la mesure.

### Prime trop forte — rien ne mord

Prime 25 000, dotation 150 000. **Zéro mort, énergie doublée, `none` vainqueur 8/8.**

Une prime très supérieure au coût d'une résolution bon marché rend toute bibliothèque,
même encombrée, sans conséquence. La condition d'invalidation était préenregistrée :
« si `none` domine, c'est que la rareté n'est pas assez mordante ». Le diagnostic est
objectif — une population qui ne perd personne et double son énergie n'est pas sous
contrainte.

### Prime trop faible — la sélection élimine l'apprentissage

Prime 6 000. La population converge vers une profondeur de recherche de **2** et
**zéro macro**, résolvant 6 épisodes ; l'organisme de contrôle, lui, en résout **103**
et construit 18 macros.

**La sélection a découvert que ne pas essayer coûte moins cher qu'essayer.** Une
résolution en profondeur 3 coûte ~23 000 nœuds pour une prime de 6 000 : apprendre fait
perdre 17 000. S'abstenir en profondeur 2 n'en coûte que 1 296. Elle a sélectionné la
prudence stérile.

### La cause n'était pas le nombre

C'était une décision de conception, prise pour une bonne raison apparente :
réinitialiser l'énergie des survivants à chaque génération, « pour sélectionner une
stratégie et non une avance accumulée ».

Cela rendait **tout investissement invisible**. Apprendre coûte immédiatement et ne
rapporte qu'aux épisodes suivants ; l'apprenti était donc classé sous le prudent et
éliminé avant d'avoir transmis sa bibliothèque. Une fonction de fitness qui n'évalue
qu'une génération ne peut pas valoriser un investissement, quel que soit le montant de
la prime.

L'énergie est désormais **reportée d'une génération à l'autre**, plafonnée au double de
la dotation pour que la richesse ne compose pas indéfiniment.

## Ce que ces échecs valent

Ils ne sont pas du bruit de mise au point. Ils cernent une difficulté réelle, et qui
dépasse ce projet : **une pression de sélection mal formée sélectionne la stagnation.**

- trop faible, elle ne trie rien ;
- trop forte sur l'horizon court, elle élimine l'exploration avant qu'elle ne rapporte ;
- et l'horizon d'évaluation compte davantage que l'intensité de la pression.

C'est exactement le piège que M014b avait rencontré sous une autre forme — un critère
qui mesure la mauvaise chose ne devient pas juste en changeant ses seuils.

## Prochaine porte

Vérifier que la troisième version fait mordre la rareté **sans** éliminer
l'apprentissage : mortalité non nulle, macros non nuls, et une composition finale de
population qui diffère de sa composition initiale de façon reproductible sur plusieurs
lignées.

Tant que ces trois conditions ne tiennent pas ensemble, M019 ne mesure pas ce qu'elle
prétend mesurer et aucune conclusion n'en sera tirée.
