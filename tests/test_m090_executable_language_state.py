"""M090: is the lineage's language actually its state?"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from metamorphosis.m090_language import (
    CONST_VALUES,
    FORBIDDEN_CAPABILITIES,
    LanguageError,
    MetaLanguageState,
    PrimitiveDefinition,
    available_operations,
    execute,
    run_body,
)
from metamorphosis.m090_lineage import (
    ARMS,
    CONDITIONS,
    HISTORICAL_ARMS,
    Probe,
    evaluate,
    observations,
    rollback_proof,
    run_arm,
)
from metamorphosis.m090_migration import (
    PROBE_EXTENSION,
    conservation_report,
    legacy_alphabet,
    migrated_l0,
    with_probe_extension,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "experiments/M090/RESULT.json"

# Probes must exercise every primitive an arm perturbs, or an arm that really did change
# behaviour would look inert. The first draft omitted APPLY_UNARY and the mutation arm read as
# a no-op.
PROBES = (
    Probe("inherited_copy", (("COPY_INPUT", (0, 1)),), (1, 2, 3), "inherited"),
    Probe("inherited_const", (("SET_CONST", (2, 1)),), (1, 2, 3), "inherited"),
    Probe(
        "inherited_composite",
        (("COPY_INPUT", (0, 2)), ("APPLY_UNARY", (0, "double"))), (1, 2, 3),
        "inherited_composite",
    ),
    Probe("acquired_combine", (("COMBINE_INPUTS", (3, 0, 1)),), (4, 5, 6), "acquired"),
)


# ---------------------------------------------------------------------------------------------
# the M089 defect must be impossible
# ---------------------------------------------------------------------------------------------


def test_m089_base_language_split_is_impossible() -> None:
    """The named regression. In M089 this program still ran with the state stripped."""

    language = migrated_l0()
    program = (("COPY_INPUT", (0, 1)),)
    assert execute(program, (1, 2, 3), language) == (2, 0, 0, 0)
    stripped = language.without("COPY_INPUT", "regression")
    with pytest.raises(LanguageError, match="not defined"):
        execute(program, (1, 2, 3), stripped)


def test_the_interpreter_names_no_primitive() -> None:
    """No branch on a primitive identifier anywhere in the executing module's code."""

    tree = ast.parse((ROOT / "metamorphosis/m090_language.py").read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            text = ast.get_docstring(node, clean=False)
            if text:
                docstrings.add(text)
    literals = {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    } - docstrings
    for identifier in with_probe_extension(migrated_l0()).primitive_ids:
        assert identifier not in literals, identifier


def test_the_interpreter_never_imports_the_historical_language() -> None:
    for relative in ("metamorphosis/m090_language.py", "scripts/run_m090_fresh_process.py"):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert not any(item.startswith("metamorphosis.m089") for item in imported), relative
        assert not (imported & {"socket", "urllib", "http", "requests", "openai"})


# ---------------------------------------------------------------------------------------------
# migration conserves the inherited semantics
# ---------------------------------------------------------------------------------------------


def test_migration_conserves_every_inherited_behaviour() -> None:
    report = conservation_report(2)
    assert report["semantics_conserved"] is True
    assert report["mismatch_count"] == 0
    assert report["programs_checked"] >= 1000


def test_each_inherited_operation_is_one_definition() -> None:
    """One entry per operation, not one per literal — the registry shape hides no semantics."""

    language = migrated_l0()
    assert sorted(language.primitive_ids) == ["APPLY_UNARY", "COPY_INPUT", "SET_CONST"]
    assert len({name for name, _ in legacy_alphabet()}) == 3


def test_every_inherited_primitive_carries_a_body_not_a_host_reference() -> None:
    for definition in migrated_l0().primitives:
        assert definition.body
        assert all(isinstance(name, str) for name, _ in definition.body)


# ---------------------------------------------------------------------------------------------
# state is the sole authority
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("primitive_id", ["SET_CONST", "COPY_INPUT", "APPLY_UNARY"])
def test_removing_any_inherited_primitive_disables_it(primitive_id: str) -> None:
    language = migrated_l0()
    assert primitive_id in available_operations(language)
    stripped = language.without(primitive_id, "test")
    assert primitive_id not in available_operations(stripped)
    program = ((primitive_id, tuple(
        {"slot": 0, "const": CONST_VALUES[0], "input": 0, "unary_op": "inc"}[kind]
        for kind in language.definition(primitive_id).parameter_kinds
    )),)
    execute(program, (1, 2, 3), language)
    with pytest.raises(LanguageError):
        execute(program, (1, 2, 3), stripped)


def test_removing_the_acquired_primitive_disables_it_the_same_way() -> None:
    language = with_probe_extension(migrated_l0())
    program = (("COMBINE_INPUTS", (0, 1, 2)),)
    execute(program, (1, 2, 3), language)
    with pytest.raises(LanguageError, match="not defined"):
        execute(program, (1, 2, 3), language.without("COMBINE_INPUTS", "test"))


def test_mutating_a_primitive_body_changes_behaviour() -> None:
    language = migrated_l0()
    program = (("COPY_INPUT", (0, 1)),)
    before = execute(program, (1, 2, 3), language)
    mutated = language.with_mutated(
        "COPY_INPUT", (("PUSH_CONST", 1), ("STORE_SLOT", "$0")), "test",
    )
    assert execute(program, (1, 2, 3), mutated) != before


def test_an_unregistered_primitive_cannot_run() -> None:
    with pytest.raises(LanguageError, match="not defined"):
        execute((("ANYTHING", ()),), (1, 2, 3), migrated_l0())


def test_inherited_and_acquired_live_in_one_registry() -> None:
    language = with_probe_extension(migrated_l0())
    origins = {item.origin for item in language.primitives}
    assert origins == {"inherited", "acquired"}
    assert len(language.primitives) == 4


# ---------------------------------------------------------------------------------------------
# semantics over names
# ---------------------------------------------------------------------------------------------


def test_renaming_a_primitive_preserves_its_semantics_digest() -> None:
    from dataclasses import replace

    original = PROBE_EXTENSION
    renamed = replace(original, primitive_id="ANOTHER_NAME")
    assert renamed.semantics_digest() == original.semantics_digest()
    assert renamed.digest() != original.digest()


def test_changing_a_body_changes_the_semantics_digest_without_renaming() -> None:
    from dataclasses import replace

    tampered = replace(
        PROBE_EXTENSION,
        body=(("PUSH_INPUT", "$1"), ("PUSH_INPUT", "$2"), ("BINOP", "mul"), ("STORE_SLOT", "$0")),
    )
    assert tampered.primitive_id == PROBE_EXTENSION.primitive_id
    assert tampered.semantics_digest() != PROBE_EXTENSION.semantics_digest()


def test_the_language_semantics_digest_ignores_identifiers() -> None:
    from dataclasses import replace

    language = migrated_l0()
    renamed = MetaLanguageState(
        tuple(replace(item, primitive_id=item.primitive_id.lower()) for item in language.primitives),
        language.language_version, language.provenance,
    )
    assert renamed.semantics_digest() == language.semantics_digest()
    assert renamed.digest() != language.digest()


# ---------------------------------------------------------------------------------------------
# authority
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("capability", FORBIDDEN_CAPABILITIES)
def test_a_primitive_cannot_request_new_authority(capability: str) -> None:
    with pytest.raises(LanguageError, match="forbidden capability"):
        PrimitiveDefinition(
            "GREEDY", ("slot",), (("PUSH_CONST", 0), ("STORE_SLOT", "$0")),
            "acquired", (), (capability,),
        )


def test_state_ownership_is_not_arbitrary_code_execution() -> None:
    with pytest.raises(LanguageError, match="unknown micro-operation"):
        run_body((("EXEC_SHELL", "rm -rf /"),), (0,), (0, 0, 0, 0), (1, 2, 3))


def test_argument_kinds_are_enforced() -> None:
    language = migrated_l0()
    with pytest.raises(LanguageError):
        execute((("SET_CONST", (0, 99)),), (1, 2, 3), language)
    with pytest.raises(LanguageError):
        execute((("APPLY_UNARY", (0, "explode")),), (1, 2, 3), language)


# ---------------------------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fault,target", [("removal", "COPY_INPUT"), ("semantic_mutation", "APPLY_UNARY")],
)
def test_rollback_of_the_inherited_language_is_exact_and_behavioural(
    fault: str, target: str,
) -> None:
    probes = (
        Probe("copy", (("COPY_INPUT", (0, 1)),), (1, 2, 3), "inherited"),
        Probe(
            "composite", (("COPY_INPUT", (0, 2)), ("APPLY_UNARY", (0, "double"))),
            (1, 2, 3), "inherited_composite",
        ),
    )
    proof = rollback_proof(migrated_l0(), probes, fault=fault, target=target, label="test")
    assert proof["corruption_detected"] is True
    assert proof["fault_actually_changed_behaviour"] is True
    assert proof["probes_whose_behaviour_changed"]
    assert proof["byte_identical_restore"] is True
    assert proof["behaviour_restored"] is True


