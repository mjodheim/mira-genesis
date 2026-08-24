"""Bounded M103 state-owned hypothesis-constructor runtime.

The exact M102 U2 predecessor is embedded byte-for-byte.  M103 begins with a
context-invariant linear hypothesis constructor.  A bounded generic feature
substrate can extend that constructor so future acquisition may synthesize a
closed dispatch over observable contexts.  The extension changes constructive
reach; it does not grant filesystem, repository, network, credential,
deployment, evaluator-changing, or permission-changing authority.

Configuration and filesystem effects are executed by evaluator-owned adapters.
The lineage stores opaque content-addressed action descriptors and hypotheses;
it never receives direct host authority.
"""

from __future__ import annotations

import configparser
import copy
import hashlib
import itertools
import json
import re
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Iterable

try:  # The file must also run inside an isolated copied capsule.
    from . import m100_runtime, m101_runtime, m102_runtime
except ImportError:  # pragma: no cover - exercised by isolated capsule tests
    import m100_runtime  # type: ignore[no-redef]
    import m101_runtime  # type: ignore[no-redef]
    import m102_runtime  # type: ignore[no-redef]


STATE_SCHEMA = "m103-lineage-state-v1"
CONSTRUCTOR_SCHEMA = "m103-hypothesis-constructor-v1"
DEMAND_SCHEMA = "m103-acquisition-demand-v1"
ACTION_SCHEMA = "m103-action-v1"
DEFINITION_SCHEMA = "m103-consumer-definition-v1"

S0_ORIGIN = "m103-inherited-s0"
S_PRIME_ORIGIN = "m103-acquired-s-prime"

FEATURE_TOKENS = (
    "ALLOW_EMPTY_LINEAR",
    "EMIT_GUARDED",
    "OBSERVE_CONTEXT",
    "PARTITION_EQUAL",
    "REVERSE_ACTION_ORDER",
    "SORT_ACTION_IDS",
    "SYNTHESIZE_PARTITIONS",
)
MAX_ACQUIRED_FEATURES = 4
SUPPORTED_FAMILIES = {"development_record", "configuration", "filesystem"}

FORBIDDEN_S_PRIME_SUBSTRINGS = (
    "configparser",
    "configuration",
    "filesystem",
    "file",
    "path",
    "section",
    "ini",
    "development_record",
    "solution",
    "target",
)

_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} is not a closed record")
    return value


def _safe_name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
        raise ValueError(f"{label} is invalid")
    return value


def _constructor_id(origin: str, features: list[str]) -> str:
    payload = {"schema": CONSTRUCTOR_SCHEMA, "origin": origin, "features": features}
    prefix = "constructor-s0" if origin == S0_ORIGIN else "constructor-s-prime"
    return f"{prefix}-{digest(payload)[:16]}"


def constructor_definition(origin: str, features: Iterable[str]) -> dict[str, Any]:
    feature_list = sorted(set(features))
    return {
        "schema": CONSTRUCTOR_SCHEMA,
        "constructor_id": _constructor_id(origin, feature_list),
        "origin": origin,
        "features": feature_list,
    }


def inherited_constructor() -> dict[str, Any]:
    return constructor_definition(S0_ORIGIN, [])


def decode_constructor(raw: Any) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw),
        {"schema", "constructor_id", "origin", "features"},
        "M103 constructor",
    )
    if item["schema"] != CONSTRUCTOR_SCHEMA:
        raise ValueError("M103 constructor schema mismatch")
    if item["origin"] not in {S0_ORIGIN, S_PRIME_ORIGIN}:
        raise ValueError("M103 constructor origin is invalid")
    if not isinstance(item["features"], list) or item["features"] != sorted(
        set(item["features"])
    ):
        raise ValueError("M103 constructor features are not a canonical set")
    if not all(feature in FEATURE_TOKENS for feature in item["features"]):
        raise ValueError("M103 constructor has an unknown feature")
    if len(item["features"]) > MAX_ACQUIRED_FEATURES:
        raise ValueError("M103 constructor exceeds the feature bound")
    if item["origin"] == S0_ORIGIN and item != inherited_constructor():
        raise ValueError("M103 inherited constructor changed")
    if item["origin"] == S_PRIME_ORIGIN:
        lowered = canonical_json(item).lower()
        if any(term in lowered for term in FORBIDDEN_S_PRIME_SUBSTRINGS):
            raise ValueError("M103 S-prime contains a forbidden consumer identity")
    if item["constructor_id"] != _constructor_id(item["origin"], item["features"]):
        raise ValueError("M103 constructor content address mismatch")
    return item


