# M019 — Pression de sélection

## Ce qui manquait

L'évolution n'est pas un moteur de variation. C'est un moteur de **filtrage sous
contrainte**. Sans la contrainte, la variation est de la dérive.

Jusqu'à M018, Genesis n'avait aucun enjeu. On lui posait un épisode, elle le résolvait
ou s'abstenait, et rien ne s'ensuivait. Le budget de recherche valait 200 000 nœuds,
délibérément généreux, et le dépasser coûtait une abstention sans conséquence.

C'est l'explication du résultat négatif de M018 : les trois mécanismes d'oubli n'ont
rien rapporté parce qu'**il n'y avait rien pour quoi être efficace**. Un organisme qui
ne peut pas mourir de son inefficacité n'a aucune raison de devenir efficace.

## Trois absences, trois ajouts

| | Ce que l'évolution a | Ce que Genesis avait |
|---|---|---|
| **Rareté** | mourir de faim | budget généreux, échec sans conséquence |
| **Population** | la lignée survit à l'individu | un organisme seul |
| **Variation sur l'encodage** | duplication de gène puis divergence | absorption de motifs récurrents seulement |

### La rareté

L'énergie **est** le budget de recherche. Un organisme appauvri cherche moins loin,
donc résout moins, donc s'appauvrit davantage. La spirale de famine est voulue : c'est
elle qui fait de l'efficacité un enjeu de survie plutôt qu'une élégance.

Le classement porte sur l'**énergie restante**, c'est-à-dire ce qui reste après avoir
payé ses recherches. Résoudre cher n'y vaut pas mieux que ne pas résoudre.

### La population

La chenille se dissout une fois, et si cela échoue, cette chenille meurt — pas
l'espèce. L'organisme de M018 était seul, donc une stratégie ruineuse dans neuf cas sur
dix et géniale dans le dixième lui était interdite.

Relu ainsi, le résultat négatif de M018 ne dit pas que détruire est inutile : il dit
que **détruire est intenable pour un individu isolé**. Ce n'est pas la même chose, et
la seconde lecture ouvre une porte que la première fermait.

### La duplication

L'évolution copie un gène et laisse la copie dériver, ce qui produit une structure
nouvelle sans détruire l'ancienne. Genesis absorbait des motifs récurrents mais ne
dupliquait jamais un symbole pour en faire varier une version. `duplicate_and_diverge`
comble ce manque.

## La question que cela permet enfin de poser

> Une population sous sélection découvre-t-elle ce que je n'ai pas su concevoir ?

M018 a montré que trois mécanismes d'oubli écrits à la main ne payaient pas. Ici,
personne ne choisit : les quatre sont présents dans la population de départ et la
sélection tranche. Si elle converge vers un réglage qu'aucune de mes heuristiques
n'atteignait, le projet tient pour la première fois **une amélioration que personne n'a
écrite**.

## Notre avantage sur l'évolution

L'évolution est lente pour deux raisons : sa variation est **aveugle**, et sa fitness
se mesure en générations. Ici la variation peut être dirigée, et la fitness se calcule
exactement et instantanément puisque le domaine est décidable.

C'est le seul endroit où la petitesse du domaine devient un atout plutôt qu'un plafond.

## Statut

Développement. Voir [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) et [`STATUS.md`](STATUS.md).
