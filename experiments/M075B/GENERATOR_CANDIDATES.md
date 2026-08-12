# Candidate generators, and what each one can and cannot prove

**No generator is chosen.** This document exists so that the choice, when it is made, is made
against criteria written before a candidate was preferred — and so that the antecedence argument
each candidate supports is recorded honestly rather than assembled afterwards to fit whichever
model was convenient.

## Criteria, in order of scientific weight

1. **Open weights.** A hash-identifiable checkpoint is the difference between "we ran this model"
   and "we asked a service that says it ran this model". Only an open-weight candidate can carry
   `weights_digest_available: true`.
2. **Local or container execution.** An API call cannot be run with `--network none`, so an
   API-hosted generator gives up the strongest half of the isolation attestation.
3. **Checkpoint antecedence.** A checkpoint published before this research line became publicly
   accessible cannot have memorized these tasks. See below for what that does and does not buy.
4. **Reproducible sampling.** A runtime that guarantees a seed reproduces the sample lets a third
   party re-derive the bank from the frozen spec. Where it is not guaranteed, `seed` must be
   `null` — the spec validator refuses a recorded seed the runtime cannot honour.
5. **Capacity.** The bank requires structured JSON of real length with internally consistent
   capability vocabularies. A model that cannot hold the schema will fail structurally at V, which
   supersedes the protocol rather than retrying it — an expensive way to discover a size limit.

Criteria 1–3 pull toward larger open-weight checkpoints; criterion 5 pulls the same way; criterion
2 pulls toward whatever fits the available hardware. The tension is real and is not resolved here.

## The antecedence reference date

Mira Genesis is a public repository, and the M074/M075 refusal-calibration line has been publicly
readable since its commits landed. The conservative reference date is therefore the **first public
appearance of the M074 protocol**, not the date of this document. Any candidate whose checkpoint
postdates that is not antecedent, and its descriptor must record
`antecedence_demonstrable: false` — which is permitted, and simply moves the claim down.

`validate_generator_descriptor` enforces the arithmetic: `antecedence_demonstrable: true` requires
both dates and a checkpoint published strictly before the reference.

## Candidates

| Candidate | Open weights | Local/container | Antecedent to the M074/M075 line | Notes |
|---|---|---|---|---|
| Llama 3.1 70B Instruct | Yes | Yes, quantized on one large GPU or CPU with patience | Yes — July 2024 | Weights are hash-identifiable and widely mirrored. Long-context JSON at this size is the main risk. |
| Qwen 2.5 72B Instruct | Yes | Yes | Yes — September 2024 | Stronger structured-output behaviour than Llama 3.1 in most reports; same size class. |
| Mixtral 8x22B Instruct | Yes | Yes, with substantial memory | Yes — April 2024 | Earliest of the strong candidates, so the best antecedence argument; weakest instruction-following of the four. |
| Gemma 2 27B Instruct | Yes | Yes, comfortably | Yes — June 2024 | Cheapest to run. Capacity is the open question; a structural failure here is unusually likely. |
| A current hosted frontier model | No | No | No | Would fail criteria 1, 2 and 3 at once. Listed only to record that it was considered and why it loses. |

Nothing in this table is a recommendation. It is the shortlist the decision must be made from, or
justified against.

## Two things a candidate choice may never be made on

**Not on how the tested system performs on its output.** That would be selecting the bank by the
result, through the generator. If a first candidate produces a structurally invalid bank, the
failure is preserved in the ledger and the protocol is superseded — a new candidate is a new
protocol version with a new prospective justification, not a retry.

**Not on a preview.** Reading a sample bank from a candidate before freezing the spec would mean
the spec was written knowing what that generator tends to produce. If a capacity check is needed
before committing, it must be run against a **different prompt** on a **different subject** and
recorded as such.

## What the descriptor must record, whichever is chosen

```
model_identifier, checkpoint_revision, weights_sha256 (or null),
weights_digest_available, runtime {name, version, image_reference, image_digest_sha256},
checkpoint_published_on, antecedence_reference_date, antecedence_demonstrable,
training_data_independence_proven  # always false
```

The last field is a constant, not a finding. See [`CLAIM_BOUNDARY.md`](CLAIM_BOUNDARY.md).
