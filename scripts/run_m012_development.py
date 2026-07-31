from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.morphogenesis import (
    GATE_GRAPH_CATALOG,
    QUANTIZED_RECURRENT_CATALOG,
    REGISTER_CATALOG,
    GenericMorphogenesisEngine,
    TransitionConstraint,
)


def constraints(kind: str) -> list[TransitionConstraint]:
    rows: list[TransitionConstraint] = []
    for state in (0, 1):
        for symbol in (0, 1):
            if kind == "toggle":
                nxt = state ^ symbol
            elif kind == "latch":
                nxt = state | symbol
            else:
                raise ValueError(kind)
            rows.append(TransitionConstraint((state,), symbol, (nxt,), nxt))
    return rows


def main() -> None:
    catalogues = [REGISTER_CATALOG, GATE_GRAPH_CATALOG, QUANTIZED_RECURRENT_CATALOG]
    report: dict[str, dict[str, object]] = {}
    for catalogue in catalogues:
        engine = GenericMorphogenesisEngine(catalogue)
        report[catalogue.name] = {}
        for task in ("toggle", "latch"):
            result = engine.synthesize(constraints(task), state_width=1)
            report[catalogue.name][task] = {
                "reason": result.reason,
                "expressions_considered": result.expressions_considered,
                "signatures_discovered": result.signatures_discovered,
                "body": json.loads(result.body.to_json()) if result.body else None,
            }
    output = Path("experiments/M012/development_scaffold.json")
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
