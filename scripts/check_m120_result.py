#!/usr/bin/env python3
"""Independent H65 checker: recompute everything, from evidence this script resolves itself.

M119's checker recomputed the paired outcomes and every guard measure from per-demand evidence,
which was right, and it took both the analysis plan and the measurements file from the command
line, which was not. Closing review reproduced two consequences:

* a plan file with `minimum_qualifying_carriers` and `minimum_distinct_qualifying_structures` set
  to zero, carrying the frozen commitment string verbatim, was accepted -- because the check
  compared the measurement's recorded plan digest against the plan's *own copy* of that digest and
  never recomputed it from the plan's contents, let alone re-derived the plan from code;
* the replay gate proved the committed `MEASUREMENTS.json` was at HEAD and unchanged, and then
  scored whatever path `--measurements` named.

Both are the same defect: **the checker authenticated one thing and scored another.** This one has
no scientific evidence path a caller can point at. It takes no arguments that select evidence, it
resolves the committed canonical artifacts from the chronology's own constants, and it scores the
bytes it authenticated.

Authenticating a file, though, is not the same as knowing what is in it. M120's own DEVELOPMENT
rehearsal proved that on an earlier draft of this script: an attack that rewrote every score in the
committed measurements, recomputed the digest and committed it over the canonical path was
**accepted**, because the file was at HEAD, matched its own digest, named the committed reveal and
carried the right freeze commitment. Every binding held and the numbers were still invented.

So this checker does not read the measurements at all. It **reproduces** them.

Four bindings, in this order:

1. `assert_frozen_system_unchanged(phase="replay")` proves the tested system still matches its
   freeze and that every artifact the earlier phases produced -- the plan, the ledger, the
   admission and adequacy records, the sealed bank, the reveal and the measurements -- is
   committed at HEAD byte-identically to disk.
2. `m120_bank.validate_analysis_plan` re-derives the plan from code and compares canonical bytes.
   A forged plan preserving the old digest string fails here, because the digest is recomputed
   from contents and the contents are then rebuilt from the derivation.
3. `m120_measurement.measure` re-runs the whole measurement over the committed carrier bank, the
   re-derived plan and the committed nonce, and the result must equal the committed measurements
   byte for byte. The measurement is a pure function of those three inputs and the frozen arms,
   evaluator, runtime and host, so a fabricated `entries` array is not a file that has to be
   caught by a rule someone remembered to write: it is a file that does not reproduce.
4. every number in the report is then recomputed from the reproduced evidence.

It reads no verdict the runner could have written, and no number either.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m113_evaluator as evaluator  # noqa: E402
from metamorphosis import m119_arms as arms  # noqa: E402
from metamorphosis import m119_decomposition as decomposition  # noqa: E402
from metamorphosis import m119_endpoint as endpoint  # noqa: E402
from metamorphosis import m120_adequacy as adequacy  # noqa: E402
from metamorphosis import m120_admission as admission  # noqa: E402
from metamorphosis import m120_bank as bank  # noqa: E402
from metamorphosis import m120_carrier_contract as contract  # noqa: E402
from metamorphosis import m120_chronology as chronology  # noqa: E402
from metamorphosis import m120_measurement as measurement  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

CHECK_SCHEMA = "m120-h65-check-report-v1"
MEASUREMENTS_SCHEMA = measurement.MEASUREMENTS_SCHEMA


class CheckError(RuntimeError):
    """The record does not reproduce. Every path fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def recompute_outcomes(entries) -> dict[str, list[bool]]:
    """Paired primary outcomes per arm, from the per-demand evidence alone."""
    outcomes: dict[str, list[bool]] = {name: [] for name in arms.ALL_ARM_NAMES}
    for entry in entries:
        for demand_class in evaluator.DEMAND_CLASSES:
            for name in arms.ALL_ARM_NAMES:
                row = entry["arms"][name][demand_class]
                # Recomputed from the score, not read from the runner's `primary_success`.
                outcomes[name].append(endpoint.primary_success(demand_class, row["score"]))
    return outcomes


