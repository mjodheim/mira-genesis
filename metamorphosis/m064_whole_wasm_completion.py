"""Authoritative M064 whole-WebAssembly completion experiment.

The lineage reconstructed here is continuous:

* M047 version six in CPython;
* M048 version eight in Node ESM, including the post-migration ``max`` tool;
* a discovered, import-free M060-style whole-body WebAssembly migration at
  version nine;
* three independently admitted native rewrites at versions ten to twelve.

Node is only the passive WebAssembly host after the second migration.  Every
semantic pipeline stage and every learned route resides in the emitted module.
"""
from __future__ import annotations

import base64
from functools import lru_cache
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Mapping, Sequence

from metamorphosis.m047_software_body import BASELINE_CASES, SoftwareCase, module_metadata
from metamorphosis.m058_discovered_migration import SCAN_PAIRS, scan_instruction_space
from metamorphosis.m058_instruction_discovery import discovered_from
from metamorphosis.m060_body_compiler import arithmetic_opcodes
from metamorphosis.m060_whole_body_migration import reconstruct_m048_version_eight
from metamorphosis.m061_discovered_structure import run_m061_discovered_structure
import metamorphosis.m064_real_substrate_completion as core
import metamorphosis.m064_wasm_body_compiler as wasm_compiler


M064Error = core.M064Error
M064Manifest = core.M064Manifest
M064Protocol = core.M064Protocol
M064_PROTOCOL = core.M064_PROTOCOL
M064_TASK_BANK = core.M064_TASK_BANK


def _digest(domain: bytes, value: object) -> str:
    return core._digest(domain, value)


def _canonical_json(value: object) -> bytes:
    return core._canonical_json(value)


def _wasm_body_digest(body: Mapping[str, object]) -> str:
    return _digest(b"m064-whole-wasm-body-v1\x00", body)


def _wasm_state_digest(state: Mapping[str, object]) -> str:
    return _digest(b"m064-whole-wasm-state-v1\x00", state)


def _journal_entry_digest(entry: Mapping[str, object]) -> str:
    return _digest(b"m064-whole-wasm-journal-entry-v1\x00", entry)


def _case_dicts(cases: Sequence[SoftwareCase]) -> list[dict[str, object]]:
    return [case.to_dict() for case in cases]


