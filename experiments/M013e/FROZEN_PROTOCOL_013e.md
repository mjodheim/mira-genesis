# Protocole figé M013e — Découverte scellée d’un substrat inconnu

**Statut : FROZEN avant toute génération de cas d’évaluation**  
**Date de gel : 31 juillet 2026**  
**Remplace : M013d, échec de développement sans run canonique**

## 1. Question scientifique

Une compétence finie héritée peut-elle être migrée vers une machine dont les opérations natives n’ont ni nom logique ni documentation, après découverte expérimentale de leurs effets, sans oracle de tâche, carte d’opcodes ou compilateur spécifique à la machine ?

## 2. Correction apportée après M013d

M013d utilisait un plafond absolu de 8/36 pour la baseline sans sondage. Dans le run de développement, une permutation fixe d’opcodes a fortuitement fourni une base utilisable sur une machine entière, donnant 12/36. M013d est donc classé `FAILED — DEVELOPMENT BASELINE CRITERION`.

M013e ne réinterprète pas ce résultat. Il préenregistre à la place un critère d’information relatif : Genesis doit réussir au moins **12 migrations principales de plus** que la meilleure baseline ne recevant aucune sémantique vraie par sondage.

## 3. Scellement

Avant le premier run canonique, aucune graine de passeport, machine, contrôle, recherche ou suite cachée n’existe dans le dépôt. Le premier workflow `pull_request/opened` génère une nonce cryptographique de 256 bits. Les graines sont dérivées par SHA-256 et publiées avec les résultats.

Le run numéro 1, tentative 1, est contraignant. Toute relance ou correction matérielle impose M013f.

## 4. Compétences et machines

- douze DFA minimaux binaires de 3 à 8 états, fournis comme compétences héritées ;
- trois machines positives à opcodes anonymes et bases complètes différentes ;
- aucun oracle de tâche pendant la migration ;
- seulement identifiants, arités, coûts, sondes et exécution exposés à Genesis.

## 5. Découverte

Chaque entrée binaire d’un opcode est répétée trois fois. Budget maximal : 120 sondes. Une opération non reproductible est exclue.

Genesis construit un catalogue découvert, cherche une base logique et synthétise un corps contenant seulement les identifiants opaques et sa structure. Aucune table de vérité n’est sérialisée dans le corps.

## 6. Évaluation

- 36 migrations principales : 12 passeports × 3 machines ;
- 108 exécutions : trois graines de recherche par migration ;
- équivalence DFA exacte par exécution native ;
- 10 000 mots cachés par passeport ;
- sérialisation et audit exact des sémantiques utilisées.

## 7. Baselines

- B1 : rôles fixes sans sondage ;
- B2 : sémantiques aléatoires sans sondage ;
- B3 : carte oracle, plafond externe.

Le score de référence sans information est le maximum entre B1 et B2.

## 8. Contrôles négatifs

Douze machines : quatre bases monotones insuffisantes, quatre bases à opération universelle instable, quatre bases non reproductibles. Toutes doivent provoquer une abstention.

## 9. Budgets

120 sondes, 75 000 candidats, 120 secondes CPU, 320 composants, 16 MiB sérialisés.

## 10. Critères d’acceptation

1. au moins 32 migrations principales exactes sur 36 ;
2. au moins 10 sur 12 par machine ;
3. toutes les sémantiques stables utilisées identifiées exactement ;
4. tous les succès exactement équivalents et à 100 % caché ;
5. aucun succès au-delà de 120 sondes ;
6. avantage d’au moins 12 migrations sur la meilleure baseline sans sémantique vraie ;
7. écart d’au plus deux migrations avec le plafond oracle ;
8. 12/12 abstentions négatives ;
9. zéro faux succès négatif ;
10. isolation scellée et traçabilité du premier run.

## 11. Portée

Un succès démontre seulement une découverte bornée de sémantiques booléennes opaques et une migration exacte de compétence finie. Il ne démontre pas une adaptation à une physique continue ou arbitraire.