def recompute_measures(entries) -> dict[str, dict[str, Any]]:
    """Every guard measure, recounted from the per-demand evidence."""
    measures: dict[str, dict[str, Any]] = {}
    for name in arms.ALL_ARM_NAMES:
        counts = {key: 0 for key in ("invented_adapter", "false_refusal")}
        correct = examined = 0
        for entry in entries:
            for demand_class in evaluator.DEMAND_CLASSES:
                row = entry["arms"][name][demand_class]
                for key in counts:
                    counts[key] += bool(row["score"].get(key))
                if demand_class == evaluator.CLASS_REACHABLE and "attribution_correct" in row:
                    examined += 1
                    correct += bool(row["attribution_correct"])
        measures[name] = dict(counts)
        measures[name]["attribution_correct"] = correct
        measures[name]["attribution_examined"] = examined
        measures[name]["attribution_agreement_rate"] = (correct / examined) if examined else None
    return measures


def budget_attribution(entries, rates: Mapping[str, Any], verdict: str) -> dict[str, Any]:
    """Was a negative the machinery's, or the observation budget's?

    Inherited unchanged from M119's checker. The policy gates a diagnostic probe, the probe
    consumes observations, and an exploration that runs out does not close -- so at a fixed budget
    an arm that probes can be penalised for the cost of probing rather than for what it acquired.
    It can attribute a negative. It can never create a positive: it is reported beside the verdict,
    never fed into it.
    """
    exhausted = {name: 0 for name in arms.ALL_ARM_NAMES}
    undetermined_at_the_ceiling = {name: 0 for name in arms.ALL_ARM_NAMES}
    for entry in entries:
        for demand_class in evaluator.DEMAND_CLASSES:
            for name in arms.ALL_ARM_NAMES:
                row = entry["arms"][name][demand_class]
                if row.get("budget_exhausted"):
                    exhausted[name] += 1
                    if row.get("verdict") == "undetermined":
                        undetermined_at_the_ceiling[name] += 1
    descendant = rates.get(arms.DESCENDANT_ARM)
    at_higher_budget = rates.get(arms.FULL_BUDGET_PLUS)
    improves = (None if descendant is None or at_higher_budget is None
                else at_higher_budget - descendant)
    return {
        "schema": "m120-budget-attribution-v1",
        "budget_exhausted_demands": exhausted,
        "undetermined_at_the_invocation_ceiling": undetermined_at_the_ceiling,
        "descendant_success_rate": descendant,
        "descendant_success_rate_at_%dx_budget" % arms.BUDGET_MULTIPLIER[arms.FULL_BUDGET_PLUS]:
            at_higher_budget,
        "improvement_from_budget_alone": improves,
        "reading": (
            "not applicable: the verdict is not negative" if verdict != endpoint.NEGATIVE
            else "the negative is not explained by the observation budget: the same machinery does "
                 "no better with four times as many observations"
            if improves is not None and improves < endpoint.MINIMUM_RISK_DIFFERENCE
            else "the negative may be a budget cost rather than a competence cost: the same "
                 "machinery does materially better with four times as many observations, so this "
                 "run does not separate 'the policy does not help' from 'the policy is too "
                 "expensive at this budget'"),
        "this_can_attribute_a_negative_and_never_create_a_positive": True,
    }


def assert_binds_the_committed_reveal(measurements: Mapping[str, Any],
                                      reveal_record: Mapping[str, Any]) -> None:
    """Is this measurement of the bank that was actually sealed, revealed and committed?

    The freeze commitment is no help here: it is derivable from the source and the re-derivable
    plan, spec and nonce, so it is knowable before the generation and identical for every
    measurement taken under this freeze. What authenticates a one-shot artifact is the committed
    record of the reveal that produced it.
    """
    for key in ("reveal_record_sha256", "carrier_bank_sha256"):
        if measurements.get(key) != reveal_record.get(key):
            raise CheckError(
                "the measurement does not match the committed reveal: %s is %r, the committed "
                "reveal record says %r"
                % (key, measurements.get(key), reveal_record.get(key)))


