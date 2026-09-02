#!/usr/bin/env python3
"""Write M120's commitments, in the order the chronology requires and no other.

Four steps, each single-use and each refusing to run behind a later one:

    --plan       derive and write the analysis plan
    --spec       derive and write the generator spec and the qualifying input
    --nonce      draw and write the bank nonce commitment
    --freeze     take the tested-system freeze against all three

Inherited from M119's builder unchanged in shape. What differs is what the chronology will not let
it do: `--plan` cannot run until the DEVELOPMENT sizing, rehearsal and route-readiness records are
committed, and `--freeze` cannot run until a committed M120 readiness result says this route
enforces *this* candidate schema.

Nothing here sends a request, reads a completion or scores anything. Every artifact is derived from
committed code rather than authored here, so `m120_bank.validate_*` can refuse anything that is not
what the derivation produces -- which makes a post-freeze edit an error rather than a silent change
of contract.

The nonce is drawn from the operating system's entropy, written once, and must be committed before
the generation: the comparator's per-demand draw consults the opaque carrier references derived
from it, so a nonce chosen after the bank existed would be a degree of freedom over the comparator.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m120_admission as admission  # noqa: E402
from metamorphosis import m120_bank as bank  # noqa: E402
from metamorphosis import m120_chronology as chronology  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

PLAN_PATH = ROOT / chronology.ANALYSIS_PLAN
SPEC_PATH = ROOT / chronology.GENERATOR_SPEC
INPUT_PATH = ROOT / chronology.QUALIFYING_INPUT
NONCE_PATH = ROOT / chronology.BANK_NONCE_COMMITMENT
FREEZE_PATH = ROOT / chronology.TESTED_SYSTEM_FREEZE


class BuildError(RuntimeError):
    """A commitment cannot be written honestly. Every path fails closed."""


def _refuse_if_present(*paths: Path) -> None:
    present = [p.name for p in paths if p.exists()]
    if present:
        raise BuildError("already written, and each commitment is written once: %s"
                         % ", ".join(present))


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise BuildError("%s has not been written yet" % path.name)
    return json.loads(path.read_text(encoding="utf-8"))


def write_plan() -> dict[str, Any]:
    chronology.assert_stage_permitted("commitments", ROOT)
    _refuse_if_present(PLAN_PATH, SPEC_PATH, NONCE_PATH, FREEZE_PATH)
    chronology.assert_no_scientific_observation_yet(ROOT)
    plan = bank.build_analysis_plan(ROOT)
    bank.validate_analysis_plan(plan, ROOT)
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_bytes(canonical_bytes(plan) + b"\n")
    return {"wrote": PLAN_PATH.name,
            "plan_commitment_sha256": plan["plan_commitment_sha256"],
            "session_budget": plan["session_budget"],
            "requested_carriers": plan["bank_sizing"]["requested_carriers"],
            "minimum_qualifying_carriers": plan["minimum_qualifying_carriers"]}


def write_spec() -> dict[str, Any]:
    _refuse_if_present(SPEC_PATH, INPUT_PATH, NONCE_PATH, FREEZE_PATH)
    chronology.assert_no_scientific_observation_yet(ROOT)
    plan = _load(PLAN_PATH)
    bank.validate_analysis_plan(plan, ROOT)
    spec = bank.build_generator_spec(plan, ROOT)
    bank.validate_generator_spec(spec, plan, ROOT)
    INPUT_PATH.write_bytes(bank.qualifying_input(ROOT).encode("utf-8"))
    SPEC_PATH.write_bytes(canonical_bytes(spec) + b"\n")
    if sha256_hex(INPUT_PATH.read_bytes()) != spec["qualifying_input"]["sha256"]:
        raise BuildError("the written qualifying input does not match the spec's digest")
    return {"wrote": [SPEC_PATH.name, INPUT_PATH.name],
            "spec_commitment_sha256": spec["spec_commitment_sha256"],
            "canonical_request_body_sha256": spec["canonical_request_body_sha256"],
            "provider": spec["generator_identity"]["provider"],
            "requested_carrier_count": spec["requested_carrier_count"],
            "contamination_hits_in_the_prompt":
                spec["blindness_contract"]["contamination_hits_in_the_prompt"]}


def write_nonce() -> dict[str, Any]:
    _refuse_if_present(NONCE_PATH, FREEZE_PATH)
    chronology.assert_no_scientific_observation_yet(ROOT)
    _load(SPEC_PATH)
    nonce = secrets.token_hex(32)
    record = {
        "schema": "m120-bank-nonce-commitment-v1", "milestone": "M120", "hypothesis": "H65",
        "bank_nonce": nonce,
        "bank_nonce_sha256": sha256_hex(nonce.encode("ascii")),
        "envelope_version": admission.ENVELOPE_VERSION,
        "drawn_from": "os entropy via secrets.token_hex(32)",
        "committed_before_generation": True,
        "why_it_must_precede_the_bank": "the comparator's per-demand draw consults the opaque "
                                       "carrier references derived from this nonce, so a nonce "
                                       "chosen after the bank existed would be a degree of "
                                       "freedom over the comparator",
        "the_generator_never_sees_it": True,
    }
    NONCE_PATH.write_bytes(canonical_bytes(record) + b"\n")
    return {"wrote": NONCE_PATH.name, "bank_nonce_sha256": record["bank_nonce_sha256"]}


def take_freeze() -> dict[str, Any]:
    _refuse_if_present(FREEZE_PATH)
    chronology.assert_stage_permitted("scientific_freeze", ROOT)
    # The readiness result must exist *and* say the route enforces this candidate schema. M119
    # inherited a readiness result across a schema change; this one refuses to.
    readiness = chronology.assert_readiness_passed(ROOT)
    record = chronology.build_freeze(ROOT)
    FREEZE_PATH.write_bytes(canonical_bytes(record) + b"\n")
    chronology.validate_freeze(record, ROOT)
    return {"wrote": FREEZE_PATH.name,
            "freeze_commitment_sha256": record["freeze_commitment_sha256"],
            "tested_system_paths": len(record["tested_system_digests"]),
            "interpretation_closure": len(record["inventory"]["interpretation_closure"]),
            "closure_is_fully_bound": record["inventory"]["closure_is_fully_bound"],
            "bound_commitments": record["bound_commitments"],
            "readiness": readiness}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--spec", action="store_true")
    mode.add_argument("--nonce", action="store_true")
    mode.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    try:
        if args.plan:
            report = write_plan()
        elif args.spec:
            report = write_spec()
        elif args.nonce:
            report = write_nonce()
        else:
            report = take_freeze()
    except (BuildError, bank.BankError, chronology.ChronologyError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
