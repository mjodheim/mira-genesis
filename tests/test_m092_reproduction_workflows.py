"""Static pre-arm invariants for M092 canonical/reproduction workflow separation."""
from __future__ import annotations

from pathlib import Path

from scripts import check_m092_canonical_guard as guard

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / ".github/workflows/m092-canonical-search.yml"
REPRODUCTION = ROOT / ".github/workflows/m092-independent-reproduction.yml"


def test_target_workflows_never_dispatch_scientific_continuations_from_main() -> None:
    canonical = CANONICAL.read_text(encoding="utf-8")
    reproduction = REPRODUCTION.read_text(encoding="utf-8")

    assert "'ref': 'main'" not in canonical
    assert "'ref': 'main'" not in reproduction
    assert canonical.count("'ref': branch_ref") >= 2
    assert reproduction.count("'ref': os.environ['ARMING_BRANCH_REF']") >= 1


def test_canonical_result_is_preserved_before_reproduction_dispatch() -> None:
    text = CANONICAL.read_text(encoding="utf-8")
    preserved = text.index("name: Upload immutable completed canonical search artifact")
    dispatch = text.index("name: Dispatch independent reproduction from immutable arming branch")
    assert preserved < dispatch
    assert "id: completed_upload" in text[preserved:dispatch]


def test_reproduction_cannot_download_canonical_content_before_terminal_checkpoint() -> None:
    text = REPRODUCTION.read_text(encoding="utf-8")
    execute = text.index("name: Execute next independent reproduction segment")
    segment = text.index("name: Upload immutable reproduction segment")
    download = text.index("name: Download canonical result only after reproduction is terminal")
    compare = text.index("name: Compare terminal reproduction with independently validated canonical result")
    preserve = text.index("name: Preserve completed independent reproduction before enforcing match")
    enforce = text.index("name: Enforce reproduction match only after preservation")

    assert execute < segment < download < compare < preserve < enforce
    assert "steps.segment_record.outputs.terminal == 'true'" in text[segment:compare]
    assert "test ! -e canonical-reference" in text[:execute]


def test_future_arm_binds_every_independent_reproduction_runtime_file() -> None:
    expected = {
        "independent_reproduction_core_sha256": Path("metamorphosis/m092_independent_reproduction.py"),
        "independent_reproduction_runner_sha256": Path("scripts/run_m092_independent_reproduction.py"),
        "independent_reproduction_segment_packager_sha256": Path("scripts/package_m092_reproduction_segment.py"),
        "independent_reproduction_packager_sha256": Path("scripts/package_m092_independent_reproduction.py"),
        "independent_reproduction_workflow_sha256": Path(".github/workflows/m092-independent-reproduction.yml"),
    }
    for field, path in expected.items():
        assert guard.BOUND_FILES.get(field) == path
        assert (ROOT / path).is_file()