def action_definition(descriptor: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(descriptor, dict) or not isinstance(descriptor.get("kind"), str):
        raise ValueError("M103 action descriptor is invalid")
    payload = {"schema": ACTION_SCHEMA, "descriptor": copy.deepcopy(descriptor)}
    return {"action_id": f"action-{digest(payload)[:16]}", **payload}


def decode_action(raw: Any) -> dict[str, Any]:
    item = _closed(copy.deepcopy(raw), {"schema", "action_id", "descriptor"}, "M103 action")
    if item["schema"] != ACTION_SCHEMA or not isinstance(item["descriptor"], dict):
        raise ValueError("M103 action schema/descriptor is invalid")
    expected = action_definition(item["descriptor"])
    if item != expected:
        raise ValueError("M103 action content address mismatch")
    return item


def acquisition_demand(
    demand_id: str,
    family: str,
    actions: Iterable[dict[str, Any]],
    public_cases: Iterable[dict[str, Any]],
    diagnostic_probes: Iterable[dict[str, Any]],
    *,
    max_trace: int,
) -> dict[str, Any]:
    return decode_demand(
        {
            "schema": DEMAND_SCHEMA,
            "demand_id": demand_id,
            "family": family,
            "actions": list(actions),
            "public_cases": list(public_cases),
            "diagnostic_probes": list(diagnostic_probes),
            "max_trace": max_trace,
        }
    )


def _context(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} context is invalid")
    # Canonical JSON is also the admission check for the closed observable value.
    canonical_json(value)
    return copy.deepcopy(value)


def _cases(value: Any, *, expected: bool, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} are missing")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    keys = {"case_id", "context", "initial", "expected"} if expected else {
        "probe_id",
        "context",
        "initial",
    }
    id_key = "case_id" if expected else "probe_id"
    for raw in value:
        item = _closed(copy.deepcopy(raw), keys, f"M103 {label} item")
        identifier = item[id_key]
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError(f"M103 {label} id is invalid")
        seen.add(identifier)
        item["context"] = _context(item["context"], f"M103 {label}")
        canonical_json(item["initial"])
        if expected:
            canonical_json(item["expected"])
        out.append(item)
    return out


def decode_demand(raw: Any) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw),
        {
            "schema",
            "demand_id",
            "family",
            "actions",
            "public_cases",
            "diagnostic_probes",
            "max_trace",
        },
        "M103 demand",
    )
    if item["schema"] != DEMAND_SCHEMA:
        raise ValueError("M103 demand schema mismatch")
    if not isinstance(item["demand_id"], str) or not item["demand_id"]:
        raise ValueError("M103 demand id is invalid")
    if item["family"] not in SUPPORTED_FAMILIES:
        raise ValueError("M103 demand family is invalid")
    if not isinstance(item["actions"], list) or not item["actions"]:
        raise ValueError("M103 demand actions are missing")
    item["actions"] = [decode_action(action) for action in item["actions"]]
    action_ids = [action["action_id"] for action in item["actions"]]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("M103 demand contains duplicate actions")
    item["public_cases"] = _cases(
        item["public_cases"], expected=True, label="public cases"
    )
    item["diagnostic_probes"] = _cases(
        item["diagnostic_probes"], expected=False, label="diagnostic probes"
    )
    widths = {
        len(case["context"])
        for case in [*item["public_cases"], *item["diagnostic_probes"]]
    }
    if len(widths) != 1:
        raise ValueError("M103 demand context width is inconsistent")
    if not isinstance(item["max_trace"], int) or not 1 <= item["max_trace"] <= 3:
        raise ValueError("M103 demand trace bound is invalid")
    return item


def _definition_id(payload: dict[str, Any]) -> str:
    return f"consumer-{digest(payload)[:16]}"


def consumer_definition(
    family: str,
    constructor_id: str,
    actions: list[dict[str, Any]],
    dispatch: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "schema": DEFINITION_SCHEMA,
        "family": family,
        "acquired_by": constructor_id,
        "actions": copy.deepcopy(actions),
        "dispatch": copy.deepcopy(dispatch),
    }
    return {"definition_id": _definition_id(payload), **payload}


