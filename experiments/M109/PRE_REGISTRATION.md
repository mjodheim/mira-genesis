# M109 — two successive machinery generations, and recursive depth of two

**Hypothesis:** H54
**Decision slot:** D078 (reserved; unfilled until a canonical result exists)
**Track:** A — endogenous bounded lineage
**Pre-registration date:** 25 August 2026
**Status:** **PRE-REGISTERED QUESTION; NO PROTOCOL, POPULATION OR RESULT EXISTS**

## The ceiling M108 left

M108/H53 qualified the first lineage-acquired modification of the acquisition machinery (D077): an
acquired attribution rule causally expanded the set of later improvements the lineage could construct
under an equal budget. Recursive depth was **one**. Two limits were conceded before that freeze and
both are the subject of this milestone:

- the attribution episodes carried **authored blame labels**;
- there was exactly **one** machinery generation, so nothing established that a modified machinery
  can produce the next modification.

M108 asked whether an acquisition can change how the lineage acquires. M109 asks whether the
**changed machinery can itself produce the next change**.

## Three registered components, three distinct structural exclusions

| component | what it holds | how a demand is excluded from it |
|---|---|---|
| operator table | the operators the interpreter applies | not in the closure of the held operators |
| signal interface | which signals an expression may read | depends on an unread signal — census, any operator set, any budget |
| **candidate space** | which operators the machinery may *consider* adopting | a monotone candidate space keeps the image monotone — lemma, any budget |

The third component is new and is what makes a second generation possible. A candidate space
restricted to the monotone operators is **closed**: every operator table reachable through it keeps
the image monotone, so a non-monotone demand is excluded from the operator axis by the same lemma
M107 and M108 used, at every node bound. Widening the candidate space is therefore a machinery act
structurally distinct from extending the operator table.

The lineage starts with operator table `{AND, OR}`, interface width 2, and a monotone candidate
space.

## The staged world

Demands arrive in sequence, and each is revealed only once the previous one is resolved. This is a
curriculum, declared as such: it is the mechanism by which a lineage's **history** determines what
evidence it can ever hold.

- **`D1 = x0 AND x1 AND x2`** — monotone, and it depends on the signal the interface cannot read.
  Extending the operator table cannot reach it; widening the candidate space cannot reach it. Only
  the interface can.
- **`D2 = (NOT x0) AND x1`** — non-monotone. At the world width the interface is exhausted and the
  monotone candidate space is closed by the lemma. Only widening the candidate space can reach it.

The hardwired machinery blames the operator table, searches its candidate space for an operator that
would resolve `D1`, and adopts nothing. Its refusal is not "nothing left to try": at that very failure
`g2` is true, so the operator axis still offers strict progress in general. It is exhausted only for
this demand, on the only axis the machinery can name. See the corrections below.

## Episodes the lineage generates for itself

M108's blame labels were authored. Here they are not. After a demand is resolved or abandoned, the
lineage may enter a **learning phase** in which it performs a controlled trial on itself: extend each
registered component in turn and observe which extension makes that demand constructible. The label
is the outcome of that trial, not a host annotation.

Trials are permitted **only** in the learning phase and **only** on demands the lineage has actually
encountered. At resolution time the machinery holds a single step and must attribute without trials —
which is precisely why an attribution rule is worth acquiring at all.

## H54

Within one frozen run, a lineage `M0` whose acquisition machinery attributes every failure to the
operator table:

1. acquires from its own trial record a persistent attribution rule `A1`, becoming `M1`;
2. resolves `D1`, which `M0` provably cannot resolve;
3. encounters `D2` — reachable only because `D1` was resolved;
4. acquires from its own trial record a second, distinct machinery rule `A2`, becoming `M2`;
5. resolves `D2`, which `M1` provably cannot resolve.

and the improvement-reach of the three machineries forms a **strict chain**

```
ReachImprove(M0) = 6  ⊂  ReachImprove(M1) = 20  ⊂  ReachImprove(M2) = 243
```

computed by exhaustive census over the whole state family and all 256 world functions, not by
sampling.

