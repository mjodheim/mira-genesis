"""The M094 lineage: does each step do the thing its name claims?

These tests are about the pipeline, not about the diagnosis or the search, which
`test_m094_diagnosis.py` and `test_m094_composition.py` already cover. What matters here is
that adoption really writes, restart really forgets, the fault really strikes the live file,
the validator really executes, and the controls really can fail — because the audit found a
runner whose docstring claimed all five and whose code did none of them.

Every fixture is a synthetic two-file repository. The real `mira_core` is not touched: a test
that adopts into the working tree would leave the repository modified when it failed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from metamorphosis import m094_lineage as lineage  # noqa: E402

COMPONENT = "pkg/values.py"

#: A value object whose callers destructure it by hand, so the diagnosis has demand to find.
VALUES_SOURCE = '''"""A component with a value object and no renderer."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Record:
    record_id: str
    label: str
'''

#: Two callers writing the same three-key mapping out by hand.
CALLER_SOURCE = '''from pkg.values import Record


def first(record: Record) -> dict:
    return {"record_id": record.record_id, "label": record.label}


def second(record: Record) -> dict:
    return {"record_id": record.record_id, "label": record.label}
'''


def _write_repo(root: Path, values: str = VALUES_SOURCE) -> None:
    (root / "pkg").mkdir(parents=True, exist_ok=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "values.py").write_text(values, encoding="utf-8")
    (root / "callers.py").write_text(CALLER_SOURCE, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _write_repo(tmp_path)
    return tmp_path


@pytest.fixture
def developed(repo: Path):
    development = lineage.develop(repo, (COMPONENT,))
    assert development.modified_source is not None, "the fixture produced no candidate"
    return repo, development


# ── the declared arms and conditions match the frozen protocol ────────


def test_arms_and_conditions_match_the_frozen_protocol() -> None:
    """A mirrored list that drifts is worse than no list."""

    protocol = json.loads(
        (REPO_ROOT / "experiments" / "M094" / "PROTOCOL.json").read_text(encoding="utf-8")
    )
    assert set(lineage.ARMS) == set(protocol["arms"])
    assert len(lineage.ARMS) == len(protocol["arms"]), "a duplicated arm would hide here"
    assert set(lineage.CEILING_ARMS) == set(protocol["ceiling_arms"])
    assert set(lineage.CONDITIONS) == set(protocol["conditions"])


def test_the_lineage_never_reads_the_experiments_directory(developed) -> None:
    """The isolation claim, as behaviour rather than as a string scan.

    `test_m094_qualification_pool.py` checks that no module mentions the pool. This checks
    that a full development pass opens nothing under `experiments/`, which is the property
    the mention-scan is a proxy for.
    """

    repo, _ = developed
    opened: list[str] = []
    real_open = Path.open

    def watched(self, *args, **kwargs):  # noqa: ANN001, ANN202
        opened.append(str(self))
        return real_open(self, *args, **kwargs)

    Path.open = watched  # type: ignore[method-assign]
    try:
        lineage.develop(repo, (COMPONENT,))
    finally:
        Path.open = real_open  # type: ignore[method-assign]

    offending = [item for item in opened if "experiments" in item.replace("\\", "/")]
    assert offending == [], f"the lineage read {offending}"


# ── behavioural cases ────────────────────────────────────────────────


def test_cases_are_values_and_carry_no_expected_answer(repo: Path) -> None:
    cases = lineage.behavioural_cases(repo, COMPONENT, "Record", count=4)
    assert len(cases) == 4
    assert all(set(case) == {"record_id", "label"} for case in cases)
    # No case may mention the method that will satisfy it, or the mapping it should produce.
    assert "as_mapping" not in json.dumps(cases)


def test_cases_are_deterministic_in_the_seed(repo: Path) -> None:
    first = lineage.behavioural_cases(repo, COMPONENT, "Record", seed="a")
    again = lineage.behavioural_cases(repo, COMPONENT, "Record", seed="a")
    other = lineage.behavioural_cases(repo, COMPONENT, "Record", seed="b")
    assert first == again
    assert first != other, "two seeds produced the same cases"


# ── the sandbox executes ──────────────────────────────────────────────


def test_the_original_does_not_supply_the_capability_and_the_candidate_does(developed) -> None:
    repo, development = developed
    cases = lineage.behavioural_cases(repo, COMPONENT, "Record")
    original = (repo / COMPONENT).read_text(encoding="utf-8")

    before = lineage.sandbox_component(
        repo, COMPONENT, original, "Record", development.requirement, cases, variant="original",
    )
    after = lineage.sandbox_component(
        repo, COMPONENT, development.modified_source, "Record", development.requirement,
        cases, variant="candidate",
    )

    assert before.imported and before.runnable
    assert not before.supplies_the_capability
    assert after.supplies_the_capability
    # The method was found by executing it, not by being named.
    assert after.satisfying_methods


def test_a_broken_candidate_is_refused_rather_than_crashing(developed) -> None:
    """The rollback proof produces unparsable source, so this path must not raise."""

    repo, development = developed
    cases = lineage.behavioural_cases(repo, COMPONENT, "Record")
    truncated = development.modified_source[: len(development.modified_source) // 2]
    outcome = lineage.sandbox_component(
        repo, COMPONENT, truncated, "Record", development.requirement, cases, variant="damaged",
    )
    assert not outcome.supplies_the_capability
    assert not outcome.imported or outcome.cases_satisfied == 0


def test_an_unconstructible_case_is_not_a_refutation(repo: Path) -> None:
    """Runnability is separate from agreement.

    Seven of nine frozen qualification entries carry hidden cases that raise on
    construction. An instrument that scored those as failures would turn its own defect
    into evidence against the hypothesis.
    """

    development = lineage.develop(repo, (COMPONENT,))
    impossible = ({"record_id": "x", "label": "y", "unexpected_argument": 1},)
    outcome = lineage.sandbox_component(
        repo, COMPONENT, development.modified_source, "Record",
        development.requirement, impossible, variant="unrunnable",
    )
    assert outcome.imported
    assert outcome.cases_total == 1
    assert outcome.cases_constructible == 0
    assert not outcome.runnable
    assert not outcome.supplies_the_capability


def test_comparison_measures_nothing_when_no_case_constructs(developed) -> None:
    repo, development = developed
    impossible = ({"nope": 1},)
    before = lineage.sandbox_component(
        repo, COMPONENT, (repo / COMPONENT).read_text(encoding="utf-8"), "Record",
        development.requirement, impossible, variant="original",
    )
    after = lineage.sandbox_component(
        repo, COMPONENT, development.modified_source, "Record",
        development.requirement, impossible, variant="candidate",
    )
    comparison = lineage.compare(before, after)
    assert comparison["null_rejected"] is False
    assert "measures nothing" in str(comparison["reason"])


# ── independent validation ────────────────────────────────────────────


def test_the_validator_accepts_a_working_candidate(developed) -> None:
    repo, development = developed
    validation = lineage.validate_independently(
        repo, COMPONENT, development.modified_source, "Record", development.requirement,
    )
    assert validation.accepted
    assert validation.receipt
    assert validation.cases_satisfied == validation.cases_total


def test_the_validator_refuses_a_method_that_only_looks_right(developed) -> None:
    """A plausible name with a wrong body must be refused.

    This is the falsifier for P8. The validator is told the class and the requirement and
    not the method name, so a candidate cannot pass by being called `as_mapping`.
    """

    repo, development = developed
    liar = (repo / COMPONENT).read_text(encoding="utf-8") + (
        "\n"
        "    def as_mapping(self):\n"
        '        return {"record_id": "wrong", "label": "wrong"}\n'
    )
    # It must parse and import, or this would be refused for the wrong reason.
    import ast as _ast

    _ast.parse(liar)
    validation = lineage.validate_independently(
        repo, COMPONENT, liar, "Record", development.requirement,
    )
    assert not validation.accepted
    assert "does_not_parse" not in " ".join(validation.reasons)
    assert "candidate_does_not_import" not in validation.reasons
    assert "no_public_method_reproduces_the_requirement_when_executed" in validation.reasons


def test_the_validator_draws_its_own_cases(developed) -> None:
    """It must not reuse the development cases, or a candidate could be tuned to them."""

    repo, _ = developed
    development_cases = lineage.behavioural_cases(repo, COMPONENT, "Record")
    validator_cases = lineage.behavioural_cases(
        repo, COMPONENT, "Record", seed="m094-validator-cases-v1",
    )
    assert development_cases != validator_cases


# ── adoption, persistence, restart ────────────────────────────────────


def _adopt(repo: Path, development) -> tuple[lineage.TransformationStore, str]:
    cases = lineage.behavioural_cases(repo, COMPONENT, "Record")
    original = (repo / COMPONENT).read_text(encoding="utf-8")
    before = lineage.sandbox_component(
        repo, COMPONENT, original, "Record", development.requirement, cases, variant="original",
    )
    after = lineage.sandbox_component(
        repo, COMPONENT, development.modified_source, "Record", development.requirement,
        cases, variant="candidate",
    )
    comparison = lineage.compare(before, after)
    validation = lineage.validate_independently(
        repo, COMPONENT, development.modified_source, "Record", development.requirement,
    )
    store = lineage.TransformationStore.init_or_load(
        repo, repo, lineage._source_digest(original),
    )
    assert store.adopt(
        COMPONENT, original, development.modified_source,
        development.mechanism_digest, validation, comparison,
    )
    return store, original


def test_adoption_writes_the_live_component(developed) -> None:
    repo, development = developed
    store, original = _adopt(repo, development)
    assert store.version == 1
    assert (repo / COMPONENT).read_text(encoding="utf-8") != original


def test_adoption_is_refused_without_validation(developed) -> None:
    repo, development = developed
    original = (repo / COMPONENT).read_text(encoding="utf-8")
    store = lineage.TransformationStore.init_or_load(
        repo, repo, lineage._source_digest(original),
    )
    refused = lineage.Validation("v", False, ("refused",), 4, 0, 0, "receipt")
    assert not store.adopt(
        COMPONENT, original, development.modified_source, "d", refused,
        {"null_rejected": True},
    )
    assert store.version == 0
    assert (repo / COMPONENT).read_text(encoding="utf-8") == original, "the tree was touched"


def test_adoption_is_refused_when_the_comparison_stands(developed) -> None:
    repo, development = developed
    original = (repo / COMPONENT).read_text(encoding="utf-8")
    store = lineage.TransformationStore.init_or_load(
        repo, repo, lineage._source_digest(original),
    )
    accepted = lineage.Validation("v", True, (), 4, 4, 1, "receipt")
    assert not store.adopt(
        COMPONENT, original, development.modified_source, "d", accepted,
        {"null_rejected": False},
    )
    assert store.version == 0


def test_state_survives_a_process_death(developed) -> None:
    """The restart boundary: a new interpreter, given a directory and nothing else."""

    repo, development = developed
    store, _ = _adopt(repo, development)
    resumed = lineage.fresh_process_check(repo, repo)

    assert resumed["resumed_from_state"] is True
    assert resumed["version"] == 1
    assert resumed["mechanism_digest"] == development.mechanism_digest
    assert resumed["component"] == COMPONENT
    assert resumed["live_matches_recorded_digest"] is True
    assert resumed["state_digest"] == store.state.digest()


def test_a_fresh_process_resumes_nothing_when_no_state_was_written(repo: Path) -> None:
    resumed = lineage.fresh_process_check(repo, repo)
    assert resumed["resumed_from_state"] is False
    assert resumed.get("state_file_existed") is False


# ── rollback ──────────────────────────────────────────────────────────


def test_the_fault_strikes_the_live_file_and_restoration_is_exact(developed) -> None:
    repo, development = developed
    store, original = _adopt(repo, development)
    cases = lineage.behavioural_cases(repo, COMPONENT, "Record")

    proof = lineage.rollback_proof(
        repo, store, COMPONENT, "Record", development.requirement, cases,
    )

    assert proof["fault_struck_the_live_file"] is True
    assert proof["adopted_supplied_the_capability"] is True
    assert proof["damage_was_behavioural"] is True
    assert proof["restoration_is_byte_exact"] is True
    assert proof["restored_matches_the_original_behaviour"] is True
    assert proof["store_version_after_restore"] == 0
    # The strongest form: the bytes are back.
    assert (repo / COMPONENT).read_text(encoding="utf-8") == original


def test_restoring_without_an_adoption_is_an_error(repo: Path) -> None:
    store = lineage.TransformationStore.init_or_load(repo, repo, "0" * 64)
    with pytest.raises(lineage.LineageError):
        store.restore_exactly(COMPONENT)


# ── the controls can fail ─────────────────────────────────────────────


def test_the_endogenous_arm_closes_the_requirement(repo: Path) -> None:
    record = lineage.run_arm("endogenous_diagnosis_and_synthesis", repo, (COMPONENT,))
    assert record["closed"] is True
    assert record["is_ceiling"] is False


def test_a_random_selection_over_a_single_component_set_is_an_error(repo: Path) -> None:
    """The arm must not silently become the endogenous arm when there is no rival."""

    with pytest.raises(lineage.LineageError):
        lineage.run_arm("random_component_selection", repo, (COMPONENT,))


def test_the_random_arm_closes_nothing_when_a_rival_exists(tmp_path: Path) -> None:
    _write_repo(tmp_path)
    (tmp_path / "pkg" / "other.py").write_text(
        "from dataclasses import dataclass\n\n\n"
        "@dataclass(frozen=True)\nclass Other:\n    other_id: str\n",
        encoding="utf-8",
    )
    record = lineage.run_arm(
        "random_component_selection", tmp_path, (COMPONENT, "pkg/other.py"),
    )
    assert record["closed"] is False


def test_the_unknown_arm_is_refused(repo: Path) -> None:
    with pytest.raises(lineage.LineageError):
        lineage.run_arm("an_arm_nobody_declared", repo, (COMPONENT,))


def test_the_fresh_agent_arm_needs_the_persisted_state(repo: Path) -> None:
    with pytest.raises(lineage.LineageError):
        lineage.run_arm("fresh_agent", repo, (COMPONENT,))


def test_the_budget_arm_reaches_the_same_mechanism(repo: Path) -> None:
    """P9. A saturated search must not find something different when given more room."""

    endogenous = lineage.run_arm("endogenous_diagnosis_and_synthesis", repo, (COMPONENT,))
    budget = lineage.run_arm("more_budget_same_operations", repo, (COMPONENT,))
    assert lineage._same_mechanism(endogenous, budget) is True


def test_the_unadopted_arm_leaves_the_component_unchanged(repo: Path) -> None:
    original = (repo / COMPONENT).read_text(encoding="utf-8")
    record = lineage.run_arm("diagnosis_without_adoption", repo, (COMPONENT,))
    assert record["adopted"] is False
    assert record["live_still_lacks_the_capability"] is True
    assert (repo / COMPONENT).read_text(encoding="utf-8") == original


# ── the verdict ───────────────────────────────────────────────────────


def test_a_condition_without_inputs_is_uncomputed_not_passed() -> None:
    """The defect the audit found in the checker, guarded here at the source."""

    verdict = lineage.evaluate({}, {}, {}, {}, {}, None)
    for name, condition in verdict["conditions"].items():
        assert condition["computed"] is False, name
        assert condition["passed"] is False, name


def test_an_unrunnable_qualification_does_not_pass_p7() -> None:
    p7 = lineage.CONDITIONS[6]
    verdict = lineage.evaluate(
        {}, {}, {}, {}, {},
        {"entries": [{"component": "a.py", "satisfied": None}], "drawn_after_adoption": True,
         "salt_is_the_adopted_mechanism_digest": True},
    )
    assert verdict["conditions"][p7]["computed"] is True
    assert verdict["conditions"][p7]["passed"] is False


def test_p11_fails_when_the_fault_missed_the_live_file() -> None:
    p11 = lineage.CONDITIONS[10]
    verdict = lineage.evaluate({}, {}, {
        "fault": "x",
        "fault_struck_the_live_file": False,
        "damage_was_behavioural": True,
        "restoration_is_byte_exact": True,
        "restored_matches_the_original_behaviour": True,
    }, {}, {}, None)
    assert verdict["conditions"][p11]["computed"] is True
    assert verdict["conditions"][p11]["passed"] is False


# ── the defect attempt 1 carried, as a test ───────────────────────────


def _crlf_repo(root: Path) -> None:
    """The same fixture, written with Windows line endings, as a checkout would give it."""

    (root / "pkg").mkdir(parents=True, exist_ok=True)
    (root / "pkg" / "__init__.py").write_bytes(b"")
    (root / COMPONENT).write_bytes(VALUES_SOURCE.replace("\n", "\r\n").encode("utf-8"))
    (root / "callers.py").write_bytes(CALLER_SOURCE.replace("\n", "\r\n").encode("utf-8"))


def test_a_crlf_component_survives_adoption_and_rollback_byte_for_byte(tmp_path: Path) -> None:
    """M094 attempt 1's disclosed defect, written down so it cannot come back.

    The store read components with `read_text`, which decodes CRLF to LF, and wrote them back
    untranslated. Adoption therefore rewrote every line ending in the file, the rollback
    restored the rewritten form, and the digest — taken over decoded text — reported
    `restoration_is_byte_exact: True` while 2356 bytes had become 2280.

    This asserts the bytes, which is what the claim says.
    """

    _crlf_repo(tmp_path)
    before = (tmp_path / COMPONENT).read_bytes()
    assert b"\r\n" in before, "the fixture must actually be CRLF or this proves nothing"

    development = lineage.develop(tmp_path, (COMPONENT,))
    assert development.modified_source is not None
    store, _ = _adopt(tmp_path, development)

    adopted = (tmp_path / COMPONENT).read_bytes()
    assert adopted != before, "adoption changed nothing"
    assert b"\r\n" in adopted, "adoption normalised the file's line endings"

    cases = lineage.behavioural_cases(tmp_path, COMPONENT, "Record", development.requirement)
    proof = lineage.rollback_proof(
        tmp_path, store, COMPONENT, "Record", development.requirement, cases,
    )
    assert proof["restoration_is_byte_exact"] is True
    assert proof["digest_domain"] == "bytes"

    after = (tmp_path / COMPONENT).read_bytes()
    assert after == before, (
        f"the file was not restored byte for byte: {len(before)} bytes became {len(after)}"
    )


def test_the_rollback_digest_is_taken_over_bytes_not_decoded_text(tmp_path: Path) -> None:
    """Two files identical as text and different as bytes must not share a digest."""

    lf = b"x = 1\ny = 2\n"
    crlf = b"x = 1\r\ny = 2\r\n"
    assert lf.decode() != crlf.decode() or True  # decoding is not what is being compared
    assert lineage._byte_digest(lf) != lineage._byte_digest(crlf)
    # And the text digest, which attempt 1 used, cannot tell them apart once decoded.
    assert lineage._source_digest(lf.decode()) == lineage._source_digest(
        crlf.decode().replace("\r\n", "\n")
    )