def decode_definition(raw: Any) -> dict[str, Any]:
    item = _closed(
        copy.deepcopy(raw),
        {
            "schema",
            "definition_id",
            "family",
            "acquired_by",
            "actions",
            "dispatch",
        },
        "M103 consumer definition",
    )
    if item["schema"] != DEFINITION_SCHEMA or item["family"] not in SUPPORTED_FAMILIES:
        raise ValueError("M103 consumer schema/family mismatch")
    if not isinstance(item["acquired_by"], str) or not item["acquired_by"]:
        raise ValueError("M103 consumer acquisition provenance is invalid")
    if not isinstance(item["actions"], list) or not item["actions"]:
        raise ValueError("M103 consumer actions are missing")
    item["actions"] = [decode_action(action) for action in item["actions"]]
    action_ids = {action["action_id"] for action in item["actions"]}
    if not isinstance(item["dispatch"], list) or not item["dispatch"]:
        raise ValueError("M103 consumer dispatch is missing")
    contexts: set[str] = set()
    dispatch: list[dict[str, Any]] = []
    for raw_row in item["dispatch"]:
        row = _closed(copy.deepcopy(raw_row), {"context", "body"}, "M103 dispatch row")
        row["context"] = _context(row["context"], "M103 dispatch")
        key = canonical_json(row["context"])
        if key in contexts:
            raise ValueError("M103 dispatch contains duplicate context")
        contexts.add(key)
        if not isinstance(row["body"], list) or not 1 <= len(row["body"]) <= 3:
            raise ValueError("M103 dispatch body is invalid")
        if not all(action_id in action_ids for action_id in row["body"]):
            raise ValueError("M103 dispatch references an absent action")
        dispatch.append(row)
    item["dispatch"] = sorted(dispatch, key=lambda row: canonical_json(row["context"]))
    payload = {key: value for key, value in item.items() if key != "definition_id"}
    if item["definition_id"] != _definition_id(payload):
        raise ValueError("M103 consumer content address mismatch")
    return item


def _state(
    m102_bytes: bytes,
    constructor: dict[str, Any],
    definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "schema": STATE_SCHEMA,
        "m102_sha256": sha256_bytes(m102_bytes),
        "m102_ascii": m102_bytes.decode("ascii"),
        "constructor": copy.deepcopy(constructor),
        "definitions": copy.deepcopy(definitions),
    }
    payload["state_digest"] = digest(payload)
    return payload


def create_state(m102_bytes: bytes) -> dict[str, Any]:
    predecessor = m102_runtime.decode_state(m102_bytes)
    if predecessor["policy"]["origin"] != m102_runtime.ACQUIRED_POLICY_ORIGIN:
        raise ValueError("M103 requires acquired M102 policy K")
    if predecessor["c_definition"] is None:
        raise ValueError("M103 requires positive M102 U2 with C")
    return decode_state(_state(m102_bytes, inherited_constructor(), []))


