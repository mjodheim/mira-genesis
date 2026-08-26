# Genesis II preprint — proposed submission metadata

**Status: PROPOSAL. No manuscript exists, no DOI is reserved, and nothing here has been submitted.**

This file records what a Genesis II package would claim if the owner decides to publish. It is
downstream of the scientific record in the strict sense: every number below is read from a frozen
result, and no experiment may be altered to serve any sentence in it.

## Author

Anthony Mets, Independent Researcher. AI development assistance is recorded in
`docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md`; no AI system is an author.

## Proposed scope

**M107 through M112.** This is a change: the previous proposal scoped M107-M111 and named M112 as an
architecture whose bank did not exist. **The bank now exists**, the milestone ran once, and D081
recorded a mixed result. The scope recommendation below is restated on that evidence, and M113 is
**not** in scope because it has no result and cannot obtain one without an owner-only freeze.

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
| M112 | D081 | worlds this project did not choose: one blind sealed invocation, the diagnosis reproducing 24/24 and every transfer outcome reproducing while the arm stays **negative at 22/24** |

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
| `metamorphosis/m107_runtime.py` … `m112_world_bank.py` | the substrate chain, imported unchanged at each level |
| `scripts/run_m1{07..12}_*.py`, `scripts/check_m1{07..12}_result.py` | orchestration and the independent checkers |
| `tests/test_m1{07..12}_*.py` | the milestone suites |
| `DECISIONS.md` (D076–D081), `FAILURE_LOG.md` | including the preserved negatives |
| `docs/CURRENT_RESEARCH_FRONTIER.md`, `MIRA_GENERALITY_CRITERIA.md` | the interpretation layer and the gates that did not move |
| `experiments/M112` in full | the isolation attestation, the published commitment, the sealed bank, the reveal authorization, the preserved result and the recorded materialization defect |

## Exact snapshot to freeze

The publication snapshot must be a **merge commit on `main`** at or after PR #211, so that all six
milestones and their preserved results are present. The tags below are the scientific anchors and
must be pushed before the deposit:

```
experiment/m107-positive-result
experiment/m108-positive-result
experiment/m109-positive-result
experiment/m110-positive-result
experiment/m111-positive-result
experiment/m112-canonical-first-result
experiment/m112-mixed-result
```

Recommended anchor commit: `8176c53` — *Merge pull request #211*, the point at which M112's revealed
bank, its preserved result and its recorded materialization defect entered `main`. If the owner keeps
the scope at M111 instead, the anchor is `566e498` — *Merge pull request #209*.

## Decision the owner has to make, and the honest reading

**Recommendation: PUBLISH, and extend the scope to M112.**

The previous recommendation was *publish at M111*, and its stated weakness was exact: without a bank
the project did not author, every world in the paper is one this project chose, and a reviewer is
entitled to say so. That weakness now has a measurement against it rather than a reply.

M112 answers the objection **in the direction that costs the project something**, which is why it
belongs in the paper rather than in a successor:

- the **diagnosis result does not depend on the project having chosen its worlds** — 24 of 24, five
  ambiguous blind worlds, both probe orders, unanimous;
- **every transfer outcome reproduces**, including the row-5 harm that is the paper's spine, on six
  worlds the project did not select;
- and the arm is nevertheless recorded **negative at 22/24**, because `P1` is an invocation artifact
  and `P5` is a real measurement: a blind world's constructive image closed at nine nodes where
  1 160 project-authored worlds had always closed at seven.

That last item is the strongest single piece of evidence in the package that project-authored worlds
are not neutral — and the project found it by being wrong in public, under a commitment published
before the tested system was frozen. A paper whose central claim is *capacity rises, competence does
not* is the right place for it, and a paper that omits it in order to keep an arm positive would be
the selective reporting the harm result exists to rule out.

Two boundaries hold whatever the owner decides. M112 is **not** external human evaluation and must
never be described as one: the evidence tier is `blind_generated_sealed_bank`, custody is procedural,
and `human_maintained_sealed_bank` remains an external blocker. And **no generality gate advances**,
so the gates table in the paper is unchanged by the extension.

**M113 is not in scope.** It has no result, its canonical run is behind owner-only gates, and a
milestone that is described in a paper before it runs is a commitment the record has not earned.

### Genesis II, or the beginning of Genesis III

The three options in the mandate resolve on where the *question* changes rather than on where the
milestone numbers do.

M107 through M112 are one question asked five times: **can a lineage improve the machinery it uses to
acquire capabilities, and how far does that improvement carry?** M112 does not change the question —
it removes one confound from the answer by taking the worlds out of the project's hands, while the
carrier, the evaluator, the registry, the feature vocabulary and the probe primitive stay exactly
where M107 put them.

M113 changes the question: **can the project stop designing the world the lineage learns in at all?**
The generator emits the machine rather than filling in a form, and the pre-freeze survey already says
the inherited three-feature vocabulary is not a function on that family. That is a different line of
work with a different failure mode, and its natural successor — whether the lineage can establish
that its own vocabulary is insufficient and acquire an extension to it — is a different paper.

**So: Genesis II is M107–M112. Genesis III opens at M113.** This is a recommendation on the evidence
as it stands, not a decision; scope is the owner's, and nothing here may alter a frozen result to
suit it.
