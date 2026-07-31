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

## Premiers prototypes sensorimoteurs

Plusieurs protocoles ont été ajustés après pilotes. Ils constituent du développement exploratoire, pas une validation indépendante.

## Principe permanent

Un échec ou une révocation n’est jamais supprimé. Il est classé `FAILED` ou `INCONCLUSIVE`, expliqué, puis suivi d’un nouveau protocole lorsqu’une correction scientifique est justifiée.