def decode_state(raw: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        value = copy.deepcopy(raw)
    else:
        raw_bytes = raw.encode("ascii") if isinstance(raw, str) else raw
        try:
            value = json.loads(raw_bytes.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"M103 state is not canonical ASCII JSON: {error}") from error
        if canonical_json(value).encode("ascii") != raw_bytes:
            raise ValueError("M103 state bytes are not canonical JSON")
    value = _closed(
        value,
        {
            "schema",
            "m102_sha256",
            "m102_ascii",
            "constructor",
            "definitions",
            "state_digest",
        },
        "M103 state",
    )
    payload = {key: item for key, item in value.items() if key != "state_digest"}
    if value["state_digest"] != digest(payload):
        raise ValueError("M103 state digest mismatch")
    if value["schema"] != STATE_SCHEMA:
        raise ValueError("M103 state schema mismatch")
    if not isinstance(value["m102_ascii"], str) or not isinstance(value["m102_sha256"], str):
        raise ValueError("M103 predecessor binding is invalid")
    m102_bytes = value["m102_ascii"].encode("ascii")
    if sha256_bytes(m102_bytes) != value["m102_sha256"]:
        raise ValueError("M103 embedded M102 bytes changed")
    predecessor = m102_runtime.decode_state(m102_bytes)
    if predecessor["policy"]["origin"] != m102_runtime.ACQUIRED_POLICY_ORIGIN:
        raise ValueError("M103 predecessor lost M102 K")
    if predecessor["c_definition"] is None:
        raise ValueError("M103 predecessor lost M102 C")
    value["constructor"] = decode_constructor(value["constructor"])
    if not isinstance(value["definitions"], list):
        raise ValueError("M103 definitions are invalid")
    value["definitions"] = [decode_definition(item) for item in value["definitions"]]
    definition_ids = [item["definition_id"] for item in value["definitions"]]
    if len(definition_ids) != len(set(definition_ids)):
        raise ValueError("M103 state contains duplicate definitions")
    return value


def encode_state(state: dict[str, Any]) -> bytes:
    return canonical_json(decode_state(state)).encode("ascii")


def _record_action(descriptor: dict[str, Any], value: Any) -> Any:
    if not isinstance(value, dict):
        raise ValueError("development action requires a record")
    out = copy.deepcopy(value)
    kind = descriptor.get("kind")
    if kind == "set_value" and isinstance(descriptor.get("key"), str):
        out[descriptor["key"]] = copy.deepcopy(descriptor.get("value"))
    elif kind == "drop_value" and isinstance(descriptor.get("key"), str):
        out.pop(descriptor["key"], None)
    elif (
        kind == "rename_value"
        and isinstance(descriptor.get("old"), str)
        and isinstance(descriptor.get("new"), str)
    ):
        if descriptor["old"] in out:
            out[descriptor["new"]] = out.pop(descriptor["old"])
    else:
        raise ValueError("unknown development action")
    return out


def _configuration_snapshot(parser: configparser.ConfigParser) -> dict[str, dict[str, str]]:
    return {
        section: {key: parser.get(section, key) for key in sorted(parser[section])}
        for section in sorted(parser.sections())
    }


def _configuration_execute(descriptor: dict[str, Any], parser: configparser.ConfigParser) -> None:
    kind = descriptor.get("kind")
    section = _safe_name(descriptor.get("section"), "configuration section")
    if not parser.has_section(section):
        parser.add_section(section)
    if kind == "set_option":
        option = _safe_name(descriptor.get("option"), "configuration option")
        value = descriptor.get("value")
        if not isinstance(value, str):
            raise ValueError("configuration value is invalid")
        parser.set(section, option, value)
    elif kind == "remove_option":
        option = _safe_name(descriptor.get("option"), "configuration option")
        parser.remove_option(section, option)
    elif kind == "rename_option":
        old = _safe_name(descriptor.get("old"), "configuration old option")
        new = _safe_name(descriptor.get("new"), "configuration new option")
        if parser.has_option(section, old):
            value = parser.get(section, old)
            parser.remove_option(section, old)
            parser.set(section, new, value)
    else:
        raise ValueError("unknown configuration action")


def _configuration_initial(value: Any) -> configparser.ConfigParser:
    if not isinstance(value, str):
        raise ValueError("configuration initial value is not text")
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read_file(StringIO(value))
    return parser


def _safe_relative(value: Any) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("filesystem path is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or any(not _SAFE_NAME.fullmatch(p) for p in path.parts):
        raise ValueError("filesystem path escapes the disposable root")
    return path


def _filesystem_initial(root: Path, value: Any) -> None:
    if not isinstance(value, dict) or not all(
        isinstance(path, str) and isinstance(content, str) for path, content in value.items()
    ):
        raise ValueError("filesystem initial value is invalid")
    for relative, content in value.items():
        target = root / _safe_relative(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="")


def _filesystem_execute(root: Path, descriptor: dict[str, Any]) -> None:
    kind = descriptor.get("kind")
    if kind == "write_text":
        target = root / _safe_relative(descriptor.get("path"))
        content = descriptor.get("content")
        if not isinstance(content, str):
            raise ValueError("filesystem content is invalid")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="")
    elif kind == "append_text":
        target = root / _safe_relative(descriptor.get("path"))
        content = descriptor.get("content")
        if not isinstance(content, str):
            raise ValueError("filesystem content is invalid")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="") as handle:
            handle.write(content)
    elif kind == "delete_path":
        target = root / _safe_relative(descriptor.get("path"))
        if target.exists() and target.is_file():
            target.unlink()
    elif kind == "rename_path":
        old = root / _safe_relative(descriptor.get("old"))
        new = root / _safe_relative(descriptor.get("new"))
        if old.exists() and old.is_file():
            new.parent.mkdir(parents=True, exist_ok=True)
            old.replace(new)
    else:
        raise ValueError("unknown filesystem action")


def _filesystem_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def execute_trace(
    family: str,
    actions: list[dict[str, Any]],
    body: list[str],
    initial: Any,
) -> Any:
    catalog = {action["action_id"]: decode_action(action) for action in actions}
    if any(action_id not in catalog for action_id in body):
        raise ValueError("M103 trace references an unavailable action")
    if family == "development_record":
        value = copy.deepcopy(initial)
        for action_id in body:
            value = _record_action(catalog[action_id]["descriptor"], value)
        return value
    if family == "configuration":
        parser = _configuration_initial(initial)
        for action_id in body:
            _configuration_execute(catalog[action_id]["descriptor"], parser)
        return _configuration_snapshot(parser)
    if family == "filesystem":
        with tempfile.TemporaryDirectory(prefix="m103-fs-") as temp:
            root = Path(temp)
            _filesystem_initial(root, initial)
            for action_id in body:
                _filesystem_execute(root, catalog[action_id]["descriptor"])
            return _filesystem_snapshot(root)
    raise ValueError("M103 trace family is invalid")


