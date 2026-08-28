# M115+ — Audit instrumental des routes de remplacement

**Date:** 28 August 2026
**HEAD:** `c3b10ae` (CI verte)
**Statut:** DEVELOPMENT AUDIT ONLY. Aucun freeze, credential, qualifying input, ou gate consommé.
**Credential OpenRouter:** `failure_reason=billing` — indisponible. Aucun smoke probe possible.

---

## 1. État du dépôt

| Vérification | Résultat |
|---|---|
| `main` commit | `c3b10ae` — CI ✅ (3 runs success, dernier 06:13Z) |
| M113/H58 | Fermé — 1× 429, pas de banque |
| M114/H59 | `instrument-aborted` — 3× 429, pas de banque |
| M115 | DeepSeek BYOK ne satisfait pas le contrat gelé |

---

## 2. Le contrat instrumental (inchangé depuis M113)

| Propriété | Valeur |
|---|---|
| **Modèle** | `deepseek/deepseek-v4-flash-0731` |
| **Structured output** | `response_format: {type: "json_schema", json_schema: {strict: true, ...}}` |
| **Seed** | `seed: 0` |
| **Routing** | `provider: {only: ["nom"], allow_fallbacks: false, require_parameters: true}` |
| **BYOK** | Préféré si disponible, mais `route_viable` suffit |
| **Retry** | Aucun — une seule invocation physique |
| **Identité** | Modèle exact, pas d'alias, pas de fallback |

---

## 3. M115 confirmé (inchangé)

DeepSeek first-party BYOK échoue sur **3 blockers fatals** :

| Blocker | Fatal | Preuve catalogue |
|---|---|---|
| **A** — `structured_outputs` non supporté | ✅ | Paramètre absent du catalogue DeepSeek |
| **B** — Data policy exclut DeepSeek | ✅ | Probe contrôle → 404, contrôle Morph/Together → 200 |
| **C** — BYOK jamais exercé | ❌ Seul | `byok_usage=0` toutes fenêtres |
| **D** — `seed` non supporté | ❌ Seul | Paramètre absent du catalogue DeepSeek |

---

## 4. Routes cataloguées compatibles (15 providers)

Découverte publique du catalogue OpenRouter. **Tous** supportent `structured_outputs` + `seed` + endpoint live.

| Provider | Q | Uptime 1d | Uptime 30m | Tag | Note |
|---|---|---|---|---|---|
| OpenInference | fp4 | 100.0% | 100.0% | open-inference/fp4 | Meilleure uptime |
| Alibaba | unknown | 100.0% | 100.0% | alibaba | |
| Cloudflare | unknown | 100.0% | 99.8% | cloudflare | Plus grand ctx (1.3M) |
| AtlasCloud | fp4 | 99.8% | 100.0% | atlas-cloud/fp4 | |
| Inceptron | fp4 | 99.7% | 99.6% | inceptron/fp4 | |
| AkashML | fp8 | 99.6% | 99.6% | akashml/fp8 | |
| NextBit | fp8 | 99.2% | 100.0% | nextbit/fp8 | |
| **DeepInfra** | **fp8** | **99.0%** | **98.9%** | **deepinfra/fp8** | **Meilleur fp8** |
| Ambient | fp4 | 98.8% | 99.2% | ambient/fp4 | |
| **Morph** | **bf16** | **98.3%** | **100.0%** | **morph/bf16** | **Déjà sélectionné, déjà 429** |
| Mancer 2 | fp8 | 98.0% | 99.5% | mancer/fp8 | |
| Parasail | fp8 | 97.8% | 99.9% | parasail/fp8 | |
| Phala | unknown | 96.6% | 98.1% | phala | |
| Wafer | unknown | 96.6% | 100.0% | wafer/fast | |
| Makora | unknown | 95.3% | 97.9% | makora | |

---

## 5. Ce qui reste inconnu (runtime)

Ces propriétés ne peuvent être vérifiées que par un smoke probe DEVELOPMENT avec le credential OpenRouter :

- `is_byok` runtime attestation
- `served_model == requested_model`
- `structured_output_strictly_parsed`
- `finish_reason == stop`
- `no_fallback_attempt` (router metadata)
- `latency_last_30m.p50` (absent du catalogue pour tous)
- BYOK effectif sur le compte

---

## 6. Recommandation

**Je ne franchis aucun gate, ne sélectionne aucune route, ne crée aucun milestone.**

Le catalogue montre 15 providers instrumentally capables. Le critère de sélection de M113 (meilleure quantification → bf16) a sélectionné Morph. Ce résultat tient. Les options pour le propriétaire :

### Option A — Re-sélection sur fp8
Si Morph est exclu pour cause de pool partagé saturé, le meilleur fp8 est **DeepInfra** (99.0% uptime 1d, tag `deepinfra/fp8`). Aussi : AkashML, Parasail, Mancer 2, NextBit.

### Option B — Re-sélection sur fp4
OpenInference (100% uptime, tag `open-inference/fp4`), AtlasCloud, Ambient, Inceptron.

### Option C — BYOK / pool dédié
Un credential dédié BYOK contournerait le `upstream_provider_shared_pool` qui a tué M113/M114. L'owner avait refusé pour Morph (changement d'identité servie).

### Option D — Clore la question carrier
Aucune des 15 routes ne peut être vérifiée runtime sans credential. La question H58/H59 reste instrumentalement non résolue.

---

## 7. Ce qui a été fait / pas fait

- ✅ `main` et CI vérifiés
- ✅ M115 confirmé (DeepSeek BYOK bloqué)
- ✅ 15 providers catalogués compatibles
- ✅ Contrainte credential documentée (billing)
- ❌ Aucun smoke probe (credential indisponible)
- ❌ Aucun qualifying input envoyé
- ❌ Aucun credential, data policy ou protocole modifié
- ❌ Aucune route qualifying sélectionnée
- ❌ Aucun milestone créé
- ❌ Aucun gate franchi