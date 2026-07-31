# Journal des échecs et corrections

## M004 — Échec partiel

- La preuve exhaustive avait été comptée dans le budget d’expérience de Genesis.
- Certaines restructurations composées étaient fonctionnellement équivalentes à une mutation simple.
- Correction : séparation stricte organisme/évaluateur et protocole M005.

## M013 — Contamination des graines avant évaluation

- Les tests d’implémentation ont exécuté plusieurs passeports et les trois machines prévues pour l’évaluation.
- Ces cas n’étaient donc plus cachés et ne pouvaient soutenir une validation scientifique.
- Statut : `INCONCLUSIVE — CONTAMINATED`.
- Aucun résultat M013 n’est revendiqué.

## M013b — Deuxième contamination

- Une validation automatisée a utilisé des graines déjà exercées pendant l’implémentation, puis trois contrôles négatifs réservés ont également été touchés.
- Le workflow vert démontrait la reproductibilité logicielle, pas la validité d’un test caché.
- La revendication `VALIDATED` a été explicitement révoquée et les fichiers sont conservés uniquement comme preuve d’ingénierie contaminée.
- Correction : M013c impose deux espaces de graines disjoints par construction, `12xxx` pour le développement et `14xxx` pour l’évaluation.

## Premiers prototypes sensorimoteurs

Plusieurs protocoles ont été ajustés après pilotes. Ils constituent du développement exploratoire, pas une validation indépendante. Cette dérive a motivé le recentrage sur Metamorphosis et les protocoles figés.

## Contrôle GRU exhaustif

L’interrogation exhaustive d’un GRU entraîné était trop lente sur CPU dans l’environnement initial. Un parent récurrent entraîné plus léger a été utilisé pour M002. La validation GRU complète reste à exécuter sur GPU.

## Principe permanent

Un échec n’est jamais supprimé. Il est classé `FAILED` ou `INCONCLUSIVE`, expliqué, puis suivi d’un nouveau protocole lorsqu’une correction scientifique est justifiée.