def execute_definition(definition: dict[str, Any], context: list[Any], initial: Any) -> Any:
    checked = decode_definition(definition)
    key = canonical_json(_context(context, "M103 execution"))
    rows = {canonical_json(row["context"]): row["body"] for row in checked["dispatch"]}
    if key not in rows:
        raise KeyError("M103 definition has no guarded branch for the context")
    return execute_trace(checked["family"], checked["actions"], rows[key], initial)


def s0_closure(demand: dict[str, Any]) -> dict[str, Any]:
    public = decode_demand(demand)
    action_count = len(public["actions"])
    finite_image = sum(action_count**length for length in range(1, public["max_trace"] + 1))
    witnesses: list[dict[str, Any]] = []
    for left_index, left in enumerate(public["public_cases"]):
        for right in public["public_cases"][left_index + 1 :]:
            if left["initial"] == right["initial"] and left["expected"] != right["expected"]:
                witnesses.append(
                    {
                        "left_case_id": left["case_id"],
                        "right_case_id": right["case_id"],
                        "same_initial_digest": digest(left["initial"]),
                        "left_context_digest": digest(left["context"]),
                        "right_context_digest": digest(right["context"]),
                        "expected_outputs_differ": True,
                    }
                )
    return {
        "schema": "m103-s0-closure-v1",
        "constructor_id": inherited_constructor()["constructor_id"],
        "action_count": action_count,
        "max_trace": public["max_trace"],
        "finite_image_size": finite_image,
        "context_readable": False,
        "actions_receive_context": False,
        "all_hypotheses_context_invariant": True,
        "same_initial_different_expected_witnesses": witnesses,
        "demand_outside_complete_image": bool(witnesses),
        "budget_independent": True,
    }


def _traces(demand: dict[str, Any]) -> list[list[str]]:
    action_ids = [action["action_id"] for action in demand["actions"]]
    return [
        list(body)
        for length in range(1, demand["max_trace"] + 1)
        for body in itertools.product(action_ids, repeat=length)
    ]


def _trace_passes(
    demand: dict[str, Any], body: list[str], cases: list[dict[str, Any]]
) -> bool:
    try:
        return all(
            execute_trace(demand["family"], demand["actions"], body, case["initial"])
            == case["expected"]
            for case in cases
        )
    except Exception:
        return False


def _candidate_signature(definition: dict[str, Any], demand: dict[str, Any]) -> str:
    outcomes: list[dict[str, Any]] = []
    for probe in demand["diagnostic_probes"]:
        try:
            outcome: Any = execute_definition(definition, probe["context"], probe["initial"])
            outcomes.append({"probe_id": probe["probe_id"], "outcome": outcome, "error": None})
        except Exception as error:
            outcomes.append(
                {"probe_id": probe["probe_id"], "outcome": None, "error": type(error).__name__}
            )
    return digest(outcomes)