def test_rollback_of_the_extended_language_is_exact_and_behavioural() -> None:
    proof = rollback_proof(
        with_probe_extension(migrated_l0()), PROBES,
        fault="removal", target="COMBINE_INPUTS", label="test",
    )
    assert proof["fault_actually_changed_behaviour"] is True
    assert proof["byte_identical_restore"] is True
    assert proof["behaviour_restored"] is True


# ---------------------------------------------------------------------------------------------
# fresh process
# ---------------------------------------------------------------------------------------------


def _fresh(state: MetaLanguageState) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as scratch:
        state_path = Path(scratch) / "state.json"
        probe_path = Path(scratch) / "probes.json"
        state_path.write_text(json.dumps(state.to_dict(), sort_keys=True), encoding="utf-8")
        probe_path.write_text(
            json.dumps([item.to_dict() for item in PROBES], sort_keys=True), encoding="utf-8",
        )
        completed = subprocess.run(
            [
                sys.executable, str(ROOT / "scripts/run_m090_fresh_process.py"),
                "--state", str(state_path), "--probes", str(probe_path),
            ],
            capture_output=True, text=True, check=True,
        )
    return json.loads(completed.stdout)


def test_a_fresh_process_reproduces_the_serialized_language() -> None:
    language = with_probe_extension(migrated_l0())
    payload = _fresh(language)
    assert payload["language_digest"] == language.digest()
    in_process = observations(language, PROBES)
    assert payload["observations"] == in_process
    assert payload["m089_module_imported"] is False
    assert payload["migration_module_imported"] is False


