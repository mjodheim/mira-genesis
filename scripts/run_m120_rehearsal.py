#!/usr/bin/env python3
"""The complete M120 success path, rehearsed on DEVELOPMENT data in a disposable checkout.

M119 ran a DEVELOPMENT rehearsal and still shipped a checker with two defects, because what its
rehearsal exercised was not what its checker did in anger: a refusal-path smoke test proves that
the gate says no, and says nothing about what happens when it says yes. So this rehearsal runs the
**exact** path -- the real scripts, in a real git repository, in the real order -- and then runs the
scoring entry point again from a second, clean clone and demands the same bytes.

    disposable checkout
      -> DEVELOPMENT commitments (sizing, rehearsal placeholder, readiness placeholder)
      -> build_m120_freeze.py --plan --spec --nonce --freeze
      -> run_m120_generation.py, with the one HTTP call replaced and nothing else
      -> run_m120_seal.py
      -> run_m120_authorize.py
      -> run_m120_reveal.py
      -> run_m120_qualification.py
      -> check_m120_result.py
      -> second clean clone -> check_m120_result.py -> byte-identical report

Then five substitutions, each of which must fail closed:

    a plan with its minimums set to zero, keeping the frozen commitment string verbatim
    a plan with a recomputed commitment over rewritten thresholds
    a measurements file with a self-consistent digest, written over the canonical path
    an adequacy record whose counts no longer match the revealed bank
    an edit to a tested-system module after the freeze

**Everything it writes is DEVELOPMENT and stays inside the sandbox.** The bank is drawn from
`m120_devkit`, not from the generator; the readiness placeholder is a sandbox fixture and not a
route measurement; and the script refuses to run at all if any qualifying M120 artifact already
exists in the real repository. What leaves the sandbox is a record of counts and outcomes.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m120_bank as bank  # noqa: E402
from metamorphosis import m120_carrier_contract as contract  # noqa: E402
from metamorphosis import m120_chronology as chronology  # noqa: E402
from metamorphosis import m120_devkit as devkit  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

REHEARSAL_SCHEMA = "m120-development-rehearsal-v1"
OUT_PATH = ROOT / chronology.DEVELOPMENT_REHEARSAL
PASSPHRASE = "m120-development-rehearsal-passphrase"
DRAW_MODE = devkit.MODE_UNIFORM
DRAW_SEED = "m120-rehearsal-"


class RehearsalError(RuntimeError):
    """The rehearsal did not reproduce. Every path fails closed."""


# ---------------------------------------------------------------------------------------------
# The disposable checkout
# ---------------------------------------------------------------------------------------------

def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                               check=False)
    if completed.returncode != 0:
        raise RehearsalError("git %s failed in %s: %s"
                             % (" ".join(args), cwd, completed.stderr.strip()))
    return completed.stdout


def _commit(cwd: Path, message: str) -> None:
    _git(cwd, "add", "-A")
    _git(cwd, "-c", "user.name=M120 rehearsal", "-c", "user.email=rehearsal@localhost",
         "commit", "--allow-empty", "-q", "--no-verify", "-m", message)


def _materialize_checkout(destination: Path) -> Path:
    """A real git repository holding the working tree's tracked and untracked-but-not-ignored files.

    Copied rather than cloned, because the point is to rehearse the code as it stands right now,
    including changes that are not committed yet. The sandbox then makes its own commits, so every
    committed-at-HEAD gate the chronology enforces is enforced for real.
    """
    listed = _git(ROOT, "ls-files", "--cached", "--others", "--exclude-standard")
    destination.mkdir(parents=True, exist_ok=True)
    for line in listed.splitlines():
        relative = line.strip()
        if not relative:
            continue
        source = ROOT / relative
        if not source.is_file():
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    # No qualifying M120 artifact may travel into the sandbox: the rehearsal must start from a
    # milestone that has generated nothing, exactly as the real one will.
    for relative in chronology.NO_SCIENTIFIC_ARTIFACT_BEFORE:
        (destination / relative).unlink(missing_ok=True)
    _git(destination, "init", "-q")
    # A checkout whose git normalizes line endings would make every committed-at-HEAD check fail
    # on the copied bytes rather than on anything the rehearsal did. The sandbox stores what it is
    # given, exactly as the real repository does.
    _git(destination, "config", "core.autocrlf", "false")
    _git(destination, "config", "core.eol", "lf")
    _git(destination, "config", "commit.gpgsign", "false")
    _commit(destination, "rehearsal base")
    return destination


# ---------------------------------------------------------------------------------------------
# DEVELOPMENT fixtures the chronology requires before the commitments may be written
# ---------------------------------------------------------------------------------------------

def _development_fixtures(checkout: Path) -> None:
    """Sandbox stand-ins for the three DEVELOPMENT records the chronology requires.

    These are fixtures, not measurements. The real sizing derivation is
    `scripts/build_m120_bank_sizing.py`; the real readiness gate is `scripts/run_m120_readiness.py` and it
    needs the route and a credential. Each fixture says so in its own bytes, and none of them
    leaves the sandbox.
    """
    directory = checkout / chronology.DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    marker = {
        "development": True,
        "is_a_qualifying_call": False,
        "this_is_a_rehearsal_sandbox_fixture_and_is_not_a_measurement": True,
    }
    for relative, extra in (
        (chronology.BANK_SIZING, {"schema": "m120-bank-sizing-development-v1",
                                  "requested_carriers": bank.REQUESTED_CARRIER_COUNT}),
        (chronology.DEVELOPMENT_REHEARSAL, {"schema": REHEARSAL_SCHEMA, "state": "in_progress"}),
        (chronology.READINESS_RESULT, {
            "schema": "m120-readiness-result-v1",
            "milestone": "M120", "hypothesis": "H65",
            "verdict": "ready", "ready": True,
            "candidate_schema_sha256": sha256_hex(
                canonical_bytes(contract.candidate_schema())),
            "result_sha256": "0" * 64,
        }),
    ):
        record = dict(marker)
        record.update(extra)
        (checkout / relative).write_bytes(canonical_bytes(record) + b"\n")


# ---------------------------------------------------------------------------------------------
# The synthetic completion
# ---------------------------------------------------------------------------------------------

def development_completion(count: int, *, mode: str = DRAW_MODE) -> dict[str, Any]:
    """A completion shaped exactly like the route's, carrying a DEVELOPMENT bank."""
    machines = list(devkit.development_candidates(DRAW_SEED, count, mode=mode))
    content = json.dumps({"machines": machines}, separators=(",", ":"))
    return {
        "model": "deepseek/deepseek-v4-flash-0731",
        "provider": "OpenInference",
        "choices": [{"finish_reason": "stop", "index": 0,
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"completion_tokens": len(content) // 3, "prompt_tokens": 1000,
                  "completion_tokens_details": {"reasoning_tokens": 0}},
        "openrouter_metadata": {
            "requested": "deepseek/deepseek-v4-flash-0731",
            "strategy": "direct",
            "attempt": 1,
            "is_byok": False,
            "endpoints": {"available": [
                {"provider": "OpenInference",
                 "model": "deepseek/deepseek-v4-flash-20260731",
                 "selected": True}]},
        },
    }


_DRIVER = '''
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import run_m120_generation as runner

body = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raw = json.dumps(body, separators=(",", ":")).encode("utf-8")


def _fake_request(url, *, body=None, timeout=1800):
    """The one physical call, and nothing else about the runner, is replaced."""
    return {"started_at": "2026-09-02T00:00:00Z", "finished_at": "2026-09-02T00:00:01Z",
            "status": 200, "response_headers": {"x-generation-id": "gen-development"},
            "raw": raw, "body": json.loads(raw.decode("utf-8"))}


runner._request = _fake_request
runner._secret = lambda: "development-not-a-credential"
raise SystemExit(runner.deliver())
'''


def _run(checkout: Path, *args: str, expect: int | None = 0,
         env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment.update(env or {})
    environment["PYTHONPATH"] = str(checkout)
    completed = subprocess.run([sys.executable, *args], cwd=str(checkout), env=environment,
                               capture_output=True, text=True, check=False)
    if expect is not None and completed.returncode != expect:
        raise RehearsalError(
            "%s exited %d, expected %d\n--- stdout ---\n%s\n--- stderr ---\n%s"
            % (" ".join(args), completed.returncode, expect,
               completed.stdout[-4000:], completed.stderr[-4000:]))
    return completed


# ---------------------------------------------------------------------------------------------
# The rehearsal
# ---------------------------------------------------------------------------------------------

def _read(checkout: Path, relative: Path) -> dict[str, Any]:
    return json.loads((checkout / relative).read_text(encoding="utf-8"))


def rehearse(workspace: Path) -> dict[str, Any]:
    checkout = _materialize_checkout(workspace / "checkout")
    _development_fixtures(checkout)
    _commit(checkout, "development fixtures")

    steps: list[dict[str, Any]] = []

    def _step(name: str, *args: str, expect: int | None = 0,
              env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        completed = _run(checkout, *args, expect=expect, env=env)
        steps.append({"step": name, "exit_code": completed.returncode})
        _commit(checkout, name)
        return completed

    _step("plan", "scripts/build_m120_freeze.py", "--plan")
    _step("spec", "scripts/build_m120_freeze.py", "--spec")
    _step("nonce", "scripts/build_m120_freeze.py", "--nonce")
    _step("freeze", "scripts/build_m120_freeze.py", "--freeze")

    completion = development_completion(bank.REQUESTED_CARRIER_COUNT)
    response_path = workspace / "development_response.json"
    response_path.write_text(json.dumps(completion), encoding="utf-8")
    driver = checkout / "scripts" / "rehearsal_generation_driver.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    _step("generation", str(driver), str(response_path))

    admission = _read(checkout, chronology.ADMISSION)
    gate = _read(checkout, chronology.ADEQUACY)
    if admission.get("admitted") is not True:
        raise RehearsalError("the development completion was not admitted: %s"
                             % admission.get("refusal_reasons"))
    if gate.get("adequate") is not True:
        raise RehearsalError("the development bank was not adequate: %s" % gate.get("shortfalls"))
    if admission["admission"]["carriers_refused"] != 0:
        raise RehearsalError(
            "the decoder let %d carriers reach a host refusal, which the contract forbids"
            % admission["admission"]["carriers_refused"])

    seal_env = {"M120_BANK_SEAL_PASSPHRASE": PASSPHRASE}
    _step("seal", "scripts/run_m120_seal.py", env=seal_env)
    _step("authorize", "scripts/run_m120_authorize.py",
          "--authorized-by", "development rehearsal")
    _step("reveal", "scripts/run_m120_reveal.py", "--reveal", env=seal_env)
    _step("qualification", "scripts/run_m120_qualification.py")
    scored = _step("check", "scripts/check_m120_result.py", "--require-result", expect=None)
    report = json.loads(scored.stdout[scored.stdout.index("{"):])

    # ---- the same entry point, from a second clean clone ------------------------------------
    replay_root = workspace / "replay"
    # Cloned with normalization off, because the chronology authenticates raw bytes: a clone
    # that rewrote line endings would fail every committed-at-HEAD gate for a reason that has
    # nothing to do with what is being rehearsed.
    _git(workspace, "-c", "core.autocrlf=false", "clone", "-q", str(checkout), str(replay_root))
    replayed = _run(replay_root, "scripts/check_m120_result.py", "--require-result", expect=None)
    replay_report = json.loads(replayed.stdout[replayed.stdout.index("{"):])
    if replay_report["report_sha256"] != report["report_sha256"]:
        raise RehearsalError(
            "the clean clone did not reproduce the report: %s against %s"
            % (replay_report["report_sha256"], report["report_sha256"]))

    substitutions = _substitutions(workspace, checkout, report)

    measurements = _read(checkout, chronology.MEASUREMENTS)
    reveal = _read(checkout, chronology.REVEAL_RECORD)
    return {
        "schema": REHEARSAL_SCHEMA,
        "milestone": "M120", "hypothesis": "H65",
        "development": True,
        "is_a_qualifying_call": False,
        "is_evidence_for_h65": False,
        "advances_a_generality_gate": False,
        "the_bank_was_drawn_from_the_development_emitter_not_the_generator": True,
        "draw_mode": DRAW_MODE,
        "draw_seed_prefix": DRAW_SEED,
        "contract_version": contract.CONTRACT_VERSION,
        "decoder_version": contract.DECODER_VERSION,
        "candidate_schema_sha256": sha256_hex(canonical_bytes(contract.candidate_schema())),
        "steps": steps,
        "carriers_enveloped": admission["admission"]["carriers_enveloped"],
        "carriers_refused_by_the_frozen_host": admission["admission"]["carriers_refused"],
        "every_decoded_candidate_was_accepted":
            admission["admission"]["carriers_refused"] == 0,
        "qualifying_carriers": gate["qualifying_carriers"],
        "distinct_qualifying_structures": gate["distinct_qualifying_structures"],
        "paired_demands_available": gate["paired_demands_available"],
        "preseal_adequacy_verdict": gate["adequate"],
        "reveals_performed": reveal["reveals_performed"],
        "paired_demands_scored": report["verdict"] and len(measurements["entries"]) * 2,
        "development_verdict": report["verdict"],
        "development_verdict_is_not_evidence_about_h65": True,
        "report_sha256": report["report_sha256"],
        "clean_clone_reproduced_the_report_byte_identically": True,
        "substitutions": substitutions,
        "every_substitution_failed_closed": all(s["refused"] for s in substitutions),
        "rehearsal_sha256": "",
    }


def _substitutions(workspace: Path, source: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    """Each attack gets its own clone, so no attack can be masked by an earlier one."""
    attacks: list[dict[str, Any]] = []

    def _attack(name: str, mutate) -> None:
        target = workspace / ("attack_%s" % name)
        _git(workspace, "-c", "core.autocrlf=false", "clone", "-q", str(source), str(target))
        _git(target, "config", "core.autocrlf", "false")
        _git(target, "config", "commit.gpgsign", "false")
        mutate(target)
        completed = _run(target, "scripts/check_m120_result.py", "--require-result", expect=None)
        refused = completed.returncode != 0 and "REFUSED" in completed.stdout
        attacks.append({
            "attack": name,
            "refused": bool(refused),
            "exit_code": completed.returncode,
            "message": completed.stdout.strip().splitlines()[0][:300]
            if completed.stdout.strip() else "",
        })

    def _zeroed_plan(target: Path) -> None:
        """M119's exact defect: rewrite the thresholds, keep the commitment string verbatim."""
        path = target / chronology.ANALYSIS_PLAN
        plan = json.loads(path.read_text(encoding="utf-8"))
        plan["minimum_qualifying_carriers"] = 0
        plan["minimum_distinct_qualifying_structures"] = 0
        path.write_bytes(canonical_bytes(plan) + b"\n")
        _commit(target, "attack: zeroed plan minimums")

    def _recommitted_plan(target: Path) -> None:
        """The same rewrite, with the digest recomputed so it matches its own contents."""
        path = target / chronology.ANALYSIS_PLAN
        plan = json.loads(path.read_text(encoding="utf-8"))
        plan["minimum_qualifying_carriers"] = 0
        plan["alpha"] = 0.5
        plan["plan_commitment_sha256"] = sha256_hex(canonical_bytes(
            {k: v for k, v in plan.items() if k != "plan_commitment_sha256"}))
        path.write_bytes(canonical_bytes(plan) + b"\n")
        _commit(target, "attack: recommitted plan")

    def _forged_measurements(target: Path) -> None:
        """A fabricated measurement, self-consistent, written over the canonical path."""
        path = target / chronology.MEASUREMENTS
        measurements = json.loads(path.read_text(encoding="utf-8"))
        for entry in measurements["entries"]:
            for arm, rows in entry["arms"].items():
                for demand_class, row in rows.items():
                    if not isinstance(row, dict) or "score" not in row:
                        continue
                    if arm == "FULL":
                        row["score"]["correct_construction"] = True
                        row["score"]["calibrated_refusal"] = True
                    if arm == "FRESH":
                        row["score"]["correct_construction"] = False
                        row["score"]["calibrated_refusal"] = False
        measurements["measurements_sha256"] = sha256_hex(canonical_bytes(
            {k: v for k, v in measurements.items() if k != "measurements_sha256"}))
        path.write_bytes(canonical_bytes(measurements) + b"\n")
        _commit(target, "attack: forged measurements")

    def _tampered_adequacy(target: Path) -> None:
        path = target / chronology.ADEQUACY
        gate = json.loads(path.read_text(encoding="utf-8"))
        gate["qualifying_carriers"] = gate["qualifying_carriers"] + 1
        path.write_bytes(canonical_bytes(gate) + b"\n")
        _commit(target, "attack: tampered adequacy")

    def _swapped_carrier_bank(target: Path) -> None:
        """A different bank, committed over the canonical path."""
        from metamorphosis import m120_admission as m120_admission_module
        path = target / chronology.CARRIER_BANK
        payload = json.loads(path.read_text(encoding="utf-8"))
        replacement = m120_admission_module.envelope_payload(
            {"machines": list(devkit.development_candidates("m120-attack-", 48,
                                                            mode=DRAW_MODE))},
            payload["bank_nonce"])
        path.write_bytes(canonical_bytes(replacement) + b"\n")
        _commit(target, "attack: swapped carrier bank")

    def _swapped_bank_and_reveal(target: Path) -> None:
        """The same swap, with the reveal record rewritten to name the new bank."""
        from metamorphosis import m120_admission as m120_admission_module
        bank_path = target / chronology.CARRIER_BANK
        payload = json.loads(bank_path.read_text(encoding="utf-8"))
        replacement = m120_admission_module.envelope_payload(
            {"machines": list(devkit.development_candidates("m120-attack-", 48,
                                                            mode=DRAW_MODE))},
            payload["bank_nonce"])
        bank_path.write_bytes(canonical_bytes(replacement) + b"\n")
        reveal_path = target / chronology.REVEAL_RECORD
        reveal = json.loads(reveal_path.read_text(encoding="utf-8"))
        reveal["carrier_bank_sha256"] = sha256_hex(canonical_bytes(replacement))
        reveal["reveal_record_sha256"] = sha256_hex(canonical_bytes(
            {k: v for k, v in reveal.items() if k != "reveal_record_sha256"}))
        reveal_path.write_bytes(canonical_bytes(reveal) + b"\n")
        _commit(target, "attack: swapped bank and reveal record")

    def _tampered_public_commitment(target: Path) -> None:
        path = target / chronology.PUBLIC_BANK_COMMITMENT
        commitment = json.loads(path.read_text(encoding="utf-8"))
        commitment["preseal_adequacy_verdict"] = True
        commitment["admission_sha256"] = "0" * 64
        commitment["commitment_sha256"] = sha256_hex(canonical_bytes(
            {k: v for k, v in commitment.items() if k != "commitment_sha256"}))
        path.write_bytes(canonical_bytes(commitment) + b"\n")
        _commit(target, "attack: tampered public commitment")

    def _tampered_admission(target: Path) -> None:
        path = target / chronology.ADMISSION
        record = json.loads(path.read_text(encoding="utf-8"))
        record["admission"]["carriers_refused"] = 7
        path.write_bytes(canonical_bytes(record) + b"\n")
        _commit(target, "attack: tampered admission record")

    def _edited_tested_system(target: Path) -> None:
        path = target / "metamorphosis" / "m120_adequacy.py"
        path.write_text(path.read_text(encoding="utf-8") + "\n# edited after the freeze\n",
                        encoding="utf-8")
        _commit(target, "attack: edited tested system")

    _attack("zeroed_plan_minimums_keeping_the_commitment_string", _zeroed_plan)
    _attack("rewritten_plan_with_a_recomputed_commitment", _recommitted_plan)
    _attack("forged_measurements_with_a_self_consistent_digest", _forged_measurements)
    _attack("tampered_preseal_adequacy_record", _tampered_adequacy)
    _attack("tested_system_edited_after_the_freeze", _edited_tested_system)
    _attack("carrier_bank_swapped_for_another", _swapped_carrier_bank)
    _attack("carrier_bank_and_reveal_record_swapped_together", _swapped_bank_and_reveal)
    _attack("tampered_public_bank_commitment", _tampered_public_commitment)
    _attack("tampered_preseal_admission_record", _tampered_admission)
    return attacks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", required=True)
    parser.add_argument("--write", action="store_true",
                        help="write the rehearsal record to its committed path")
    parser.add_argument("--keep", type=Path,
                        help="keep the sandbox in this directory instead of a temporary one")
    args = parser.parse_args()
    try:
        chronology.assert_no_scientific_observation_yet(ROOT)
        if args.keep:
            args.keep.mkdir(parents=True, exist_ok=True)
            record = rehearse(args.keep)
        else:
            with tempfile.TemporaryDirectory(prefix="m120-rehearsal-") as temporary:
                record = rehearse(Path(temporary))
    except (RehearsalError, chronology.ChronologyError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    record["rehearsal_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "rehearsal_sha256"}))
    if args.write:
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_bytes(canonical_bytes(record) + b"\n")
        print("wrote %s" % OUT_PATH.name)
    print(json.dumps({k: record[k] for k in (
        "carriers_enveloped", "carriers_refused_by_the_frozen_host", "qualifying_carriers",
        "distinct_qualifying_structures", "paired_demands_available", "development_verdict",
        "clean_clone_reproduced_the_report_byte_identically", "every_substitution_failed_closed",
        "report_sha256", "rehearsal_sha256")}, indent=2, sort_keys=True))
    for attack in record["substitutions"]:
        print("  %-58s %s" % (attack["attack"], "refused" if attack["refused"] else "ACCEPTED"))
    return 0 if record["every_substitution_failed_closed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
