# Genesis Free Metamorphosis v7.2 — research-history window synchronization erratum

**Status:** prospective control-plane repair after canonical Attempt 018, before Attempt 019  
**Date:** 20 September 2026  
**External observations consumed by this repair:** 0  
**Canonical A018 external observation:** preserved from run `35512801831`; not rerun

## Trigger

After canonical Attempt 018, the accumulated aggregate research history crossed the already-frozen public context bound `MAX_HISTORY = 24`.

The proposer context builder already used the bounded history:

```text
(prior_v6_history + v7_attempt_history)[-24:]
```

The post-observation research refresh helper still used the unbounded concatenation. A018 itself completed its frozen external evaluation successfully, but generation of the next proposer context refused because the research-memory digest stored by the unbounded refresh no longer matched the 24-item memory recomputed by the context builder.

## Repair

v7.2 changes only the control-plane synchronization rule so the post-observation refresh uses the same already-declared 24-item history window as the context builder.

The following scientific authorities remain unchanged:

- external evaluator and hidden cases;
- `research_strategy_v7.py` deterministic tournament scorer;
- `fitness_policy_v7.py` promotion/neutral/rejection policy;
- strategy weights and generation;
- parent-selection rule;
- attempt and retained-generation budgets;
- canonical A018 proposal, transcript, child tree and observation.

The v7.2 control head is `395e240a25c5e4ec30d9ac57d62a9ebbfff201b4`. Its Python 3.11 and 3.13 control matrices pass, including explicit byte-identity checks for the frozen scorer and fitness policy relative to v7.1.

## Canonical A018 recovery boundary

The external evaluator was **not** rerun.

The recovery reconstructed the exact A018 child tree from the preserved A018 proposal and parent, replayed the already-recorded canonical observation locally, reproduced the original post-observation unbounded research-memory digest and state digest, then applied the bounded-history repair as a separate control-plane transition.

Canonical A018 identities remain:

- canonical evaluator run: `35512801831`;
- proposal patch SHA-256: `94e1ce0a6e2ab9b1f555f388fcbdc5169555e8088ee12589df562f13620eaf2b`;
- transcript SHA-256: `ad6e9ba3c8fdd0371b8a099878b9e81e7f714b563ecc1f7afcbbdd1e7618034c`;
- child tree: `42d818da1221e26cf0ceb1af016d57bbedf03ff662ef5d805bb67e9dd60f5bec`;
- observation result digest: `e6316aa96937d702d8c62037e096000f4b5d6dc18d3ff4ad8d72ec59c7dc9ed6`;
- neutral id: `neutral-018-42d818da1221`, depth 2.

The original unbounded post-observation memory digest was `e425268898125b726c17e094933510bb52c5f6a63279881b73f2999fbd1167e3`, with original state digest `4131137fbd8392a3a72c92d78d391a67eedfb6b7ad1456fbd5dc5380c1ad9729`.

After the prospective v7.2 synchronization transition, the bounded research-memory digest is `85b22913eeef9c3a3835718036bc904d3fbfe3d9e6b9c882f51b3c343cb1294e`, with state digest `e7bf454e34bd769575897411ba59317f6f4f6daa05ed654e95ae559832fcf01a`.

## Continuation rule

Attempt 019 and later proposer contexts use the synchronized 24-item aggregate-history window. Prior canonical evaluator measurements are not rewritten. A018 counts exactly once toward the 24-observation budget.
