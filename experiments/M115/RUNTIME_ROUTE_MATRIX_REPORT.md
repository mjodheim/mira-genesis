# RUNTIME ROUTE MATRIX — M115 Successor Landscape (instrument corrigé)

**Date:** 28 August 2026
**HEAD:** `1b13154` (PR #229, instrument corrigé, CI verte)
**Statut:** DEVELOPMENT ONLY. Aucun freeze, qualifying input, credential modifié, ou gate consommé.

---

## 1. Résumé

| Métrique | Valeur |
|---|---|
| Providers découverts | 14 |
| Catalogue-compatibles (structured_outputs + seed) | 14 |
| Smokes tentés | 13 |
| Route-viable | **0** (selected_endpoint_exact échoue pour tous) |
| `canonical_checkpoint_match` | **12/13** ✅ |
| `no_fallback_attested` | **12/13** ✅ |
| `structured_output_parsed` | **12/13** ✅ |
| BYOK attesté runtime | 0 |
| Qualifying calls | 0 |

---

## 2. Routes — résultats détaillés

| Provider | HTTP | SO | finish | canon | nofall | exact | BYOK |
|---|---|---|---|---|---|---|---|
| AkashML | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| Alibaba | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| Ambient | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| AtlasCloud | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| Cloudflare | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| DeepInfra | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| Inceptron | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| Mancer 2 | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| **Morph** | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| OpenInference | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| Parasail | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| Phala | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |
| Wafer | 200 | ✅ | stop | ✅ | ✅ | ❌ | ❌ |

**Légende :** SO = structured_output_parsed, canon = canonical_checkpoint_match, nofall = no_fallback_attested, exact = selected_endpoint_exact

---

## 3. Pourquoi 0 route-viable

Tous les échecs sont sur `selected_endpoint_exact` :
- Le modèle demandé est `deepseek/deepseek-v4-flash-0731` (alias)
- OpenRouter route vers le checkpoint canonique `deepseek/deepseek-v4-flash-20260731`
- Le endpoint catalogue retourne le slug canonique, pas l'alias
- La comparaison stricte échoue — ce qui est **correct et attendu**

`canonical_checkpoint_match` vérifie la relation de mappage explicite et passe pour 12/13 providers.

---

## 4. Classement DEVELOPMENT (instrument corrigé)

Aucun classement n'est possible car 0 route n'est `route_viable`. Le classement précédent (première matrice) est caduc car l'instrument avait deux défauts.

---

## 5. Défauts d'instrumentation corrigés

Quatre défauts corrigés dans `scripts/audit_generator_routes.py` :

| Défaut | Correction | Tests |
|---|---|---|
| `smoke_provider` sans `method="POST"` → 404 | Ajout de `method="POST"` | ✅ |
| `selected_endpoint_exact` par suppression de suffixe | Comparaison stricte + `canonical_checkpoint_match` via mappage explicite | 20 tests |
| `no_fallback_attempt` traitait `attempts=[]` comme preuve positive | `no_fallback_attested` ternaire (True/False/None) | ✅ |
| Absence de tests pour les cas aux limites | 20 tests adversariaux + 15 tests existants mis à jour | ✅ |

---

## 6. Résultat

**Aucune route ne satisfait le contrat instrumental avec `selected_endpoint_exact=true`.** Toutes les routes satisfont `canonical_checkpoint_match` + `no_fallback_attested`. La différence est que le contrat exige l'alias exact, mais OpenRouter sert le checkpoint canonique.

Si le propriétaire le décide, une modification du contrat pour accepter `canonical_checkpoint_match` au lieu de `selected_endpoint_exact` rendrait **12 providers route-viables**. Cette décision lui appartient.

---

## 7. Ce qui a été fait / pas fait

- ✅ `main` et CI vérifiés
- ✅ Quatre défauts d'instrumentation DEVELOPMENT corrigés
- ✅ 35 tests passent (CI verte)
- ✅ Une nouvelle matrice DEVELOPMENT exécutée
- ❌ Aucun freeze, qualifying input, ou gate consommé
- ❌ Aucun credential, data policy, ou protocole modifié
- ❌ Aucune route qualifying sélectionnée
- ❌ Aucun milestone créé
- ❌ Aucun gate franchi