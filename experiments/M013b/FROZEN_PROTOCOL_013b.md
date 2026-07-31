# Protocole figé M013b — Découverte d’un substrat inconnu

Date de gel : 31 juillet 2026
Statut : FROZEN avant relance M013b

M013b reprend sans modification les passeports, machines, graines, budgets, contrôles négatifs et seuils de M013.

## Correction unique

Le critère de proximité avec la carte oracle compare désormais des unités identiques : une migration principale oracle est exacte seulement si ses trois graines de recherche sont exactes. Le plafond oracle est donc compris entre 0 et 36, comme le résultat principal, et non entre 0 et 108.

## Question

À partir d’un passeport cognitif acquis et d’une machine dont les opérations sont désignées uniquement par des identifiants opaques, Genesis peut-elle découvrir expérimentalement leur sémantique, détecter les bases insuffisantes ou instables, puis construire un corps natif exact sans carte d’opcodes ni compilateur spécifique ?

## Données figées

- Passeports : 12011, 12023, 12037, 12041, 12049, 12071, 12073, 12097, 12101, 12109, 12113, 12119.
- Machines positives : 13011, 13023, 13037.
- Graines de recherche : 17, 31, 59.
- 12 contrôles négatifs.
- 3 répétitions par entrée d’opcode.

## Budgets

- 120 sondes natives ;
- 75 000 évaluations de candidats ;
- 120 secondes CPU ;
- 320 composants natifs ;
- 16 MiB sérialisés.

## Critères

1. au moins 32 migrations exactes sur 36 ;
2. au moins 10 sur 12 par machine ;
3. toutes les tables stables utilisées identifiées exactement ;
4. aucune réussite au-delà de 120 sondes ;
5. équivalence DFA exacte et 100 % sur les mots cachés ;
6. baseline sans sondage au plus 8 migrations sur 36 ;
7. résultat principal à moins de deux migrations du plafond oracle, tous deux agrégés sur 36 migrations principales ;
8. au moins 10 abstentions correctes sur 12 ;
9. aucun faux certificat sur les contrôles négatifs ;
10. traçabilité complète des graines, commit et hash du protocole.

## Limite

Cette expérience reste limitée à la découverte de sémantiques booléennes finies. Elle ne démontre pas l’adaptation à un matériel analogique, continu ou ouvert.
