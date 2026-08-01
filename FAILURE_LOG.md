# Journal des échecs et corrections

## M004 — Échec partiel

- La preuve exhaustive avait été comptée dans le budget d’expérience de Genesis.
- Certaines restructurations composées étaient fonctionnellement équivalentes à une mutation simple.
- Correction : séparation stricte organisme/évaluateur et protocole M005.

## M012 — Évaluation contaminée

- Plusieurs graines déclarées réservées à l’évaluation apparaissaient dans les tests.
- Statut : `INCONCLUSIVE — CONTAMINATED`.
- Correction : M012b avec cas générés seulement après création du SHA immuable.

## M013 / M013b — Contaminations successives

- Des passeports, machines ou contrôles réservés avaient été exécutés pendant le développement.
- Statut : `INCONCLUSIVE — CONTAMINATED`.

## M013c — Commit de reproduction incomplet

- Le commit annoncé ne contenait pas son protocole figé.
- Statut : `INCONCLUSIVE — NON REPRODUCIBLE AT ANNOUNCED COMMIT`.

## M013d — Échec du critère de baseline en développement

- Aucun run canonique scellé n’a été ouvert.
- Le contrôle non canonique donnait 36/36 migrations exactes à Genesis.
- La baseline fixe sans sondage obtenait 12/36, au-dessus du maximum préenregistré de 8/36.
- Statut : `FAILED — DEVELOPMENT BASELINE CRITERION`.
- Correction : M013e utilise un avantage relatif préenregistré sur la meilleure baseline sans information.

## M014 — Arrêt préventif

- Le protocole initial a été stoppé avant évaluation lorsque ses prérequis ont été révoqués.
- Statut : `HALTED — NEVER EVALUATED`.
- Remplacement : M014b.

## M014b — Plasticité transportable sans avantage généralisable

- Première évaluation canonique : run `30650363802`, tentative 1, SHA `5a0947afb96d7d59438c222028f2cabb34bc0cd5`.
- La chaîne technique a réussi 36/36 fois : migration de l’ancienne compétence, transport du passeport, identification, consolidation, nouvelle morphogenèse et archive intacte.
- Genesis utilisait 14 requêtes médianes d’identification.
- L* depuis zéro utilisait également 14 requêtes médianes.
- Les baselines aléatoire et sans passeport appris utilisaient chacune 17 requêtes médianes.
- Deux critères figés ont échoué : avantage de 25 % sur L* et avantage de 20 % sur les deux baselines locales.
- Statut : `FAILED — PORTABILITY WITHOUT GENERALIZABLE LEARNING ADVANTAGE`.
- Aucun rerun et aucun assouplissement de seuil ne remplacent ce résultat.

### Leçon scientifique

Le développement avait appris un langage de transformations et un prior utiles sur ses propres distributions, mais cet avantage ne s’est pas maintenu sur la distribution scellée. La portabilité structurelle d’une politique n’implique pas la portabilité de son efficacité.

### Défaut de traçabilité découvert

- La reproduction retrouve tous les résultats scientifiques.
- `consolidation_record_sha256` diffère entre environnements parce qu’il inclut des scores flottants dans la trace.
- Correction obligatoire pour M014c : décisions et hashes fondés sur des nombres quantifiés, entiers ou rationnels canoniques.

### Remplacement

M014c devra apprendre à travers plusieurs distributions, détecter le décalage, adapter son prior sous budget et être comparé au passeport statique M014b en plus des baselines précédentes.

## M014c — Arrêt avant évaluation

- Statut : `HALTED — SUPERSEDED BY M017`. Aucune évaluation canonique n'a été ouverte
  et aucun résultat n'est revendiqué.
- Branche préservée : `research/m014c-distribution-general-plasticity`, tête `fc46005`.
- L'implémentation fonctionnait, les tests passaient, la CI était verte. Le défaut
  était dans ce qui était mesuré.
- `MetaPlasticitySession.identify` énumère strictement `passport.programs` — douze
  programmes structurels écrits à la main. L'adaptation en ligne se réduit à
  repondérer des compteurs de groupe sur ce catalogue fermé.
- Le banc affichait `active_to_scratch_ratio = 0,083`, lisible comme un gain de quinze
  fois. C'est un effet de taille d'automate : L\* paye un coût qui croît avec l'automate,
  Genesis un coût qui croît avec sa bibliothèque de douze entrées. Agrandir les
  automates aurait gonflé le ratio sans rien changer à ce qui avait été appris.
- La comparaison qui portait l'hypothèse était `active_to_static_ratio = 0,88` : douze
  pour cent, sur une fenêtre large de quatre requêtes.
- **C'est la géométrie exacte de l'échec de M014b.** Figer M014c contre L\* aurait
  passé trivialement et répété l'erreur en sens inverse.

### Leçon scientifique

Un catalogue fermé rend indécidable toute expérience sur l'apprentissage : la fenêtre
mesurable est bornée par la taille du catalogue, pas par la capacité de l'organisme.
Voir D009 et D010.

### Remplacement

M017 — langage auto-extensible. Le vocabulaire de départ ne contient que des atomes ;
tout ce qui dépasse l'atome doit être construit, et ce qui est construit peut être
absorbé.

## M017 — Confirmation non fiable, découverte en développement

- Statut : `DEVELOPMENT DEFECT — CORRECTED BEFORE ANY FREEZE`.
- Aucune évaluation canonique n'avait été ouverte. Le défaut est corrigé avant le gel,
  et non découvert après un run irremplaçable.

### Le défaut

La confirmation d'un candidat portait sur tous les mots jusqu'à la longueur 6, plus
**96 mots tirés au hasard** entre 7 et 20. La docstring affirmait que ces mots longs
couvraient la borne de distinction de deux automates.

