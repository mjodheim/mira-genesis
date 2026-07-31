# Feuille de route

| Étape | Objectif | Statut | Critère de sortie |
|---|---|---|---|
| M001–M011 | Fondations de métamorphose | VALIDATED dans leurs domaines finis | Passeport, migration, plasticité locale et chirurgie native exactes |
| M012 | Morphogenèse autonome | INCONCLUSIVE — CONTAMINATED | Graines d’évaluation exécutées dans les tests |
| M012b | Morphogenèse autonome propre | READY FOR SEALED EVALUATION | Premier run PR scellé, dix critères passés, artefact et SHA reproductibles |
| M013 / M013b | Substrat inconnu | INCONCLUSIVE — CONTAMINATED | Aucun résultat revendiqué |
| M013c | Substrat inconnu | INCONCLUSIVE — NON REPRODUCIBLE | Le commit annoncé ne contient pas le protocole figé |
| M013d | Substrat inconnu propre | BLOCKED BY M012b | Protocole, code et reproduction présents avant toute exécution |
| M014 | Plasticité portable | HALTED | Reprendre seulement après M012b et M013d |
| M015 | Mémoire et stratégie | PLANNED | Migrer souvenirs, incertitudes et stratégie d’exploration |
| M016 | Compétence sensorimotrice | PLANNED | Transporter un modèle du monde entre architectures différentes |
| M017 | Langage auto-extensible | PLANNED | Inventer un dialecte requis par une capacité hors langage |
| M018 | Auto-métamorphose | PLANNED | Détecter, construire et adopter seul un corps mieux adapté |

## Étape active — M012b

Le moteur, le laboratoire, le protocole et le workflow sont figés sur la branche `research/m012b-sealed-morphogenesis`.

1. Les tests utilisent exclusivement des graines de développement explicites.
2. Aucune graine d’évaluation n’existe avant l’ouverture de la PR.
3. Le premier run GitHub Actions dérive les cas depuis une nonce cryptographique créée à l’exécution.
4. La première tentative est définitive ; un rerun invalide M012b et impose M012c.
5. Les résultats complets, hashes, nonce et graines dérivées sont conservés comme artefact.
6. La fusion n’est autorisée qu’après audit de l’artefact et reproduction depuis le SHA évalué.

## Suite conditionnelle

### M013d

Après une validation recevable de M012b, utiliser de nouvelles machines opaques et de nouveaux passeports. Le commit d’évaluation devra déjà contenir le protocole, les scripts, le laboratoire et les contrôles avant la première exécution.

### M014

Le protocole existant reste gelé mais suspendu. Les graines `17xxx` ne doivent pas être exécutées avant que la chaîne M012b → M013d soit proprement établie.

## Test ultime de la première phase

Genesis apprend dans un corps A, reçoit un substrat B inconnu, en découvre les règles, construit son nouveau corps, transfère mémoire, compétence et plasticité, puis apprend une nouvelle tâche plus vite qu’un organisme vierge.