def _isolated_wasm_call(
    mode: str,
    request: Mapping[str, object],
    protocol: M064Protocol,
) -> Mapping[str, object]:
    """Run the passive M060 host with explicit memory, cwd and wall bounds."""
    script = Path(__file__).with_name("m060_wasm_runtime.mjs")
    with tempfile.TemporaryDirectory(prefix="m064-wasm-host-") as directory:
        try:
            completed = subprocess.run(
                ["node", "--max-old-space-size=128", str(script), mode],
                input=_canonical_json(request),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=directory,
                timeout=protocol.node_timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise M064Error(
                f"isolated WebAssembly host unavailable or timed out: {type(exc).__name__}"
            ) from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M064Error("isolated WebAssembly host returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = (
            response.get("fatal_error")
            if isinstance(response, Mapping)
            else completed.stderr.decode("utf-8", "replace")
        )
        raise M064Error(f"isolated WebAssembly host failed: {detail}")
    if response.get("schema") != "m060-node-response-v1" or response.get("mode") != mode:
        raise M064Error("isolated WebAssembly response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M064Error("isolated WebAssembly result is not an object")
    return result


def _module_bytes(body: Mapping[str, object]) -> bytes:
    value = body.get("module_hex")
    if not isinstance(value, str):
        raise M064Error("whole-WebAssembly body lacks module bytes")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise M064Error("whole-WebAssembly body carries malformed hexadecimal") from exc


def _inspect(body: Mapping[str, object], protocol: M064Protocol) -> Mapping[str, object]:
    return _isolated_wasm_call(
        "inspect",
        {"wasm": base64.b64encode(_module_bytes(body)).decode("ascii")},
        protocol,
    )


def _execute(
    body: Mapping[str, object],
    cases: Sequence[SoftwareCase],
    protocol: M064Protocol,
) -> Mapping[str, object]:
    return _isolated_wasm_call(
        "execute",
        {
            "wasm": base64.b64encode(_module_bytes(body)).decode("ascii"),
            "cases": _case_dicts(cases),
        },
        protocol,
    )


def _founder_specs() -> dict[str, dict[str, object]]:
    return {
        "add": {"kind": "primitive", "primitive": "add", "arity": 2, "origin": "m047_founder"},
        "mul": {"kind": "primitive", "primitive": "mul", "arity": 2, "origin": "m047_founder"},
    }


def _complete_specs() -> dict[str, dict[str, object]]:
    return {
        **_founder_specs(),
        "mean": {"kind": "primitive", "primitive": "mean", "arity": 3, "origin": "m047_learned"},
        "max": {"kind": "primitive", "primitive": "max", "arity": 2, "origin": "m048_learned"},
    }


def _complete_aliases() -> dict[str, str]:
    return {
        "add": "add",
        "average": "mean",
        "maximum": "max",
        "mean": "mean",
        "mul": "mul",
        "sum": "add",
    }


def _make_body(
    aliases: Mapping[str, str],
    tool_specs: Mapping[str, Mapping[str, object]],
    opcodes: Mapping[str, int],
    regression_cases: Sequence[Mapping[str, object]],
    protocol: M064Protocol,
) -> dict[str, object]:
    aliases_value = dict(sorted((str(key), str(value)) for key, value in aliases.items()))
    specs_value = json.loads(json.dumps(tool_specs, sort_keys=True))
    opcodes_value = dict(sorted((str(key), int(value)) for key, value in opcodes.items()))
    module = wasm_compiler.compile_dynamic_body(aliases_value, specs_value, opcodes_value)
    if len(module) > protocol.max_candidate_bytes:
        raise M064Error("whole-WebAssembly candidate exceeds the frozen byte bound")
    body = {
        "schema": "m064-whole-wasm-body-v1",
        "aliases": aliases_value,
        "tool_specs": specs_value,
        "discovered_arithmetic_opcodes": opcodes_value,
        "module_hex": module.hex(),
        "module_bytes": len(module),
        "module_sha256": hashlib.sha256(module).hexdigest(),
        "regression_cases": [dict(case) for case in regression_cases],
    }
    _audit_body(body)
    return body


def _audit_body(body: Mapping[str, object]) -> None:
    if body.get("schema") != "m064-whole-wasm-body-v1":
        raise M064Error("invalid whole-WebAssembly body schema")
    aliases = body.get("aliases")
    specs = body.get("tool_specs")
    opcodes = body.get("discovered_arithmetic_opcodes")
    if not isinstance(aliases, Mapping) or not isinstance(specs, Mapping) or not isinstance(opcodes, Mapping):
        raise M064Error("whole-WebAssembly body metadata is malformed")
    rebuilt = wasm_compiler.compile_dynamic_body(aliases, specs, opcodes)
    module = _module_bytes(body)
    if rebuilt != module:
        raise M064Error("whole-WebAssembly bytes do not replay from their owned compiler trace")
    if body.get("module_bytes") != len(module) or body.get("module_sha256") != hashlib.sha256(module).hexdigest():
        raise M064Error("whole-WebAssembly byte identity is inconsistent")
    if module[:8] != b"\x00asm\x01\x00\x00\x00":
        raise M064Error("native body is not a WebAssembly version-one module")


@lru_cache(maxsize=1)
def _discover_substrate() -> dict[str, object]:
    arithmetic_scan = scan_instruction_space()
    observations = {
        item.name: list(item.observations)
        for item in discovered_from(arithmetic_scan)
    }
    opcodes = arithmetic_opcodes(observations, SCAN_PAIRS)
    structural = run_m061_discovered_structure()
    structural_mapping = structural.to_dict()
    if not structural_mapping["discovery_recovered_every_authored_opcode"]:
        raise M064Error("structural discovery did not recover the compiler floor")
    return {
        "arithmetic_space_scanned": int(arithmetic_scan["scanned"]),
        "arithmetic_observations_digest": _digest(
            b"m064-arithmetic-observations-v1\x00", observations
        ),
        "arithmetic_opcodes": dict(sorted(opcodes.items())),
        "structural_manifest_digest": structural.digest(),
        "structural_protocol_digest": structural_mapping["protocol_digest"],
        "structural_opcodes": structural_mapping["resolved_structural_opcodes"],
        "structural_shapes": structural_mapping["scaffolds"],
        "block_structure_authored": structural_mapping["block_structure_authored"],
        "compiler_authored": structural_mapping["compiler_authored"],
    }


def _constructor_registry() -> dict[str, object]:
    expression_registry = core._constructor_registry()
    compiler_source = Path(wasm_compiler.__file__).read_text(encoding="utf-8")
    mapping = {
        "schema": "m064-whole-wasm-construction-registry-v1",
        "expression_registry": expression_registry,
        "whole_body_compiler": {
            "implementation_source": compiler_source,
            "implementation_sha256": hashlib.sha256(compiler_source.encode("utf-8")).hexdigest(),
        },
    }
    return {**mapping, "digest": _digest(b"m064-whole-wasm-registry-v1\x00", mapping)}


def _build_migrated_state(
    protocol: M064Protocol,
) -> tuple[dict[str, object], tuple[SoftwareCase, ...], Mapping[str, object]]:
    lineage = reconstruct_m048_version_eight()
    discovery = _discover_substrate()
    body = _make_body(
        _complete_aliases(),
        _complete_specs(),
        discovery["arithmetic_opcodes"],
        (),
        protocol,
    )
    inspected = _inspect(body, protocol)
    if inspected.get("import_count") != 0:
        raise M064Error("migrated whole body declares an import")
    retained = tuple(lineage.retained)
    execution = _execute(body, retained, protocol)
    if not execution.get("all_passed"):
        raise M064Error("whole-body migration lost an inherited capability")
    source_state_digest = core._support._native_state_digest(lineage.state)
    migration_core = {
        "schema": "m064-whole-wasm-migration-v1",
        "source_runtime": "node-esm",
        "target_runtime": "webassembly",
        "source_version": lineage.version(),
        "source_state_digest": source_state_digest,
        "source_body_digest": core._support._native_body_digest(lineage.body()),
        "target_body_digest": _wasm_body_digest(body),
        "constructor_registry_digest": _constructor_registry()["digest"],
        "discovery_digest": _digest(b"m064-substrate-discovery-v1\x00", discovery),
        "declared_imports": int(inspected["import_count"]),
        "source_native_episode_count": len(
            lineage.state["causal_memory"]["native_episodes"]
        ),
    }
    migration = {
        **migration_core,
        "digest": _digest(b"m064-whole-wasm-migration-v1\x00", migration_core),
    }
    journal_entry = {
        "sequence": 9,
        "event": "migrate_complete_node_body_to_discovered_whole_webassembly",
        "body_digest": _wasm_body_digest(body),
        "migration_digest": migration["digest"],
        "patch_digest": None,
        "validation_digest": None,
        "previous_entry_digest": None,
    }
    state = {
        "schema": "m064-whole-wasm-lineage-state-v1",
        "version": 9,
        "runtime": "webassembly",
        "body": body,
        "patch_registry": [],
        "body_archive": [],
        "accepted_task_ids": list(lineage.state["accepted_task_ids"]),
        "native_journal": [journal_entry],
        "causal_memory": lineage.state["causal_memory"],
        "inherited_node_state_digest": source_state_digest,
        "migration": migration,
        "constructor_registry": _constructor_registry(),
    }
    _audit_state(state)
    return state, retained, {
        "lineage": lineage,
        "discovery": discovery,
        "migration_execution": execution,
        "migration_inspection": inspected,
    }


def _audit_state(state: Mapping[str, object]) -> None:
    if state.get("schema") != "m064-whole-wasm-lineage-state-v1" or state.get("runtime") != "webassembly":
        raise M064Error("invalid whole-WebAssembly lineage state")
    body = state.get("body")
    registry = state.get("patch_registry")
    archive = state.get("body_archive")
    journal = state.get("native_journal")
    if not isinstance(body, Mapping) or not isinstance(registry, list) or not isinstance(archive, list) or not isinstance(journal, list):
        raise M064Error("whole-WebAssembly lineage components are malformed")
    _audit_body(body)
    if state.get("version") != 9 + len(registry) or len(journal) != 1 + len(registry) or len(archive) != len(registry):
        raise M064Error("whole-WebAssembly version, registry, archive and journal diverged")
    if journal[0].get("sequence") != 9 or journal[0].get("event") != "migrate_complete_node_body_to_discovered_whole_webassembly":
        raise M064Error("whole-WebAssembly journal lost its migration origin")
    if journal[0].get("body_digest") != state["migration"]["target_body_digest"]:
        raise M064Error("migration journal no longer binds the initial native body")
    previous = _journal_entry_digest(journal[0])
    for index, (record, entry, archived) in enumerate(zip(registry, journal[1:], archive), start=10):
        if not isinstance(record, Mapping) or not isinstance(entry, Mapping) or not isinstance(archived, Mapping):
            raise M064Error("native transaction record is malformed")
        if record.get("adopted_version") != index or entry.get("sequence") != index:
            raise M064Error("native transaction sequence is discontinuous")
        if entry.get("previous_entry_digest") != previous:
            raise M064Error("native causal journal hash chain is broken")
        if entry.get("patch_digest") != record.get("record_digest"):
            raise M064Error("native journal no longer binds its patch record")
        if entry.get("validation_digest") != record.get("validation_digest"):
            raise M064Error("native journal no longer binds independent validation")
        if archived.get("version") != index - 1 or archived.get("body_digest") != _wasm_body_digest(archived["body"]):
            raise M064Error("native parent archive is not exact")
        if record.get("parent_body_digest") != archived.get("body_digest"):
            raise M064Error("native patch no longer binds its archived parent")
        previous = _journal_entry_digest(entry)
    if registry:
        if registry[-1].get("candidate_body_digest") != _wasm_body_digest(body):
            raise M064Error("latest native patch no longer binds the current body")
        if journal[-1].get("body_digest") != _wasm_body_digest(body):
            raise M064Error("latest native journal no longer binds the current body")
    memory = state.get("causal_memory")
    if not isinstance(memory, Mapping) or not isinstance(memory.get("native_episodes"), list):
        raise M064Error("whole-WebAssembly lineage lost its causal memory")
    expected_episodes = int(state["migration"]["source_native_episode_count"]) + len(registry)
    if len(memory["native_episodes"]) != expected_episodes:
        raise M064Error("whole-WebAssembly causal memory is discontinuous")


def _adopt_candidate(
    state: Mapping[str, object],
    task_id: str,
    selection: Mapping[str, object],
    *,
    forced_fault: bool = False,
) -> tuple[dict[str, object], dict[str, object]]:
    before = json.loads(json.dumps(state))
    before_bytes = _canonical_json(before)
    before_digest = _wasm_state_digest(before)
    candidate = selection.get("selected_candidate")
    if selection.get("action") != "adopt" or not isinstance(candidate, Mapping):
        return before, {"adopted": False, "exact_restoration": False, "reason": "selection_not_admitted"}
    validation_digest = _digest(b"m064-whole-wasm-validation-v1\x00", selection)
    record_core = {
        "task_id": task_id,
        "parent_body_digest": _wasm_body_digest(state["body"]),
        "candidate_body_digest": _wasm_body_digest(candidate["candidate_body"]),
        "expression_digest": candidate["expression_digest"],
        "validation_digest": validation_digest,
        "adopted_version": int(state["version"]) + 1,
    }
    record = {
        **record_core,
        "record_digest": _digest(b"m064-whole-wasm-patch-v1\x00", record_core),
    }
    entry = {
        "sequence": int(state["version"]) + 1,
        "event": "adopt_validated_whole_webassembly_rewrite",
        "body_digest": record["candidate_body_digest"],
        "migration_digest": state["migration"]["digest"],
        "patch_digest": record["record_digest"],
        "validation_digest": validation_digest,
        "previous_entry_digest": _journal_entry_digest(state["native_journal"][-1]),
    }
    staged = json.loads(json.dumps(state))
    staged["version"] = int(state["version"]) + 1
    staged["body_archive"].append(
        {
            "version": state["version"],
            "body": state["body"],
            "body_digest": _wasm_body_digest(state["body"]),
        }
    )
    staged["body"] = candidate["candidate_body"]
    staged["patch_registry"].append(record)
    staged["accepted_task_ids"].append(task_id)
    staged["native_journal"].append(entry)
    memory = dict(staged["causal_memory"])
    episodes = list(memory["native_episodes"])
    episodes.append(
        {
            "task_id": task_id,
            "outcome": "accepted_whole_webassembly_rewrite",
            "expression_digest": candidate["expression_digest"],
            "referenced_tools": list(candidate["referenced_tools"]),
            "validation_digest": validation_digest,
            "reason": selection.get("reason"),
        }
    )
    memory["native_episodes"] = episodes
    staged["causal_memory"] = memory
    try:
        if forced_fault:
            corrupted = json.loads(json.dumps(staged))
            corrupted["native_journal"][-1]["patch_digest"] = "0" * 64
            _audit_state(corrupted)
        else:
            _audit_state(staged)
    except M064Error as exc:
        exact = _canonical_json(before) == before_bytes and _wasm_state_digest(before) == before_digest
        if not exact:
            raise M064Error("forced native fault did not restore the exact state") from exc
        return before, {
            "adopted": False,
            "exact_restoration": True,
            "reason": str(exc),
            "attempted_version": int(state["version"]) + 1,
            "restored_version": state["version"],
            "before_digest": before_digest,
            "after_digest": _wasm_state_digest(before),
        }
    return staged, {
        "adopted": True,
        "exact_restoration": False,
        "committed_version": staged["version"],
        "before_digest": before_digest,
        "after_digest": _wasm_state_digest(staged),
    }


def _append_regressions(
    existing: Sequence[Mapping[str, object]],
    cases: Sequence[SoftwareCase],
) -> list[dict[str, object]]:
    result = [dict(item) for item in existing]
    identities = {str(item["case_id"]) for item in result}
    for case in cases:
        if case.case_id not in identities:
            result.append(case.to_dict())
            identities.add(case.case_id)
    return result


def _materialize_candidate(
    parent: Mapping[str, object],
    task_id: str,
    token: str,
    public_cases: Sequence[SoftwareCase],
    expression: Mapping[str, object],
    protocol: M064Protocol,
) -> dict[str, object]:
    aliases = dict(parent["aliases"])
    aliases[token] = token
    specs = json.loads(json.dumps(parent["tool_specs"]))
    specs[token] = {
        "kind": "constructed",
        "expression": dict(expression),
        "arity": 2,
        "origin": task_id,
        "referenced_tools": list(core._expression_tools(expression)),
    }
    body = _make_body(
        aliases,
        specs,
        parent["discovered_arithmetic_opcodes"],
        _append_regressions(parent.get("regression_cases", []), public_cases),
        protocol,
    )
    expression_digest = _digest(b"m064-whole-wasm-expression-v1\x00", expression)
    return {
        "template_id": f"m064_whole_wasm_{expression_digest[:20]}",
        "expression_digest": expression_digest,
        "expression_ast": dict(expression),
        "referenced_tools": list(core._expression_tools(expression)),
        "changed_native_components": [
            "whole_webassembly_module",
            "alias_table",
            "arity_dispatch",
            "route_admission",
            "tool_dispatch",
        ],
        "added_routes": [token],
        "candidate_body": body,
    }


def _propose_whole_wasm(
    body: Mapping[str, object],
    tool_registry: Mapping[str, Mapping[str, object]],
    task_id: str,
    public_cases: Sequence[SoftwareCase],
    protocol: M064Protocol,
) -> dict[str, object]:
    """Construct whole native bodies from public evidence only."""
    tokens = {case.request.split()[0] for case in public_cases}
    if len(tokens) != 1:
        raise M064Error("public cases do not identify one native task token")
    token = next(iter(tokens))
    incumbent = _execute(body, public_cases, protocol)
    failures = [item for item in incumbent["case_results"] if not item["passed"]]
    diagnosed = bool(failures) and token not in body["aliases"] and all(item["refused"] for item in failures)
    if not diagnosed:
        raise M064Error("native lineage could not diagnose a parser refusal before search")
    expressions = core._enumerate_expression_candidates(
        tool_registry,
        protocol.expression_node_limit,
        protocol.candidate_budget_per_arm_cycle,
    )
    survivors: list[dict[str, object]] = []
    for expression in expressions:
        if all(
            core._round_two(
                core._evaluate_expression(
                    expression,
                    core._parse_binary_case(case, token),
                    tool_registry,
                )
            )
            == case.expected
            for case in public_cases
        ):
            candidate = _materialize_candidate(
                body, task_id, token, public_cases, expression, protocol
            )
            native_public = _execute(candidate["candidate_body"], public_cases, protocol)
            if native_public["all_passed"]:
                survivors.append(candidate)
    return {
        "schema": "m064-whole-wasm-public-proposal-v1",
        "task_id": task_id,
        "token": token,
        "diagnosis": {
            "stage": "native_interpretation",
            "limitation": f"unknown_operator:{token}",
            "predicted_recovery": "extend the owned whole-body compiler trace and native route registry",
            "emitted_before_hidden_validation": True,
        },
        "candidate_budget": protocol.candidate_budget_per_arm_cycle,
        "expressions_constructed": len(expressions),
        "complete_program_space_enumerated": False,
        "public_survivor_count": len(survivors),
        "public_survivors": survivors,
        "constructor_registry_digest": _digest(b"m064-whole-wasm-tool-specs-v1\x00", tool_registry),
    }


def _candidate_audit(
    parent: Mapping[str, object],
    candidate: Mapping[str, object],
    token: str,
    protocol: M064Protocol,
) -> tuple[bool, str, int]:
    body = candidate.get("candidate_body")
    if not isinstance(body, Mapping):
        return False, "candidate_body_missing", -1
    try:
        _audit_body(body)
    except M064Error:
        return False, "compiler_trace_mismatch", -1
    if _wasm_body_digest(body) == _wasm_body_digest(parent):
        return False, "native_body_unchanged", -1
    specs = body.get("tool_specs")
    aliases = body.get("aliases")
    if not isinstance(specs, Mapping) or not isinstance(aliases, Mapping):
        return False, "native_registry_missing", -1
    learned = specs.get(token)
    if not isinstance(learned, Mapping) or aliases.get(token) != token:
        return False, "native_route_missing", -1
    if learned.get("expression") != candidate.get("expression_ast"):
        return False, "transformation_trace_mismatch", -1
    inspected = _inspect(body, protocol)
    imports = int(inspected["import_count"])
    if imports != 0:
        return False, "native_module_declares_imports", imports
    return True, "passed", imports


def _independent_validate_whole_class(
    parent: Mapping[str, object],
    proposal: Mapping[str, object],
    retained_cases: Sequence[SoftwareCase],
    public_cases: Sequence[SoftwareCase],
    hidden_cases: Sequence[SoftwareCase],
    protocol: M064Protocol,
) -> dict[str, object]:
    """Validate every public survivor without owning transactional adoption."""
    candidates = proposal.get("public_survivors")
    if not isinstance(candidates, list) or not candidates:
        return {
            "action": "terminate_insufficient_public_evidence",
            "reason": "no whole-native expression survived public evidence",
            "selected_candidate": None,
            "attempts": [],
            "entire_public_class_validated": True,
        }
    complete = tuple(retained_cases) + tuple(public_cases) + tuple(hidden_cases)
    retained_ids = {case.case_id for case in retained_cases}
    public_ids = {case.case_id for case in public_cases}
    hidden_ids = {case.case_id for case in hidden_cases}
    attempts: list[dict[str, object]] = []
    all_admitted = True
    for candidate in candidates:
        safe, reason, imports = _candidate_audit(parent, candidate, str(proposal["token"]), protocol)
        if safe:
            execution = _execute(candidate["candidate_body"], complete, protocol)
            results = execution["case_results"]
            retained_passed = sum(1 for item in results if item["case_id"] in retained_ids and item["passed"])
            public_passed = sum(1 for item in results if item["case_id"] in public_ids and item["passed"])
            hidden_passed = sum(1 for item in results if item["case_id"] in hidden_ids and item["passed"])
        else:
            retained_passed = public_passed = hidden_passed = 0
        admitted = bool(
            safe
            and retained_passed == len(retained_ids)
            and public_passed == len(public_ids)
            and hidden_passed == len(hidden_ids)
        )
        all_admitted = all_admitted and admitted
        attempts.append(
            {
                "template_id": candidate["template_id"],
                "body_digest": _wasm_body_digest(candidate["candidate_body"]),
                "safety_reason": reason,
                "declared_imports": imports,
                "retained_passed": retained_passed,
                "retained_total": len(retained_ids),
                "public_passed": public_passed,
                "public_total": len(public_ids),
                "hidden_passed": hidden_passed,
                "hidden_total": len(hidden_ids),
                "admitted": admitted,
            }
        )
    if not all_admitted:
        return {
            "action": "terminate_ambiguous_public_equivalence_class",
            "reason": "a public-equivalent native body disagreed with independent evidence",
            "selected_candidate": None,
            "attempts": attempts,
            "entire_public_class_validated": True,
        }
    selected = min(candidates, key=lambda item: _wasm_body_digest(item["candidate_body"]))
    return {
        "action": "adopt",
        "reason": "every public-equivalent whole-native body passed independent admission",
        "selected_candidate": selected,
        "attempts": attempts,
        "entire_public_class_validated": True,
        "public_equivalence_class_size": len(candidates),
        "canonicalisation_after_admission": True,
    }


def _parent_aliases() -> dict[str, str]:
    source = core._source_snapshots()
    snapshot = source["snapshots"][2]
    aliases = module_metadata(snapshot.accepted_body.source("interpretation"))["aliases"]
    return {
        str(token): str(tool)
        for token, tool in dict(aliases).items()
        if str(tool) in _founder_specs()
    }


def _arm(
    name: str,
    body: Mapping[str, object],
    retained: Sequence[SoftwareCase],
    protocol: M064Protocol,
    *,
    state: Mapping[str, object] | None,
    constructor_specs: Mapping[str, Mapping[str, object]],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    inspection = _inspect(body, protocol)
    execution = _execute(body, retained, protocol)
    if inspection["import_count"] != 0 or not execution["all_passed"]:
        raise M064Error(f"arm {name} failed whole-native migration admission")
    return {
        "name": name,
        "body": body,
        "retained": tuple(retained),
        "state": state,
        "constructor_specs": json.loads(json.dumps(constructor_specs)),
        "provenance": dict(provenance),
        "migration_body_digest": _wasm_body_digest(body),
        "migration_retained_passed": int(execution["passed_count"]),
        "migration_imports": int(inspection["import_count"]),
        "cycles": [],
    }


def _build_arms(
    protocol: M064Protocol,
) -> tuple[dict[str, dict[str, object]], Mapping[str, object]]:
    complete_state, complete_retained, evidence = _build_migrated_state(protocol)
    discovery = evidence["discovery"]
    opcodes = discovery["arithmetic_opcodes"]
    source = core._source_snapshots()
    parent_retained = source["retained"][2]
    founder_body = _make_body(
        {"add": "add", "mul": "mul"}, _founder_specs(), opcodes, (), protocol
    )
    parent_body = _make_body(
        _parent_aliases(), _founder_specs(), opcodes, (), protocol
    )
    ablated_state = json.loads(json.dumps(complete_state))
    ablated_specs = _founder_specs()
    arms = {
        "complete_continued_lineage": _arm(
            "complete_continued_lineage",
            complete_state["body"],
            complete_retained,
            protocol,
            state=complete_state,
            constructor_specs=_complete_specs(),
            provenance={"source_version": 6, "node_version": 8, "wasm_version": 9, "continuous": True},
        ),
        "fresh_on_b": _arm(
            "fresh_on_b",
            founder_body,
            BASELINE_CASES,
            protocol,
            state=None,
            constructor_specs=_founder_specs(),
            provenance={"source_version": 0, "native_founder": True, "continuous": False},
        ),
        "unchanged_parent_migrated": _arm(
            "unchanged_parent_migrated",
            parent_body,
            parent_retained,
            protocol,
            state=None,
            constructor_specs=_founder_specs(),
            provenance={"source_version": 2, "pre_mean_parent": True, "continuous": False},
        ),
        "learned_state_ablated": _arm(
            "learned_state_ablated",
            ablated_state["body"],
            complete_retained,
            protocol,
            state=ablated_state,
            constructor_specs=ablated_specs,
            provenance={
                "source_version": 6,
                "node_version": 8,
                "wasm_version": 9,
                "continuous": True,
                "mean_and_max_available_to_execution": True,
                "mean_and_max_withheld_from_constructor": True,
            },
        ),
    }
    if tuple(arms) != protocol.arms:
        raise M064Error("whole-native four-arm order drifted")
    return arms, {**dict(evidence), "source": source}


def _run_bank(
    bank_index: int,
    protocol: M064Protocol,
    *,
    selection_mode: str,
    marker_parent_sha: str | None = None,
) -> M064Manifest:
    if not 0 <= bank_index < len(M064_TASK_BANK):
        raise M064Error("whole-native bank index is outside the commitment")
    arms, evidence = _build_arms(protocol)
    event_trace: list[dict[str, object]] = [
        {
            "sequence": index,
            "event": "arm_migrated",
            "substrate": "whole_webassembly",
            "arm": name,
        }
        for index, name in enumerate(protocol.arms, start=1)
    ]
    event_trace.append(
        {
            "sequence": 5,
            "event": "task_bank_selected",
            "selection_mode": selection_mode,
            "bank_index": bank_index,
        }
    )
    tasks = M064_TASK_BANK[bank_index]
    all_hidden: list[SoftwareCase] = []
    selections: list[Mapping[str, object]] = []
    forced_rollback: dict[str, object] | None = None
    for cycle_number, task in enumerate(tasks, start=1):
        public = task.public_cases()
        hidden = task.hidden_cases()
        all_hidden.extend(hidden)
        for name in protocol.arms:
            arm = arms[name]
            proposal = _propose_whole_wasm(
                arm["body"], arm["constructor_specs"], task.task_id, public, protocol
            )
            selection = _independent_validate_whole_class(
                arm["body"], proposal, arm["retained"], public, hidden, protocol
            )
            adopted = False
            rollback_receipt: Mapping[str, object] | None = None
            if name == "complete_continued_lineage":
                if selection["action"] != "adopt":
                    raise M064Error(f"complete whole-native lineage failed cycle {cycle_number}: {selection['reason']}")
                selected = selection["selected_candidate"]
                references = set(selected["referenced_tools"])
                if not set(task.required_prior_tools).issubset(references):
                    raise M064Error("whole-native later cycle did not execute an earlier learned route")
                state = arm["state"]
                if cycle_number == 1:
                    restored, rollback_receipt = _adopt_candidate(
                        state,
                        f"{task.task_id}_forced_fault",
                        selection,
                        forced_fault=True,
                    )
                    restored_execution = _execute(restored["body"], arm["retained"], protocol)
                    if not rollback_receipt["exact_restoration"] or not restored_execution["all_passed"]:
                        raise M064Error("whole-native forced fault failed code-and-behaviour restoration")
                    forced_rollback = {
                        **dict(rollback_receipt),
                        "restored_behaviour_passed": True,
                        "restored_body_digest": _wasm_body_digest(restored["body"]),
                    }
                    state = restored
                updated, receipt = _adopt_candidate(state, task.task_id, selection)
                if not receipt["adopted"]:
                    raise M064Error("whole-native candidate was admitted but not adopted")
                arm["state"] = updated
                arm["body"] = updated["body"]
                arm["retained"] = tuple(arm["retained"]) + public + hidden
                arm["constructor_specs"] = updated["body"]["tool_specs"]
                selections.append(selection)
                adopted = True
            elif selection["action"] == "adopt":
                raise M064Error(f"control arm {name} unexpectedly solved cycle {cycle_number}")
            hidden_execution = _execute(arm["body"], hidden, protocol)
            arm["cycles"].append(
                {
                    "cycle": cycle_number,
                    "task_id": task.task_id,
                    "diagnosis": proposal["diagnosis"],
                    "proposal_digest": _digest(b"m064-whole-wasm-proposal-v1\x00", proposal),
                    "expressions_constructed": proposal["expressions_constructed"],
                    "public_survivors": proposal["public_survivor_count"],
                    "selection_action": selection["action"],
                    "entire_public_class_validated": selection["entire_public_class_validated"],
                    "validation_attempts": len(selection["attempts"]),
                    "adopted": adopted,
                    "hidden_passes_after_cycle": int(hidden_execution["passed_count"]),
                    "hidden_total": len(hidden),
                    "selected_template": (
                        selection["selected_candidate"]["template_id"]
                        if isinstance(selection.get("selected_candidate"), Mapping)
                        else None
                    ),
                    "selected_referenced_tools": (
                        selection["selected_candidate"]["referenced_tools"]
                        if isinstance(selection.get("selected_candidate"), Mapping)
                        else []
                    ),
                    "selected_module_bytes": (
                        selection["selected_candidate"]["candidate_body"]["module_bytes"]
                        if isinstance(selection.get("selected_candidate"), Mapping)
                        else None
                    ),
                    "rollback_receipt": dict(rollback_receipt) if rollback_receipt else None,
                }
            )
    if forced_rollback is None:
        raise M064Error("whole-native forced rollback did not execute")
    complete = arms["complete_continued_lineage"]
    final_state = complete["state"]
    if final_state["version"] != 12:
        raise M064Error("whole-native lineage did not complete exactly three rewrites")
    retained_execution = _execute(complete["body"], complete["retained"], protocol)
    if not retained_execution["all_passed"]:
        raise M064Error("whole-native final body regressed a retained capability")
    quality: dict[str, dict[str, object]] = {}
    for name, arm in arms.items():
        execution = _execute(arm["body"], all_hidden, protocol)
        passed = int(execution["passed_count"])
        quality[name] = {
            "hidden_passes": passed,
            "hidden_total": len(all_hidden),
            "exact": passed == len(all_hidden),
        }
    strict_advantage = core._strict_quality_advantage(quality, "complete_continued_lineage")
    if not strict_advantage:
        raise M064Error("whole-native complete lineage lacks strict held-out advantage")

    replay, _retained, _evidence = _build_migrated_state(protocol)
    replay_restored, replay_fault = _adopt_candidate(
        replay,
        f"{tasks[0].task_id}_forced_fault",
        selections[0],
        forced_fault=True,
    )
    if not replay_fault["exact_restoration"]:
        raise M064Error("whole-native replay fault did not restore")
    replay = replay_restored
    for task, selection in zip(tasks, selections):
        replay, receipt = _adopt_candidate(replay, task.task_id, selection)
        if not receipt["adopted"]:
            raise M064Error("whole-native deterministic adoption replay failed")
    replay_identical = _wasm_state_digest(replay) == _wasm_state_digest(final_state)
    if not replay_identical:
        raise M064Error("whole-native lineage replay diverged")

    arm_results: dict[str, object] = {}
    for name, arm in arms.items():
        cycles = arm["cycles"]
        validations = sum(int(cycle["validation_attempts"]) for cycle in cycles)
        survivors = sum(int(cycle["public_survivors"]) for cycle in cycles)
        processes = 3 + sum(2 + int(cycle["public_survivors"]) + 2 * int(cycle["validation_attempts"]) for cycle in cycles)
        if name == "complete_continued_lineage":
            processes += 2
        arm_results[name] = {
            "provenance": arm["provenance"],
            "migration_body_digest": arm["migration_body_digest"],
            "migration_retained_passed": arm["migration_retained_passed"],
            "migration_imports": arm["migration_imports"],
            "equal_candidate_budget_per_cycle": protocol.candidate_budget_per_arm_cycle,
            "cycles": cycles,
            "accepted_cycles": sum(1 for cycle in cycles if cycle["adopted"]),
            "final_body_digest": _wasm_body_digest(arm["body"]),
            "final_module_bytes": arm["body"]["module_bytes"],
            "held_out_quality": quality[name],
            "cost_accounting": {
                "expressions_constructed": sum(int(cycle["expressions_constructed"]) for cycle in cycles),
                "public_candidate_processes": survivors,
                "independent_inspection_processes": validations,
                "independent_execution_processes": validations,
                "native_host_process_invocations": processes,
                "accepted_rewrites": sum(1 for cycle in cycles if cycle["adopted"]),
            },
        }
    proposal_parameters = inspect.signature(_propose_whole_wasm).parameters
    validator_source = inspect.getsource(_independent_validate_whole_class)
    mapping = {
        "schema": "m064-whole-webassembly-completion-manifest-v1",
        "protocol_digest": protocol.digest(),
        "task_bank_commitment": protocol.task_bank_commitment,
        "selected_bank_index": bank_index,
        "selection_mode": selection_mode,
        "marker_parent_sha": marker_parent_sha,
        "selected_task_commitments": [task.commitment() for task in tasks],
        "source_runtime": "cpython",
        "source_version": 6,
        "intermediate_runtime": "node-esm",
        "intermediate_version": 8,
        "target_runtime": "webassembly",
        "migration_version": 9,
        "complete_final_version": 12,
        "source_retained_cases_after_node_learning": 32,
        "complete_final_retained_cases": len(complete["retained"]),
        "complete_final_retained_passed": int(retained_execution["passed_count"]),
        "complete_patch_records": len(final_state["patch_registry"]),
        "complete_archived_parent_versions": [
            item["version"] for item in final_state["body_archive"]
        ],
        "source_native_memory_episodes": final_state["migration"][
            "source_native_episode_count"
        ],
        "final_native_memory_episodes": len(
            final_state["causal_memory"]["native_episodes"]
        ),
        "migration_digest": final_state["migration"]["digest"],
        "constructor_registry": _constructor_registry(),
        "substrate_discovery": evidence["discovery"],
        "whole_body_modules_left_in_node": 0,
        "target_declared_imports": int(evidence["migration_inspection"]["import_count"]),
        "event_trace": event_trace,
        "all_arms_migrated_before_task_selection": bool(
            core._migration_precedes_task_selection(event_trace, protocol.arms)
        ),
        "constructor_receives_hidden_cases": any("hidden" in name for name in proposal_parameters),
        "validator_owns_adoption": any(
            token in validator_source for token in ("_adopt_candidate", "patch_registry", "native_journal")
        ),
        "arm_results": arm_results,
        "forced_rollback": forced_rollback,
        "strict_held_out_advantage": strict_advantage,
        "replay_identical": replay_identical,
        "execution_limits": {
            "wall_timeout_seconds": protocol.node_timeout_seconds,
            "node_old_space_megabytes": 128,
            "filesystem": "disposable_host_working_directory",
            "network_and_syscalls": "zero-import_webassembly_module",
            "linear_memory_pages": 1,
            "expression_node_limit": protocol.expression_node_limit,
            "candidate_budget_per_arm_cycle": protocol.candidate_budget_per_arm_cycle,
        },
        "authorship_boundary": {
            "whole_body_compiler_authored": evidence["discovery"]["compiler_authored"],
            "block_structure_authored": evidence["discovery"]["block_structure_authored"],
            "task_families_authored_and_precommitted": True,
            "candidate_expressions_constructed_by_serialised_registry": True,
        },
        "claim_scope": "bounded_cpython_node_whole_webassembly_four_arm_three_cycle_completion_candidate",
        "canonical_workflow_authorised": selection_mode == "marker_parent_commitment",
        "repository_write_authority_granted_to_lineage": False,
    }
    return M064Manifest(mapping)


def run_m064_development(
    bank_index: int = 0,
    protocol: M064Protocol = M064_PROTOCOL,
) -> M064Manifest:
    return _run_bank(bank_index, protocol, selection_mode="development_explicit_index")


def run_m064_canonical(
    marker_parent_sha: str,
    protocol: M064Protocol = M064_PROTOCOL,
) -> M064Manifest:
    return _run_bank(
        core.select_task_bank(marker_parent_sha, protocol),
        protocol,
        selection_mode="marker_parent_commitment",
        marker_parent_sha=marker_parent_sha,
    )


__all__ = [
    "M064_PROTOCOL",
    "M064_TASK_BANK",
    "M064Error",
    "M064Manifest",
    "M064Protocol",
    "run_m064_canonical",
    "run_m064_development",
]
