# M101 pre-run amendment 003 — remove the host-side composition shortcut

**Date:** 2026-08-23  
**Status:** accepted correction before any canonical attempt  
**Superseded freeze:** `experiment/m101-frozen-protocol-v3` (`ef7a0945ede28128ebde956effc032aaa85011af`)  
**Qualification population executed before this amendment:** no  
**Scientific result existed before this amendment:** no

## Defect found by adversarial audit

The v3 runtime claimed that T0's constructive image contained at most one atomic effect, while the
retained arm and fresh baseline had the same runtime semantics. That claim was false.

Both `metamorphosis/m101_runtime.py` and `metamorphosis/m101_executor.py` contained a host helper
that enumerated an ordered tuple of atomics and executed it directly (`infer_slots` / `resolve_slots`
through `apply_pipeline`). On a development-only record fixture, T0 found the two-effect binding
`[0, 1]` in nine candidates and produced the correct held-out output without any registered A.

The recorded baseline nevertheless called a different one-atomic-only function from the
acquisition capsule. Its 0/8 score would therefore have been caused by an arm-specific prohibition,
not by a constructive limitation of the otherwise identical T0 runtime. This is the disguised
`compose` primitive and baseline-parity falsifier named in the pre-registration and pre-implementation
review.

No M101 qualification world was executed to find this defect. The reproduction used only a
development fixture. The v3 tag remains immutable as a refused pre-run protocol and cannot support a
scientific claim.

## Correction

The successor mechanism preserves H46, the fifteen conditions, the complete frozen population and
all thresholds, but materially changes the mechanism and controls:

1. `apply_pipeline`, `infer_slots` and `resolve_slots` are removed from both M101 runtimes.
2. A candidate or registered A binding can be tested only by interpreting that explicit A body over
   opaque slots. B bindings can be tested only through the explicit B body and its live A call.
3. The acquisition capsule contains no hidden-case reader and no execution helper.
4. T0 and T1 consumer comparisons now call the same `execute-a` action in the same execution-only
   capsule with the same exact world bytes. Their input states are machine-diffed; the only permitted
   differing keys are `definitions` and the `state_digest` implied by A registration.
5. T0's branch enumerates only one-atomic applications. Repeating that finite image spends the same
   `catalog_size ** 2` candidate budget as registered-A binding, but cannot compose candidates.
6. The live A fault now replaces the second distinct effect with a duplicate of the first. This
   prevents carrier rebinding from compensating for a mere reversal while retaining a digest-valid,
   content-addressed dependency graph.
7. The boundary audit and independent verdict checker fail when the host shortcut returns, when the
   arms use different executors/actions/world bytes, or when their state diff contains any extra key.

Targeted development tests pass after the correction. They include forged parity-summary controls
that the checker rejects. The frozen qualification pool remains source-only and untouched.

## Scientific disposition

This is a **material pre-run mechanism correction**, not a reinterpretation and not a retry. A new
candidate commit, protocol binding and immutable v4 tag are required before any canonical attempt.
The v1, v2 and v3 tags remain accessible and refused for their recorded pre-run defects.
