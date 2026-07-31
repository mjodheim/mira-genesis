# Journal des échecs et corrections

## M004 — Échec partiel

- La preuve exhaustive avait été comptée dans le budget d’expérience de Genesis.
- Certaines restructurations composées étaient fonctionnellement équivalentes à une mutation simple.
- Correction : séparation stricte organisme/évaluateur et protocole M005.

## Premiers prototypes sensorimoteurs

Plusieurs protocoles ont été ajustés après pilotes. Ils constituent du développement exploratoire, pas une validation indépendante. Cette dérive a motivé le recentrage sur Metamorphosis et les protocoles figés.

## Contrôle GRU exhaustif

L’interrogation exhaustive d’un GRU entraîné était trop lente sur CPU dans l’environnement initial. Un parent récurrent entraîné plus léger a été utilisé pour M002. La validation GRU complète reste à exécuter sur GPU.

## Principe permanent

Un échec n’est jamais supprimé. Il est classé `FAILED` ou `INCONCLUSIVE`, expliqué, puis suivi d’un nouveau protocole lorsqu’une correction scientifique est justifiée.
