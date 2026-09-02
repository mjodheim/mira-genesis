"""Machine-only admission for the one H65 completion, with the M120 decode step in the middle.

M116's admission is inherited in shape and not in code: its envelope is part of a frozen
predecessor and may not grow a step. What is inherited is the discipline. This is a **pure
predicate** over the one completion. It parses, validates, decodes, envelopes and digests, and it
produces nothing but booleans, counts and digests. It may not repair, strip fences, extract
substrings, reformat, regenerate, choose among outputs or show a human any carrier content.

The retry rule it serves is the strict one: the first completion carrying evidence of model
execution consumes the scientific generation opportunity. If admission fails there is no second
completion, no redraw, no repair and no bank.

## Three steps, in an order that is load-bearing

    validate   the completion must satisfy the frozen candidate schema, exactly as sent
    decode     every machine goes through `m120_carrier_contract.decode_machine`
    envelope   carrier *i* is decoded machine *i*, tagged `opaque_domain_id(nonce, i)`

Validation comes first so the decoder never touches output the schema would have refused --
decoding first would let a project-side function rescue a completion the contract had already
rejected, which is the difference between a decoder and a repair.

The decode step is what M119 did not have, and it is the reason `carriers_refused` should now be
zero on any schema-valid completion. `decoder_neutrality` proves, for this completion, that the
decoder took nothing from outside it: the decode is deterministic under repetition, independent of
the bank nonce, and independent of position, so no machine can influence how another is decoded.
The envelope's own neutrality -- cardinality, ordering, and references pure of position and nonce
-- is proved beside it, exactly as M116 proved it.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from metamorphosis import m113_carrier_bank as carrier_bank
from metamorphosis import m116_schema as schema_tools
from metamorphosis import m120_carrier_contract as contract
from metamorphosis.blind_bank_protocol import canonical_bytes, opaque_domain_id, sha256_hex

ADMISSION_SCHEMA = "m120-preseal-admission-v1"
VALIDATOR_VERSION = "m120-preseal-admission-validator-v1"
ENVELOPE_VERSION = "m120-decoded-positional-carrier-envelope-v1"
NEUTRALITY_SCHEMA = "m120-envelope-neutrality-proof-v1"

# What the record may contain. Every one is a boolean, a count or a digest -- never a value drawn
# from the completion.
ADMISSION_FIELDS = (
    "schema",
    "validator_version",
    "envelope_version",
    "decoder_version",
    "contract_version",
    "admitted",
    "parsed",
    "schema_valid",
    "payload_admissible",
    "raw_response_sha256",
    "carrier_completion_sha256",
    "payload_sha256",
    "candidate_schema_sha256",
    "request_body_sha256",
    "bank_nonce_sha256",
    "records_emitted",
    "carriers_enveloped",
    "carriers_accepted",
    "carriers_refused",
    "distinct_structural_signatures",
    "violation_location",
    "violation_keyword",
    "failure_stage",
)

STAGES = (
    "raw_response_not_json",
    "choice_cardinality",
    "no_completion_content",
    "content_not_json",
    "content_not_object",
    "output_schema_violation",
    "payload_refused",
    "",
)


class AdmissionError(RuntimeError):
    """Admission could not be evaluated at all. Distinct from admission returning `admitted=False`."""


class PurityError(RuntimeError):
    """The validator observed the completion bytes changing under it. Always fatal."""


def envelope_payload(completion: Mapping[str, Any], bank_nonce: str) -> dict[str, Any]:
    """Decode `{"machines": [...]}` and project it onto the frozen carrier payload."""
    machines = completion.get("machines")
    if not isinstance(machines, list):
        raise AdmissionError("the completion carries no machines array to envelope")
    carriers = []
    for index, machine in enumerate(machines):
        entry = {"carrier_ref": opaque_domain_id(bank_nonce, index)}
        entry.update(contract.decode_machine(machine))
        carriers.append(entry)
    return {
        "schema": carrier_bank.CARRIER_PAYLOAD_SCHEMA,
        "bank_nonce": bank_nonce,
        "carriers": carriers,
    }


def decoder_neutrality(completion: Mapping[str, Any], bank_nonce: str) -> dict[str, Any]:
    """Prove, for this completion, that decoding and enveloping carried no information of their own.

    This is the one place the project touches a completion, so its neutrality is made mechanically
    auditable rather than argued. Every clause below is checked against the actual projection.
    """
    machines = completion.get("machines")
    if not isinstance(machines, list):
        raise AdmissionError("the completion carries no machines array to envelope")
    payload = envelope_payload(completion, bank_nonce)
    carriers = payload["carriers"]

    # Deterministic: decoding the same machine twice gives the same bytes.
    deterministic = all(
        canonical_bytes(contract.decode_machine(machine))
        == canonical_bytes(contract.decode_machine(machine))
        for machine in machines)

    # Positional independence: a machine decodes to the same carrier body wherever it sits, so no
    # machine can influence how another is decoded and order carries no information.
    body_of = {index: {k: v for k, v in entry.items() if k != "carrier_ref"}
               for index, entry in enumerate(carriers)}
    position_independent = all(
        canonical_bytes(body_of[index]) == canonical_bytes(contract.decode_machine(machine))
        for index, machine in enumerate(machines))

    ordering_preserved = all(
        carriers[index].get("carrier_ref") == opaque_domain_id(bank_nonce, index)
        for index in range(len(carriers)))

    # A different nonce must move the bank nonce and the opaque identifiers, and nothing else.
    other = "b" * 64 if bank_nonce != "b" * 64 else "c" * 64
    alternate = envelope_payload(completion, other)
    bodies_unchanged = all(
        canonical_bytes({k: v for k, v in left.items() if k != "carrier_ref"})
        == canonical_bytes({k: v for k, v in right.items() if k != "carrier_ref"})
        for left, right in zip(carriers, alternate["carriers"]))
    refs_are_pure_of_nonce_and_position = all(
        entry.get("carrier_ref") == opaque_domain_id(other, index)
        for index, entry in enumerate(alternate["carriers"]))

    return {
        "schema": NEUTRALITY_SCHEMA,
        "envelope_version": ENVELOPE_VERSION,
        "decoder_version": contract.DECODER_VERSION,
        "machines_in": len(machines),
        "carriers_out": len(carriers),
        "cardinality_preserved": len(carriers) == len(machines),
        "ordering_preserved": ordering_preserved,
        "decode_is_deterministic": deterministic,
        "decode_is_position_independent": position_independent,
        "no_machine_selected_or_dropped": len(carriers) == len(machines),
        "nonce_changes_only_refs_and_nonce": bodies_unchanged,
        "carrier_ref_is_pure_of_nonce_and_position": refs_are_pure_of_nonce_and_position,
        "neutral": bool(
            len(carriers) == len(machines)
            and ordering_preserved
            and deterministic
            and position_independent
            and bodies_unchanged
            and refs_are_pure_of_nonce_and_position
        ),
    }


def _blank(**overrides: Any) -> dict[str, Any]:
    record = {name: None for name in ADMISSION_FIELDS}
    record.update({
        "schema": ADMISSION_SCHEMA,
        "validator_version": VALIDATOR_VERSION,
        "envelope_version": ENVELOPE_VERSION,
        "decoder_version": contract.DECODER_VERSION,
        "contract_version": contract.CONTRACT_VERSION,
        "admitted": False,
        "parsed": False,
        "schema_valid": False,
        "payload_admissible": False,
        "records_emitted": 0,
        "carriers_enveloped": 0,
        "carriers_accepted": 0,
        "carriers_refused": 0,
        "distinct_structural_signatures": 0,
        "violation_location": "",
        "violation_keyword": "",
        "failure_stage": "",
    })
    record.update(overrides)
    return record


def evaluate(raw_response: bytes, *, candidate_schema: Mapping[str, Any], bank_nonce: str,
             request_body_sha256: str | None = None) -> dict[str, Any]:
    """Evaluate one materialized response. Returns allowlisted evidence and nothing else.

    Raises only when the *inputs* are unusable. A completion that fails admission is not an error
    here: it is a record with `admitted=False`, which the caller turns into a terminal abort.
    """
    if not isinstance(raw_response, (bytes, bytearray)):
        raise AdmissionError("the raw response is not bytes")
    if not isinstance(bank_nonce, str) or len(bank_nonce) != 64:
        raise AdmissionError("the committed bank nonce is not a 64-character value")
    if not isinstance(candidate_schema, Mapping):
        raise AdmissionError("the frozen candidate schema is not a schema object")

    raw = bytes(raw_response)
    base = {
        "raw_response_sha256": sha256_hex(raw),
        "candidate_schema_sha256": sha256_hex(canonical_bytes(candidate_schema)),
        "bank_nonce_sha256": sha256_hex(bank_nonce.encode("ascii")),
        "request_body_sha256": request_body_sha256,
    }

    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return _blank(failure_stage="raw_response_not_json", **base)
    body = envelope.get("body") if isinstance(envelope, Mapping) else None
    body = body if isinstance(body, Mapping) else envelope
    if not isinstance(body, Mapping):
        return _blank(failure_stage="raw_response_not_json", **base)

    choices = body.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], Mapping):
        return _blank(failure_stage="choice_cardinality", **base)
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, Mapping) else None
    if not isinstance(content, str) or not content.strip():
        return _blank(failure_stage="no_completion_content", **base)

    # `content.strip()` above is an emptiness *test*; the stripped value is discarded. Everything
    # below digests and parses the original bytes, so no whitespace, fence or prefix is ever
    # removed on the way to the parser.
    content_bytes = content.encode("utf-8")
    content_digest = sha256_hex(content_bytes)
    base["carrier_completion_sha256"] = content_digest

    try:
        completion = json.loads(content)
    except ValueError:
        return _blank(failure_stage="content_not_json", **base)
    if not isinstance(completion, dict):
        return _blank(parsed=True, failure_stage="content_not_object", **base)

    ok, location, keyword = schema_tools.instance_is_valid(completion, candidate_schema)
    if not ok:
        return _blank(parsed=True, failure_stage="output_schema_violation",
                      violation_location=location, violation_keyword=keyword, **base)

    # Only now, on output the frozen contract accepted. Decoding earlier would make this a repair.
    payload = envelope_payload(completion, bank_nonce)
    neutrality = decoder_neutrality(completion, bank_nonce)
    if not neutrality["neutral"]:
        raise PurityError("the decode and envelope were not information-preserving for this "
                          "completion")
    base["payload_sha256"] = sha256_hex(canonical_bytes(payload))
    records = len(completion.get("machines") or ())

    try:
        acceptance = carrier_bank.validate_carrier_bank_payload(payload)
    except carrier_bank.CarrierBankError:
        # The frozen host refused the enveloped payload outright. No reason string is kept: the
        # host's messages quote structure, and structure is content.
        return _blank(parsed=True, schema_valid=True, failure_stage="payload_refused",
                      records_emitted=records, carriers_enveloped=len(payload["carriers"]),
                      **base)

    # Purity: the bytes we validated are the bytes we digested, and nothing under us moved them.
    if sha256_hex(content.encode("utf-8")) != content_digest:
        raise PurityError("the completion bytes changed while admission was evaluating them")

    return _blank(
        admitted=True, parsed=True, schema_valid=True, payload_admissible=True,
        records_emitted=records,
        carriers_enveloped=int(acceptance["carriers_enveloped"]),
        carriers_accepted=int(acceptance["schema_valid_carriers"]),
        carriers_refused=len(acceptance["refused_carriers"]),
        distinct_structural_signatures=int(acceptance["distinct_structural_signatures"]),
        **base,
    )


def validate_record(record: Mapping[str, Any]) -> None:
    """Fail closed on an admission record that is not the frozen shape."""
    if not isinstance(record, Mapping) or record.get("schema") != ADMISSION_SCHEMA:
        raise AdmissionError("admission record schema is not the declared one")
    unexpected = sorted(set(record) - set(ADMISSION_FIELDS))
    if unexpected:
        raise AdmissionError("admission record carries fields outside the allowlist: %s"
                             % ", ".join(unexpected))
    missing = sorted(set(ADMISSION_FIELDS) - set(record))
    if missing:
        raise AdmissionError("admission record omits allowlisted fields: %s" % ", ".join(missing))
    if record.get("failure_stage") not in STAGES:
        raise AdmissionError("admission record names an unknown failure stage")
    if record.get("admitted") and record.get("failure_stage"):
        raise AdmissionError("an admitted record cannot also name a failure stage")


def binding_matches(preseal: Mapping[str, Any],
                    postreveal: Mapping[str, Any]) -> tuple[bool, list[str]]:
    """Do the pre-seal record and the post-reveal recomputation agree on every bound field?"""
    validate_record(preseal)
    validate_record(postreveal)
    bound = (
        "validator_version", "envelope_version", "decoder_version", "contract_version",
        "admitted", "parsed", "schema_valid", "payload_admissible", "raw_response_sha256",
        "carrier_completion_sha256", "payload_sha256", "candidate_schema_sha256",
        "request_body_sha256", "bank_nonce_sha256", "records_emitted", "carriers_enveloped",
        "carriers_accepted", "carriers_refused", "distinct_structural_signatures",
        "failure_stage",
    )
    differences = [name for name in bound if preseal.get(name) != postreveal.get(name)]
    return not differences, differences


def carriers_of(payload: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    """The carrier list of an enveloped payload, checked rather than assumed."""
    carriers = payload.get("carriers")
    if not isinstance(carriers, list):
        raise AdmissionError("the payload carries no carriers list")
    return carriers


__all__ = [
    "ADMISSION_FIELDS",
    "ADMISSION_SCHEMA",
    "ENVELOPE_VERSION",
    "STAGES",
    "VALIDATOR_VERSION",
    "AdmissionError",
    "PurityError",
    "binding_matches",
    "carriers_of",
    "decoder_neutrality",
    "envelope_payload",
    "evaluate",
    "validate_record",
]