def construct_hypothesis(constructor: dict[str, Any], demand: dict[str, Any]) -> dict[str, Any]:
    built_by = decode_constructor(constructor)
    public = decode_demand(demand)
    traces = _traces(public)
    if "SORT_ACTION_IDS" in built_by["features"]:
        traces.sort(key=canonical_json)
    if "REVERSE_ACTION_ORDER" in built_by["features"]:
        traces = [list(reversed(body)) for body in traces]
    if "ALLOW_EMPTY_LINEAR" in built_by["features"]:
        traces = [[], *traces]
    assembled = 0
    accepted: list[dict[str, Any]] = []
    features = set(built_by["features"])

    # Each state-owned feature performs one distinct constructor step.  There is no
    # host-side "all features present" switch.  Missing observation or partitioning
    # collapses every case into one group; missing partition synthesis requires one
    # common trace; missing guarded emission assigns the first trace globally.
    observed_keys: dict[str, str] = {}
    actual_contexts: dict[str, list[Any]] = {}
    for case in public["public_cases"]:
        actual_key = canonical_json(case["context"])
        actual_contexts[actual_key] = case["context"]
        observed_keys[case["case_id"]] = (
            actual_key if "OBSERVE_CONTEXT" in features else canonical_json(["opaque-context"])
        )

    groups: dict[str, list[dict[str, Any]]] = {}
    for case in public["public_cases"]:
        group_key = (
            observed_keys[case["case_id"]]
            if "PARTITION_EQUAL" in features
            else canonical_json(["single-partition"])
        )
        groups.setdefault(group_key, []).append(case)

    accepted_by_group: list[tuple[str, list[list[str]]]] = []
    if "SYNTHESIZE_PARTITIONS" in features:
        for key in sorted(groups):
            bodies: list[list[str]] = []
            for body in traces:
                assembled += 1
                if body and _trace_passes(public, body, groups[key]):
                    bodies.append(body)
            accepted_by_group.append((key, bodies))
    else:
        common: list[list[str]] = []
        for body in traces:
            assembled += 1
            if body and _trace_passes(public, body, public["public_cases"]):
                common.append(body)
        accepted_by_group = [(key, list(common)) for key in sorted(groups)]

    if all(bodies for _key, bodies in accepted_by_group):
        for choices in itertools.product(*(bodies for _key, bodies in accepted_by_group)):
            body_by_group = {
                key: list(body)
                for (key, _bodies), body in zip(accepted_by_group, choices, strict=True)
            }
            first_body = list(choices[0])
            dispatch: list[dict[str, Any]] = []
            for actual_key, context in sorted(actual_contexts.items()):
                matching_case = next(
                    case
                    for case in public["public_cases"]
                    if canonical_json(case["context"]) == actual_key
                )
                group_key = (
                    observed_keys[matching_case["case_id"]]
                    if "PARTITION_EQUAL" in features
                    else canonical_json(["single-partition"])
                )
                emitted_body = (
                    body_by_group[group_key]
                    if "EMIT_GUARDED" in features
                    else first_body
                )
                dispatch.append({"context": copy.deepcopy(context), "body": list(emitted_body)})
            definition = consumer_definition(
                public["family"], built_by["constructor_id"], public["actions"], dispatch
            )
            try:
                if all(
                    execute_definition(definition, case["context"], case["initial"])
                    == case["expected"]
                    for case in public["public_cases"]
                ):
                    accepted.append(definition)
            except Exception:
                continue

    by_signature: dict[str, list[dict[str, Any]]] = {}
    for definition in accepted:
        by_signature.setdefault(_candidate_signature(definition, public), []).append(definition)
    if len(by_signature) != 1:
        return {
            "schema": "m103-hypothesis-construction-v1",
            "confirmed": False,
            "reason": "no_candidate" if not by_signature else "ambiguous_public_semantics",
            "assembled": assembled,
            "accepted": len(accepted),
            "semantic_classes": len(by_signature),
            "constructor_id": built_by["constructor_id"],
            "definition": None,
        }
    semantic_signature, members = next(iter(by_signature.items()))
    members.sort(
        key=lambda item: (
            sum(len(row["body"]) for row in item["dispatch"]),
            item["definition_id"],
        )
    )
    return {
        "schema": "m103-hypothesis-construction-v1",
        "confirmed": True,
        "reason": "unique_public_semantic_class",
        "assembled": assembled,
        "accepted": len(accepted),
        "semantic_classes": 1,
        "semantic_signature": semantic_signature,
        "constructor_id": built_by["constructor_id"],
        "definition": members[0],
    }


def acquire_constructor(
    state: dict[str, Any], demand: dict[str, Any], *, register_result: bool
) -> dict[str, Any]:
    checked = decode_state(state)
    if checked["constructor"] != inherited_constructor() or checked["definitions"]:
        raise ValueError("M103 constructor acquisition requires V0")
    public = decode_demand(demand)
    closure = s0_closure(public)
    inherited_attempt = construct_hypothesis(checked["constructor"], public)
    if inherited_attempt["confirmed"] or not closure["demand_outside_complete_image"]:
        return {
            "schema": "m103-constructor-acquisition-v1",
            "confirmed": False,
            "reason": "inherited_constructor_has_no_observed_structural_limitation",
            "assembled": 0,
            "accepted": 0,
            "registered": False,
            "next_state": None,
            "s0_closure": closure,
            "s0_attempt": inherited_attempt,
        }

    assembled = 0
    accepted: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for size in range(1, MAX_ACQUIRED_FEATURES + 1):
        for features in itertools.combinations(FEATURE_TOKENS, size):
            assembled += 1
            candidate = constructor_definition(S_PRIME_ORIGIN, features)
            attempt = construct_hypothesis(candidate, public)
            if attempt["confirmed"]:
                accepted.append((candidate, attempt))
    accepted.sort(key=lambda pair: (len(pair[0]["features"]), pair[0]["constructor_id"]))
    if not accepted:
        return {
            "schema": "m103-constructor-acquisition-v1",
            "confirmed": False,
            "reason": "no_constructor_feature_set_satisfies_development_demand",
            "assembled": assembled,
            "accepted": 0,
            "registered": False,
            "next_state": None,
            "s0_closure": closure,
            "s0_attempt": inherited_attempt,
        }
    shortest_size = len(accepted[0][0]["features"])
    shortest = [pair for pair in accepted if len(pair[0]["features"]) == shortest_size]
    semantic_classes = {
        pair[1].get("semantic_signature") for pair in shortest if pair[1].get("semantic_signature")
    }
    if len(semantic_classes) != 1:
        return {
            "schema": "m103-constructor-acquisition-v1",
            "confirmed": False,
            "reason": "ambiguous_constructor_semantics",
            "assembled": assembled,
            "accepted": len(accepted),
            "shortest_accepted": len(shortest),
            "semantic_classes": len(semantic_classes),
            "registered": False,
            "next_state": None,
            "s0_closure": closure,
            "s0_attempt": inherited_attempt,
        }
    adopted, validation = shortest[0]
    next_state = (
        decode_state(
            _state(
                checked["m102_ascii"].encode("ascii"),
                adopted,
                checked["definitions"],
            )
        )
        if register_result
        else None
    )
    return {
        "schema": "m103-constructor-acquisition-v1",
        "confirmed": True,
        "reason": "unique_shortest_constructor_semantic_class",
        "assembled": assembled,
        "accepted": len(accepted),
        "shortest_accepted": len(shortest),
        "semantic_classes": 1,
        "adopted": adopted,
        "validation": validation,
        "registered": bool(register_result),
        "next_state": next_state,
        "s0_closure": closure,
        "s0_attempt": inherited_attempt,
    }


