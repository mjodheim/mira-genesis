# Genesis II preprint — proposed submission metadata

**Status: PROPOSAL. No manuscript exists, no DOI is reserved, and nothing here has been submitted.**

This file records what a Genesis II package would claim if the owner decides to publish. It is
downstream of the scientific record in the strict sense: every number below is read from a frozen
result, and no experiment may be altered to serve any sentence in it.

## Author

Anthony Mets, Independent Researcher. AI development assistance is recorded in
`docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md`; no AI system is an author.

## Proposed scope

**M107 through M111**, with M112 named as the architecture and its bank recorded as absent.

Genesis I (`10.5281/zenodo.22067855`) covers M094–M100 and is not rewritten. Its stated limitation —
that the qualified cumulative chain lives inside one authored operation family — is the sentence this
package starts from.

| milestone | decision | what it contributes to the paper |
|---|---|---|
| M107 | D076 | first endogenous extension of the lower interpreter; reach 4 → 16 by acquiring one operator |
| M108 | D077 | first modification of the acquisition machinery itself; blame labels still authored |
| M109 | D078 | two successive machinery generations; the lineage determines its own blame labels by controlled trial |
| M110 | D079 | causal transfer into a materially different carrier — and an acquired improvement measured **doing harm** |
| M111 | D080 | self-directed diagnosis under a scarce experiment budget, at recursive depth three by lemma |
| M112 | — | the receiving architecture for an externally authored world bank; **the bank does not exist** |

## Three candidate titles

1. **When an Acquired Improvement Makes Things Worse: Bounded Machinery Self-Modification and the
   Limits of Its Transfer**
2. **Census-Conditional Transfer: A Bounded Software Lineage That Improves Its Own Acquisition
   Machinery, and Where That Improvement Stops**
3. **Capacity Without Competence: Three Generations of Acquisition-Machinery Improvement in a
   Persistent Software Lineage**

The first is recommended. The harm result is the paper's most defensible contribution and the one a
reviewer is least likely to have seen before; leading with it also makes the positive results harder
to dismiss as selective reporting.

## Proposed abstract (211 words)

> A software lineage that modifies the machinery it uses to acquire capabilities raises an obvious
> question and a less obvious one. The obvious question is whether such a modification helps. The
> less obvious one is where it stops helping. We report five frozen experiments in a bounded,
> model-free setting in which a lineage extends its own interpreter, then modifies its acquisition
> machinery, then uses the modified machinery to produce a second modification, with the attribution
> labels determined by the lineage's own controlled trials rather than supplied. We then restore that
> machinery, unchanged, into a materially different carrier — reference-bearing JSON records over a
> four-valued chain — that took no part in producing it. Transfer is **conditional on the producer's
> own failure census**: inside it the restored machinery strictly increases resolved capability, and
> outside it the same machinery is confidently wrong and strictly worse than the fresh predecessor it
> improved on, while its reachable set grows monotonically throughout. Capacity rises; competence
> does not. A further experiment shows the lineage can recover part of that gap by deriving, from a
> record spanning its own history, which observations do not determine an answer, and spending a
> scarce experiment exactly there — a derivation inexpressible in the language it held one generation
> earlier. All carriers remain project-authored; no generality gate advances.

## Primary claim

**Bounded multi-generation acquisition-machinery improvement with census-conditional causal transfer
and self-directed diagnosis, at recursive depth three.**

## Secondary claims

1. An acquired machinery improvement can be measured **doing harm**, on a failure geometry its
   producer could not present, while its `ReachImprove` grows strictly. *(M110: 6/6 for the fresh
   control, 0/6 for both descendants, on the row the producer's census could not reach.)*
2. The boundary of transfer is **derivable before the consumer runs**, from the producer's own
   attribution census plus the conservatism rule its adoption used.
3. A lineage can identify, from its own pooled record, the observations its vocabulary does not
   determine, and spend a scarce experiment there — outperforming every static strategy and both
   fixed probe strategies **under an equal budget**.
4. Generation *n* can create the **expressibility** of generation *n+1* as a side effect of resolving
   its own demand, verified by a monotonicity lemma rather than by a failed search.
5. The instruments are falsifiable in practice: three of the eleven milestones on this line are
   preserved **negative** results, and defects were allowed to invalidate evidence rather than be
   repaired after the fact.

## Limitations, to be stated in the paper and not only in an appendix

- **Every carrier, registry, feature vocabulary, probe primitive and evaluator is project-authored.**
  No gate in `MIRA_GENERALITY_CRITERIA.md` advances; G7 has no evidence at all.
- The M110 consumer family was **chosen** to reach the row that breaks the acquired rule, and the
  M111 population was **selected for ambiguity**. Both are declared in the frozen protocols.
- The M111 probe is an authored primitive. The lineage does not invent experimentation; it decides
  where to spend one. Elimination is complete only because two candidates remain.
- No model is called anywhere on this line. Nothing here is evidence about language-model agents, and
  nothing here should be compared to one.
- Recursive depth three is bounded by an authored registry ceiling. It licenses neither "open-ended"
  nor "compounding": **no acceleration is claimed**, because no pre-registered trend across
  generations survives its controls.
- Everything is single-site. There is no independent reproduction and no external adversarial audit.

## Claims the paper must not make

AGI; general intelligence; intelligence explosion; open-ended or unbounded self-improvement;
autonomous self-evolution; independent external-domain transfer; any statement that a generality gate
has been closed.

## Recommended categories and keywords

Primary `cs.AI`; cross-list `cs.SE`, `cs.LG`.

Keywords: recursive self-modification; acquisition machinery; causal transfer; negative transfer;
capability–competence dissociation; self-directed diagnosis; pre-registration; frozen protocols;
adaptive software lineage.

## Artifacts to archive

| artifact | why |
|---|---|
| `experiments/M107` … `experiments/M111` in full | protocols, results, check reports, adversarial reviews, pre-freeze rehearsals |
| `metamorphosis/m107_runtime.py` … `m111_runtime.py` | the substrate chain, imported unchanged at each level |
| `scripts/run_m1{07..11}_*.py`, `scripts/check_m1{07..11}_result.py` | orchestration and the independent checkers |
| `tests/test_m1{07..11}_*.py` | the milestone suites |
| `DECISIONS.md` (D076–D080), `FAILURE_LOG.md` | including the preserved negatives |
| `docs/CURRENT_RESEARCH_FRONTIER.md`, `MIRA_GENERALITY_CRITERIA.md` | the interpretation layer and the gates that did not move |
| `experiments/M112` | the architecture, with the bank recorded as absent |

## Exact snapshot to freeze

The publication snapshot must be a **merge commit on `main`** at or after PR #209, so that all five
milestones and their preserved results are present. The tags below are the scientific anchors and
must be pushed before the deposit:

```
experiment/m107-positive-result
experiment/m108-positive-result
experiment/m109-positive-result
experiment/m110-positive-result
experiment/m111-positive-result
```

Recommended anchor commit: `566e498` — *Merge pull request #209*, the point at which M111 entered
`main`. If M112 is included in scope, use its merge commit instead.

## Decision the owner has to make, and the honest reading

**Recommendation: PUBLISH, at M111.**

The frontier condition set in the previous mandate was one additional closed objection. Two were
closed — a positive cross-carrier transfer *and* a precisely located structural ceiling — and a third
result was added on top. Waiting for an externally authored bank means waiting on a third party, and
that wait has no defined end.

The argument against is worth stating too: without M112's bank, every world in the paper is one this
project chose, and a reviewer is entitled to say so. The reply is that the paper says so first, in
the abstract, and that the harm result cuts against the interest that selection would serve.
