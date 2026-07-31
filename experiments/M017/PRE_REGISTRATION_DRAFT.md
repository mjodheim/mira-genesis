# M017 — Préenregistrement (brouillon)

**Statut : BROUILLON. Aucun seuil n'est encore figé, aucune évaluation canonique
n'est autorisée.**

Ce document franchit la **porte de gel n°1** : désigner la comparaison qui décide de
l'expérience, avant d'observer quoi que ce soit de nouveau.

Il est rédigé après le banc de développement à trois environnements, et **avant**
l'étude de dispersion. C'est l'ordre correct : les données de développement ont le
droit d'informer la conception d'un protocole ; l'évaluation canonique, elle, devra
porter sur des cas scellés engendrés après l'existence du head immuable.

## La comparaison décisive — une seule

> **Médiane, sur les épisodes tardifs d'un environnement, du rapport apparié entre le
> coût de recherche de la recherche ouverte et celui de l'organisme auto-extensible,
> mesuré sur le même épisode.**

Le coût de recherche est le nombre de programmes évalués avant qu'une solution
confirmée soit trouvée. C'est un entier, et le rapport est exprimé en centièmes
entiers.

### Pourquoi celle-là

Les deux organismes ont **la même capacité au premier épisode** : même vocabulaire
atomique, même profondeur maximale, même budget, même politique de sondage, même jeu
de confirmation. Seule l'absorption les sépare ensuite.

La seconde moitié plutôt que la totalité : l'absorption n'a rien à absorber avant
d'avoir vu un motif deux fois. Mesurer sur l'ensemble diluerait l'effet dans une phase
où, par construction, il ne peut pas exister.

**Appariée**, parce que la première version ne l'était pas et que la mesure l'a
sanctionnée. Voir ci-dessous.

### Version rejetée, et pourquoi

La première désignation comparait deux médianes séparées : coût médian de Genesis
contre coût médian de la recherche ouverte, sur les épisodes tardifs. L'étude de
dispersion l'a réfutée.

Sur huit environnements, l'avantage allait de **2,4× à 605×**, médiane 372×. Une
amplitude de 250 entre le meilleur et le pire environnement rend tout seuil sur la
magnitude indéfendable : il passerait ou échouerait selon l'échantillon.

Le facteur de confusion a été identifié, ce n'est pas du bruit. Le coût de Genesis
est **bimodal** : environ 42 nœuds quand l'épisode tardif est un motif pur, atteint
dès la profondeur 1 par un macro absorbé ; environ 1 800 quand il porte en plus un
atome de bruit et exige la profondeur 2. Un épisode sur trois porte du bruit, et la
médiane de sept épisodes tardifs bascule d'un mode à l'autre selon le tirage.

Comparer deux organismes sur des tirages d'épisodes agrégés séparément laissait donc
la composition des épisodes décider du résultat. L'appariement supprime ce facteur au
lieu de l'espérer négligeable.

## Découverte à ne pas dissimuler : absorber a un coût

`env-90274`, épisode 9 : Genesis évalue **2 245 programmes contre 1 711** pour la
recherche ouverte. Genesis est plus lent.

La raison est structurelle. Ayant absorbé douze macros, sa bibliothèque compte 48
symboles contre 36 : son espace de profondeur 2 fait 2 304 nœuds contre 1 296.
**Chaque symbole absorbé élargit le facteur de branchement.** C'est le problème
d'utilité classique des macro-opérateurs, et il apparaît ici de lui-même.

Genesis gagne massivement en moyenne parce qu'un succès en profondeur 1 vaut bien plus
que l'inflation ; mais sur un épisode où aucun macro ne s'applique, il paye une
pénalité. Le protocole doit rapporter le nombre d'épisodes tardifs où l'organisme
auto-extensible est **plus lent**, et ce nombre est une condition d'admission, pas une
note de bas de page : une règle d'absorption qui avalerait tout finirait par se
ruiner elle-même.

## Ce qui est rapporté mais ne décide de rien

| Grandeur | Statut | Pourquoi elle ne décide pas |
|---|---|---|
| catalogue fermé, capacité de M014c | **contrôle** | Structurellement incapable : 0/42 en développement. Un seuil calé sur lui passerait trivialement et ne mesurerait que le fait, déjà connu, qu'un catalogue de douze programmes n'exprime pas une trajectoire de trois atomes. |
| épisodes résolus par le seul auto-extensible | rapporté | Gain de capacité réel, mais son ampleur dépend du budget de recherche, qui est un paramètre et non une propriété de l'organisme. |
| longueur de description médiane | rapportée | Suit mécaniquement l'absorption ; elle décrit le mécanisme plutôt qu'elle ne le teste. |
| nombre de macro-symboles absorbés | rapporté | Mesure l'activité de la règle, pas son utilité. Une règle qui absorbe tout obtiendrait le meilleur score. |
| exactitude, abstentions, réincarnation | **conditions d'admission** | Zéro faux succès, abstention sur tout contrôle négatif, corps reconstruits exacts et archive intacte. Non satisfaites, l'expérience est nulle quel que soit le coût de recherche. |

