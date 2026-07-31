# Journal des échecs et corrections

## M004 — Échec partiel

- La preuve exhaustive avait été comptée dans le budget d’expérience de Genesis.
- Certaines restructurations composées étaient fonctionnellement équivalentes à une mutation simple.
- Correction : séparation stricte organisme/évaluateur et protocole M005.

## M012 — Évaluation contaminée

- Plusieurs graines déclarées réservées à l’évaluation apparaissent directement dans `tests/test_morphogenesis.py`.
- Elles ont donc été exécutées pendant le développement et n’étaient plus cachées.
- Le résultat 36/36 reste une preuve d’ingénierie, pas une validation scientifique préenregistrée.
- Statut corrigé : `INCONCLUSIVE — CONTAMINATED`.
- Correction requise : M012b avec cas scellés absents des tests et du code de développement.

## M013 — Contamination des graines avant évaluation

- Les tests d’implémentation ont exécuté plusieurs passeports et les trois machines prévues pour l’évaluation.
- Ces cas n’étaient donc plus cachés et ne pouvaient soutenir une validation scientifique.
- Statut : `INCONCLUSIVE — CONTAMINATED`.

## M013b — Deuxième contamination

- Une validation automatisée a utilisé des graines déjà exercées pendant l’implémentation, puis des contrôles réservés ont également été touchés.
- Le workflow vert démontrait la reproductibilité logicielle, pas la validité d’un test caché.
- Statut : `INCONCLUSIVE — CONTAMINATED`.

## M013c — Commit de reproduction incomplet

- Le commit d’évaluation annoncé `40ac0f64a1fb9465e1c4cadf6c32c0cfde3b84dd` ne contient pas le protocole M013c figé.
- La commande documentée checkout ce commit puis tente de lire `experiments/M013c/protocol.yaml`, absent à ce point de l’historique.
- Le critère de traçabilité complète ne peut donc pas être considéré comme passé.
- Statut corrigé : `INCONCLUSIVE — NON REPRODUCIBLE AT ANNOUNCED COMMIT`.
- Correction requise : M013d sur un commit unique et auto-contenu, avant toute exécution des nouvelles graines.

## M014 — Arrêt préventif

- Le protocole a été gelé, mais aucune évaluation ne doit être lancée tant que M012b et M013d ne sont pas proprement validées.
- Aucun fichier d’implémentation partiel n’a été laissé sur la branche M014.

## Premiers prototypes sensorimoteurs

Plusieurs protocoles ont été ajustés après pilotes. Ils constituent du développement exploratoire, pas une validation indépendante.

## Principe permanent

Un échec ou une révocation n’est jamais supprimé. Il est classé `FAILED` ou `INCONCLUSIVE`, expliqué, puis suivi d’un nouveau protocole lorsqu’une correction scientifique est justifiée.