def assert_binds_the_preseal_adequacy(measurements: Mapping[str, Any],
                                      preseal: Mapping[str, Any]) -> dict[str, Any]:
    """The bank measured after the reveal must be the bank the gate cleared before the seal.

    The gate decided, on the whole bank and before anything was sealed, that the frozen plan could
    be run on it. If the post-reveal recomputation disagrees on a single count, something between
    the two changed the bank, and that is a terminal instrument failure rather than a discrepancy
    to reconcile in prose.
    """
    postreveal = measurements.get("adequacy_recomputed_after_the_reveal")
    if not isinstance(postreveal, Mapping):
        raise CheckError("the measurement carries no post-reveal adequacy recomputation")
    matches, differences = adequacy.binding_matches(preseal, postreveal)
    if not matches:
        raise CheckError(
            "the bank measured after the reveal is not the bank the pre-seal gate cleared: %s"
            % ", ".join(differences))
    if preseal.get("adequate") is not True:
        raise CheckError(
            "the pre-seal adequacy gate did not clear this bank, so no scoring may follow it")
    return dict(postreveal)


def check(measurements: Mapping[str, Any], plan: Mapping[str, Any],
          preseal_adequacy: Mapping[str, Any],
          custody: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute the verdict. `plan` has already been re-derived by the caller."""
    _require(measurements.get("schema") == MEASUREMENTS_SCHEMA,
             "not an M120 measurements record")
    _require(measurements.get("measurements_sha256") == sha256_hex(canonical_bytes(
        {k: v for k, v in measurements.items() if k != "measurements_sha256"})),
        "the measurements digest does not reproduce")

    # The plan digest is recomputed from the plan's contents rather than read from its own field,
    # and the plan itself has been rebuilt from code before this function was called.
    plan_commitment = sha256_hex(canonical_bytes(
        {k: v for k, v in plan.items() if k != "plan_commitment_sha256"}))
    _require(plan.get("plan_commitment_sha256") == plan_commitment,
             "the analysis plan commitment does not match its own contents")
    _require(measurements.get("analysis_plan_commitment_sha256") == plan_commitment,
             "the measurements were produced under a different analysis plan")

    # The comparator must be the frozen one, checked against the constant rather than the record.
    _require(measurements.get("fresh_seed") == arms.FRESH_SEED,
             "the comparator seed is not the frozen one")
    _require(measurements.get("fresh_seed_source") == arms.FRESH_SEED_SOURCE,
             "the comparator seed derivation is not the frozen one")
    _require(measurements.get("descendant_arm") == arms.DESCENDANT_ARM
             and measurements.get("comparator_arm") == arms.COMPARATOR_ARM,
             "the primary comparison is not the frozen one")
    _require(list(measurements.get("arm_names") or []) == list(arms.ARM_NAMES),
             "the principal arm set is not the frozen one")
    _require(list(measurements.get("diagnostic_arm_names") or [])
             == list(arms.DIAGNOSTIC_ARM_NAMES),
             "the diagnostic arm set is not the frozen one")
    _require(arms.DESCENDANT_ARM not in arms.DIAGNOSTIC_ARM_NAMES
             and arms.COMPARATOR_ARM not in arms.DIAGNOSTIC_ARM_NAMES,
             "a diagnostic arm is standing in the primary comparison")
    _require(int(measurements.get("session_budget", -1)) == int(plan["session_budget"]),
             "the run used a budget the plan does not specify")

    # The carrier contract the bank was generated under must be the one this checker holds.
    _require(measurements.get("candidate_schema_sha256")
             == sha256_hex(canonical_bytes(contract.candidate_schema())),
             "the bank was generated under a different candidate schema")
    _require(measurements.get("decoder_version") == contract.DECODER_VERSION,
             "the bank was decoded by a different decoder")

    # Provenance is asserted, not passed through.
    provenance = measurements.get("provenance_checks") or {}
    failed = sorted(k for k, v in provenance.items() if v is not True)
    _require(not failed, "producer provenance checks failed: %s" % ", ".join(failed))
    _require((measurements.get("corruption") or {}).get("failed_closed") is True,
             "a corrupted acquired rule was not refused")

    for key in ("freeze_commitment_sha256", "reveal_record_sha256", "carrier_bank_sha256"):
        _require(isinstance(measurements.get(key), str) and len(measurements[key]) == 64,
                 "the measurement does not bind %s" % key)

    entries = measurements.get("entries") or []
    outcomes = recompute_outcomes(entries)
    measures = recompute_measures(entries)

    # Admissibility, from the re-derived plan rather than from whatever the bank happened to yield,
    # and recounted from the evidence rather than read from the runner's summary.
    instrument_failures: list[str] = []
    qualifying = int(measurements["qualifying_carriers"])
    structures = int(measurements["distinct_qualifying_structures"])
    if qualifying < int(plan["minimum_qualifying_carriers"]):
        instrument_failures.append("fewer qualifying carriers than the plan requires")
    if structures < int(plan["minimum_distinct_qualifying_structures"]):
        instrument_failures.append("fewer distinct structures than the plan requires")
    if not entries:
        instrument_failures.append("no paired demand was posed")

    verdict = endpoint.decide(
        outcomes[arms.DESCENDANT_ARM], outcomes[arms.COMPARATOR_ARM],
        measures[arms.DESCENDANT_ARM], measures[arms.COMPARATOR_ARM],
        instrument_valid=not instrument_failures,
        instrument_failures=instrument_failures)

    rates = {name: (sum(1 for x in series if x) / len(series) if series else None)
             for name, series in outcomes.items()}
    # The decomposition sees the principal cells only. A diagnostic arm attributes a negative; it
    # is never an input to what the four cells are said to show.
    decomposed = decomposition.decompose(
        {name: rates[name] for name in arms.ARM_NAMES}, verdict=verdict["verdict"])
    budget = budget_attribution(entries, rates, verdict["verdict"])

    report = {
        "schema": CHECK_SCHEMA,
        "milestone": "M120", "hypothesis": "H65",
        "measurements_sha256": measurements["measurements_sha256"],
        "analysis_plan_commitment_sha256": plan_commitment,
        "analysis_plan_was_rederived_from_code": True,
        "measurements_were_resolved_by_the_checker_not_supplied_by_the_caller": True,
        "measurements_were_reproduced_from_the_committed_carrier_bank": True,
        "preseal_adequacy_gate_version": preseal_adequacy["gate_version"],
        "preseal_adequacy_matched_the_post_reveal_recomputation": True,
        "custody_chain": dict(custody),
        "qualifying_carriers": qualifying,
        "distinct_qualifying_structures": structures,
        "paired_demands": len(outcomes[arms.DESCENDANT_ARM]),
        "primary_comparison": "%s vs %s" % (arms.DESCENDANT_ARM, arms.COMPARATOR_ARM),
        "outcomes_recomputed_from_per_demand_evidence": True,
        "measures_recomputed_from_per_demand_evidence": True,
        "runner_verdict_was_not_read": True,
        "arm_success_rates": rates,
        "recomputed_measures": measures,
        "budget_attribution": budget,
        "primary": verdict,
        "decomposition": decomposed,
        "hypothesis_status": {
            endpoint.POSITIVE: "supported",
            endpoint.NEGATIVE: "not_supported",
            endpoint.INCONCLUSIVE: "inconclusive",
            endpoint.INSTRUMENT_ABORTED: "untested",
        }[verdict["verdict"]],
        "verdict": verdict["verdict"],
        "report_sha256": "",
    }
    report["report_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in report.items() if k != "report_sha256"}))
    return report


def reproduce_measurements(committed: Mapping[str, Any],
                           plan: Mapping[str, Any]) -> dict[str, Any]:
    """Re-run the measurement over the committed bank and require the same bytes.

    The inputs are the committed carrier bank, the re-derived analysis plan and the committed bank
    nonce; the machinery is the frozen arms, evaluator, runtime and host. Nothing else enters, so
    the record is reproducible and a difference is a forgery rather than a discrepancy.
    """
    nonce = measurement.committed_nonce(ROOT, chronology.BANK_NONCE_COMMITMENT)
    carriers = measurement.load_carriers(ROOT / chronology.CARRIER_BANK, nonce)
    recomputed = measurement.measure(carriers, nonce, plan, provenance={
        "freeze_commitment_sha256": committed.get("freeze_commitment_sha256"),
        "reveal_record_sha256": committed.get("reveal_record_sha256"),
        "carrier_bank_sha256": committed.get("carrier_bank_sha256"),
    })
    if canonical_bytes(recomputed) != canonical_bytes(committed):
        differing = sorted(
            key for key in set(recomputed) | set(committed)
            if canonical_bytes({"v": recomputed.get(key)})
            != canonical_bytes({"v": committed.get(key)}))
        raise CheckError(
            "the committed measurement does not reproduce from the committed carrier bank; it was "
            "not produced by this measurement over these carriers. Fields that differ: %s"
            % ", ".join(differing))
    return recomputed


def _self_digest(record: Mapping[str, Any], field: str) -> str:
    return sha256_hex(canonical_bytes({k: v for k, v in record.items() if k != field}))


def assert_custody_chain(carrier_bank: Mapping[str, Any]) -> dict[str, Any]:
    """Walk the custody chain from the sealed ciphertext down to the carrier bank being scored.

    Every artifact between the one completion and the carriers is committed, and each one names
    the previous by digest. Until now the checker read the two ends of that chain and none of the
    middle, so an artifact could be replaced as long as the pair the checker happened to compare
    still agreed. The links, in the order custody actually ran:

        sealed ciphertext on disk  ->  public commitment `ciphertext_sha256`
        pre-seal admission record  ->  public commitment `admission_sha256`
        pre-seal adequacy record   ->  public commitment `preseal_adequacy_sha256`
        public commitment          ->  reveal authorization `commitment_sha256`
        reveal authorization       ->  reveal record `authorization_sha256`
        public commitment          ->  reveal record `ciphertext_sha256`, `generation_response_sha256`
        carrier bank               ->  reveal record `carrier_bank_sha256`
        carrier bank               ->  admission `payload_sha256`, committed *before* the seal

    The last link is the load-bearing one. The admission record digested the enveloped payload
    before anything was sealed, and the reveal writes exactly that payload, so the bytes being
    scored were committed to before the bank was ever encrypted. A forgery that rewrites the
    carrier bank must also rewrite the admission record, the public commitment, the authorization
    and the reveal record, in a repository whose history is public.

    **What this cannot detect** is an operator who rewrites every committed artifact *and* re-seals
    a fabricated completion under a passphrase of their own. No unkeyed checker can: there is no
    secret and no external timestamp in this chain. That boundary is bounded by the public commit
    history, and it is stated rather than papered over.
    """
    commitment = _read_committed(chronology.PUBLIC_BANK_COMMITMENT)
    authorization = _read_committed(chronology.REVEAL_AUTHORIZATION)
    reveal = _read_committed(chronology.REVEAL_RECORD)
    admitted = _read_committed(chronology.ADMISSION)
    gate = _read_committed(chronology.ADEQUACY)
    ciphertext = (ROOT / chronology.SEALED_BANK).read_bytes()
    bank_digest = sha256_hex(canonical_bytes(carrier_bank))

    inner = admitted.get("admission") or {}
    admission.validate_record(inner)

    links = {
        "commitment_digest_reproduces":
            commitment.get("commitment_sha256") == _self_digest(commitment, "commitment_sha256"),
        "authorization_digest_reproduces":
            authorization.get("authorization_sha256")
            == _self_digest(authorization, "authorization_sha256"),
        "reveal_digest_reproduces":
            reveal.get("reveal_record_sha256")
            == _self_digest(reveal, "reveal_record_sha256"),
        "sealed_ciphertext_matches_the_public_commitment":
            sha256_hex(ciphertext) == commitment.get("ciphertext_sha256"),
        "public_commitment_binds_the_preseal_admission":
            commitment.get("admission_sha256") == sha256_hex(canonical_bytes(admitted)),
        "public_commitment_binds_the_preseal_adequacy":
            commitment.get("preseal_adequacy_sha256") == sha256_hex(canonical_bytes(gate)),
        "authorization_binds_the_public_commitment":
            authorization.get("commitment_sha256") == commitment.get("commitment_sha256"),
        "authorization_records_a_cleared_adequacy_gate":
            authorization.get("preseal_adequacy_cleared_this_bank") is True,
        "reveal_binds_the_authorization":
            reveal.get("authorization_sha256") == authorization.get("authorization_sha256"),
        "reveal_binds_the_sealed_ciphertext":
            reveal.get("ciphertext_sha256") == commitment.get("ciphertext_sha256"),
        "reveal_binds_the_sealed_plaintext":
            reveal.get("generation_response_sha256")
            == commitment.get("generation_response_sha256"),
        "reveal_binds_the_carrier_bank": reveal.get("carrier_bank_sha256") == bank_digest,
        "the_preseal_admission_committed_to_these_exact_carrier_bytes":
            inner.get("payload_sha256") == bank_digest,
        "the_preseal_admission_admitted_the_completion": inner.get("admitted") is True,
        "the_preseal_admission_used_this_candidate_schema":
            inner.get("candidate_schema_sha256")
            == sha256_hex(canonical_bytes(contract.candidate_schema())),
        "the_decoder_left_no_carrier_for_the_host_to_refuse":
            inner.get("carriers_refused") == 0,
    }
    broken = sorted(name for name, held in links.items() if held is not True)
    if broken:
        raise CheckError("the custody chain is broken: %s" % ", ".join(broken))
    return {
        "schema": "m120-custody-chain-v1",
        "links": links,
        "every_link_holds": True,
        "a_total_rewrite_of_every_committed_artifact_with_a_re_seal_is_out_of_scope": True,
        "that_boundary_is_bounded_by_the_public_commit_history_not_by_this_checker": True,
    }


def _read_committed(relative: Path) -> Any:
    """Read one of the artifacts the replay stage has just proved is committed at HEAD.

    The path comes from the chronology's constants. There is deliberately no parameter through
    which a caller may name a different one: the file that is authenticated and the file that is
    scored have to be the same file, and the only way to guarantee that is to give the caller no
    say in which file it is.
    """
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        help="where to write the report; the evidence is never taken from argv")
    parser.add_argument("--require-result", action="store_true",
                        help="fail if no committed M120 result exists yet")
    args = parser.parse_args()
    try:
        if not (ROOT / chronology.MEASUREMENTS).is_file():
            if args.require_result:
                raise CheckError("no committed M120 measurement exists")
            print("M120 has no committed measurement yet; nothing to replay.")
            return 0
        # An independent replay is only independent of the run, not of the freeze. This proves the
        # tested system is unchanged *and* that the plan, ledger, admission, adequacy, sealed bank,
        # reveal and measurements are all committed at HEAD byte-identically to disk.
        permission = chronology.assert_frozen_system_unchanged(ROOT, phase="replay")

        measurements = _read_committed(chronology.MEASUREMENTS)
        if measurements.get("freeze_commitment_sha256") != permission["freeze_commitment_sha256"]:
            raise CheckError("the measurement was taken under a different tested-system freeze")

        # The plan is re-derived from code, not trusted because its JSON repeats a known string.
        plan = _read_committed(chronology.ANALYSIS_PLAN)
        bank.validate_analysis_plan(plan, ROOT)

        reveal_record = _read_committed(chronology.REVEAL_RECORD)
        assert_binds_the_committed_reveal(measurements, reveal_record)

        preseal = _read_committed(chronology.ADEQUACY)
        adequacy.validate_record(preseal)
        assert_binds_the_preseal_adequacy(measurements, preseal)

        carrier_bank = _read_committed(chronology.CARRIER_BANK)
        custody = assert_custody_chain(carrier_bank)

        # The measurement is reproduced from the committed bank rather than believed. This is the
        # binding that a self-consistent forgery cannot survive, and the one an earlier draft of
        # this file did not have.
        reproduced = reproduce_measurements(measurements, plan)

        report = check(reproduced, plan, preseal, custody)
    except (CheckError, adequacy.AdequacyError, bank.BankError, chronology.ChronologyError,
            endpoint.EndpointError, measurement.MeasurementError, ValueError) as exc:
        print("REFUSED: %s" % exc)
        return 1
    if args.out:
        args.out.write_bytes(canonical_bytes(report) + b"\n")
    print(json.dumps({"verdict": report["verdict"],
                      "hypothesis_status": report["hypothesis_status"],
                      "p_value": report["primary"]["p_value"],
                      "risk_difference": report["primary"]["risk_difference"],
                      "guards_failed": report["primary"]["no_harm"]["failed"],
                      "statement": report["decomposition"]["strongest_supported_statement"],
                      "report_sha256": report["report_sha256"]}, indent=2, sort_keys=True))
    return 0 if report["verdict"] in (endpoint.POSITIVE, endpoint.NEGATIVE) else 1


if __name__ == "__main__":
    raise SystemExit(main())
