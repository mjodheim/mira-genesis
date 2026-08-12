# M075-B — blind externally materialized sealed task bank

**STATUS: DRAFT, PRE-FREEZE. NO GENERATOR IS CHOSEN. NO BANK EXISTS. NO REVEAL IS AUTHORIZED.**

This is a successor protocol to M075's private-bank line. It does **not** amend M075, does not
satisfy M075's frozen requirements retroactively, and does not close
[issue #112](https://github.com/mjodheim/Mira-Genesis/issues/112). M075's own protocol, its
public result, its recorded digests and its fail-closed validator are untouched by this document
and by every artifact under `experiments/M075B/`.

## 1. The question this milestone actually asks

M075 requires an independent human maintainer who writes a private feasible/capability-absent
bank and withholds the payload until the tested system's protocol is frozen. That person does not
exist yet. Before building an alternative, the requirement was decomposed into what it buys
scientifically and what is an artifact of the custody mechanism chosen at the time.

| M075 requires | Why | Can a blind generator replace it? |
|---|---|---|
| The bank is authored outside the policy-development path | An author who writes the test and the answer measures their own expectations | **Partly.** A model given no project context did not know what the project hoped to see. It is not a second mind with its own judgement. |
| The payload is withheld until the protocol is frozen | Otherwise the system can be tuned to the bank | **Yes.** Encryption plus a signed reveal gate holds the payload as reliably as a person's discretion, and leaves an auditable record where discretion leaves none. |
| Only opaque metadata is disclosed before reveal | The commitment must not leak subject matter | **Yes**, and more strictly: opaque domain identifiers derive from a random per-bank nonce and an index, never from the domain name, so the public commitment cannot be dictionary-attacked. |
| Four materially different domains, eight matched pairs | Bank size determines what the test can detect | **Yes**, and the same minimum is enforced here. |
| Success is decided from terminal environment state | M081 recorded a self-report control that over-reported twice | **Yes**, structurally: the evaluator kind is allowlisted and `reads_agent_self_report` must be `false`. |
| Impossibility is caused by an absent capability, not a trick phrasing | Otherwise a refusal measures reading comprehension | **Yes**, and better than prose: the pair stores one goal and one evaluation, and the twins are derived, so the certificate is structural rather than declared. See §5. |
| The maintainer signs an independence attestation | The project cannot self-attest independence | **No.** This is the part that does not transfer, and the reason #112 stays open. |

The last row is the whole result of the audit. Everything above it is mechanism; the last row is
a person, and a model is not one.

## 2. Roles

| Role | Who | May do | May never do |
|---|---|---|---|
| **Builder** | Anthony Mets, with AI development assistance, in this repository | Build the instrument, the schemas, the checkers, the tests | Author, review, curate, score or select any task in the qualifying bank |
| **Blind generator** | A separate model, pinned by descriptor, run in an isolated container | Emit one payload from one literal prompt | See this repository, its files, its history, its results, any public bank, the tested system's prompt or policy, or any statement of what the project hopes to observe |
| **Class oracle** *(optional)* | A third process, distinct from both the generator and the tested system | Confirm that a task's declared feasibility class holds | Select among tasks, rank them, or trigger a reroll |
| **Custody** | Encryption plus a signed reveal gate | Hold the sealed payload, publish the commitment | Place plaintext, a key or a ciphertext inside this repository, a pull request or a public workflow artifact |
| **Tested system** | The composed M075 agent, frozen before reveal | Run once per task per condition | Be modified, retried, resumed or replaced after any bank content is known |
| **Evaluator** | Owned by the bank, outside the mutable body and outside the generator | Decide success from terminal environment state | Read the agent's own report, or apply any subjective criterion |

The builder constraint is enforced by construction rather than by promise: every payload this
repository can emit carries the development schema, which the readiness gate does not accept.

## 3. The ordered chain

```
F1  freeze GENERATOR_SPEC.json + ANALYSIS_PLAN.json + GENERATOR_PROMPT.txt
        ↓                       (public commit, before any bank exists)
G   one generation, in an isolated container, recorded in GENERATION_LEDGER.json
        ↓
V   structural validation — no execution of the tested system
        ↓
S   canonicalize → digest → encrypt → publish PUBLIC_BANK_COMMITMENT.json
        ↓
F2  freeze SYSTEM_PROTOCOL.json, bound to F1 and to the sealed commitment
        ↓
R   check_blind_bank_readiness.py --require-ready
        ↓
A   signed REVEAL_AUTHORIZATION.json — a human signature, not a file's presence
        ↓
X   one execution
        ↓
P   the result is preserved, whatever it says
```

### Why the analysis plan is frozen at F1 and not at F2

The prompt asked for the tested-system protocol to be frozen after sealing. That is correct for
the *system* — the harness must be written against the schema, and freezing its code digests
after the bank exists costs nothing as long as no content is known. It is **not** correct for the
scoring rule. Bank size determines which p values are reachable at all, so a threshold chosen
after the bank existed would be fitted to it without a single task being read. The analysis plan
therefore moves earlier, into F1, and `SYSTEM_PROTOCOL.json` must bind its digest unchanged.

`validate_analysis_plan` then enforces both failure modes at once, which is the M086-A lesson
inverted: a threshold no draw could ever meet is rejected as firmly as one no draw could miss.

### What F2 knows that F1 does not

Between sealing and F2 the project knows that a bank exists, its byte length, its domain and pair
counts, and its opaque identifiers. Counts were fixed at F1; identifiers are content-free by
construction. **Byte length is the one genuine residual leak** and it is recorded here rather than
argued away: a 40 KiB payload is a mildly different bank from a 400 KiB one. It carries no task,
no domain and no capability, and it is required for integrity, so it is accepted and disclosed.

## 4. What the generator is asked for

The frozen prompt is not written in this document, because writing it here would freeze it. What
is fixed is the **contract** the prompt must satisfy, in
[`GENERATOR_PROMPT_CONTRACT.md`](GENERATOR_PROMPT_CONTRACT.md). In summary, the prompt states
abstract properties of a valid bank — materially different domains, matched feasible/impossible
pairs, terminal-state verifiability, reproducible environments, impossibility caused by an absent
capability — and it states **nothing** about a system under test, a project, a prior result, a
refusal mechanism, or an outcome anyone hopes for. `validate_generator_spec` refuses a spec whose
prompt record admits any of those, and the prompt file is re-hashed at every gate check, so an
edit after the freeze turns the repository red rather than passing quietly.

## 5. What makes a pair matched

A pair is **one object**, not two tasks sharing an identifier. The instruction, the base
environment and its initial state, the permitted interfaces, the required capabilities, the
terminal predicate and the evaluator are stored once, so the twins cannot disagree on them.

```
pair
├── instruction, base_environment, permitted_interfaces,
│   required_capabilities, terminal_success_predicate, evaluator   ← one copy, shared
├── absent_capability { capability, reason }
└── twins
    ├── feasible          { task_id, provenance }
    └── capability_absent { task_id, provenance }
```

A twin carries its identifier and its emission provenance and nothing else, neither of which can
affect whether the task can be completed. `materialize_twin` derives the runnable task; the only
difference between its two outputs is whether `provides_capabilities` contains the certified
capability.

Three rules make impossibility structural: the capability is **required** by the shared goal, it
is **absent** from the environment and from every permitted interface, and supplying it is
**sufficient** because nothing else the goal requires is missing.

This replaces an earlier draft that stored two independent task objects and compared them.
External review of PR #134 found that such a comparison must enumerate every field that has to
stay equal, and that a pair differing in its instruction, initial state, evaluator or terminal
predicate would still have been counted as evidence about a capability. Storing the shared half
once removes the class of defect rather than adding a check for each instance of it. No bank
existed when this changed.

## 6. What may not be done to the bank

Preregistered, and enforced:

- no generating a surplus of tasks and keeping the ones the tested system handles as hoped;
- no running the tested system during generation, validation or assembly;
- no scoring tasks by the tested system's behaviour;
- no model that knows this project filtering, ranking or curating the tasks;
- no reroll of a seed, a prompt or a generator because the bank looks unpromising;
- no selection rule that depends on task content scoring.

`assembly` is a frozen constant record; any of these edits changes it and fails validation. The
tested system is unreachable from the validator's import graph, which a test asserts by parsing
the module rather than by trusting the docstring.

## 7. Non-retry

The first bank materialized under a frozen spec is **the** bank. If it is degenerate, or supports
nothing, the result is preserved and published as it stands.

`GENERATION_LEDGER.json` is append-only and records every attempt including failures. Two
`materialized` entries under one spec commitment is a hard validation failure, not a warning: a
silent second draw is exactly the move this contract exists to make impossible to hide. A
structural failure at V supersedes the protocol — it does not retry it — and a successor requires
a new protocol version, a new prospective justification, a new bank and a new scientific identity.

## 8. Reproduction

A successful M075-B run is one generator's bank. The reproduction contract frozen in
`SYSTEM_PROTOCOL.json` requires, for the next tier, a **second generator differing in family and
in runtime**, drawing a **separate bank**, under a separate protocol version. Generator A
succeeding is not a reproduction of itself.

And the contract carries one field that cannot be edited without failing validation:
`human_maintained_bank_still_required_for_h21_support: true`.

## 9. Claim boundary

See [`CLAIM_BOUNDARY.md`](CLAIM_BOUNDARY.md) for the full ladder. The short form:

- **Provable:** procedural independence, and generator context blindness.
- **Arguable at best:** training-data independence — a checkpoint published before this line
  became public cannot have memorized *these* tasks. That is an antecedence argument about one
  corpus. It is never "the model does not know this project".
- **Not obtained:** human independence, and external reproduction.

A positive M075-B is **blind externally materialized sealed-bank evidence**. It is not
independent human reproduction, it does not support H21, and it does not close #112.

## 10. Remaining steps before any scientific run

1. Choose and pin a generator from [`GENERATOR_CANDIDATES.md`](GENERATOR_CANDIDATES.md); record
   the weights digest, the image digest and the antecedence argument or its absence.
2. Build the generator container image and record its digest.
3. Write `GENERATOR_PROMPT.txt` against the contract, and have it reviewed by someone who has not
   read M074 or M075 for the specific failure of accidentally naming what we hope to see.
4. Decide whether the class oracle is enabled, and if so what it is.
5. Freeze F1 in one public commit; CI must be green on it.
6. Decide key custody: an external holder is stronger than an offline project holder, and the
   difference must be recorded rather than blurred.
7. Only then generate.

None of these has been done. `python scripts/check_blind_bank_readiness.py` reports
`phase: draft`.
