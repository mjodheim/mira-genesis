# Feuille de route

| Étape | Objectif | Statut | Critère de sortie |
|---|---|---|---|
| M001–M011 | Fondations de métamorphose | VALIDATED dans leurs domaines finis, **non vérifiable ici** | Aucune archive versionnée ; voir `archives/README.md` |
| M012 | Morphogenèse autonome | INCONCLUSIVE — CONTAMINATED | Graines d'évaluation exécutées dans les tests |
| M012b | Morphogenèse autonome propre | VALIDATED dans le domaine fini | Évaluation scellée 36/36 et reproduction scientifique |
| M013 / M013b | Substrat inconnu | INCONCLUSIVE — CONTAMINATED | Aucun résultat revendiqué |
| M013c | Substrat inconnu | INCONCLUSIVE — NON REPRODUCIBLE | Commit annoncé incomplet |
| M013d | Substrat inconnu, seuil absolu | FAILED IN DEVELOPMENT | Baseline sans sondage 12/36 contre plafond 8/36 |
| M013e | Substrat inconnu, avantage relatif | VALIDATED dans le domaine fini | 36/36, découverte d'opcodes scellés et reproduction |
| M014 | Plasticité portable initiale | HALTED — NEVER EVALUATED | Prérequis révoqués ; remplacée par M014b |
| M014b | Plasticité portable scellée | FAILED — NO GENERALIZABLE ADVANTAGE | 36/36 exact mais 2 critères d'efficacité échouent |
| M014c | Plasticité portable hors distribution | **HALTED — SUPERSEDED BY M017** | Jamais évaluée ; mesurait un catalogue fermé. Code au tag `archive/m014c-halted` |
| **M017** | **Langage auto-extensible** | **ACTIVE — DEVELOPMENT** | Absorber les motifs récurrents et battre la recherche ouverte sur la décroissance du coût |
| M018 | Auto-métamorphose | BLOCKED BY M017 | Détecter, construire et adopter seul un corps mieux adapté |
| M015 | Mémoire et stratégie | DEFERRED | Migrer souvenirs, incertitudes et stratégie d'exploration |
| M016 | Compétence sensorimotrice | DEFERRED | Transporter un modèle du monde entre architectures différentes |

## Correction de direction — 31 juillet 2026

L'ordre de la feuille de route était faux. Les noms ne l'étaient pas.

M017 y figurait en sixième position, après la mémoire et la sensorimotricité. Or
M012b, M013e, M014b et M014c partagent tous une limite qu'aucun de leurs critères ne
mesurait : **l'organisme ne peut exprimer que ce qui lui a été écrit à la main.**
Dans `m014c_meta.py`, l'identification énumère strictement douze programmes ; tout
l'apprentissage consiste à repondérer des compteurs sur ce catalogue fermé.

Ajouter la mémoire (M015) ou la sensorimotricité (M016) à cet organisme aurait étendu
latéralement un paradigme dont le cœur n'est pas établi. Ces deux étapes sont donc
reportées, non abandonnées : elles reprendront leur place lorsqu'il y aura un
organisme dont le langage grandit à qui les confier.

M017 attaque ce cœur, et M018 — l'auto-métamorphose, H6 — en dépend directement : un
organisme qui ne peut pas étendre son langage ne peut pas se décrire un corps que ses
primitives ne savent pas écrire.

## M014b — échec canonique informatif

M014b a démontré la portabilité exacte de la chaîne de plasticité : 36/36 adaptations
exactes, trois machines à 12/12, archive intacte, 12/12 abstentions négatives. Mais
Genesis utilisait 14 requêtes médianes et L\* depuis zéro également 14. Les critères
d'avantage relatif ont échoué.

La leçon est structurante et vaut au-delà de M014b : **transporter une politique
n'implique pas que son avantage survive**, et un critère mesuré sur une fenêtre large
de quatre requêtes ne peut pas séparer le signal du bruit d'échantillonnage.

## M017 — étape active

Développement sur `research/m017-self-extending-language`. Résultat observé sur 42
épisodes, trois environnements :

| | résolus | nœuds médians, 1re moitié | 2de moitié |
|---|---|---|---|
| catalogue fermé, capacité de M014c | **0 / 42** | — | — |
| recherche ouverte, sans absorption | 34 / 42 | 7 154 | 8 545 |
| auto-extensible | **37 / 42** | 4 222 | **43** |

Le coût de recherche s'effondre d'un facteur cent pour le seul organisme qui étend son
langage, et reste plat pour celui qui ne l'étend pas. Réincarnation 9/9 exacte sur
trois familles de machines opaques, 4/4 abstentions négatives, zéro faux succès.

Aucune évaluation canonique n'est autorisée. Les portes de gel sont dans
`experiments/M017/PROTOCOL_DRAFT.md`, et la première est de désigner la comparaison
décisive **avant** d'observer quoi que ce soit de nouveau.

## Test ultime de la première phase

Genesis apprend dans un corps A, reçoit un substrat B inconnu, en découvre les règles,
construit son nouveau corps, transfère mémoire, compétence et plasticité, puis apprend
une tâche nouvelle plus vite qu'un organisme vierge — sans qu'un humain redessine son
architecture.

Ce test suppose que Genesis puisse exprimer des compétences que personne ne lui a
écrites. C'est la raison d'être de M017.
