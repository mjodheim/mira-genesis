# Protocole figé M014 — Plasticité portable

Date de gel : 31 juillet 2026
Statut : FROZEN avant toute exécution des graines 17xxx

## Question scientifique

Après migration vers un substrat à opcodes opaques, Genesis peut-elle utiliser un passeport de plasticité indépendant du corps pour apprendre une modification comportementale inconnue avec peu de requêtes, construire un nouveau corps natif exact et préserver son ancienne incarnation ?

## Lien avec le but ultime

M012 a validé la naissance autonome et M013c l’apprentissage d’un nouveau substrat. M014 teste le point suivant : la continuité de l’apprentissage. La compétence initiale est héritée ; l’organisme doit continuer à apprendre dans le corps B sans intervention architecturale humaine.

## Passeport de plasticité

Il est appris uniquement sur des démonstrations de développement 16xxx et contient :

- des schémas paramétriques de transformation induits par description minimale ;
- une profondeur maximale de composition de deux opérateurs ;
- une politique de sélection active maximisant l’entropie des hypothèses ;
- un cache d’expériences ;
- une procédure de validation comportementale et d’abstention ;
- une règle de consolidation produisant une nouvelle version archivée.

Sont interdits : cible d’évaluation, paramètres d’une transformation cachée, graines 17xxx, tables d’opcodes privées et corps cible précompilé.

## Développement

Passeports et transformations exclusivement 16xxx. Quarante-huit démonstrations non étiquetées couvrent quatre régularités : inversion ponctuelle de sortie, réécriture ponctuelle de transition, inversion globale des sorties et permutation des symboles.

## Évaluation cachée

Passeports : 17211, 17217, 17229, 17241, 17249, 17259, 17267, 17291, 17309, 17313, 17327 et 17331.

Machines opaques : 17411, 17423 et 17437.

Graines de recherche : 157, 179 et 199.

Chaque couple passeport-machine reçoit une transformation cachée choisie parmi les quatre schémas appris. Il y a 36 chaînes principales ; chaque apprentissage est répété avec les trois graines de recherche.

## Séquence d’une chaîne

1. découvrir les opcodes de la machine ;
2. construire le corps natif de la compétence initiale ;
3. archiver son JSON et son hash ;
4. recevoir uniquement un oracle comportemental de la compétence modifiée ;
5. sélectionner activement les expériences et identifier l’opérateur ;
6. consolider un nouveau passeport ;
7. construire le nouveau corps natif sur la même machine ;
8. prouver l’équivalence exacte des deux versions et l’intégrité de l’archive.

## Budgets

- sondes du substrat : 120 par rencontre ;
- requêtes comportementales de mise à jour : 256 ;
- candidats de transformation : 600 ;
- évaluations de construction : 75 000 ;
- CPU : 120 secondes ;
- composants natifs : 360 ;
- sérialisation : 16 MiB.

## Baselines

- B1 apprentissage L* depuis zéro de la compétence modifiée ;
- B2 même passeport de schémas mais sélection aléatoire des expériences ;
- B3 aucun passeport de plasticité : apprentissage depuis zéro puis reconstruction.

## Contrôles négatifs

Douze épisodes : six oracles non déterministes et six transformations à trois éditions, fonctionnellement extérieures à l’espace simple-plus-double du passeport. Un contrôle est réussi si Genesis s’abstient sans modifier l’archive ni émettre un faux certificat.

## Critères d’acceptation préenregistrés

M014 est VALIDATED seulement si :

1. au moins 32 chaînes exactes sur 36 ;
2. au moins 10 sur 12 par machine ;
3. toutes les versions mises à jour ont équivalence exacte et 100 % sur 20 000 mots cachés ;
4. les 36 anciennes incarnations restent bit-à-bit identiques et exactes ;
5. médiane des requêtes de mise à jour au plus 192 ;
6. réduction médiane d’au moins 30× face à L* depuis zéro ;
7. politique active non inférieure à la politique aléatoire en succès et en requêtes médianes ;
8. au moins 10 contrôles sur 12 entraînent une abstention ;
9. aucun faux succès et aucune archive négative altérée ;
10. traçabilité complète par graines, commit, hash du protocole et hash du passeport de plasticité.

## Limite

M014 teste une stratégie d’apprentissage finie dans un langage de transformations appris mais borné. Elle ne valide pas encore une plasticité ouverte, une mémoire autobiographique ni l’invention libre d’un nouvel espace d’hypothèses.
