# M115+ instrumental audit — routes disponibles après l'échec DeepSeek BYOK

**Date:** 28 August 2026
**Statut:** **DEVELOPMENT AUDIT ONLY. Aucun freeze consommé. Aucun qualifying call. Aucune banque.**
**HEAD:** `c3b10ae` (CI verte)

---

## 1. État du dépôt

- `main` (`c3b10ae`) : CI ✅ (3 runs success, dernier à 06:13Z)
- M113/H58 : **fermé — instrument failure** (1× 429, pas de banque)
- M114/H59 : **instrument-aborted** (3× 429, pas de banque)
- M115 : **DEVELOPMENT audit — DeepSeek BYOK ne satisfait pas le contrat gelé**

---

## 2. Le contrat instrumental gelé (inchangé depuis M113)

| Propriété | Valeur |
|---|---|
| **Modèle** | `deepseek/deepseek-v4-flash-0731` |
| **Structured output** | `response_format: {type: "json_schema", json_schema: {strict: true, ...}}` |
| **Seed** | Envoyé comme `seed: 0` dans le body canonique |
| **Routing provider** | `provider: {only: ["nom"], allow_fallbacks: false, require_parameters: true}` |
| **BYOK préféré** | Si disponible, mais route_viable suffit |
| **Retry** | Aucun — une seule invocation physique |
| **Identité** | Modèle exact, pas d'alias, pas de fallback |

---

## 3. Résultat de M115 (confirmé)

DeepSeek first-party BYOK échoue sur **3 blockers fatals** :

| Blocker | Fatal ? | Preuve |
|---|---|---|
| **A** — `structured_outputs` non supporté | ✅ Fatal | Catalogue DeepSeek ne liste pas `structured_outputs` ; probe → HTTP 404 |
| **B** — Data policy exclut DeepSeek | ✅ Fatal | Probe sans structured output → HTTP 404 ; contrôle Morph+Together → 200 |
| **C** — BYOK jamais exercé sur ce compte | ❌ Non fatal seul | `byok_usage=0` sur toutes les fenêtres |
| **D** — `seed` non supporté | Non fatal seul | Mais `require_parameters=true` le rend fatal |

---

## 4. Routes cataloguées compatibles avec le contrat

Découverte publique du catalogue OpenRouter le 28 août 2026 :

**15 providers** supportent `structured_outputs` + `seed` + endpoint live :

| Provider | Quantization | Uptime 1d | Uptime 30m | Tag |
|---|---|---|---|---|
| Alibaba | unknown | 100.0% | 100.0% | alibaba |
| OpenInference | **fp4** | 100.0% | 100.0% | open-inference/fp4 |
| Cloudflare | unknown | 100.0% | 99.8% | cloudflare |
| AtlasCloud | **fp4** | 99.8% | 100.0% | atlas-cloud/fp4 |
| **Inceptron** | **fp4** | 99.7% | 99.6% | inceptron/fp4 |
| **AkashML** | **fp8** | 99.6% | 99.6% | akashml/fp8 |
| NextBit | **fp8** | 99.2% | 100.0% | nextbit/fp8 |
| **DeepInfra** | **fp8** | 99.0% | 98.9% | deepinfra/fp8 |
| **Ambient** | **fp4** | 98.8% | 99.2% | ambient/fp4 |
| **Morph** | **bf16** | 98.3% | 100.0% | morph/bf16 |
| Mancer 2 | **fp8** | 98.0% | 99.5% | mancer/fp8 |
| **Parasail** | **fp8** | 97.8% | 99.9% | parasail/fp8 |
| Phala | unknown | 96.6% | 98.1% | phala |
| Wafer | unknown | 96.6% | 100.0% | wafer/fast |
| Makora | unknown | 95.3% | 97.9% | makora |

Les providers qui *ne satisfont pas* le contrat (14 exclus) : **DeepSeek** (pas de so ni seed), **Together, Fireworks, Baidu, Reka, SiliconFlow, Venice** (pas de seed), **Relace, BaseTen, DigitalOcean, StreamLake** (ni so ni seed), **GMICloud, CoreWeave, Novita** (pas de structured_outputs).

