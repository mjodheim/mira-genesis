# M018 — Dissolution

## Pourquoi

M017 a mesuré que l'accumulation seule finit par coûter. Une bibliothèque héritée d'un
environnement aux motifs disjoints donne **0,69×** — strictement pire que pas de
bibliothèque du tout, quatre paires sur quatre. Ses macros ne s'appliquent jamais et
gonflent pourtant le facteur de branchement à chaque épisode.

Le projet n'a jamais donné à un organisme le droit de **détruire** ce qu'il a appris.
Depuis M012b, tout va dans un sens : absorber, transporter, accumuler. M018 ouvre
l'autre sens.

## Ce que ce n'est pas

Ce n'est pas une découverte du projet. Le **problème d'utilité** est établi depuis les
années 80–90 sur les systèmes qui apprennent des macro-opérateurs : à force
d'accumuler, le système devient plus lent que s'il n'avait rien appris, et Markovitch
et Scott ont montré que l'oubli sélectif en était une nécessité, non un raffinement.
La perte de plasticité en apprentissage continu raconte la même chose, et son remède
connu est de réinitialiser périodiquement les unités les moins utiles.

Ce que M018 apporte n'est pas l'idée, c'est le **domaine décidable**. On peut prouver
l'équivalence exacte, compter les nœuds explorés, isoler l'effet. Sur la question
« faut-il détruire pour continuer à s'améliorer », on peut produire un résultat exact
là où la littérature produit des courbes.

## Les trois mécanismes

| | Ce qu'il fait | Ce qu'il coûte |
|---|---|---|
| `UtilityForgetting` | jette les symboles jamais employés, passé un délai de grâce | réactif : il faut avoir déjà payé pour savoir |
| `BudgetForgetting` | plafond dur ; admettre oblige à expulser | la contrepartie est payée à chaque instant |
| `DissolutionForgetting` | jette **tous** les macros, affaiblit de moitié les compteurs | le plus radical, et le seul dont on attend qu'il coûte |

Le contrôle est `NoForgetting` — l'organisme de M017, qui accumule et ne jette jamais.

## La contrainte qui rend le problème difficile

L'organisme **ne lit jamais ce que fait un macro**. Il ne connaît que son nombre
d'usages et son âge. C'est délibéré, et c'est la contrainte exacte d'un organisme qui
manipule du code que personne ne comprend : juger sur l'usage, jamais sur la
sémantique.

Le coût d'un symbole est **uniforme** — il multiplie le facteur de branchement quelle
que soit son utilité. C'est ce qui rend la comptabilité honnête et entière : un
symbole jamais employé est du coût pur, sans qu'aucune pondération soit nécessaire.

## La chenille

Dans la chrysalide, l'essentiel du corps de la chenille est dissous. Ce qui survit
tient dans quelques disques imaginaux — et, expérimentalement, une partie de la
mémoire apprise.

`DissolutionForgetting` copie cette structure : les macros — le corps — partent tous ;
les compteurs de motifs — le plan — survivent, divisés par deux. Ce qui récurre encore
repassera le seuil et renaîtra ; ce qui ne récurre plus ne reviendra pas.

**Là où la métaphore s'arrête :** le plan du papillon est dans le génome, spécifié
d'avance. Le projet a déjà fait ça — c'est M012b, construire un corps depuis un
contrat donné. Ce que M018 vise est plus dur qu'une métamorphose biologique : que
l'organisme choisisse la forme que personne n'a écrite.

## Statut

Développement. Voir [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) et [`STATUS.md`](STATUS.md).