## What kind of dependency this is, stated precisely

M108's dependency was **expressibility**: the corrected rule was inexpressible in the pre-generation
language, by lemma.

M109 carries **two** dependencies, and the second was not anticipated.

The first is **evidence reachability**: `M0` never resolves `D1`, therefore never encounters `D2`,
therefore never runs `D2`'s trial, therefore holds no episode distinguishing the candidate space from
the operator table.

The second is **expressibility**, and it is the same monotonicity lemma applied one level up — to the
attribution cascade rather than to the operator table. Every monotone program true at row 3 is true at
row 7, so no rule the lineage can express fires for the candidate space without also firing for the
signal interface. Generation 2 becomes expressible only once generation 1 has claimed row 7. This was
found by building the instrument, contradicts the first draft, and is recorded below.

The milestone still **measures** the handed-episode counterfactual rather than assuming it: a fresh
`M0` is given the stage-two episode from outside and the outcome is recorded whatever it is.

## Corrections recorded before freeze

Building the instrument falsified three statements in the first draft of this pre-registration. All
three are recorded here rather than repaired silently. No protocol, population or result existed at
any point during them.

### 1. The hardwired failure is exhaustion, not progress on the wrong axis

The draft claimed the hardwired machinery "extends the operator table, strictly enlarges its reach,
and still fails". It does not. The operator search is demand-directed: it looks for a candidate that
makes *this* demand constructible and adopts nothing when none does. The honest statement, and what
the instrument measures, is sharper:

> at the failure, the operator axis is **not** exhausted in general — `g2` is true, some candidate
> would strictly enlarge reach — while it **is** exhausted for this demand. The hardwired machinery
> fails with progress still available on the only axis it can name.

P5 is restated accordingly.

### 2. The dependency between generations is expressibility, not only evidence reachability

The draft predicted that a fresh `M0` **handed** the stage-two episode from outside would acquire the
second rule, bounding the claim to *within the lineage's own operation*. It does not, and the reason
is a lemma:

Row 3 `(False, True, True)` is below row 7 `(True, True, True)` componentwise, so every monotone
program true at row 3 is necessarily true at row 7. None of the eighteen programs the lineage can
express fires for the candidate space without also firing for the signal interface. A conservative
second rule is therefore **inexpressible** until generation 1 has claimed row 7 and removed it from
the relevant domain.

This is the same monotonicity lemma M107 and M108 used, applied one level up — to the attribution
cascade rather than to the operator table. It is a stronger dependency than the draft claimed, and P17
remains a measurement rather than a hurdle: whatever the counterfactual returns is recorded.

The barrier is robust to the adoption rule. A fresh `M0` is refused under **both** conservative and
non-conservative adoption, for different reasons:

| adoption rule | `M0` alone | `M1` after generation 1 |
|---|---|---|
| conservative | refused — no expressible rule (0 consistent) | **confirmed** — 8 consistent, 1 class |
| non-conservative | refused — underdetermined (13 consistent, 2 classes) | refused — 13 consistent, 2 classes |

### 3. Adoption is conservative, and that is load-bearing for the positive half

A rule may fire only on rows for which the lineage holds positive evidence; a relevant row it has
never observed is required **not** to fire. This is a standard induction principle — do not act where
you have not looked — and it is what leaves later rows available to a later generation.

It is also **authored**, and the table above shows exactly what it carries: it is not what stops
`M0`, but it *is* what lets `M1` succeed. Under non-conservative adoption neither lineage acquires the
second rule and M109 would be negative. This is declared as a limitation of the result, not concealed
inside it.

The draft's underdetermination control is restated for the same reason. Under conservatism a single
episode determines generation 1, so "one episode leaves it underdetermined" is false here. The
genuine refusals the instrument must exhibit are: a record naming **no** attributable component, and
a record naming **more than one**.

## Decisive conditions

- **P1** runtime and input preflight bind the canonical runtime and the exact fixtures.
- **P2** the registry holds all three components from the start; `M0` attributes by the hardwired
  operator axis; M109's enumerator is certified to denote exactly M107's image at M107's width.
