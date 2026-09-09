# Architecture audit — M107–M112 as Genesis primitives

**Prospective engineering audit, 8 September 2026. Reads frozen sources; changes none of them.**

The mechanisms qualified in M107–M112 are the primitives of the metamorphosis objective stated in
[`METAMORPHOSIS_TARGET.md`](METAMORPHOSIS_TARGET.md). This audit asks, for each: **what does the
lineage actually own, what is still written by the host, what is only an experimental limitation,
and what can become a generic interface in the integrated runtime.**

Sources audited: `metamorphosis/m107_runtime.py` (522 lines), `m108_runtime.py` (845),
`m109_runtime.py` (852), `m110_runtime.py` (1021), `m111_runtime.py` (692), `m112_world_bank.py`
(425). Nothing in them is modified; the runtime will reuse their invariants by construction, not by
editing their sources.

## The shape that already exists

The modules chain by **import**: M109 imports M108 as `base`, M110 imports M109 as `lineage`, M111
imports M109 as `machinery` and M110 as `consumer`. There is therefore a real lineage — of *source
files*, resolved at import time. What does not exist is a lineage of **runtime state**: each
milestone declares its own state schema (`m107-lineage-state-v1` … `m111-diagnostic-state-v1`) and
rebuilds it from the ones below.

That distinction is the whole gap. The program has ancestry in its code and none in its execution.

## Mechanism-by-mechanism

### 1. Endogenous extension of the lower interpreter — M107

| | |
|---|---|
| **Lineage-owned** | the acquired operator, held as state; the decision to acquire it; the constructive reach it unlocks |
| **Host-written** | `operator_space()` — the enumerable space the acquisition draws from; `MAX_EXPRESSION_NODES = 9`; `MAX_ACQUIRED_ARITY = 2`; the two-signal interface |
| **Experimental limitation only** | the specific 2-signal / 16-function world; `SIGNAL_ROWS` |
| **Generic interface** | `complete_image()` and `insufficiency_certificate()`. These prove *by exhaustion or by a monotonicity lemma* that the current body cannot express a target, independently of budget. That is the reusable form of "the lineage established its own limitation" and it must be an interface in the runtime, not a per-milestone function. |

The insufficiency certificate is the single most valuable artifact in this line: it converts "the
search failed" into "the search could not have succeeded", which is what makes an acquisition
causally necessary rather than merely helpful.

### 2. Modification of the acquisition machinery — M108

| | |
|---|---|
| **Lineage-owned** | the attribution rule, held as lineage state and expressed in the lineage's own language |
| **Host-written** | `COMPONENTS = ("operator_table", "signal_interface")` — a module constant; `FEATURE_NAMES`, two features; `MAX_MACHINERY_STEPS = 2` |
| **Experimental limitation only** | `WORLD_SIGNAL_WIDTH = 3`, the specific lift/liftable-image construction |
| **Generic interface** | holding the *rule that assigns blame* as state rather than as code. This is what makes depth ≥ 1 possible at all, and it generalises directly. |

### 3. A modified machinery producing the next modification — M109

| | |
|---|---|
| **Lineage-owned** | generation 2's rule, derived from the lineage's own experimental blame findings rather than host annotations |
| **Host-written** | `COMPONENT_CANDIDATES = "candidate_space"` added to the tuple **by the host**; `CANDIDATE_SPACES = ("monotone", "complete")` — two named spaces, both host-supplied; `MAX_MACHINERY_GENERATIONS = 2` |
| **Experimental limitation only** | the particular `ReachImprove` 6 ⊂ 20 ⊂ 243 chain |
| **Generic interface** | `candidate_space_closure_certificate()` — closing a component by lemma. Same family as M107's certificate and belongs to the same runtime interface. |

**The pattern to notice:** each new *class of thing the lineage can modify* arrived by a human
editing a tuple. M108 has two components, M109 three, M111 four. The lineage has never named one.

### 4. Transfer into a materially different consumer family — M110

| | |
|---|---|
| **Lineage-owned** | the transferred cascade and the reach it adds inside the producer's attribution census |
| **Host-written** | the consumer family itself — `VALUES`, `VISIBLE_FIELDS`, `DOCUMENT_COUNT`, the operator constructors; the census that bounds where transfer is expected to hold |
| **Experimental limitation only** | five documents, three visible fields |
| **Generic interface** | the **bounded transfer claim**: strictly adds capability inside a declared census and strictly removes it outside. A transfer measured only where it helps is not measured. This bound must be a runtime property. |

### 5. Self-directed diagnosis and probe — M111

