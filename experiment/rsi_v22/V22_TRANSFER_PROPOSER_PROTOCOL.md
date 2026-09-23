# Genesis RSI V22 — isolated retained-evaluator Brewstead repair proposer

Status: **FROZEN before any V22 proposer output or reserved-evaluator observation on a proposal**.

This is the complete proposer-facing contract for one V22 Brewstead transfer slot.

## Runtime and information boundary

Use a fresh isolated ChatGPT conversation, GPT-5.6 Sol, High thinking effort, and only the exact supplied bundle.

Forbidden:

- web, URLs or GitHub;
- plugins/connectors/connected apps;
- saved memory or previous conversations;
- Mira Genesis project context;
- reserved evaluator JUnit source or result;
- another V22 task, attempt or slot output;
- G1/G2 policy-selection information;
- human candidate-specific implementation guidance.

The bundle contains the exact defected Brewstead parent archive, public Brewstead tests, one public symptom, exact task manifest, this protocol, and a mechanical output verifier. The reserved evaluator is intentionally absent.

## Objective

Repair the supplied public symptom while preserving existing correct behavior. Do not infer or speculate about the withheld evaluator implementation.

## Scope

Modify exactly the single `allowed_source_path` recorded in `task-manifest.json`. No test, build, workflow, dependency, resource, configuration, or other production file may change. No rename is allowed. Prefer the smallest causal repair.

## Output

Return exactly `proposal.patch` and `transcript.json`, with no prose outside those files.

## Transcript contract

Schema: `mira-genesis-rsi-v22-transfer-proposal-v1`

Top-level keys exactly:

- schema
- task_id
- campaign_slot_id
- parent_node_id
- parent_tree_digest
- host_commit
- task_manifest_sha256
- proposer_protocol_sha256
- proposal_patch_sha256
- intent
- rationale
- files_changed
- public_checks
- uncertainties
- information_boundary

`files_changed` must be a sorted unique list containing exactly the allowed production source path. `public_checks` and `uncertainties` must be sorted, unique, and non-empty.

`information_boundary` exactly:

```json
{
  "used_only_supplied_bundle": true,
  "used_web_or_github": false,
  "used_saved_memory_or_previous_chats": false,
  "used_reserved_evaluator_source_or_result": false,
  "used_other_v22_attempt_or_slot_output": false,
  "used_g1_g2_selection_information": false,
  "used_human_candidate_specific_guidance": false
}
```

## Required bindings

Copy exactly from `task-manifest.json`: `task_id`, `campaign_slot_id`, `parent_node_id`, `parent_tree_digest`, and `host_commit`.

Compute and bind SHA-256 of `task-manifest.json`, this protocol, and `proposal.patch`.

## Mechanical self-check

Before returning, run:

```text
python3 VERIFY_OUTPUT.py proposal.patch transcript.json
```

Do not return until it prints exactly:

`GENESIS_RSI_V22_TRANSFER_OUTPUT=PASS`

The laboratory independently applies the patch and runs the frozen public guard plus the withheld reserved objective. Passing the output verifier does not imply evaluator success.