- **P3** the monotone candidate space is certified **closed**: every reachable operator table through
  it keeps the image monotone, at every node bound.
- **P4** `D1` is excluded from the operator-table and candidate-space axes and reachable only through
  the interface; `D2` is excluded from the operator-table and interface axes and reachable only
  through the candidate space. Both by complete census, both budget-independent.
- **P5** at the hardwired failure the operator axis offers progress in general (`g2` true) while
  being exhausted for this demand, so the refusal is not "nothing left to try".
- **P6** every episode label is produced by the lineage's own component trial; no label is read from a
  fixture, and the trial procedure is identical for every component.
- **P7** trials occur only in the learning phase; at resolution time the machinery performs no trial
  and holds one machinery step.
- **P8** a trial record naming no attributable component is refused, and one naming more than one
  component is refused; adoption is conservative and never fires on a relevant row never observed.
- **P9** `A1` is determined, adopted as content-addressed lineage state, and attribution switches to
  the state-held rule.
- **P10** the producer process dies between generations; each later stage receives only serialized
  state, and no stage holds a demand it is not entitled to see.
- **P11** `M1` resolves `D1` and the witness executes to target; `M0` does not, at the frozen bound
  and at a strictly larger one.
- **P12** `D2` is revealed only after `D1` is resolved, and `M0`'s own history provably contains no
  stage-two episode.
- **P13** `A2` is determined from the lineage's own extended trial record, is distinct from `A1`, and
  is adopted as state; `M2` resolves `D2` and `M1` does not.
- **P14** `ReachImprove(M0) ⊂ ReachImprove(M1) ⊂ ReachImprove(M2)` with both inclusions **strict**, by
  exhaustive census.
- **P15** ablation of `A2` returns the lineage to `M1` byte-exactly and removes `D2`; ablation of both
  returns to `M0` byte-exactly and removes `D1`; mutation and corruption fail closed; the lineage
  cannot extend its own component registry or exceed any authored ceiling.
- **P16** every isolated process runs on a capsule-only import path with no leaked project module and
  reports zero model, network and remote-execution calls.
- **P17** the handed-episode counterfactual is computed and recorded, whatever it returns.
- **P18** independent replay reproduces the stable evidence projection exactly.

**Verdict rule:** positive if and only if P1-P18 are all computed and true; negative otherwise. P17
is satisfied by being *computed and recorded*, not by any particular outcome — it is a measurement,
not a hurdle. One canonical attempt and one canonical checker replay are permitted. The first result
is preserved even if negative and may not be repaired.

## Instrument requirements

M103 and M105 were lost to checkers that could not start; M107's rehearsal caught four further
defects including M098's stable-projection failure; M108's rehearsal was rerun after a late change
because a rehearsal that does not cover the frozen bytes is worth nothing. Before any M109 freeze the
complete `CANONICAL -> PRESERVE -> CHECK -> REPLAY` chain must be rehearsed end to end in a throwaway
clean checkout that receives the sources with platform line endings, using exactly the frozen
commands, exercising the checker as a direct script through the replay branch, with exit codes
asserted for result-present, result-absent, corrupted-result, tampered-result-with-recomputed-digest
and report-already-exists, and with every predicate computed.

M109 binds its members by the scheme M108 established — JSON evidence by raw bytes, text members by
LF-normalized content, mode recorded per member — and binds no file an earlier frozen protocol binds.

## What M109 cannot establish

Recursive depth of three or more; measured recursive acceleration; autonomous invention of the
component registry, the feature vocabulary or the demands; open-ended machinery growth; transfer to
an independently maintained domain; G1-G10 closure; general-agent evidence; self-hosting; AGI.

The registry, the feature vocabulary, the demand sequence, the trial procedure and the evaluator
remain authored. What is no longer authored is the **blame label**: the lineage determines it by
experiment on itself.

A positive M109 would license only this: *within a frozen bounded environment, a lineage-acquired
modification to the acquisition machinery enabled a second, distinct machinery modification that the
unmodified lineage could not have reached, and the improvement-reach of the three successive
machineries is a strict chain.*
