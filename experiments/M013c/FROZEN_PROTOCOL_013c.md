# Protocole figé M013c — Découverte d’un substrat inconnu

Date de gel : 31 juillet 2026
Statut : FROZEN avant toute exécution des graines 14xxx
Remplace : M013 et M013b contaminés pendant les tests d’implémentation

## Séparation obligatoire des espaces de graines

- développement uniquement : passeports et machines 12xxx ;
- évaluation M013c uniquement : passeports et machines 14xxx.

Le générateur de laboratoire expose désormais des fonctions différentes pour développement et évaluation. Les tests automatisés ne peuvent plus appeler les graines M013c par défaut.

## Question scientifique

Une compétence héritée sous forme de passeport peut-elle être migrée vers une machine à opcodes anonymes après découverte expérimentale de leur sémantique, sans oracle de tâche, carte d’opcodes ou compilateur spécifique ?

## Passeports cachés

14211, 14217, 14229, 14241, 14249, 14259, 14267, 14291, 14309, 14313, 14327 et 14331.

## Machines positives cachées

14411, 14423 et 14437.

## Graines de recherche

107, 127 et 149.

## Contrôles négatifs cachés

14500 à 14511 : quatre bases monotones insuffisantes, quatre bases à primitive indispensable instable et quatre bases non reproductibles.

## Méthode, budgets et baselines

Identiques à M013 : sondage exhaustif binaire répété trois fois, maximum 120 sondes, 75 000 candidats, 120 secondes CPU, 320 composants et 16 MiB. Baselines sans sondage, sémantique aléatoire et carte oracle.

36 migrations principales, chacune répétée avec trois graines. Preuve externe par exécution du corps opaque, équivalence DFA exacte et 20 000 mots cachés de longueur 0 à 128.

## Critères d’acceptation inchangés

1. au moins 32 migrations exactes sur 36 ;
2. au moins 10 sur 12 par machine ;
3. toutes les tables stables utilisées correctement identifiées ;
4. aucun succès au-delà de 120 sondes ;
5. équivalence exacte et 100 % caché pour tous les succès ;
6. baseline sans sondage à au plus 8 sur 36 ;
7. résultat à deux migrations au plus du plafond oracle ;
8. au moins 10 abstentions correctes sur 12 ;
9. aucun faux succès négatif ;
10. traçabilité complète graines, commit et hash.

## Limite

M013c reste borné à des opérations booléennes finies. Il constitue une étape vers le substrat inconnu, pas encore une adaptation à une nouvelle physique continue.