| | |
|---|---|
| **Lineage-owned** | the diagnostic policy, held as state, expressed in the lineage's language; the decision of *where* to spend a scarce probe |
| **Host-written** | `COMPONENT_DIAGNOSTIC` added to the tuple by the host; `PROBE_ORDERS` — two hardcoded orderings; the `probe()` primitive itself; `DEFAULT_PROBE_BUDGET = 1` |
| **Experimental limitation only** | budget of exactly one probe |
| **Generic interface** | `probe()`'s **shape**: speculatively extend a component, ask whether that resolves the demand, roll back, and *prove the rollback* by comparing the serialized state byte-for-byte before and after. Speculation with proven rollback is a runtime primitive. |

### 6. Content-addressed state and its validation — M107–M111

Every state carries `state_digest`, and `decode_state()` does not merely check it: it **rebuilds the
state from its parts and compares the rebuilt digest**. A forged state is not caught by a rule
someone remembered to write; it is a value that does not reconstruct.

This is the strongest reusable invariant in the line and goes into the runtime unchanged in spirit.

### 7. Persistence and process death — M099, and absent here

M099 qualified hard process-death persistence, but **none of the M107–M111 modules writes to disk**.
Persistence lives in each experiment's runner. The runtime must own it generically, or every future
mechanism re-implements it.

### 8. Ablation, mutation, rollback

Present throughout and consistently done well: ablation returns to a byte-identical S0, mutation and
corruption are refused, rollback is exact. These are runtime obligations, not per-milestone controls.

## The three authored ceilings, stated precisely

The directive names three handholds to attack. This audit locates them exactly.

### Ceiling 1 — the component registry is closed by validation, not merely unset

`m111_runtime.py`, `decode_state()`:

```python
if list(value.get("component_registry") or []) != list(COMPONENTS):
    raise ValueError("M111 component registry changed")
if list(value.get("feature_vocabulary") or []) != list(FEATURE_NAMES):
    raise ValueError("M111 feature vocabulary changed")
```

The lineage does not merely lack a way to add a component class. **The decoder rejects any state
whose registry differs from the host's module constant.** A state carrying a self-named fifth
component is not unsupported — it is invalid.

`probe()` enforces the same closure from the other side:

```python
if component not in machinery.COMPONENTS:
    raise ValueError("M111 probe names a component outside the registry")
```

So the lineage cannot name a new component class, cannot hold one in state, and cannot probe one.
This is the first priority, and the fix is not to delete the check — the check is what makes the
state honest. The runtime needs a registry that **grows by evidence**, where an added component
carries a certificate that the previous registry could not express the limitation, and where the
digest covers the grown registry so nothing is smuggled in.

### Ceiling 2 — the diagnostic vocabulary is a fixed tuple

`FEATURE_NAMES` is declared once in M108 and inherited unchanged through M111. M113's pre-freeze
survey already found this inherited three-feature vocabulary **ambiguous on four of six occupied
rows**, including one M111 recorded as determined.

That is the empirical trigger the second priority needs: two situations the existing features cannot
distinguish. The runtime must let the lineage extend the vocabulary when it meets such a pair — and
must require proof that the *old* vocabulary could not separate them, not merely that the new one
does.

### Ceiling 3 — the probe is a host primitive over host-named components

`probe()` is written by the host, takes a host-named component, and applies host-written extension
functions (`extend_signal_interface`, `extend_operator_table`, `_widened_then_extended`).
`PROBE_ORDERS` offers exactly two orderings. The lineage chooses *among* prepared experiments; it has
never composed one.

The third priority requires the lineage to construct or compose a new experimental probe when
passive observation cannot determine the cause. Selection from a prepared list does not qualify.

## What this means for the runtime

The audit yields the interfaces the integrated runtime must expose, each already validated in a
bounded setting:

1. `LineageState` — content-addressed, rebuild-verified, versioned, and **persistent**, unifying the
   per-milestone schemas without editing them.
2. An **insufficiency certificate** interface — prove a target is unreachable by exhaustion or lemma,
   not by a failed search.
3. A **component registry that can grow by evidence**, with the growth covered by the state digest.
4. A **diagnostic vocabulary that can grow by evidence**, on a demonstrated indistinguishability.
5. A **speculation primitive with proven rollback**, generalised beyond a fixed component list.
6. A **bounded transfer claim** — strict gain inside a declared census, strict loss outside.
7. **Ablation, mutation, corruption and exact rollback** as permanent runtime obligations.
8. **Causal dependency between generations**, measured by real ablation at equal budget, as a
   property of every generation rather than a control written once.

None of these requires editing a frozen module. All of them are already true somewhere in
M107–M112; none of them is true in one program.
