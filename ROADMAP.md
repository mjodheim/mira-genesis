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
| M017 | Langage auto-extensible | **READY TO FREEZE** | Six portes franchies ; critère devenu directionnel après le balayage à 50 environnements |
| M018 | Dissolution — savoir détruire | **HYPOTHESIS NOT SUPPORTED** | Aucun des trois mécanismes n'annule le passif ; l'oubli est réactif, la destruction aveugle |
| **M019** | **Pression de sélection** | **ACTIVE — DEVELOPMENT** | Une population sous rareté découvre-t-elle ce qu'aucune conception n'a atteint ? |
| M020 | Auto-métamorphose | BLOCKED BY M019 | Détecter, construire et adopter seul un corps mieux adapté |
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

Les six portes de gel sont franchies. Le protocole complet, seuils compris, attend une
signature humaine dans `experiments/M017/FROZEN_PROTOCOL_017_CANDIDATE.md`.

Deux mesures ont changé le protocole en cours de route, et méritent d'être retenues :

- **la première statistique décisive a été rejetée par la mesure.** Non appariée, elle
  donnait un avantage de 2,4× à 605× selon l'environnement ; appariée épisode par
  épisode, de 95× à 620×. La dispersion est divisée par trente-huit sans que la médiane
  bouge. C'est la vérification que M014b n'a jamais faite ;
- **le langage étendu ne se transporte pas.** Une bibliothèque héritée d'un
  environnement aux motifs disjoints donne 0,69× — strictement pire que pas de
  bibliothèque du tout, quatre fois sur quatre. La leçon de M014b, retrouvée un cran
  plus haut, et portée dans le protocole **avant** le gel plutôt que découverte après.

Ce passif a une cause nommable : l'organisme ne sait ni oublier ses macros, ni juger
qu'ils ne s'appliquent plus. C'est ce qui a rendu M018 nécessaire plutôt que souhaitable.

## M018 — l'hypothèse n'est pas soutenue

Trois mécanismes de destruction, aucun n'annule le passif de 0,69×. Le budget fixe est
gratuit mais ne rapporte que 6 % ; la dissolution est **350× pire** en régime stable.

Le diagnostic déplace la cause : **l'oubli est réactif.** Un symbole inutile est payé
d'avance, à chaque nœud de recherche ; quand l'organisme sait enfin qu'un macro ne sert
pas, il l'a déjà financé. Et la destruction indiscriminée jette le bon avec le mauvais.

Deux lectures en découlent, et la seconde ouvre M019 :

1. le remède n'est pas la suppression mais la **sélection au moment de l'emploi** ;
2. **détruire est intenable pour un individu isolé.** La chenille se dissout une fois,
   et si cela échoue, cette chenille meurt — pas l'espèce.

## M019 — étape active

Ce que le projet n'avait jamais eu : la **rareté**. Jusqu'ici l'échec ne coûtait rien,
donc l'efficacité ne servait à rien — ce qui explique le résultat de M018 mieux que
n'importe quelle propriété des mécanismes testés.

L'énergie devient le budget de recherche, une population remplace l'individu, et la
duplication-divergence complète l'absorption. Personne ne choisit de mécanisme
d'oubli : les quatre sont dans la population de départ et la sélection tranche.

La question, posée pour la première fois : **une population sous sélection
découvre-t-elle ce que je n'ai pas su concevoir ?**

## Test ultime de la première phase

Genesis apprend dans un corps A, reçoit un substrat B inconnu, en découvre les règles,
construit son nouveau corps, transfère mémoire, compétence et plasticité, puis apprend
une tâche nouvelle plus vite qu'un organisme vierge — sans qu'un humain redessine son
architecture.

Ce test suppose que Genesis puisse exprimer des compétences que personne ne lui a
écrites. C'est la raison d'être de M017.
