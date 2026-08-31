"""Machine-only pre-seal admission for a future H61 completion.

M115 placed its only carrier-admission check *after* the single authorized reveal. An instrument
failure and a scientific failure therefore consumed the same irreplaceable budget, and the failure
could only be described once the reveal had already been spent on it.

M116 moves that check to the moment after the one completion is received and before it is declared
a bank and sealed. The check is a **pure predicate**: it parses, validates and digests, and it
produces nothing but booleans, counts and digests. It may not repair, normalize, strip fences,
extract substrings, reformat, regenerate, choose among outputs or show a human any carrier content.

The retry rule this serves is the strict one. The first completion carrying evidence of model
execution consumes the scientific generation opportunity. If admission fails there is no second
completion, no redraw, no repair and no bank -- the milestone ends `instrument-aborted`. "First
schema-valid completion wins" is forbidden, because whether a completion parses is a function of
its content, and redrawing on that basis would silently select the carrier population toward
smaller and simpler families.

## The envelope, and why it is not a repair

The frozen generator asks the model for `{"machines": [...]}`. The frozen carrier host expects a
payload carrying `schema`, `bank_nonce` and `carriers`, each carrier tagged with the opaque
identifier derived from the nonce. A blind generator cannot produce those: the nonce is the
project's, and its whole purpose is that the generator never sees it.

Enveloping is therefore a project-side structural projection, not a repair. It is positional,
total and content-independent: carrier *i* is machine *i*, tagged with `opaque_domain_id(nonce, i)`.
It adds no information from the completion, drops none, reorders nothing, and cannot rescue a
malformed machine -- the host still refuses it, and a refused body is counted, not corrected. The
nonce must be committed before generation so that no degree of freedom survives into this step.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from metamorphosis import m113_carrier_bank as carrier_bank
from metamorphosis import m116_schema as schema_tools
from metamorphosis.blind_bank_protocol import canonical_bytes, opaque_domain_id, sha256_hex

ADMISSION_SCHEMA = "m116-preseal-admission-v1"
VALIDATOR_VERSION = "m116-preseal-admission-validator-v1"
ENVELOPE_VERSION = "m116-positional-carrier-envelope-v1"

# What the record may contain. Every one is a boolean, a count, a digest or a schema location --
# never a value drawn from the completion.
ADMISSION_FIELDS = (
    "schema",
    "validator_version",
    "envelope_version",
    "admitted",
    "parsed",
    "schema_valid",
    "payload_admissible",
    "raw_response_sha256",
    "carrier_completion_sha256",
    "payload_sha256",
    "output_schema_sha256",
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
    """Project `{"machines": [...]}` onto the frozen carrier payload. Positional and total."""
    machines = completion.get("machines")
    if not isinstance(machines, list):
        raise AdmissionError("the completion carries no machines array to envelope")
    carriers = []
    for index, machine in enumerate(machines):
        if not isinstance(machine, Mapping):
            # Not a repair: a non-object entry is enveloped as-is and refused downstream by the
            # host, so that it is counted rather than silently dropped.
            carriers.append({"carrier_ref": opaque_domain_id(bank_nonce, index)})
            continue
        entry = {"carrier_ref": opaque_domain_id(bank_nonce, index)}
        entry.update({key: value for key, value in machine.items() if key != "carrier_ref"})
        carriers.append(entry)
    return {
        "schema": carrier_bank.CARRIER_PAYLOAD_SCHEMA,
        "bank_nonce": bank_nonce,
        "carriers": carriers,
    }


def _blank(**overrides: Any) -> dict[str, Any]:
    record = {name: None for name in ADMISSION_FIELDS}
    record.update({
        "schema": ADMISSION_SCHEMA,
        "validator_version": VALIDATOR_VERSION,
        "envelope_version": ENVELOPE_VERSION,
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


def evaluate(
    raw_response: bytes,
    *,
    output_schema: Mapping[str, Any],
    bank_nonce: str,
    request_body_sha256: str | None = None,
) -> dict[str, Any]:
    """Evaluate one materialized response. Returns allowlisted evidence and nothing else.

    Raises only when the *inputs* are unusable. A completion that fails admission is not an error
    here: it is a record with `admitted=False`, which the caller turns into a terminal abort.
    """
    if not isinstance(raw_response, (bytes, bytearray)):
        raise AdmissionError("the raw response is not bytes")
    if not isinstance(bank_nonce, str) or len(bank_nonce) != 64:
        raise AdmissionError("the committed bank nonce is not a 64-character value")
    if not isinstance(output_schema, Mapping):
        raise AdmissionError("the frozen output schema is not a schema object")

    raw = bytes(raw_response)
    base = {
        "raw_response_sha256": sha256_hex(raw),
        "output_schema_sha256": sha256_hex(canonical_bytes(output_schema)),
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

    content_bytes = content.encode("utf-8")
    content_digest = sha256_hex(content_bytes)
    base["carrier_completion_sha256"] = content_digest

    try:
        completion = json.loads(content)
    except ValueError:
        return _blank(failure_stage="content_not_json", **base)
    if not isinstance(completion, dict):
        return _blank(parsed=True, failure_stage="content_not_object", **base)

    ok, location, keyword = schema_tools.instance_is_valid(completion, output_schema)
    if not ok:
        return _blank(parsed=True, failure_stage="output_schema_violation",
                      violation_location=location, violation_keyword=keyword, **base)

    payload = envelope_payload(completion, bank_nonce)
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


def binding_matches(preseal: Mapping[str, Any], postreveal: Mapping[str, Any]) -> tuple[bool, list[str]]:
    """Do the pre-seal record and the post-reveal recomputation agree on every bound field?"""
    validate_record(preseal)
    validate_record(postreveal)
    bound = (
        "validator_version", "envelope_version", "admitted", "parsed", "schema_valid",
        "payload_admissible", "raw_response_sha256", "carrier_completion_sha256",
        "payload_sha256", "output_schema_sha256", "request_body_sha256", "bank_nonce_sha256",
        "records_emitted", "carriers_enveloped", "carriers_accepted", "carriers_refused",
        "distinct_structural_signatures", "failure_stage",
    )
    return (
        [name for name in bound if preseal.get(name) != postreveal.get(name)] == [],
        [name for name in bound if preseal.get(name) != postreveal.get(name)],
    )


__all__ = [
    "ADMISSION_FIELDS",
    "ADMISSION_SCHEMA",
    "ENVELOPE_VERSION",
    "STAGES",
    "VALIDATOR_VERSION",
    "AdmissionError",
    "PurityError",
    "binding_matches",
    "envelope_payload",
    "evaluate",
    "validate_record",
]
