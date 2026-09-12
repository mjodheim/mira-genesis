# Free Metamorphosis v4 — publication and security boundary

This file defines what the public `mira-genesis` record may contain about the private-host v4 campaign.

It is intentionally stricter than “do not publish credentials”. The goal is to prevent accidental reconstruction of private source, hidden evaluator cases or operational infrastructure from otherwise innocuous evidence.

## Public by design

The following classes of information may be published:

- policy/version identifiers;
- retained generation numbers;
- aggregate capability-category scores and totals;
- aggregate deltas and warning counts;
- retain/reject/neutral-archive decisions;
- changed-path counts;
- high-level, redacted proposal hypotheses;
- content digests for private objects, used only as identity anchors;
- public Genesis commit/PR identities;
- claim boundaries and chronology.

## Private by design

The following must not be copied into this repository:

- private host source or complete private patches;
- private host file names/paths when they reveal implementation structure;
- private prompts, conversation text or user data;
- API keys, tokens, cookies, credentials or environment values;
- service endpoints, deployment topology or private URLs;
- raw evaluator cases, messages, capability contracts or expected labels;
- case-level observed outputs or labels;
- frozen external authority tests or evaluator implementation from the private campaign;
- stdout/stderr tails, raw runner logs or crash dumps;
- temporary signed artifact URLs;
- campaign-state tarballs, evaluator container images or proposer bundles containing the private parent organism.

## Cryptographic identities

A SHA-256 or tree digest may be published when it is useful for chronology or provenance. The digest is a **commitment**, not publication permission for the object it identifies.

For example, this record may state that a proposal patch had a given SHA-256 while withholding the patch itself.

## Proposer memory boundary

The public record may explain that later proposers receive bounded empirical history. It must not disclose the hidden case material excluded from that context.

Permitted history includes aggregate scores/deltas and redacted proposer-authored intent. Excluded history includes individual case messages/contracts, expected and observed case labels, evaluator logs and authority-test content.

## Fail-closed handling

If a field cannot confidently be classified as public, omit it. A less detailed public record is preferable to exposing private host or evaluator information.

No public document should contain a live secret even if that secret has already been rotated. Secret values belong outside repository history.

## Canonical authority

The private campaign state remains the canonical experiment authority. This public repository is a sanitized research record and cannot be used to mutate, replay or override private campaign state.