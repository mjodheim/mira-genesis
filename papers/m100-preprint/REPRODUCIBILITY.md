# Reproducibility note — M094–M100 preprint

This preprint summarizes evidence already preserved in the public Mira Genesis repository. It does not change any frozen protocol, result, checker, threshold, or qualification population.

## Paper anchor

- Repository: `https://github.com/mjodheim/mira-genesis`
- M100 integration commit: `c2273f1ea72e089cd3646e162130bc83b8070b0b`
- M100 freeze/source commit: `c4214d6bdaeb1326c9dcd6d336ff1d4173c96c98`
- Preservation tag: `experiment/m100-positive-result`

## M100 immutable identifiers

- Result digest: `241292fc81e64c8e0ec4620e72304889f52ae2185033e056b787f1b27c6c1475`
- Stable evidence digest: `4bdb1aa8f7a85108eac4e92f8cff90f05a12520462e5ea2b358fc9b5886b19da`
- Checker digest: `d8e945a595571505d9c2a44568029208f41f05010e36d8e7b3f5937016529654`

## Generic repository verification

```bash
python -m pip install -e ".[dev]"
pytest -q
python scripts/check_repository_integrity.py
```

## M100 checker replay

```bash
python scripts/check_m100_result.py --strict --require-result --no-write
```

The scientific verdict is governed by the frozen experiment-local protocol and checker. The generic repository suite is a regression/integrity check, not a replacement for the qualification protocol.

## Evidence map

- `experiments/M094/` — real-software diagnosis and compositional repair; preserved withdrawn attempt and positive successor.
- `experiments/M095/` — preserved negative causal-composition qualification.
- `experiments/M096/` — exact-contract positive successor.
- `experiments/M097/` — acquired state-owned binary-expression operation.
- `experiments/M098/` — preserved negative hard-persistence attempt.
- `experiments/M099/` — positive hard process-death persistence.
- `experiments/M100/` — repeated cumulative acquisition.
- `docs/CURRENT_RESEARCH_FRONTIER.md` — reader-facing current interpretation.
- `PROJECT_STATE.md` / `PROJECT_STATE.yaml` — authoritative project register.
- `FAILURE_LOG.md` — preserved failure history.

## Claim boundary

The preprint reports bounded mechanism evidence. It does not claim AGI, consciousness, unrestricted recursive self-improvement, arbitrary self-modification, autonomous production authority, cross-domain transfer, or independent external reproduction.
