# M105 adversarial pre-freeze review

**Date:** 24 August 2026  
**Status:** implementation complete; development rehearsals only; no final protocol or canonical
result exists

## Strongest alternative explanations examined

1. **The accepted feature is an authored target in disguise.** The acquisition implementation has
   no future carrier/action identity and no target truth table or accepted tree. Its lower image is
   independently closed over all sixteen two-input Boolean functions. DEVELOPMENT labels all four
   signal pairs twice under different nonces; exactly one semantic class survives. The serialized
   feature contains only an expression and its computed truth table.
2. **The host adapter performs the missing conditional.** JSON and SQLite action adapters accept
   descriptors and carrier state only. Context is resolved exclusively by the live state-owned
   feature before a stored branch trace is selected. Static audit and content-address-valid semantic
   mutation both check this boundary.
3. **Persistence is reconstruction.** Later acquisition capsules receive W1/W2 bytes and their
   current demand only. They contain neither DEVELOPMENT nor the producer process. The fresh arm
   receives the same runtime, exact M104 predecessor, current demand and complete sixteen-semantic
   enumeration but no F or DEVELOPMENT bytes.
4. **The baseline merely runs out of search.** Both fresh arms exhaust all sixteen feature semantics.
   Four distinct diagnostic behavioral classes survive for each carrier, so refusal is due to
   underdetermination, not time or budget.
5. **The dependency is decorative.** Each consumer definition stores F's content address and resolves
   F at execution. Removal fails decoding/acquisition/execution. A valid complementary feature plus
   dependency rebinding executes successfully and reverses the precommitted hidden behavior.
6. **M104 could already express the claimed rule with more budget.** Its exact inherited definitions
   are finite full-context dispatches. The independent checker constructs a fresh omitted context for
   each definition, and an isolated execution witness fails to materialize that context. Repetition
   cannot change the representation image.
7. **Qualification leaks into the producer.** The producer capsule contains the bound runtime, exact
   M104 bytes, DEVELOPMENT observations and an ambiguity control only. It contains no qualification
   pool, JSON/SQLite demand, hidden case, authoring script, result or checker. Later capsules do not
   contain DEVELOPMENT.
8. **A positive result would imply lower-interpreter ownership.** It would not. The Boolean
   primitives, interpreter, two-signal contract, eight-node bound, carriers, tasks, adapters and
   evaluator remain authored and form the next frontier.

## Controls implemented

- exact byte migration and M100-M104 conservation;
- build-without-register and ambiguous-DEVELOPMENT refusal;
- exhaustive fresh and repeated-fresh baselines for both carriers;
- unseen signal/nonce hidden cases;
- feature removal before later acquisition and after compilation;
- content-address-valid semantic mutation with live dependency rebinding;
- corruption refusal and byte-exact rollback from mutation and corruption;
- independent semantic, definition and M104-closure checkers;
- isolated process chronology and zero model/network/remote-execution calls;
- two full development rehearsals with identical stable evidence projection.

## Pre-freeze instrument defects found and corrected

M103 was lost to an instrument failure rather than a falsified mechanism, so the freeze lifecycle
itself was rehearsed end to end in a throwaway clone: candidate build, annotated candidate tag,
final protocol build, annotated freeze tag and runner preflight. The canonical `materialize` path
was deliberately **not** executed anywhere, so the unique attempt is unconsumed and its outcome
unknown.

Two defects were found and corrected before any candidate existed:

1. **The single checker attempt could be burned by a premature invocation.** Running
   `scripts/check_m105_result.py` with no canonical `RESULT.json` present caught the
   `FileNotFoundError` inside the verdict path, materialized `CHECK_REPORT.json` with
   `verdict: negative`, and thereby both recorded a false negative verdict and made the canonical
   run refuse on an existing evidence path. The absence of a result is a precondition failure, not
   a predicate evaluation. The checker now refuses with schema `m105-check-refusal-v1`, writes
   nothing and exits 3; a present-but-corrupt result still fails closed to a real negative report.
   No predicate semantics, falsifier or verdict rule changed.
2. **The freeze machinery was not bound to its own validator.** `tests/test_m105_protocol_builder.py`
   was absent from the protocol's apparatus file list and could therefore have changed after the
   freeze without detection. It is now bound.
3. **The apparatus binding was checkout-dependent.** M105 binds every apparatus member by raw-byte
   SHA-256, but twenty-one of its thirty-nine members — every Python and Markdown file — had no
   end-of-line attribute. A fresh Windows clone checks those out with CRLF, so a protocol frozen on
   one machine records digests no other Windows checkout can reproduce and `require_frozen` refuses
   with `M105 bound apparatus changed`. This was verified empirically in a throwaway clone, against
   `metamorphosis/m103_runtime.py` as an LF control. M103 and M104 each had to add the same entries;
   M105's were missing. `.gitattributes` now pins them, and the JSON fixtures were already covered
   by the `experiments/M1*` rule.

4. **The rehearsal test asserted a canonical-runtime fact it could not have.**
   `test_development_rehearsal_satisfies_all_predicates_with_stable_replay` asserted all sixteen
   predicates true, but P1 pins CPython 3.11.16 with SQLite 3.53.1, so it is correctly false on any
   other interpreter. Both CI jobs therefore failed on that single test — P2-P16 held on Linux under
   both 3.11 and 3.13, and only P1 differed — which would have left CI permanently red on the frozen
   commit and made the evidence commit unable to pass first CI, the standard every prior milestone
   was held to. The test now asserts P2-P16 unconditionally and P1 iff the interpreter is the
   canonical pair. The frozen verdict rule is unchanged: a canonical attempt still requires P1-P16
   all true, and `require_frozen` refuses to run off the canonical runtime, so P1 cannot be dodged.

Separately, `experiments/M100/RESULT.json` and `CHECK_REPORT.json` held stale CRLF working-tree
copies predating that rule, which made M101's predecessor verifier compare a CRLF `git hash-object`
against its LF preservation-tag blob and refuse. The working tree was renormalized to the bytes
already committed; `git diff --cached` staged nothing, so no recorded evidence, digest or verdict
changed.

The direct-script entry point that killed M103 was re-verified: `python scripts/check_m105_result.py`
imports and executes from a clean checkout with no import error.

## Remaining authored ceiling

Even a fully positive M105 would be bounded evidence that a state-owned executable high-level
constructor feature changes validated reach. It would not show that Genesis can invent, acquire or
replace the lower primitives/interpreter itself. M106 must be derived from that ceiling if M105
qualifies, or from the exact failed predicate if it does not.