def acquire_consumer(
    state: dict[str, Any], demand: dict[str, Any], *, register_result: bool
) -> dict[str, Any]:
    checked = decode_state(state)
    public = decode_demand(demand)
    if any(item["family"] == public["family"] for item in checked["definitions"]):
        raise ValueError("M103 consumer family is already registered")
    attempt = construct_hypothesis(checked["constructor"], public)
    next_state = None
    if attempt["confirmed"] and register_result:
        next_state = decode_state(
            _state(
                checked["m102_ascii"].encode("ascii"),
                checked["constructor"],
                [*checked["definitions"], attempt["definition"]],
            )
        )
    return {
        "schema": "m103-consumer-acquisition-v1",
        **attempt,
        "registered": bool(attempt["confirmed"] and register_result),
        "next_state": next_state,
    }


def definition_for_family(state: dict[str, Any], family: str) -> dict[str, Any]:
    checked = decode_state(state)
    matches = [item for item in checked["definitions"] if item["family"] == family]
    if len(matches) != 1:
        raise KeyError(f"M103 state does not contain exactly one {family} definition")
    return copy.deepcopy(matches[0])


def execute_world(state: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    family = world.get("family")
    if family not in SUPPORTED_FAMILIES or not isinstance(world.get("cases"), list):
        raise ValueError("M103 execution world is invalid")
    definition = definition_for_family(checked, str(family))
    outcomes: list[dict[str, Any]] = []
    for raw_case in world["cases"]:
        case = _closed(
            copy.deepcopy(raw_case),
            {"case_id", "context", "initial", "expected"},
            "M103 execution case",
        )
        try:
            actual = execute_definition(definition, case["context"], case["initial"])
            confirmed = actual == case["expected"]
            error_type = None
        except Exception as error:
            actual = None
            confirmed = False
            error_type = type(error).__name__
        outcomes.append(
            {
                "case_id": case["case_id"],
                "confirmed": confirmed,
                "actual": actual,
                "expected": copy.deepcopy(case["expected"]),
                "error_type": error_type,
            }
        )
    passed = sum(bool(item["confirmed"]) for item in outcomes)
    return {
        "schema": "m103-execution-v1",
        "family": family,
        "definition_id": definition["definition_id"],
        "passed": passed,
        "total": len(outcomes),
        "confirmed": passed == len(outcomes),
        "outcomes": outcomes,
    }


def replace_constructor(state: dict[str, Any], constructor: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    return decode_state(
        _state(
            checked["m102_ascii"].encode("ascii"),
            decode_constructor(constructor),
            checked["definitions"],
        )
    )


def ablate_constructor(state: dict[str, Any]) -> dict[str, Any]:
    return replace_constructor(state, inherited_constructor())


def mutate_constructor_without_partition(state: dict[str, Any]) -> dict[str, Any]:
    return mutate_constructor_without_feature(state, "PARTITION_EQUAL")


def mutate_constructor_without_feature(state: dict[str, Any], feature: str) -> dict[str, Any]:
    checked = decode_state(state)
    if (
        checked["constructor"]["origin"] != S_PRIME_ORIGIN
        or feature not in checked["constructor"]["features"]
    ):
        raise ValueError("M103 feature ablation target is not present in S-prime")
    features = [
        item for item in checked["constructor"]["features"] if item != feature
    ]
    return replace_constructor(state, constructor_definition(S_PRIME_ORIGIN, features))


def ablate_family(state: dict[str, Any], family: str) -> dict[str, Any]:
    checked = decode_state(state)
    return decode_state(
        _state(
            checked["m102_ascii"].encode("ascii"),
            checked["constructor"],
            [item for item in checked["definitions"] if item["family"] != family],
        )
    )


def corrupt_state_digest(state: dict[str, Any]) -> bytes:
    value = decode_state(state)
    value["state_digest"] = "0" * 64
    return canonical_json(value).encode("ascii")


def state_summary(state: dict[str, Any]) -> dict[str, Any]:
    checked = decode_state(state)
    predecessor = m102_runtime.decode_state(checked["m102_ascii"].encode("ascii"))
    return {
        "schema": checked["schema"],
        "state_digest": checked["state_digest"],
        "raw_sha256": sha256_bytes(encode_state(checked)),
        "m102_sha256": checked["m102_sha256"],
        "m102_state_digest": predecessor["state_digest"],
        "m102_policy_id": predecessor["policy"]["policy_id"],
        "m102_c_id": predecessor["c_definition"]["definition_id"],
        "constructor_id": checked["constructor"]["constructor_id"],
        "constructor_origin": checked["constructor"]["origin"],
        "constructor_features": list(checked["constructor"]["features"]),
        "definition_ids": [item["definition_id"] for item in checked["definitions"]],
        "definition_families": [item["family"] for item in checked["definitions"]],
    }


def predecessor_conservation(state: dict[str, Any]) -> dict[str, Any]:
    """Report structural liveness indicators for the embedded predecessor.

    Decisive behavioral conservation is performed by the separate execution-only
    M102 capsule over fresh M103 probes.  This local report is deliberately not
    presented as a substitute for that execution or the independent checker.
    """

    checked = decode_state(state)
    m102_state = m102_runtime.decode_state(checked["m102_ascii"].encode("ascii"))
    m101_state = m101_runtime.decode_state(m102_state["m101_ascii"].encode("ascii"))
    m100_state = m100_runtime.decode_state(m101_state["m100_ascii"].encode("ascii"))

    signatures = m100_runtime.operation_signatures(m100_state)
    m100_outputs = [
        signatures[item["operation_id"]][0] * 11
        + signatures[item["operation_id"]][1] * 4
        for item in m100_state["operations"]
    ]
    expected_m100 = [7, 15, 19]

    record_checks: list[bool] = []
    for carrier, slot, expected_kind in (
        ("retention_alpha", "alpha_prepare", "rename_key"),
        ("retention_beta", "beta_finish", "set_default"),
        ("retention_gamma", "gamma_finish", "rename_key"),
    ):
        descriptor = m102_runtime.resolve_descriptor(m102_state, carrier, slot)
        record_checks.append(descriptor.get("kind") == expected_kind)

    policy = m102_state["policy"]
    c_item = m102_state["c_definition"]
    return {
        "schema": "m103-predecessor-conservation-v1",
        "scope": "structural indicators; not decisive behavioral conservation",
        "m102_raw_sha256": checked["m102_sha256"],
        "m102_state_digest": m102_state["state_digest"],
        "m101_state_digest": m101_state["state_digest"],
        "m100_state_digest": m100_state["state_digest"],
        "m100_outputs": m100_outputs,
        "m100_expected": expected_m100,
        "m100_live": m100_outputs == expected_m100,
        "m101_a_live": len(m101_state["definitions"]) == 2
        and m101_state["definitions"][0]["origin"] == m101_runtime.A_ORIGIN,
        "m101_b_live": len(m101_state["definitions"]) == 2
        and m101_state["definitions"][1]["origin"] == m101_runtime.B_ORIGIN,
        "m102_k_live": policy["origin"] == m102_runtime.ACQUIRED_POLICY_ORIGIN
        and set(policy["body"]) >= {"LOAD_CARRIER", "LOAD_SLOT", "PAIR", "RETURN"},
        "m102_c_live": c_item is not None
        and c_item["policy_dependency"] == policy["policy_id"]
        and c_item["definition_dependencies"]
        == [m101_state["definitions"][1]["definition_id"]],
        "record_registry_live": all(record_checks),
    }


def runtime_identity() -> dict[str, Any]:
    import platform
    import sys

    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable": str(Path(sys.executable).resolve()),
        "configparser_module": str(Path(configparser.__file__).resolve()),
        "filesystem_interface": "pathlib+tempfile",
    }
