# Mira Genesis

**When does a proxy measure stop tracking what it claims to track, and under what
optimisation pressure?** Mira Genesis asks that question in a domain where ground truth
is **decidable**, so the answer is proved rather than estimated.

## How the project got here

The repository was first devoted to **trans-substrate cognitive metamorphosis**:
separating a competence from the computational body that acquired it, transporting it,
re-embodying it in a substrate whose semantics are unknown, and preserving its
plasticity there. That line produced two sealed validations — M012b and M013e — and
then four failures.

None of the four failed in the organism.

| | What gave way |
|---|---|
| M014b | a 25% threshold on a window four queries wide |
| M017 | a 10× threshold derived from a typical case taken for a bound |
| M018 | no consequence to inefficiency, so nothing to optimise for |
| M019 | a fitness horizon shorter than the payback period of learning |

Four times, what was being built held; what gave way was the way of judging whether it
was better. The project now follows what its own failures identified.

## What this repository adds, and what it does not invent

The problem is neither new nor unexplored. Goodhart's law, reward hacking,
specification gaming, novelty search and quality-diversity have worked on it for a long
time, with partial answers.

But those bodies of work operate almost entirely where **the true objective cannot be
verified exactly**. Reward hacking is diagnosed because a human finds the result
suspicious; novelty is judged by what looks interesting; behavioural descriptors are
picked by hand.

Here, the behavioural equivalence of two finite automata is **provable**. So this
repository can show *where exactly* a measure comes loose, instead of noting that a
result looks wrong. It is a testbed for measure design — not an attempt to solve what
others have not.

The catalogue is in [`MEASURES.md`](MEASURES.md), and every case replays:

```bash
python scripts/reproduce_measure_failures.py
```

## Current state

| | |
|---|---|
| Sealed validations | **M012b** autonomous morphogenesis, **M013e** migration to an opaque substrate |
| Ready to freeze | **M017** — self-extending language, criterion now directional |
| Not supported | **M018** — destroying does not restore improvement |
| Rig not valid | **M019** — selection too impatient to value learning |
| Active | **M021** — do these selection measures move true quality? |
| Domain | deterministic finite automata, binary alphabet, 4 to 10 states |
| Substrates | opaque Boolean machines: opcodes with no declared semantics, discovered by probing |

A bounded research laboratory. It demonstrates neither AGI, nor consciousness, nor
open-ended self-improvement. Claims resting on M001–M011 are **not verifiable in this
repository**: see [`archives/README.md`](archives/README.md).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows
pip install -e ".[dev]"
pytest -q
```

Structural checks:

```bash
python scripts/check_repository_integrity.py
```

```bash
python scripts/audit_m017_isolation.py
```

## Layout

- `MEASURES.md` — catalogue of measures that came loose, with ground truth
- `FAILURE_LOG.md` — failures and contaminations, never deleted
- `metamorphosis/` — experimental core, one module prefix per experiment
- `scripts/` — development benchmarks, canonical evaluations, audits, guardrails
- `experiments/<ID>/` — frozen protocol, readable protocol and status of each experiment
- `results/<ID>.md` and `results/<ID>_raw/` — canonical results and raw evidence
- `tests/` — development tests, run by CI on every pull request
- `archives/` — index of retired code, consumed sealed workflows, archive tags
- `.github/workflows/ci.yml` — the only permanent CI

## Scientific rule

An experiment receives exactly one of these statuses: `VALIDATED`, `FAILED` or
`INCONCLUSIVE`.

1. The protocol is frozen and hashed before any result is observed.
2. The canonical evaluation runs once, in CI, on an immutable commit.
3. No rerun replaces a first attempt, and no threshold is relaxed afterwards.
4. Failures and contaminations are kept, never deleted.

See [`PROJECT_STATE.md`](PROJECT_STATE.md), [`ROADMAP.md`](ROADMAP.md),
[`MEASURES.md`](MEASURES.md), [`FAILURE_LOG.md`](FAILURE_LOG.md) and
[`DECISIONS.md`](DECISIONS.md).
