"""Versioned, content-addressed, persistent lineage state with registries that grow by evidence.

M107–M111 each declared their own state schema and rebuilt the ones below. The program therefore had
ancestry in its source files and none in its execution. This module supplies the missing thing: one
`LineageState` that persists across process death and carries the lineage's registries with it.

Two of those registries are the authored ceilings the audit located.

`m111_runtime.decode_state` refuses any state whose component registry or feature vocabulary differs
from the host's module constant. That check is not a mistake and is **not deleted here** — it is what
made the state honest. The problem is that under it a component class can only ever arrive by a human
editing a tuple, which is how the registry went from two entries to three to four without the lineage
ever naming one.

So the registries here grow, but **only against a certificate**, and the certificate has to show that
the *previous* representation could not do the job:

* to add a **component**, the lineage must show it probed every component it already had, that none
  of them resolved the demand, and that the new one does. Adding a name is not enough; the old
  registry must be demonstrably insufficient.
* to extend the **diagnostic vocabulary**, the lineage must exhibit two demands its existing features
  map to the *same* row while their limiting components differ, and show the new feature separates
  them. An extension that merely adds a feature is refused.

The state digest covers the grown registries, so nothing enters by growing a list quietly.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from genesis.trust_root import (
    PROVENANCE_CLASSES,
    canonical_bytes,
    digest_of,
    provenance as trust_provenance,
)

STATE_SCHEMA = "genesis-lineage-state-v1"
COMPONENT_CERTIFICATE_SCHEMA = "genesis-registry-extension-certificate-v1"
VOCABULARY_CERTIFICATE_SCHEMA = "genesis-vocabulary-extension-certificate-v1"

COMPONENT_ORIGINS = ("seed", "acquired")


class StateError(ValueError):
    """Raised when a state, or a growth of one, claims more than its certificate supports."""


def _clean_name(value: object, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateError("%s must be a non-empty name" % what)
    return value


def _with_producer(record: Mapping[str, Any], what: str) -> dict[str, Any]:
    """History has to say who made it.

    `create_state` claimed every entry declared its origin and provenance while only components
    enforced it, so a tool or an acquisition could be dropped into the record with no producer at
    all and inherit the surrounding claim by implication.
    """
    if not isinstance(record, Mapping):
        raise StateError("a %s entry is not a record" % what)
    producer = record.get("provenance")
    if not isinstance(producer, Mapping) or producer.get("class") not in PROVENANCE_CLASSES:
        raise StateError("%s %r carries no recognised provenance" % (what, record.get("name")))
    return dict(record)


def _clean_names(values: Iterable[Any], what: str) -> list[str]:
    names = [_clean_name(value, what) for value in values]
    if len(set(names)) != len(names):
        raise StateError("%s contains a duplicate" % what)
    return names


# ---------------------------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------------------------
def _rebuild_component_certificate(certificate: Mapping[str, Any], name: str) -> None:
    """Re-run the builder's rules over a stored certificate, so a forged one cannot be loaded."""
    try:
        rebuilt = component_extension_certificate(
            prior_registry=list(certificate.get("prior_registry") or []),
            new_component=name,
            demand_digest=certificate.get("demand_digest", ""),
            probe_records=list(certificate.get("probe_records") or []),
            resolves_with_new_component=certificate.get("resolves_with_new_component"),
            resolving_composition=certificate.get("resolving_composition"),
        )
    except StateError as problem:
        raise StateError(
            "component %r carries a certificate whose own evidence does not establish it: %s"
            % (name, problem)
        ) from problem
    if rebuilt["certificate_digest"] != certificate.get("certificate_digest"):
        raise StateError(
            "component %r carries a certificate that does not reconstruct from its own evidence"
            % name
        )


def _rebuild_vocabulary_certificate(certificate: Mapping[str, Any], name: str) -> None:
    """The same for a diagnostic feature: rebuild it rather than trusting its digest."""
    try:
        rebuilt = vocabulary_extension_certificate(
            prior_vocabulary=list(certificate.get("prior_vocabulary") or []),
            new_feature=name,
            demand_digests=list(certificate.get("demand_digests") or []),
            shared_prior_row=list(certificate.get("shared_prior_row") or []),
            limiting_components=list(certificate.get("limiting_components") or []),
            separated_rows=list(certificate.get("separated_rows") or []),
        )
    except StateError as problem:
        raise StateError(
            "feature %r carries a certificate whose own evidence does not establish it: %s"
            % (name, problem)
        ) from problem
    if rebuilt["certificate_digest"] != certificate.get("certificate_digest"):
        raise StateError(
            "feature %r carries a certificate that does not reconstruct from its own evidence" % name
        )


