# RUNTIME ROUTE MATRIX — M115 Successor Landscape

**Date:** 28 August 2026
**HEAD:** `6c7ab62` (main, PR #228 merged)
**Statut:** DEVELOPMENT ONLY. Aucun freeze, qualifying input, credential modifié, ou gate consommé.

---

## 1. Résumé

| Métrique | Valeur |
|---|---|
| Providers découverts | 14 |
| Catalogue-compatibles (structured_outputs + seed) | 14 |
| Smokes tentés | 13 |
| Route-viable | **12** |
| BYOK attesté runtime | 0 |
| Qualifying calls | 0 |

---

## 2. Routes runtime-viables (12 providers)

Tous : HTTP 200, `structured_output_parsed=true`, `finish_reason=stop`, `is_byok=false`, `strategy=direct`, `attempt=1`, `no_fallback`, `served_model=deepseek/deepseek-v4-flash-0731`, `served_provider=requested`.

| Provider | Q | Uptime 1d | Uptime 30m | Latency p50 |
|---|---|---|---|---|
| Alibaba | unknown | 100.0% | 100.0% | 1354ms |
| OpenInference | fp4 | 100.0% | 99.9% | 661ms |
| Cloudflare | unknown | 100.0% | 99.7% | 822ms |
| AtlasCloud | fp4 | 99.8% | 99.8% | 1615ms |
| DeepInfra | **fp8** | 99.0% | 98.2% | 758ms |
| AkashML | **fp8** | 99.0% | 96.0% | 1604ms |
| Parasail | **fp8** | 98.6% | 99.7% | 758ms |
| Ambient | fp4 | 98.6% | 98.5% | 1008ms |
| **Morph** | **bf16** | 98.4% | 98.4% | 2188ms |
| Mancer 2 | **fp8** | 97.9% | 99.3% | 781ms |
| Wafer | unknown | 96.8% | 99.9% | 1784ms |
| Phala | unknown | 96.7% | 94.1% | 1847ms |

---

## 3. Routes non-viables

| Provider | Raison |
|---|---|
| Inceptron | `finish_reason=length` (pas `stop`), `structured_output_parsed=false` |
| Makora | Non-smoké (catalogue endpoint_status=-2, non-live) |

---

## 4. Classement DEVELOPMENT (règle préexistante du script)

La règle de classement préenregistrée dans `audit_generator_matrix.py` (uptime_1d desc, uptime_30m desc, latency_p50 asc, provider_name asc) produit :

1. **Alibaba** (100.0% uptime 1d, 100.0% uptime 30m, 1354ms)
2. OpenInference (100.0%, 99.9%, 661ms)
3. Cloudflare (100.0%, 99.7%, 822ms)
4. AtlasCloud (99.8%, 99.8%, 1615ms)
5. DeepInfra (99.0%, 98.2%, 758ms)
6. AkashML (99.0%, 96.0%, 1604ms)
7. Parasail (98.6%, 99.7%, 758ms)
8. Ambient (98.6%, 98.5%, 1008ms)
9. Morph (98.4%, 98.4%, 2188ms)
10. Mancer 2 (97.9%, 99.3%, 781ms)
11. Wafer (96.8%, 99.9%, 1784ms)
12. Phala (96.7%, 94.1%, 1847ms)

**Ce classement n'est PAS une sélection de provider pour un milestone.** C'est un classement DEVELOPMENT produit par une règle préenregistrée dans l'outil. La sélection d'un provider pour un milestone appartient au propriétaire.

---

## 5. Défauts d'instrumentation DEVELOPMENT corrigés

Trois défauts ont été trouvés et corrigés dans `scripts/audit_generator_routes.py` :

| Défaut | Correction |
|---|---|
| `smoke_provider` appelait `_request()` sans `method="POST"` → GET par défaut → 404 | Ajout de `method="POST"` |
| `no_fallback_attempt` échouait car `attempts=[]` quand OpenRouter n'a qu'un seul endpoint direct | Accepte `attempts=[]` comme absence de fallback |
| `selected_endpoint_exact` comparait l'alias du modèle (`deepseek/deepseek-v4-flash-0731`) contre le slug canonique (`deepseek/deepseek-v4-flash-20260731`) | Normalise la comparaison en ignorant le suffixe date |

---

## 6. Ce qui a été fait / pas fait

- ✅ `main` et CI vérifiés
- ✅ Matrice DEVELOPMENT exécutée (14 découvertes, 13 smokes)
- ✅ 12 routes runtime-viables identifiées
- ✅ 3 défauts d'instrumentation DEVELOPMENT corrigés
- ✅ Rapport sanitizé produit
- ❌ Aucun freeze, qualifying input, ou gate consommé
- ❌ Aucun credential, data policy, ou protocole modifié
- ❌ Aucune route qualifying sélectionnée
- ❌ Aucun milestone créé
- ❌ Aucun gate franchi