def test_a_fresh_process_cannot_resurrect_a_removed_primitive() -> None:
    language = with_probe_extension(migrated_l0()).without("COPY_INPUT", "test")
    payload = _fresh(language)
    refused = [item for item in payload["observations"] if item["probe_id"] == "inherited_copy"]
    assert refused and refused[0]["refused"] is True


# ---------------------------------------------------------------------------------------------
# arms and verdict
# ---------------------------------------------------------------------------------------------


def test_the_historical_arm_reproduces_the_m089_defect() -> None:
    """The comparison, not a capability: stripping M089's serialized base ops changes nothing."""

    record = run_arm("legacy_host_authority", PROBES)
    assert record["is_historical"] is True
    assert record["behaviour_changed"] is False


@pytest.mark.parametrize("arm", [item for item in ARMS if item not in HISTORICAL_ARMS])
def test_every_state_owned_arm_behaves_as_its_name_says(arm: str) -> None:
    record = run_arm(arm, PROBES)
    expected = arm != "state_owned_meta_language"
    assert record["behaviour_changed"] is expected, arm


def test_every_declared_condition_is_computed_and_can_fail() -> None:
    stub_arm = {"behaviour_changed": False, "language_digest": "", "is_historical": False}
    verdict = evaluate(
        {"semantics_conserved": False, "programs_checked": 0},
        {arm: dict(stub_arm) for arm in ARMS},
        {key: {
            "corruption_detected": False, "fault_actually_changed_behaviour": False,
            "corrupted_state_was_the_restored_state": False, "byte_identical_restore": False,
            "digest_matches": False, "behaviour_restored": False,
        } for key in ("inherited_removal", "inherited_mutation", "acquired_removal")},
        {"intact_matches_in_process": False, "m089_module_imported": True,
         "migration_module_imported": True,
         "removed_primitive_refused_in_fresh_process": False},
        {"executed_outside_state": ["X"], "state_primitives": ["A"],
         "executable_primitives": ["B"], "single_dispatch_path": False,
         "origins_share_registry": False},
        {"findings": ["something"], "legacy_module_reachable_from_execution_path": True},
    )
    assert set(verdict["conditions"]) == set(CONDITIONS)
    assert verdict["verdict"] == "negative"
    assert len(verdict["failed_conditions"]) == len(CONDITIONS), (
        "every condition must be able to fail; a vacuous pass is the M086-A defect"
    )


