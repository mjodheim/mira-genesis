# M101 scientific result — positive

M101 attempt 1 is a **positive qualified scientific result**. H46 is supported inside the frozen,
project-authored text/record/Python-syntax domain. The independent checker recomputed all fifteen
conditions true, with no failed or uncomputed condition.

## Cross-family cumulative chain

The canonical local Track-A run began from clean freeze commit `b3e172b` and used zero model,
network or remote-execution calls.

```text
T0: exact M100 state + 0 M101 definitions
  -> acquire generic two-effect combinator A from public text demand
T1: exact M100 state + A
  -> reuse A after producer death on text, records and Python syntax
  -> acquire three-effect Python-syntax operation B through a live call to A
T2: exact M100 state + A + B
```

A was acquired without an authored target trace: 9,330 bodies were assembled, 15 were well formed,
135 bindings were evaluated and eight candidates were accepted. The selected shortest body has
length four: `LOAD_INPUT, APPLY_SLOT:0, APPLY_SLOT:1, RETURN`. It carries no text-, record- or
syntax-specific identity.

After producer death, the retained A arm passed all eight held-out transfer worlds — two text,
three record and three Python-syntax worlds — while every otherwise identical fresh T0 lineage
passed zero hidden cases. Increasing the T0 budget cannot add the missing two-effect construction:
the fresh arm can execute only one atomic operation per candidate.

B was then acquired from an observable three-effect Python-syntax demand: 41,370 bodies were
assembled, 27 were well formed, 1,728 bindings were evaluated and six candidates were accepted.
Its shortest body has length four and stores a content-addressed call to A before its third effect.
Without registered A, B acquisition returns no candidate.

## Causal controls

- Building A without registration leaves T0 byte-identical; building B without registration leaves
  T1 byte-identical.
- Semantic mutation or ablation of A breaks B in every B world as predicted.
- B ablation breaks B while unrelated A reuse remains live.
- Corrupt state fails closed.
- A live semantic fault suppresses B; restoring the exact T2 bytes restores B in a fresh process.
- The exact M100 predecessor bytes remain unchanged and all three M100 operations pass their fresh
  conservation worlds.
- All 44 scientific invocations ran in isolated base-Python processes with no imported project
  module or repository search path.
- Clean replay changed only frozen ephemera and reproduced the same stable evidence digest.

## Scientific reading and boundary

This is the first qualified **bounded cross-family cumulative mechanism evidence** in Genesis II.
It establishes a constructive-reach advantage over a fresh lineage with equal atomics, runtime,
public observations and search budget: the advantage comes from persisted A bytes and their live
use, not extra host semantics or a faster search for the same reachable program.

It is partial evidence toward G4, not closure of G4. All M101 worlds, carriers, atomic adapters and
evaluators are project-authored; the families share one frozen generic runtime; the cumulative
depth is A → B; and no independently maintained environment, private external task, human baseline
or independent human reproduction participates. The result is not AGI, general-agent evidence,
open-ended or recursive self-improvement, self-hosting, arbitrary self-modification or production
authority.

The measured next ceiling is a deeper cross-family chain under genuine interference and pressure
from at least one independently maintained domain, while retaining the M101 acquisitions and M100
predecessor exactly enough for causal replay.

## Immutable evidence

- protocol/mechanism/pool freeze: `experiment/m101-frozen-protocol-v4` at
  `b3e172bba0cfdd282e6235e62bb8e7d213a77837`;
- protocol raw SHA-256: `178ff03dd748cb57f686290cf9a7de1ef412075cbe2833dc4ea0fb4a6418ee64`;
- pool digest: `85f9d5dfc0fef2d368f005594f03ba6d2b54c9935e9520650d3da33632560fd6`;
- result digest: `486f33e6673c8ad66f822ba11a91a595a155a65b36f2c5292c9ea200d9dbda35`;
- raw `RESULT.json` SHA-256: `99d00c450184ce315d0c6c3893d3baa3c44ab37454c25618c69d3e19e452a07c`;
- stable evidence digest: `45f18dc644784d38a598066e53f1b19d8619cf47fc094c8a0456574373565e92`;
- checker report digest: `95bffc8ba2a0b70d06148c71be3e28b2fc1f64f8655d380430bdedc5c682cb43`;
- first-result preservation tag: `experiment/m101-canonical-first-result` at
  `5c952cb069600fc1e15adce09f3d6f616ee82af4`;
- positive-verdict preservation tag: `experiment/m101-positive-result` at
  `0bb19744e2782925222ebb83aa56918eb874ab53`.
