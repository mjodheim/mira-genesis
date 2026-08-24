"""M106 replication tests.

The pre-freeze audit asserts that no canonical evidence exists yet. That check is a *phase* claim,
not a boundary claim: once M106's unique attempt runs it is correctly false forever. M105's
equivalent test asserted it unconditionally and turned both CI jobs red the moment its result was
sealed, so this one binds the phase check to the artefacts on disk from the start.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from scripts import audit_m106_boundaries
from scripts import author_m106_development_fixture as development_author
from scripts import author_m106_qualification_pool as pool_author
from scripts import run_m106_qualification as qualification

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M106"
MECHANISM = ROOT / "metamorphosis" / "m105_runtime.py"
_PHASE_CHECK = "canonical_evidence_absent_before_attempt"


def _canonical_evidence_exists() -> bool:
    return (EXPERIMENT / "RESULT.json").exists() or (EXPERIMENT / "CHECK_REPORT.json").exists()


def test_the_mechanism_module_is_imported_unchanged_not_forked() -> None:
    """M106 replicates M105's mechanism. A forked copy would silently end the replication."""
    assert not (ROOT / "metamorphosis" / "m106_runtime.py").exists()
    source = qualification.__file__ and Path(qualification.__file__).read_text(encoding="utf-8")
    assert "from metamorphosis import m105_runtime as runtime" in source
    assert MECHANISM.exists()


def test_the_population_is_fresh_with_respect_to_m105() -> None:
    pool = json.loads((EXPERIMENT / "QUALIFICATION_POOL.json").read_text("ascii"))
    assert pool["target_truth_table"] == [True, False, False, True]
    assert development_author.TARGET_TRUTH_TABLE == (True, False, False, True)

    m105_pool_path = ROOT / "experiments" / "M105" / "QUALIFICATION_POOL.json"
    if m105_pool_path.exists():
        m105 = json.loads(m105_pool_path.read_text("ascii"))
        assert pool["pool_digest"] != m105["pool_digest"]
        raw = (EXPERIMENT / "QUALIFICATION_POOL.json").read_bytes()
        for literal in (b"amber", b"violet", b'"route"'):
            assert literal not in raw, literal


def test_development_material_leaks_no_qualification_literal() -> None:
    raw = (EXPERIMENT / "DEVELOPMENT_FIXTURE.json").read_bytes()
    for literal in (b"harbor", b"quartz", b"channel", b"json", b"sqlite"):
        assert literal not in raw, literal


def test_authored_inputs_match_their_authoring_scripts() -> None:
    for builder, name in (
        (development_author.build, "DEVELOPMENT_FIXTURE.json"),
        (pool_author.build, "QUALIFICATION_POOL.json"),
    ):
        expected = qualification.canonical_json(builder()).encode("ascii")
        assert (EXPERIMENT / name).read_bytes() == expected, name


def test_input_preflight_binds_the_fresh_population() -> None:
    report = qualification.verify_inputs()
    assert report["confirmed"] is True, [k for k, v in report["checks"].items() if not v]
    raw = (EXPERIMENT / "QUALIFICATION_POOL.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == qualification.POOL_RAW_SHA256


def test_adversarial_boundary_audit_still_holds() -> None:
    report = audit_m106_boundaries.audit()
    checks = report["checks"]
    substantive = {key: value for key, value in checks.items() if key != _PHASE_CHECK}
    assert all(substantive.values()), [k for k, v in substantive.items() if not v]
    assert report["fresh_semantic_classes"] == {"json_document": 4, "sqlite": 4}
    assert report["feature_truth_table"] == [True, False, False, True]
    if _canonical_evidence_exists():
        assert checks[_PHASE_CHECK] is False
    else:
        assert checks[_PHASE_CHECK] is True


def test_canonical_entrypoint_is_gated_by_the_final_freeze() -> None:
    content_refusals = (
        "final protocol is absent",
        "schema or digest mismatch",
        "is not owner-authorized",
        "decisive predicate declaration changed",
        "pool binding mismatch",
        "bound apparatus changed",
    )
    if not qualification.PROTOCOL_PATH.exists():
        try:
            qualification.require_frozen()
        except qualification.QualificationRefused as error:
            assert "final protocol is absent" in str(error)
        else:  # pragma: no cover - an absent protocol must always refuse
            raise AssertionError("M106 unexpectedly has a final protocol before freeze")
        return

    protocol = qualification._read_canonical(qualification.PROTOCOL_PATH, "M106 final protocol")
    payload = {key: item for key, item in protocol.items() if key != "protocol_digest"}
    assert protocol["protocol_digest"] == qualification.digest(payload)
    assert protocol["status"] == "frozen_protocol_owner_authorized"
    assert protocol["decisive_conditions"] == qualification.EXPECTED_PREDICATES
    try:
        armed = qualification.require_frozen()
    except qualification.QualificationRefused as error:
        assert not any(reason in str(error) for reason in content_refusals), str(error)
    else:
        assert armed["protocol_digest"] == protocol["protocol_digest"]


def test_the_checker_replay_import_resolves_as_a_direct_script() -> None:
    """The exact defect that lost M105: a deferred import that never resolved under the frozen command."""
    import subprocess

    source = (ROOT / "scripts" / "check_m106_result.py").read_text(encoding="utf-8")
    assert "from scripts import run_m106_qualification" in source
    assert "_ROOT = Path(__file__).resolve().parents[1]" in source

    completed = subprocess.run(
        [sys.executable, "-c",
         "import runpy,sys;sys.argv=['check_m106_result.py'];"
         "runpy.run_path(r'%s', run_name='not_main')" % (ROOT / "scripts" / "check_m106_result.py")],
        capture_output=True, text=True, cwd=ROOT / "scripts",
    )
    assert completed.returncode == 0, completed.stderr
