# M111 — adversarial review

Written before freeze, against the milestone's own claim. Objections that survive are conceded in the
pre-registration and in `README.md`; objections that were repaired are recorded here with what
changed.

## Repaired before freeze

**D1 — the barrier did not exist in the first design.** The first apparatus acquired one policy per
world, and on a record holding only rows 1 and 3 the requirement is satisfiable monotonically:
row 1 lies *below* row 3, and monotonicity closes upward, not downward. So the policy was expressible
in the 18-program language and generation 2 was doing nothing. Caught by running the acquisition and
watching it succeed where it should have refused.

**D2 — the fix could not be a weaker requirement.** Row 7 is what makes the requirement
non-monotone, and a survey of 160 worlds measured that row-3 ambiguity and row-7 reachability
**never co-occur** here — 10 ambiguous worlds, 57 with row 7, zero together, against about 3.6 under
independence. Dropping row 7 would have deleted the depth-three claim while leaving the milestone
looking positive. The record is pooled across a two-stratum population instead, which is a stronger
claim: one policy holds across every world rather than being refitted per world.

**D3 — P20 as first written could not be true.** It required equal probe counts between the
diagnostic arm and the fixed probe arms, and the never-probe arm spends zero by construction. A
predicate that cannot be satisfied is as useless as one that cannot fail. It now states what
equalization actually needs: no arm starts with a larger budget, and the diagnostic arm never spends
more than always-probe.

**D4 — the predecessor was the wrong state.** The draft used M109's generation-2 *adoption* state.
The lineage's real end state is its **terminal** state, which additionally holds the operator the
lineage adopted while resolving stage two. Using the adoption state would have made M111 look like it
had to find a non-monotone operator itself, when in fact generation 2 already brought one. The
terminal state is now the predecessor and is verified byte-exactly at `5c08fa30…`.

**D5 — the probe had to be shown not to adopt.** A probe that quietly mutated state would make the
whole result an artefact. The probe record now carries the serialized state before and after, the
boundary audit measures byte-identity on a real world, and P13 computes it per world.

## Conceded, and declared

**C1 — the registry, the probe primitive and the budget are authored.** M111 adds a fourth registry
entry and the notion of a rollback-experiment. The lineage does not invent either. What it does is
decide **where** to spend one.

**C2 — the population is selected for ambiguity by design.** M110's criterion excluded ambiguous
worlds; M111's requires them. Both are declared. What is not selected is which components produce the
ambiguity, or how any arm behaves.

**C3 — the acquired policy also fires on row 2, which is unreachable.** `¬g1 ⟹ g2` holds in any
domain implementing these features, so every reachable row is odd. Firing on row 2 is unobservable
rather than harmless-by-argument, and it is disclosed rather than trimmed.

**C4 — elimination is complete because only two candidates remain.** At row 3 the features already
exclude the operator table, so one probe settles a two-way choice. With three live candidates one
probe would not suffice, and this milestone does not test that case.

**C5 — competence is measured on three ambiguous worlds, with one demand pair each.** The population
is the sample, not the number of demands inside a row.

## Objections a hostile reviewer should still press

**O1 — "the probe is an oracle."** It is a bounded one: it answers one yes/no question about one
component, costs the scarce budget, and rolls back. The milestone's content is not that probing works
— it is that a lineage can *derive from its own record* where probing is needed, and that this
derivation is inexpressible before generation 2.

**O2 — "always-probe fails only because of the demand order."** True, and both orders are run, and
the reversed sequences are recorded. Always-probe is order-dependent; the acquired policy is not.
That contrast is the measurement, and the order-dependence is reported rather than hidden.

**O3 — "the witness stratum is a crutch."** It is, and it is declared. Without it no world in this
carrier carries the barrier. The scientific content survives: a lineage's record spans its history,
and the policy it derives must hold across that history.

**O4 — "is this recursive depth three, or three authored components in a row?"** Both descriptions are
partly right. The registry is authored. What is not authored is that generation 2's side effect — an
operator it chose while resolving its own demand — is what makes generation 3 expressible at all, and
that the ablation refuses by lemma rather than by failed search.

**O5 — "acceleration?"** Not claimed. Measured quantities are recorded and reported; three generations
with no pre-registered trend across them licenses nothing.
