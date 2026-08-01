# Registre des mesures

Ce registre est le second actif du dépôt, à côté de [`FAILURE_LOG.md`](FAILURE_LOG.md).
Il catalogue les **mesures qui ont divergé de ce qu'elles prétendaient mesurer**, dans
un domaine où la vérité terrain est décidable.

## Pourquoi ce registre existe

Quatre expériences ont échoué. Aucune n'a échoué dans l'organisme.

| | Ce qui a cassé |
|---|---|
| M014b | seuil de 25 % sur une fenêtre large de 4 requêtes |
| M017 | seuil de 10× dérivé d'un cas typique pris pour une borne |
| M018 | aucune conséquence à l'inefficacité, donc rien à optimiser |
| M019 | horizon de fitness plus court que la période de remboursement |

À chaque fois, ce qu'on construisait tenait. C'est la façon de juger si c'était mieux
qui a cédé.

## Ce que ce dépôt a et que la littérature a rarement

La loi de Goodhart, le *reward hacking*, le *specification gaming*, la recherche de
nouveauté et les algorithmes qualité-diversité travaillent ce problème depuis
longtemps. Il n'est ni neuf ni vierge.

Mais ces travaux opèrent presque tous dans des domaines où **l'objectif vrai n'est pas
vérifiable exactement**. Un *reward hacking* se diagnostique parce qu'un humain trouve
que le résultat a l'air faux. La nouveauté s'évalue à ce qui paraît intéressant. Les
descripteurs comportementaux sont choisis à la main.

Ici, l'équivalence comportementale de deux automates finis se **prouve**. On peut donc
poser, de façon décidable :

> Cette mesure-proxy suit-elle réellement la grandeur qu'elle prétend suivre, et sous
> quelle pression d'optimisation cesse-t-elle de la suivre ?

C'est un banc d'essai pour la conception de mesures, pas une tentative de résoudre ce
que d'autres n'ont pas résolu.

---

## R001 — Une fenêtre trop étroite pour son seuil

- **Origine :** M014b, échec canonique.
- **Mesure :** nombre de requêtes d'identification, seuil d'avantage de 25 %.
- **Ce qu'elle prétendait suivre :** l'efficacité d'apprentissage transportée.
- **Divergence :** Genesis 14 requêtes, L\* depuis zéro 14. La grandeur variait sur une
  fenêtre large de quatre requêtes ; un seuil de 25 % y mesurait du bruit
  d'échantillonnage.
- **Détectable d'avance ?** Oui. Il suffisait d'établir la plage dynamique de la
  grandeur avant de fixer la marge. C'est devenu **D010**.

## R002 — Une baseline structurellement incapable prise pour critère

- **Origine :** M014c, arrêtée ; puis évitée dans M017.
- **Mesure :** rapport au coût d'un catalogue fermé.
- **Divergence :** le catalogue fermé résout 0 sur 700 épisodes. Tout seuil calé sur lui
  passe trivialement et ne mesure que son incapacité, déjà connue.
- **Règle :** une baseline incapable est un **contrôle**, jamais un critère. Le critère
  doit opposer deux systèmes de capacité identique au départ, que seul le mécanisme
  testé sépare ensuite.

## R003 — Un cas typique pris pour une borne du cas le pire

- **Origine :** M017, seuil invalidé avant gel.
- **Mesure :** rapport apparié des coûts de recherche, seuil dérivé à 10×.
- **Ce qu'elle prétendait suivre :** le gain apporté par l'extension du langage.
- **Divergence :** la dérivation prédisait ~500× en supposant qu'un macro est toujours
  atteint en profondeur 1. Sur 8 environnements, minimum 95×. Sur **50**, minimum
  **9,0×** — sous le seuil. Un épisode portant un atome de bruit impose la profondeur 2
  et effondre le rapport d'un facteur cinquante.
- **Correction :** la dispersion de la magnitude étant un facteur 69, aucune marge ne la
  dépasse ; le critère est devenu **directionnel**, dispersion nulle, 50/50.
- **Leçon :** un échantillon de 8 donnait un minimum optimiste d'un facteur dix.

## R004 — Une vérification incapable de garantir ce qu'elle affirmait

- **Origine :** M017, défaut de confirmation.
- **Mesure :** « zéro faux succès », vérifié sur tous les mots jusqu'à 6 plus 96 mots
  tirés au hasard.
- **Divergence :** 96 tirages ne couvrent pas 2⁷+…+2²⁰. Deux automates à 9 états
  confirmés identiques sont séparés par `(1,0,1,0,1,0,1)`. Le résultat rapporté était
  juste ; la procédure ne pouvait pas le garantir.
- **Aggravation :** deux corrections successives ont été annoncées correctes à tort, la
  seconde produisant **10 faux succès sur 73** — pire que le défaut d'origine.
- **Leçon :** une condition d'admission n'est pas établie parce qu'un banc la rapporte
  satisfaite, mais quand la procédure qui la vérifie est **complète**. Et le test censé
  garder la propriété n'exerçait aucune redirection : c'est pourquoi il passait sur une
  suite cassée.

## R005 — Une grandeur sans conséquence

- **Origine :** M018, hypothèse non soutenue.
- **Mesure :** coût de recherche, sous un budget de 200 000 nœuds et un échec gratuit.
- **Divergence :** aucun mécanisme d'oubli ne rapporte, non par défaut de mécanisme mais
  parce qu'**il n'y avait rien pour quoi être efficace**. Une grandeur qu'on optimise
  sans qu'elle coûte n'exerce aucune pression.

## R006 — Un horizon plus court que le délai de rendement

- **Origine :** M019, montage invalide.
- **Mesure :** énergie restante en fin de génération.
- **Ce qu'elle prétendait suivre :** l'efficacité d'une stratégie.
- **Divergence :** apprendre coûte ~23 000 nœuds pour une prime de 6 000 ; ne pas
  essayer en coûte 1 296. La sélection élimine l'apprenti à la première coupe, avant
  tout remboursement. Sur trois calibrages, la population converge vers une recherche
  superficielle et **zéro macro**, résolvant 11 épisodes contre 103 pour un contrôle
  non sélectionné.
- **Leçon :** **l'horizon d'évaluation compte davantage que l'intensité de la
  pression.** Trop faible, elle ne trie rien ; trop impatiente, elle élimine
  l'exploration avant qu'elle ne rapporte.
- **Garde-fou lui-même erroné :** « mortalité non nulle » signalait l'inverse de ce
  qu'on croyait. Zéro mort n'indiquait pas une rareté trop faible mais une rareté assez
  mordante pour que la stratégie gagnante soit de ne rien dépenser.

---

## Ce que le registre suggère déjà

Quatre régularités, tirées de six cas et non postulées :

1. **Établir la plage dynamique avant de fixer une marge** (R001, R003).
2. **Un critère oppose deux capacités égales au départ ; une incapacité est un
   contrôle** (R002).
3. **Une condition d'admission vaut ce que vaut la complétude de sa procédure de
   vérification** (R004).
4. **L'horizon d'évaluation prime sur l'intensité de la pression** (R005, R006).

Aucune n'est nouvelle prise isolément. Ce qui est inhabituel, c'est de les avoir
mesurées là où la vérité terrain est décidable, donc de pouvoir montrer *où exactement*
la mesure décroche plutôt que de constater que le résultat a l'air faux.
