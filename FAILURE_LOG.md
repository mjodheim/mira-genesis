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

### La correction

`metamorphosis/conformance.py` : test de conformité par **méthode W**. Pour une
hypothèse à k états et une cible d'au plus k+s états, la suite `P · (ε ∪ Σ ∪ … ∪ Σˢ) · W`
est complète — l'accord sur la suite implique l'équivalence.

Résultat inattendu sur le coût : pour un automate à 9 états et s = 2, la suite compte
**99 mots contre 160** au jeu probabiliste. L'ancienne confirmation était donc à la
fois plus chère et moins sûre.

Hypothèse résiduelle, énoncée plutôt que dissimulée : la complétude ne vaut que si la
cible ne dépasse pas l'hypothèse de plus de deux états après minimisation.

### Leçon

Une condition d'admission n'est pas établie parce qu'un banc la rapporte satisfaite.
Elle l'est quand la procédure qui la vérifie est **complète**. M017 rapportait
« 0 faux succès » avec une procédure incapable de le garantir — ce qui est
exactement le genre d'affirmation que la discipline du dépôt existe pour empêcher.

## Premiers prototypes sensorimoteurs

Plusieurs protocoles ont été ajustés après pilotes. Ils constituent du développement exploratoire, pas une validation indépendante.

## Principe permanent

Un échec ou une révocation n’est jamais supprimé. Il est classé `FAILED` ou `INCONCLUSIVE`, expliqué, puis suivi d’un nouveau protocole lorsqu’une correction scientifique est justifiée.
