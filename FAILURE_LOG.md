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
- Le critère `no_probe_baseline_at_most_8_of_36` a donc échoué.
- Statut : `FAILED — DEVELOPMENT BASELINE CRITERION`.
- Le plafond n’est pas modifié après observation.
- Correction : M013e utilise un nouveau protocole et préenregistre un avantage relatif d’au moins 12 migrations sur la meilleure baseline sans information sémantique vraie.

## M014 — Arrêt préventif

- Le protocole reste gelé mais aucune évaluation n’est autorisée avant validation propre du substrat inconnu.

## Premiers prototypes sensorimoteurs

Plusieurs protocoles ont été ajustés après pilotes. Ils constituent du développement exploratoire, pas une validation indépendante.

## Principe permanent

Un échec ou une révocation n’est jamais supprimé. Il est classé `FAILED` ou `INCONCLUSIVE`, expliqué, puis suivi d’un nouveau protocole lorsqu’une correction scientifique est justifiée.
