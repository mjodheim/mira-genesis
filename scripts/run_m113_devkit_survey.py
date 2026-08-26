"""Measure, before the plan is frozen, what a carrier bank under this meta-schema looks like.

M112's analysis plan could declare a minimum that was both reachable and refusable because the
project had measured the relevant base rates over 1 160 of its own worlds. Nothing comparable exists
for carriers: nothing of this kind has ever been generated here. So this script generates a large
devkit sample under the frozen meta-schema, applies the frozen qualification rule to it, and records
what came out.

Two things are being measured, and they are different.

**The qualification rate** exists only so that the plan's minimum can be shown to be both meetable
and missable at the requested bank size. It is **not** a prediction about the blind model. M112
measured a six per cent ambiguous rate over its own worlds and its blind bank returned twenty-five
per cent; a pseudo-random emitter's distribution is a third distribution again. The plan says so.

**The feature-row map** is development evidence about the *inherited vocabulary*, and it is recorded
here because it must be recorded before the freeze or it cannot be cited afterwards: if one feature
row carries different limiting components on different carriers, then no function of the inherited
three-feature vocabulary is right on all of them, and M113's central question has an answer that does
not depend on the blind bank at all.

This script writes only `experiments/M113/DEVKIT_SURVEY.json`. It generates no bank, touches no
sealed artifact, and makes no model or network call.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import carrier_host as host  # noqa: E402
from metamorphosis import m113_carrier_bank as bank  # noqa: E402
from metamorphosis import m113_carrier_devkit as devkit  # noqa: E402
from metamorphosis import m113_evaluator as evaluator  # noqa: E402

SURVEY_PATH = ROOT / bank.DEVKIT_SURVEY_PATH
DEFAULT_SAMPLE = 1200
DEFAULT_SEED = "m113-devkit-survey"


def survey(sample: int, seed: str) -> dict[str, Any]:
    qualifying = 0
    blocking: Counter[str] = Counter()
    surfaces: Counter[str] = Counter()
    signatures: set[str] = set()
    rows: dict[int, set[str]] = {}
    row_counts: Counter[int] = Counter()
    ground_truth: Counter[str] = Counter()
    closure_iterations: list[int] = []
    state_counts: list[int] = []
    observation_depths: Counter[int] = Counter()
    latent_carriers = 0

    for index in range(int(sample)):
        carrier = devkit.development_carrier("%s:%d" % (seed, index))
        surfaces[carrier["surface"]["kind"]] += 1
        signatures.add(host.structural_signature(carrier))
        if any(not shown for shown in carrier["visible"]):
            latent_carriers += 1
        report = evaluator.qualification_report(carrier)
        closure_iterations.append(int(report["closure_iterations"]))
        state_counts.append(int(report["state_count"]))
        if not report["qualifies"]:
            for clause in report["blocking_clauses"]:
                blocking[clause] += 1
            continue
        qualifying += 1
        observation_depths[int(report["max_observation_depth"])] += 1
        census = evaluator.attribution_census(carrier)
        for row, labels in census["row_labels"].items():
            rows.setdefault(int(row), set()).update(labels)
            row_counts[int(row)] += int(census["row_counts"][row])
        pair = evaluator.derive_demand_pair(carrier, "opaque-0000000000000000", 1)
        ground_truth[pair["ground_truth"]["component"]] += 1

    ambiguous = sorted(row for row, labels in rows.items() if len(labels) > 1)
    return {
        "schema": bank.SURVEY_SCHEMA,
        "milestone": bank.MILESTONE,
        "carrier_schema_version": bank.CARRIER_SCHEMA_VERSION,
        "emitter": "m113_carrier_devkit.development_carrier",
        "emitter_is_the_blind_generator": False,
        "seed": str(seed),
        "sample": int(sample),
        "qualifying_carriers": qualifying,
        "qualification_rate": round(qualifying / float(sample), 6),
        "blocking_clause_counts": dict(sorted(blocking.items())),
        "surface_kind_counts": dict(sorted(surfaces.items())),
        "distinct_structural_signatures": len(signatures),
        "every_carrier_structurally_distinct": len(signatures) == int(sample),
        "carriers_holding_a_latent_cell": latent_carriers,
        "max_observation_depth_counts": {
            str(depth): count for depth, count in sorted(observation_depths.items())
        },
        "deepest_observation_depth_seen": max(observation_depths) if observation_depths else 0,
        "closure_iterations_max": max(closure_iterations) if closure_iterations else 0,
        "state_count_max": max(state_counts) if state_counts else 0,
        "every_carrier_closed_by_fixed_point": blocking.get("closed_by_fixed_point", 0) == 0,
        "feature_row_components": {
            str(row): sorted(labels) for row, labels in sorted(rows.items())
        },
        "feature_row_counts": {str(row): row_counts[row] for row in sorted(row_counts)},
        "ambiguous_feature_rows": ambiguous,
        "inherited_vocabulary_is_a_function_on_this_sample": not ambiguous,
        "ground_truth_component_counts": dict(sorted(ground_truth.items())),
        "measures_the_blind_generator": False,
        "note": (
            "A devkit rate establishes only that the plan's minimum is both meetable and missable "
            "by a plausible emitter. M112 measured six per cent over project worlds and its blind "
            "bank returned twenty-five, so this is not a prediction and the plan may not be read "
            "as one."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--write", action="store_true", help="write the survey to experiments/M113")
    arguments = parser.parse_args()

    if arguments.sample < 100:
        print("a rate measured over fewer than a hundred carriers cannot support a minimum")
        return 2

    report = survey(arguments.sample, arguments.seed)
    rendered = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if arguments.write:
        SURVEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        SURVEY_PATH.write_bytes((rendered + "\n").encode("ascii"))
        print("wrote %s" % SURVEY_PATH.relative_to(ROOT))

    print(
        "sample %d  qualifying %d  rate %.4f"
        % (report["sample"], report["qualifying_carriers"], report["qualification_rate"])
    )
    print("distinct structural signatures: %d" % report["distinct_structural_signatures"])
    print("surfaces: %s" % report["surface_kind_counts"])
    print("deepest observation depth seen: %d" % report["deepest_observation_depth_seen"])
    print("ambiguous feature rows: %s" % report["ambiguous_feature_rows"])
    for row, labels in report["feature_row_components"].items():
        print("  row %s -> %s" % (row, labels))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
