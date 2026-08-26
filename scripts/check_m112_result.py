"""Independent M112 checker.

Recomputes the transfer and diagnosis predicate sets from the preserved evidence using the **frozen
M110 and M111 checkers**, which is what the analysis plan means by "the M110 predicate set,
recomputed on the revealed worlds". It imports those two `evaluate_conditions` functions and nothing
else: neither reads a runtime, an orchestration or a population.

The verdict rule is inherited rather than invented. The frozen plan named the two predicate sets but
did not state a threshold over them, so the **stricter** available reading is taken: each arm carries
its own milestone's rule, `positive iff every predicate is computed true`. Choosing the stricter
reading of an ambiguous freeze is the only choice that cannot be accused of having been fitted to the
outcome.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
from typing import Any  # noqa: E402

from scripts.check_m110_result import evaluate_conditions as m110_conditions  # noqa: E402
from scripts.check_m111_result import evaluate_conditions as m111_conditions  # noqa: E402

ROOT = _ROOT
EXPERIMENT = ROOT / "experiments" / "M112"
RESULT_PATH = EXPERIMENT / "RESULT.json"
REPORT_PATH = EXPERIMENT / "CHECK_REPORT.json"

EXPECTED_ARM_PREDICATES = ["P%d" % index for index in range(1, 25)]
EVIDENCE_TIER = "blind_generated_sealed_bank"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def evaluate_procedure(evidence: dict[str, Any]) -> dict[str, bool]:
    """Q1-Q10: the procedural independence M112 exists to materialize, and nothing more."""
    reveal = evidence.get("reveal") or {}
    strat = evidence.get("stratification") or {}
    isolation = evidence.get("isolation") or {}
    facts = evidence.get("generation_facts") or {}
    generator = evidence.get("generator") or {}
    boundary = evidence.get("claim_boundary") or {}
    return {
        "Q1": reveal.get("revealed_matches_commitment") is True,
        "Q2": bool(reveal.get("commitment_published_at_commit"))
        and bool(reveal.get("system_protocol_frozen_at_commit"))
        and reveal.get("commitment_published_at_commit")
        != reveal.get("system_protocol_frozen_at_commit"),
        "Q3": isolation.get("only_loopback_interface") is True
        and isolation.get("dns_resolution_fails") is True,
        "Q4": isolation.get("mnt_host_absent") is True
        and isolation.get("mnt_c_absent") is True
        and isolation.get("host_mnt_absent") is True
        and isolation.get("traversal_out_of_in_fails") is True
        and isolation.get("no_symlinks_in_the_input_mount") is True,
        "Q5": isolation.get("no_path_naming_the_project_at_root_or_home") is True
        and isolation.get("no_environment_variable_naming_the_project") is True,
        "Q6": bool(generator.get("model_blob_sha256")) and bool(generator.get("image_digest")),
        "Q7": facts.get("done") is True and facts.get("done_reason") == "stop",
        "Q8": strat.get("filtering_or_selection") is False
        and strat.get("applied_to_every_revealed_world") is True,
        "Q9": strat.get("minima_met") is True,
        "Q10": boundary.get("evidence_tier") == EVIDENCE_TIER
        and boundary.get("human_independence") is False
        and boundary.get("external_reproduction") is False
        and boundary.get("removes_carrier_authorship") is False
        and boundary.get("closes_g4") is False
        and boundary.get("advances_any_generality_gate") is False,
    }


def _read_canonical(path: Path, label: str) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("ascii"))
    if canonical_json(value).encode("ascii") != raw:
        raise RuntimeError("%s is not canonical" % label)
    return value


def check(*, result_path: Path, report_path: Path | None) -> dict[str, Any]:
    result = _read_canonical(result_path, "M112 result")
    evidence = result.get("scientific_evidence") or {}

    transfer = evidence.get("transfer_arm") or {}
    diagnosis = evidence.get("diagnosis_arm") or {}
    recomputed_transfer = {
        k: bool(v)
        for k, v in m110_conditions(transfer.get("evidence") or {}, replay_confirmed=True).items()
    }
    recomputed_diagnosis = {
        k: bool(v)
        for k, v in m111_conditions(diagnosis.get("evidence") or {}, replay_confirmed=True).items()
    }
    procedure = evaluate_procedure(evidence)

    integrity = {
        "schema_is_the_declared_one": result.get("schema") == "m112-result-v1",
        "attempt_is_the_first": result.get("attempt") == 1,
        "result_digest_recomputes": result.get("result_digest")
        == digest({k: v for k, v in result.items() if k != "result_digest"}),
        "evidence_tier_is_the_pre_registered_one": result.get("evidence_tier") == EVIDENCE_TIER,
        "transfer_conditions_recompute": recomputed_transfer == transfer.get("conditions"),
        "diagnosis_conditions_recompute": recomputed_diagnosis == diagnosis.get("conditions"),
        "qualification_made_no_model_call": result.get("model_calls_in_qualification") == 0,
        "bank_generation_made_exactly_one_model_call": result.get("model_calls_in_bank_generation")
        == 1,
    }

    transfer_true = sum(1 for v in recomputed_transfer.values() if v)
    diagnosis_true = sum(1 for v in recomputed_diagnosis.values() if v)
    procedure_true = sum(1 for v in procedure.values() if v)

    report = {
        "schema": "m112-check-report-v1",
        "milestone": "M112",
        "hypothesis": "H57",
        "evidence_tier": EVIDENCE_TIER,
        "result_digest": result.get("result_digest"),
        "bank_commitment_sha256": result.get("bank_commitment_sha256"),
        "integrity": integrity,
        "procedure": procedure,
        "procedure_true": procedure_true,
        "procedure_total": len(procedure),
        "transfer_arm": {
            "conditions": recomputed_transfer,
            "true": transfer_true,
            "total": len(EXPECTED_ARM_PREDICATES),
            "false": sorted(k for k, v in recomputed_transfer.items() if not v),
            "verdict": "positive" if transfer_true == len(EXPECTED_ARM_PREDICATES) else "negative",
        },
        "diagnosis_arm": {
            "conditions": recomputed_diagnosis,
            "true": diagnosis_true,
            "total": len(EXPECTED_ARM_PREDICATES),
            "false": sorted(k for k, v in recomputed_diagnosis.items() if not v),
            "verdict": "positive" if diagnosis_true == len(EXPECTED_ARM_PREDICATES) else "negative",
        },
        "verdict_rule": "inherited, not invented: each arm carries its own milestone's rule, and "
                        "the procedural block must be entirely true",
        "procedural_independence_established": procedure_true == len(procedure),
    }
    report["verdict"] = (
        "positive"
        if all(integrity.values())
        and report["procedural_independence_established"]
        and report["transfer_arm"]["verdict"] == "positive"
        and report["diagnosis_arm"]["verdict"] == "positive"
        else "mixed"
        if report["diagnosis_arm"]["verdict"] == "positive"
        or report["transfer_arm"]["verdict"] == "positive"
        else "negative"
    )
    report["report_digest"] = digest({k: v for k, v in report.items()})
    if report_path is not None:
        with report_path.open("xb") as handle:
            handle.write(canonical_json(report).encode("ascii"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", default=str(RESULT_PATH))
    parser.add_argument("--report", default=None)
    parser.add_argument("--write-report", action="store_true")
    arguments = parser.parse_args()
    report_path = None
    if arguments.write_report:
        report_path = Path(arguments.report) if arguments.report else REPORT_PATH
    try:
        report = check(result_path=Path(arguments.result), report_path=report_path)
    except Exception as error:  # noqa: BLE001 - the refusal is the observation
        print(
            json.dumps(
                {
                    "schema": "m112-check-refusal-v1",
                    "failed_closed": True,
                    "error": "%s: %s" % (type(error).__name__, error),
                },
                sort_keys=True,
            )
        )
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0 if report["verdict"] == "positive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