def component_extension_certificate(
    *,
    prior_registry: Sequence[str],
    new_component: str,
    demand_digest: str,
    probe_records: Sequence[Mapping[str, Any]],
    resolves_with_new_component: bool,
    resolving_composition: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the evidence required to add a component class to the registry.

    Two things this used to accept and no longer does.

    A probe that returned `resolved=False` was treated as exhaustion. It is not: a search can end
    because the budget ran out or the instrument failed, and neither says the component cannot
    resolve the demand. Each probe record must now say its search actually completed.

    And `resolves_with_new_component=True` was a caller's word for the half of the argument that
    does the work — the demonstration that something *outside* the held registry reaches the demand.
    The measured resolving composition has to travel with the certificate, so what licensed the
    acquisition survives the conversion into it.
    """
    prior = _clean_names(prior_registry, "prior registry entry")
    name = _clean_name(new_component, "new component")
    if name in prior:
        raise StateError("component %r is already in the registry" % name)
    probed = {}
    for record in probe_records:
        if not isinstance(record, Mapping):
            raise StateError("a probe record is not a record")
        component = _clean_name(record.get("component"), "probed component")
        if component not in prior:
            raise StateError("probe record names %r, which is not in the prior registry" % component)
        if component in probed:
            raise StateError("component %r is probed twice" % component)
        if record.get("resolved") is not False:
            raise StateError(
                "component %r resolved the demand, so the prior registry was sufficient" % component
            )
        if record.get("search_exhausted") is not True:
            raise StateError(
                "the search over %r did not exhaust: a probe that stopped for budget or an "
                "instrument failure is not evidence the component cannot resolve the demand"
                % component
            )
        if record.get("budget_exhausted") or record.get("instrument_failure"):
            raise StateError(
                "the search over %r ended without exhausting its options" % component
            )
        probed[component] = dict(record)
    missing = sorted(set(prior) - set(probed))
    if missing:
        raise StateError("prior components were never probed: %s" % ", ".join(missing))
    if resolves_with_new_component is not True:
        raise StateError("the proposed component does not resolve the demand either")
    if not isinstance(resolving_composition, Mapping) or not resolving_composition.get(
        "composition_digest"
    ):
        raise StateError(
            "no resolving composition was supplied: a caller boolean is not evidence that anything "
            "outside the held registry reaches the demand, and without that half exhaustion is only "
            "a failed search"
        )
    certificate = {
        "schema": COMPONENT_CERTIFICATE_SCHEMA,
        "prior_registry": prior,
        "new_component": name,
        "demand_digest": demand_digest,
        "probe_records": [probed[component] for component in prior],
        "prior_registry_exhausted": True,
        "resolves_with_new_component": True,
        "resolving_composition": dict(resolving_composition),
    }
    certificate["certificate_digest"] = digest_of(certificate)
    return certificate


def vocabulary_extension_certificate(
    *,
    prior_vocabulary: Sequence[str],
    new_feature: str,
    demand_digests: Sequence[str],
    shared_prior_row: Sequence[bool],
    limiting_components: Sequence[str],
    separated_rows: Sequence[Sequence[bool]],
) -> dict[str, Any]:
    """Build the evidence required to extend the diagnostic vocabulary.

    The lineage must exhibit two demands its current features cannot tell apart while their limiting
    components genuinely differ. Without that pair, a new feature is decoration.
    """
    prior = _clean_names(prior_vocabulary, "prior feature")
    feature = _clean_name(new_feature, "new feature")
    if feature in prior:
        raise StateError("feature %r is already in the vocabulary" % feature)
    digests = [str(value) for value in demand_digests]
    if len(digests) != 2 or digests[0] == digests[1]:
        raise StateError("a vocabulary extension needs exactly two distinct demands")
    row = [bool(value) for value in shared_prior_row]
    if len(row) != len(prior):
        raise StateError("the shared row does not match the prior vocabulary width")
    limits = [_clean_name(value, "limiting component") for value in limiting_components]
    if len(limits) != 2 or limits[0] == limits[1]:
        raise StateError(
            "the two demands must have different limiting components, or they are not confusable"
        )
    separated = [[bool(value) for value in candidate] for candidate in separated_rows]
    if len(separated) != 2:
        raise StateError("the extension must report a row for each demand")
    if any(len(candidate) != len(prior) + 1 for candidate in separated):
        raise StateError("separated rows do not match the extended vocabulary width")
    if [value[: len(prior)] for value in separated] != [row, row]:
        raise StateError("the extended rows disagree with the shared prior row")
    if separated[0] == separated[1]:
        raise StateError("the new feature does not separate the two demands")
    certificate = {
        "schema": VOCABULARY_CERTIFICATE_SCHEMA,
        "prior_vocabulary": prior,
        "new_feature": feature,
        "demand_digests": digests,
        "shared_prior_row": row,
        "limiting_components": limits,
        "separated_rows": separated,
        "prior_vocabulary_could_not_separate": True,
    }
    certificate["certificate_digest"] = digest_of(certificate)
    return certificate


# ---------------------------------------------------------------------------------------------
# Lineage state
# ---------------------------------------------------------------------------------------------
def create_state(
    *,
    body_digest: str,
    components: Sequence[Mapping[str, Any]],
    vocabulary: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]] = (),
    acquisitions: Sequence[Mapping[str, Any]] = (),
    observations: Sequence[Mapping[str, Any]] = (),
    generation: int = 0,
) -> dict[str, Any]:
    """Assemble a lineage state. Every entry declares its origin and its provenance."""
    entries = []
    for entry in components:
        name = _clean_name(entry.get("name"), "component name")
        origin = entry.get("origin")
        if origin not in COMPONENT_ORIGINS:
            raise StateError("component %r has an unrecognised origin" % name)
        certificate = entry.get("certificate")
        if origin == "acquired":
            if not isinstance(certificate, Mapping):
                raise StateError("acquired component %r carries no certificate" % name)
            if certificate.get("schema") != COMPONENT_CERTIFICATE_SCHEMA:
                raise StateError("component %r carries the wrong certificate kind" % name)
            if certificate.get("new_component") != name:
                raise StateError("component %r is certified under another name" % name)
            # A certificate that reproduces its own digest says only that nobody edited it since it
            # was written. Rebuilding it from its own records is what checks that the evidence
            # inside it establishes what it claims.
            _rebuild_component_certificate(certificate, name)
        elif certificate is not None:
            raise StateError("seed component %r may not carry an extension certificate" % name)
        provenance_record = entry.get("provenance")
        if not isinstance(provenance_record, Mapping) or provenance_record.get(
            "class"
        ) not in PROVENANCE_CLASSES:
            raise StateError("component %r carries no recognised provenance" % name)
        entries.append(
            {
                "name": name,
                "origin": origin,
                "certificate": dict(certificate) if certificate else None,
                "provenance": dict(provenance_record),
            }
        )
    if len({entry["name"] for entry in entries}) != len(entries):
        raise StateError("the component registry contains a duplicate")

    features = []
    for entry in vocabulary:
        name = _clean_name(entry.get("name"), "feature name")
        origin = entry.get("origin")
        if origin not in COMPONENT_ORIGINS:
            raise StateError("feature %r has an unrecognised origin" % name)
        certificate = entry.get("certificate")
        if origin == "acquired":
            if not isinstance(certificate, Mapping):
                raise StateError("acquired feature %r carries no certificate" % name)
            if certificate.get("schema") != VOCABULARY_CERTIFICATE_SCHEMA:
                raise StateError("feature %r carries the wrong certificate kind" % name)
            if certificate.get("new_feature") != name:
                raise StateError("feature %r is certified under another name" % name)
            _rebuild_vocabulary_certificate(certificate, name)
        elif certificate is not None:
            raise StateError("seed feature %r may not carry an extension certificate" % name)
        feature_provenance = entry.get("provenance")
        if origin == "acquired" and not (
            isinstance(feature_provenance, Mapping)
            and feature_provenance.get("class") in PROVENANCE_CLASSES
        ):
            raise StateError("feature %r carries no recognised provenance" % name)
        features.append(
            {
                "name": name,
                "origin": origin,
                "certificate": dict(certificate) if certificate else None,
                "provenance": dict(feature_provenance) if feature_provenance else None,
            }
        )
    if len({entry["name"] for entry in features}) != len(features):
        raise StateError("the diagnostic vocabulary contains a duplicate")

    payload = {
        "schema": STATE_SCHEMA,
        "generation": int(generation),
        "body_digest": str(body_digest),
        "components": entries,
        "vocabulary": features,
        "tools": [_with_producer(tool, "tool") for tool in tools],
        "acquisitions": [_with_producer(item, "acquisition") for item in acquisitions],
        "observations": [dict(item) for item in observations],
    }
    return {**payload, "state_digest": digest_of(payload)}


def decode_state(raw: bytes | str | Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild a state from its parts and require the digest to reproduce.

    A forged state is not caught by a rule someone remembered to write; it is a value that does not
    reconstruct. The registries are *not* compared against a module constant — they belong to the
    lineage — but every acquired entry must still carry a certificate the rebuild re-validates.
    """
    if isinstance(raw, (bytes, bytearray)):
        value = json.loads(bytes(raw).decode("utf-8"))
    elif isinstance(raw, str):
        value = json.loads(raw)
    else:
        value = json.loads(canonical_bytes(raw).decode("utf-8"))
    if not isinstance(value, dict) or value.get("schema") != STATE_SCHEMA:
        raise StateError("lineage state payload is invalid")
    rebuilt = create_state(
        body_digest=value.get("body_digest", ""),
        components=value.get("components") or [],
        vocabulary=value.get("vocabulary") or [],
        tools=value.get("tools") or [],
        acquisitions=value.get("acquisitions") or [],
        observations=value.get("observations") or [],
        generation=int(value.get("generation", 0)),
    )
    if rebuilt["state_digest"] != value.get("state_digest"):
        raise StateError("lineage state digest does not reproduce")
    return rebuilt


def encode_state(state: Mapping[str, Any]) -> bytes:
    return canonical_bytes(decode_state(state))


def component_names(state: Mapping[str, Any]) -> list[str]:
    return [entry["name"] for entry in state["components"]]


def vocabulary_names(state: Mapping[str, Any]) -> list[str]:
    return [entry["name"] for entry in state["vocabulary"]]


def extend_components(
    state: Mapping[str, Any],
    *,
    certificate: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Add a component class the lineage named, against evidence its prior registry was insufficient."""
    current = decode_state(state)
    prior = component_names(current)
    if list(certificate.get("prior_registry") or []) != prior:
        raise StateError("the certificate was issued against a different registry")
    if digest_of({k: v for k, v in certificate.items() if k != "certificate_digest"}) != certificate.get(
        "certificate_digest"
    ):
        raise StateError("the component certificate does not reproduce")
    return create_state(
        body_digest=current["body_digest"],
        components=current["components"]
        + [
            {
                "name": certificate["new_component"],
                "origin": "acquired",
                "certificate": dict(certificate),
                "provenance": dict(provenance),
            }
        ],
        vocabulary=current["vocabulary"],
        tools=current["tools"],
        acquisitions=current["acquisitions"],
        observations=current["observations"],
        generation=current["generation"],
    )


def extend_vocabulary(
    state: Mapping[str, Any],
    *,
    certificate: Mapping[str, Any],
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Add a diagnostic feature, against evidence the prior vocabulary could not separate two demands."""
    current = decode_state(state)
    prior = vocabulary_names(current)
    if list(certificate.get("prior_vocabulary") or []) != prior:
        raise StateError("the certificate was issued against a different vocabulary")
    if digest_of({k: v for k, v in certificate.items() if k != "certificate_digest"}) != certificate.get(
        "certificate_digest"
    ):
        raise StateError("the vocabulary certificate does not reproduce")
    return create_state(
        body_digest=current["body_digest"],
        components=current["components"],
        vocabulary=current["vocabulary"]
        + [
            {
                "name": certificate["new_feature"],
                "origin": "acquired",
                "provenance": dict(provenance)
                if provenance
                else trust_provenance("lineage_owned", produced_by="lineage vocabulary extension"),
                "certificate": dict(certificate),
            }
        ],
        tools=current["tools"],
        acquisitions=current["acquisitions"],
        observations=current["observations"],
        generation=current["generation"],
    )


# ---------------------------------------------------------------------------------------------
# Persistence across process death
# ---------------------------------------------------------------------------------------------
def save_state(state: Mapping[str, Any], path: Path) -> str:
    """Persist a state. None of M107–M111 wrote to disk; the runtime owns this generically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = encode_state(state)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_bytes(payload + b"\n")
    temporary.replace(path)  # atomic, so a death mid-write cannot leave a torn state
    return hashlib.sha256(payload).hexdigest()


def load_state(path: Path) -> dict[str, Any]:
    """Restore a state after process death, re-validating it rather than trusting the file."""
    return decode_state(Path(path).read_bytes())
