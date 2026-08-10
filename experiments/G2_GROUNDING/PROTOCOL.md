# G2 multimodal state grounding protocol

**FROZEN BEFORE IMPLEMENTING OR MATERIALIZING THE GROUNDING HARNESS.**

The experiment number is deliberately unassigned. This work was prepared in a separate worktree
while the M075 private-readiness line was still being committed on `main`; the M-number is assigned
at merge so that two concurrent lines cannot claim the same identifier.

## Why this question, and why now

`MIRA_GENERALITY_CRITERIA.md` records G2 as fully open: "No vision or multimodal grounding in one
continuing lineage." It is the largest empty gate in the register. Every result from M070 onward has
belonged to Track B, and the endogenous Track A line has produced no new gate evidence since M066.
This experiment is deliberately Track A and model-free: it calls no foundation model, selects no
external task and needs no third-party attestation, so it can be executed and audited entirely
inside the repository.

M075 stands on a genuinely different blocker. Its pre-private readiness gate is fail-closed on
inputs that only an external maintainer can sign, and no amount of internal work substitutes for
them. This experiment does not touch that boundary and does not relax it.

## Falsifiable claim

One persistent deterministic agent consumes three channels — a UTF-8 instruction, an ordered
structured field mapping, and a raw 1728-byte RGB888 raster — and emits both symbolic tool calls
and embodied effector actions. Across three precommitted families of twelve episodes each, whose
decisive information is confined to exactly one channel, the full arm must reach exact success on
all 36 episodes.

Three matched ablations must then produce a **double dissociation**:

- removing pixels must reduce `pixel_target` to zero successes and leave `structured_dial` and
  `language_route` at exactly the full-arm score;
- replacing structured values with a sentinel must reduce `structured_dial` to zero and leave the
  other two families exactly unchanged;
- replacing the instruction with a selector-free string of identical token count must reduce
  `language_route` to zero and leave the other two families exactly unchanged.

The second half of each clause carries the scientific weight. An arm that degrades everything shows
only that inputs matter. Preregistering exact equality on the non-dependent families is what makes
the contrast a dissociation rather than a general capacity loss.

## Why the ablations are matched

Each ablation preserves byte length, key order, token count and schema. A shorter raster, a missing
key or a truncated instruction would let the agent detect the ablation itself, and a detectable
ablation can produce degradation without proving that the removed *information* was used. The
pixel ablation therefore substitutes a salt-derived constant raster of the same 1728 bytes carrying
no marker triple; the structure ablation keeps every key in order and zeroes only values; the
language ablation substitutes a fixed string of the same token count.

## Why a blind-guess arm exists

A fail-closed ablation scores zero, which is the correct engineering behaviour but is uninformative
on its own. The `blind_guess` arm receives no channel and answers from the chance distribution. It
fixes the exact floor — the effector destination is one of 36 cells — so that a zero-scoring
ablation is read against a measured floor rather than an assumed one. This mirrors the `nop` floors
used in M070 and M071.

## Embodied scoring

Embodied success is computed from the terminal grid state after the emitted move sequence is
applied by the environment. The agent's own claim about where the effector ended is recorded but
never scored, following the same rule G6 applies to real environments.

## Episode materialization

`PROTOCOL.json` contains one 32-byte salt drawn before any harness code existed and a fixed family
grammar. The implementation may derive episodes only from that salt, family name and deterministic
index. Exactly 36 episodes must be emitted in ascending selection-digest order within each family.
The materialized suite is committed as a separate immutable artifact before any result is recorded.
Episode content is intentionally absent from this freeze.

## Safety boundary

The agent receives compute and in-process memory only. No arm may reach a network, repository write
path, credential, deployment path, permission interface or physical actuator. The effector is a
coordinate inside an in-memory grid; "embodied" here means a state-changing action scored from the
environment, not a physical device. No existing isolation, Harbor boundary or safety policy is
weakened.

## Claim boundary

A positive result would establish **bounded multimodal grounding with causal per-channel
dependence** in one persistent agent. It would move G2 from open to partial mechanism evidence.

It would not establish natural-image perception, cross-domain transfer, Genesis Gate 2 or Gate 3,
long-horizon autonomy, or any AGI claim. The rasters and families are project-authored, so this is
development evidence in exactly the sense M072 and M073 are, and it requires the same independent
reproduction before any stronger language is used. It does not close G2: closing G2 needs modalities
the repository does not yet handle and tasks maintained outside this project.