C'est la faute de M014b, prise à l'envers : un seuil calé sur une baseline qui ne
mesure pas ce que l'expérience prétend établir.

## Porte de gel n°2 — franchie

Re-mesure sur les huit mêmes environnements, avec la statistique appariée :

| | Statistique rejetée | Statistique retenue |
|---|---|---|
| minimum | 2,43× | **95,32×** |
| médiane | 372,47× | 377,20× |
| maximum | 605,38× | 620,14× |
| **amplitude** | **facteur 250** | **facteur 6,5** |
| environnements favorables | 8 / 8 | 8 / 8 |

L'appariement a divisé la dispersion par trente-huit sans déplacer la médiane. Ce
n'est pas un ajustement cosmétique : la statistique rejetée laissait la composition
des épisodes décider du résultat, celle-ci ne le peut plus.

C'est la vérification que M014b n'a jamais faite, et elle change tout : là où M014b
préenregistrait 25 % sur une fenêtre de quatre requêtes, M017 dispose d'un effet dont
le **minimum observé dépasse le seuil envisagé d'un ordre de grandeur**.

### Coût de l'absorption, mesuré

- pire épisode isolé : **0,74×** — l'organisme auto-extensible est 35 % plus lent ;
- épisodes tardifs où il est plus lent : **8 sur 49**, soit 16 % ;
- épisodes tardifs que lui seul résout : **7**.

Le problème d'utilité est donc réel mais minoritaire, et il est plus que compensé.

## Seuils proposés, et d'où ils viennent

Ils ne sont **pas** tirés de l'échantillon. Ils sont dérivés de l'arithmétique des
espaces de recherche, puis confrontés à la dispersion observée.

**Dérivation.** Un macro comprime un motif de trois atomes en un symbole. La
recherche le rencontre en profondeur 1, parmi environ 45 symboles. Sans macro, il faut
balayer la profondeur 3 sur 36 atomes, soit 46 656 trajectoires, dont environ la
moitié en médiane. Le rapport attendu est donc de l'ordre de 23 000 / 45 ≈ **500×**.

**Seuil décisif : 10×**, soit un ordre de grandeur sous la prédiction théorique, et un
ordre de grandeur sous le minimum observé de 95×. Exigé dans **chaque** environnement
scellé, jamais en moyenne.

**Garde anti-dégénérescence : test de signe.** Dans chaque environnement, l'organisme
auto-extensible doit être plus rapide sur **strictement plus de la moitié** des
épisodes tardifs appariés. Sans cette garde, une règle qui avalerait tout pourrait
satisfaire la médiane en dégradant la majorité des épisodes. Le seuil est à la moitié
parce que c'est le point neutre d'un test de signe, non parce que l'échantillon y
tient — il y est d'ailleurs large, son pire environnement étant à 33 %.

## Ce que le seuil devra respecter

Le seuil n'est **pas encore fixé**. Il ne pourra l'être qu'après l'étude de
dispersion (`scripts/run_m017_dispersion.py`), et devra satisfaire :

1. la marge retenue dépasse la dispersion observée entre environnements de
   développement — c'est exactement la vérification que M014b n'a pas faite ;
2. le critère porte sur **chaque** environnement, ou sur une majorité annoncée
   d'avance, jamais sur une moyenne globale qui masquerait un environnement défavorable ;
3. le budget de recherche et la profondeur maximale sont justifiés par l'hypothèse et
   fixés avant la mesure, pas ajustés jusqu'à produire une marge ;
4. toutes les grandeurs qui entrent dans la décision sont entières. M014b a montré
   qu'un hash de décision incorporant des flottants n'est pas reproductible d'un
   environnement à l'autre.

## Condition d'échec, énoncée d'avance

Si l'étude de dispersion montre que la dispersion entre environnements est du même
ordre que l'avantage — ou qu'un environnement au moins favorise la recherche ouverte —
alors **aucun seuil n'est défendable** et M017 devra être reconçue avant tout gel,
et non figée sur une marge choisie après coup.

Cette phrase est écrite avant de connaître le résultat.