C'était faux. Quatre-vingt-seize tirages ne couvrent pas 2⁷+…+2²⁰. La garantie était
probabiliste et faible.

### Ce que ça invalide

Le banc de développement M017 rapportait **zéro faux succès sur 42 épisodes**. Ce
n'était pas une garantie mais un tirage favorable. Un balayage plus large, mené pendant
le développement de M018, a produit deux automates à 9 états confirmés identiques que
le mot `(1,0,1,0,1,0,1)` sépare — un mot absent des deux jeux.

**Conséquence :** tous les chiffres de développement M017 — banc principal, dispersion,
transport — avaient été produits sous cette confirmation. Ils ne sont pas
nécessairement faux, mais ils n'étaient plus établis, et ont dû être remesurés.

### La correction, en deux temps

`metamorphosis/conformance.py` : test de conformité par **méthode W**. Pour une
hypothèse minimale à k états et une cible d'au plus k+s états, la suite
`P · (ε ∪ Σ ∪ … ∪ Σˢ) · W` est complète — l'accord sur la suite implique l'équivalence.

**La première correction a échoué, et de la même façon que le défaut d'origine.** Elle
construisait la suite depuis le candidat brut de la recherche, non minimisé, avec une
marge fixée arbitrairement à deux états. Or la méthode W exige une hypothèse minimale :
`characterizing_set` cherchait à séparer des paires d'états équivalents, échouait
silencieusement, et l'ensemble ne caractérisait plus rien. Un second faux succès a
survécu, à l'environnement 6 de l'étude de dispersion.

La version retenue minimise l'hypothèse au lieu de la supposer minimale, et **calcule**
la marge au lieu de la choisir : le langage structurel ne crée aucun état, donc la
cible ne peut pas en compter plus que la source, borne que l'organisme connaît
puisqu'il détient la source.

Le coût ne diverge pas : la suite croît en `|Σ|ˢ · k²`, or `s` décroît quand `k` croît.
Sur un automate à 9 états la suite compte **99 mots contre 160** au jeu probabiliste.
L'ancienne confirmation était donc à la fois plus chère et moins sûre.

### Trois corrections, dont deux fausses

Il a fallu trois versions pour obtenir une confirmation complète, et les deux premières
ont été annoncées comme correctes avant de l'être.

1. **Marge fixe sur hypothèse non minimisée.** Un second faux succès a survécu, à
   l'environnement 6 de l'étude de dispersion.
2. **Couverture d'états au lieu de couverture de transitions.** Pire que le défaut
   d'origine : **10 faux succès sur 73**, avec des témoins de longueur 6 que le jeu
   probabiliste attrapait. La méthode W part d'une couverture de transitions
   `S·(Σ∪{ε})` ; sans elle les transitions sortantes ne sont jamais exercées, et les
   atomes de ce langage sont majoritairement des redirections.
3. **Version retenue** : hypothèse minimisée, couverture de transitions, marge calculée
   depuis le nombre d'états de la source.

Le test censé garder cette propriété n'inversait que des bits d'acceptation et
n'exerçait **aucune redirection** — c'est précisément pourquoi il passait sur une suite
cassée. Réécrit pour engendrer ses différences avec le jeu d'atomes réel, il échoue sur
la version 2 en manquant 14 différences sur 151.

**Conséquence de calendrier :** chaque mesure lancée entre ces versions a tourné sous
une confirmation défectueuse, y compris une remesure du banc M017 annoncée « identique »
qui ne comptait donc pas. Toutes les mesures de M017 et de M018 ont été refaites sous
la version 3.

### Ce que le défaut menaçait, et ce qu'il ne menaçait pas

Distinction à ne pas perdre : **le coût de recherche ne dépend pas de la confirmation**.
Le nombre de programmes évalués est arrêté par le filtre d'empreinte ; seule la facture
d'oracle change quand la confirmation change. Le résultat de tête de M017 —
l'effondrement du coût de 4 222 à 43 nœuds — n'était donc jamais en jeu.

Ce qui l'était, c'est la condition d'admission « zéro faux succès », qui décide si
l'expérience compte pour quelque chose. Une expérience qui mesure bien un coût tout en
acceptant des solutions fausses ne mesure rien.

Le banc réexécuté sous la version 3 rend des chiffres identiques : 0/34/37 résolus,
4 222 → 43 nœuds médians, 24 macros, 9/9 réincarnations exactes, 4/4 abstentions,
0 faux succès. Sur ces 42 épisodes le premier candidat passant le filtre était toujours
le bon, ce qui explique que le coût soit inchangé. Le résultat tient — et il tient
désormais parce que la procédure est complète.

### Leçon

Une condition d'admission n'est pas établie parce qu'un banc la rapporte satisfaite.
Elle l'est quand la procédure qui la vérifie est **complète**. M017 rapportait
« 0 faux succès » avec une procédure incapable de le garantir — ce qui est
exactement le genre d'affirmation que la discipline du dépôt existe pour empêcher.

Que la remesure redonne les mêmes chiffres ne réhabilite pas l'ancienne procédure. Un
résultat juste obtenu par une méthode qui ne peut pas le garantir reste un résultat non
établi ; c'est la distinction que M014b avait déjà payée, et elle se répète ici sur la
vérification plutôt que sur la mesure.

## Premiers prototypes sensorimoteurs

Plusieurs protocoles ont été ajustés après pilotes. Ils constituent du développement exploratoire, pas une validation indépendante.

## Principe permanent

Un échec ou une révocation n’est jamais supprimé. Il est classé `FAILED` ou `INCONCLUSIVE`, expliqué, puis suivi d’un nouveau protocole lorsqu’une correction scientifique est justifiée.
