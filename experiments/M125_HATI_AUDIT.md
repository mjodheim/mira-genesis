# Hati — M125/H70 Preimplementation Audit

**Date:** 6 September 2026  
**HEAD:** `7d58df3` (main, PR #272 merged)  
**PR #273:** `7881dd5` — OPEN, MERGEABLE  
**Worktree:** `agent/hati/m125-h70-audit`  
**No network request made. No credential read. No frozen artifact modified.**

---

## 1. Chronology check

| Check | Result |
|---|---|
| PR #272 (M124 state sync) merged | ✅ |
| PR #273 rebased on main after #272 | ✅ |
| HEAD as expected (7881dd5) | ✅ |
| CI on main | ✅ (last run success) |
| Diff limited to 4 governance files | ✅ |
| No accidental/factice paths in diff | ✅ |

**Verdict:** Chronology is clean.

---

## 2. Diff integrity

The PR touches exactly 4 files:
- `IP_ASSET_REGISTER.md` — 1 line added (P-029)
- `docs/IP_REVIEWS/M125_PUBLICATION_REVIEW.md` — new (82 lines)
- `docs/IP_REVIEWS/P029_OWNER_DECISION_2026-09-06.md` — new (32 lines)
- `docs/audits/M125_PREIMPLEMENTATION_REVIEW_2026-09-06.md` — new (308 lines)

No `experiments/M125/` path appears. No code, no schema, no credential. Zero occurrences of the accidental factice path.

**Verdict:** Clean.

---

## 3. Defect coverage (M124 → M125)

| M124 defect | M125 section | Addressed? |
|---|---|---|
| A — unbounded non-target probe dimensions | §3 — bounded probe envelopes, safety cap separated from feature | ✅ Fully |
| B — missing isolated `items` probe | §4 — machine-checkable coverage map, every class covered | ✅ Fully |
| C — empty HTTP 200 / no finish_reason disagreement | §5 — unified `answered` predicate for retry+verdict | ✅ Fully |
| D — `Retry-After` read from wrong header field | §6 — `response_headers` only, normalized, tested | ✅ Fully |
| E — terminal finding masked by later delivery | §7 — short-circuit execution, checker reconstructs precedence | ✅ Fully |

**Verdict:** All 5 defects from M124 are addressed prospectively.

---

## 4. Design requirements (per handoff)

| Requirement | Status | Notes |
|---|---|---|
| probe isolé pour chaque feature, y compris `items` | ✅ | §4, explicit coverage map |
| sorties de probes statiquement bornées | ✅ | §3, finite structural bound proof |
| retry cohérent HTTP 200 vides / absence finish_reason | ✅ | §5, unified `answered` predicate |
| lecture correcte de `Retry-After` | ✅ | §6, from `response_headers` |
| 4xx déterministe terminal | ✅ | §5, instrument/request error, not transient |
| verdict terminal prioritaire et impossible à masquer | ✅ | §7, short-circuit + checker reconstruction |
| pinning déterministe des cardinalités avec census inchangé | ✅ | §8, `ceil((min+max)/2)` + census proof |
| calibration fraîche 8/16/32, sans redraw | ✅ | §9, geometric rule, completed points never redrawn |
| sizing déterministe | ✅ | §11, formulas with F=1.25 |
| stress final out-of-sample sans refit | ✅ | §12, band miss closes instrument |
| journal persistant des logical steps répondus | ✅ | §9, each point has digest, resume skips completed |
| **impossibilité de réarmer un verdict terminal** | ⚠️ **GAP** | See §5 below |
| **protocol_sha256 liant sources qui interprètent la mesure** | ⚠️ **GAP** | See §6 below |
| `--execute` fail-closed avant lecture credential | ⚠️ **PARTIAL** | See §7 below |

---

## 5. GAP A — Anti-réarmement d'un verdict terminal

**What the handoff requires:**
> "impossibilité de réarmer un verdict terminal via suppression/remplacement d'un résultat"

**What the design provides:**
- §9: completed calibration points are never redrawn (resume rule)
- §7: checker reconstructs precedence from persisted metadata
- M124 outcome mentions a once-only/finality guard hardened post-hoc

**What is missing:**
- No explicit guard against deleting a committed `READINESS_RESULT.json` and re-running to produce a different outcome
- No guard against replacing a terminal verdict artifact with a modified version
- No guard against re-arming the execution gate after a terminal verdict was produced
- The design relies on the checker reproducing the same verdict, but a checker that never runs because the result was deleted is no guard at all

**Recommendation:** Add a requirement that the execution entry point refuses to run if a committed terminal result artifact already exists under `experiments/M125/`, checked by:
1. working tree presence
2. committed HEAD blob presence
3. any archived attempt presence

This is a hardening of the M124 post-hoc guard, now required prospectively in M125's own design.

---

## 6. GAP B — `protocol_sha256` ne lie pas les sources interprétantes

**What the handoff requires:**
> "protocol_sha256 liant non seulement les paramètres mais aussi les sources qui interprètent la mesure"

**What the design provides (§10):**
> "one protocol digest binds at least: exact pinned schema digest, exact census-equivalence proof, coverage map, calibration counts, retry semantics, route identity, reasoning controls, 32K threshold, 65K ceiling, F=1.25, sizing formulas, verdict rules, request budget, delivery accounting, information-boundary fields"

**What is missing:**
- The Python source files that *interpret* the measurement — the checker, the verdict ladder, the sizing derivation, the probe parser — are not listed in the binding
- A change to `scripts/run_m125_readiness.py` or `metamorphosis/m125_*.py` between freeze and execution could change the measurement interpretation without changing the protocol digest
- The handoff explicitly requires source-level binding

**Recommendation:** Add to §10's binding list: SHA256 digests of every Python module that interprets a measurement, evaluates a verdict, derives a size, or persists a result. This can be a manifest of source files with their digests, verified before any request.

---

## 7. GAP C (minor) — `--execute` fail-closed credential ordering

**What the handoff requires:**
> "futur `--execute` fail-closed avant même lecture de credential tant qu'une autorisation réseau liée au digest exact n'est pas committée"

**What the design provides (§14, test #21):**
> "the network-capable entry point refuses unless a committed protocol/freezing gate exists"

**Issue:**
Test #21 does not specify the *ordering* of the guard before credential reading. If the entry point reads the credential first and *then* checks the gate, a credential validation error could leak information before the gate check. The handoff requires fail-closed *before* credential read.

**Recommendation:** Add explicit ordering: "the network-capable entry point MUST check the committed protocol gate BEFORE reading any credential, and refuse fail-closed if the gate is absent." This prevents any credential-timing or credential-validation side channel.

---

## 8. Implicit permissions

The design repeatedly blocks:
- "no M125 request authorized by P-029" (3×)
- "any network request remains blocked" (2×)
- "H70 has 0 scientific observations"
- "does not authorize qualifying scientific generation, carrier bank, seal, reveal, scoring or result acceptance"
- "does not reset 4/6 delivery ceiling"
- "does not authorize reuse of M122/M123/M124 observations"

**Verdict:** No implicit network or scientific permission found. The boundaries are explicit and repeated.

---

## 9. Calibration isolation

M122/M123/M124 reuse is blocked by:
- §8: pinning changes schema bytes → historical token measurements invalid
- §9: fresh calibration queue 8/16/32, not from historical rates
- §14 test #14: M122/M123/M124 observations absent from sizing inputs
- Ownership decision P-029: explicitly excludes historical calibration reuse

**Verdict:** Clean. No calibration contamination path identified.

---

## 10. Verdict

**Condition: `GO OFFLINE IMPLEMENTATION`** with three blocking corrections:

| # | Severity | Issue | Fix required |
|---|---|---|---|
| 1 | **HIGH** | Anti-réarmement absent | Add explicit guard: execution entry point refuses if committed terminal result exists under `experiments/M125/`, checked by working tree + HEAD blob + archived attempts |
| 2 | **HIGH** | `protocol_sha256` ne lie pas les sources interprétantes | Add to §10 binding: SHA256 manifest of every Python module that interprets a measurement, evaluates a verdict, derives a size, or persists a result |
| 3 | **MEDIUM** | `--execute` credential ordering | Add explicit ordering: gate check before credential read, fail-closed before any credential access |

These three corrections must be reflected in the design documentation before Claude or any agent begins offline implementation. The defects are in the *design specification*, not in any code — no code exists yet.

After these corrections are applied to the design docs, **GO OFFLINE IMPLEMENTATION**: public implementation, offline DEVELOPMENT tests, and hardening may proceed. No network request, no qualifying execution, no scientific run.