---

## 5. Contrainte opérationnelle — credential OpenRouter

**La clé OpenRouter n'est pas disponible dans cette session.** Le fichier `auth.json` enregistre `failure_reason: billing` et la clé n'est présente ni dans l'environnement ni dans le credential pool lisible. **Aucun smoke probe DEVELOPMENT n'a pu être exécuté** depuis ce worktree.

Les données catalogues ci-dessus sont des *observations publiques*, pas des *observations runtime*. Les propriétés suivantes restent donc **inconnues** pour chaque route candidate :

- `is_byok` n'est pas observable sans requête authentifiée
- `serve le modèle exact` (vérifiable seulement par HTTP 200 attesté)
- `structured_output_parsed` (le catalogue dit qu'il supporte le paramètre, pas que le endpoint le sert correctement)
- `finish_reason: stop` (vérifiable seulement runtime)
- `no_fallback` (vérifiable seulement via `X-OpenRouter-Metadata`)
- `latency_last_30m.p50` (le catalogue ne renvoie pas ces métriques pour tous)

---

## 6. Le problème instrumental racine

```
M113 → Morph (bf16, pool partagé) → 1x 429 → pas de banque
M114 → Morph (bf16, pool partagé) → 3x 429 → pas de banque  
M115 → DeepSeek BYOK (première partie) → pas de structured_outputs → bloqué
```

L'historique montre que **le pool partagé de Morph** est le goulot : tous les 429 viennent de `upstream_provider_shared_pool`. L'owner a refusé d'introduire un credential dédié BYOK pour Morph au motif que cela changeait l'identité servie.

---

## 7. Recommandation au propriétaire

**Je ne franchis aucun gate, ne sélectionne aucune route qualifying, ne crée aucun nouveau milestone.**

Le catalogue montre **15 providers** instrumentally capables. Le critère de sélection de M113 (meilleure quantification → bf16) a déjà été appliqué et a sélectionné Morph. Ce résultat tient. Les options suivantes existent pour le propriétaire :

### Option A — Re-sélection sur fp8 (sans changer le critère)
Si Morph est considéré comme défaillant pour cause de capacity partagée, le meilleur candidat suivant par quantification est **fp8**. Quatre providers fp8 compatibles : **DeepInfra**, **AkashML**, **Parasail**, **Mancer 2**, **NextBit**. DeepInfra a la meilleure uptime 1d (99.0%) et tag `deepinfra/fp8`.

### Option B — Re-sélection sur fp4
Si fp8 n'est pas acceptable : **OpenInference** (fp4, uptime 100%, tag `open-inference/fp4`), **AtlasCloud** (fp4), **Ambient** (fp4), **Inceptron** (fp4).

### Option C — BYOK/Dedicated pool
Un credential dédié BYOK pour l'un des providers ci-dessus contournerait le `upstream_provider_shared_pool` qui a tué M113/M114. Le propriétaire avait déjà refusé cette option pour Morph au motif que cela changeait l'identité servie — ce motif reste valide pour tout autre provider.

### Option D — Clore la question carrier
Si aucun des 15 providers ne peut servir le contrat avec une capacité dédiée, alors la question de H58/H59 reste **instrumentalement non résolue** et la prochaine frontière est l'infrastructure du projet, pas la science.

---

## 8. Ce que cet audit a fait et n'a pas fait

- ✅ A vérifié `main` et la CI
- ✅ A confirmé le résultat négatif de M115
- ✅ A découvert les 15 providers catalogués compatibles
- ✅ A documenté la contrainte credential (billing failure)
- ❌ N'a pas fait de smoke probe (credential indisponible)
- ❌ N'a pas envoyé le qualifying input
- ❌ N'a pas modifié de credential, data policy ou protocole
- ❌ N'a pas sélectionné de nouvelle route qualifying
- ❌ N'a pas créé de milestone
- ❌ N'a pas franchi de gate propriétaire