# ---------------------------------------------------------------------------------------------
# the preserved result
# ---------------------------------------------------------------------------------------------


@pytest.fixture()
def result() -> dict[str, object]:
    if not RESULT_PATH.exists():
        pytest.skip("the M090 result has not been materialized in this tree")
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def test_the_result_records_truthful_attempt_provenance(result: dict[str, object]) -> None:
    """PR #138: re-running a frozen protocol after inspecting a result is another attempt.

    The attempt number is derived from the preserved superseded artifacts, so a positive cannot be
    dressed as a first-run result while earlier runs sit in the directory.
    """

    preserved = sorted(
        path.name for path in (ROOT / "experiments/M090").glob("WITHDRAWN_RESULT_*.json")
    )
    assert preserved, "a re-run must preserve what it superseded"
    assert result["attempt"] == len(preserved) + 1
    assert result["retry_used"] is bool(preserved)
    assert sorted(item["artifact"] for item in result["prior_attempts"]) == preserved
    for item in result["prior_attempts"]:
        superseded = json.loads(
            (ROOT / "experiments/M090" / item["artifact"]).read_text(encoding="utf-8")
        )
        assert superseded["result_digest"] == item["result_digest"]
    assert result["model_calls"] == 0 and result["network_calls"] == 0
    assert result["reattempts_m089"] is False


def test_the_migrated_unary_domain_equals_the_inherited_one(result: dict[str, object]) -> None:
    """PR #138: `identity` had widened the accepted domain while conservation excluded it."""

    from metamorphosis.m089_meta_language import UNARY_FUNCTIONS
    from metamorphosis.m090_language import UNARY_OPERATORS

    assert set(UNARY_OPERATORS) == set(UNARY_FUNCTIONS)
    covered = {arg for name, (_slot, arg) in legacy_alphabet() if name == "APPLY_UNARY"}
    assert covered == set(UNARY_OPERATORS), "the conservation space excludes part of the domain"
    with pytest.raises(LanguageError):
        execute((("APPLY_UNARY", (0, "identity")),), (1, 2, 3), migrated_l0())


def test_the_result_makes_no_claim_about_h35(result: dict[str, object]) -> None:
    claim = json.loads(
        (ROOT / "experiments/M090/REGISTER_CLAIM.json").read_text(encoding="utf-8")
    )
    assert claim["h35_supported"] is False
    assert claim["gate_advanced"] is False
    assert claim["probe_extension_authored"] is True
    assert claim["interpreter_substrate_authored"] is True


def test_the_withdrawn_pre_amendment_result_is_preserved() -> None:
    """Amendment A1 flipped the verdict, so the superseded run stays in the record."""

    withdrawn = json.loads(
        (ROOT / "experiments/M090/WITHDRAWN_RESULT_PRE_AMENDMENT_A1.json").read_text(
            encoding="utf-8"
        )
    )
    assert withdrawn["evaluation"]["verdict"] == "negative"
    assert withdrawn["evaluation"]["failed_conditions"] == [
        "P11_no_host_side_base_operation_authority"
    ]


def test_no_host_authority_finding_survives(result: dict[str, object]) -> None:
    assert result["host_authority_scan"]["findings"] == []
    assert result["host_authority_scan"]["method"] == "ast, docstrings stripped"
