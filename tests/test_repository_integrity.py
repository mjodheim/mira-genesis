"""Regression checks for the repository-integrity checker itself."""
from __future__ import annotations

import json
from pathlib import Path

import check_repository_integrity as integrity
from check_repository_integrity import check_citations, check_dependencies


def test_repository_scripts_are_local_not_a_distribution_dependency() -> None:
    assert check_dependencies() == []


def test_every_commit_the_record_cites_is_still_reachable() -> None:
    """The live manifest, against the live repository. This is the check doing its job."""
    assert check_citations() == []


def _manifest(tmp_path: Path, commits: dict[str, dict]) -> Path:
    path = tmp_path / "COMMIT_CITATIONS.json"
    path.write_text(
        json.dumps({"schema": "commit-citations-v1", "commits": commits}),
        encoding="utf-8",
    )
    return path


def _one_real_citation() -> tuple[str, dict]:
    recorded = json.loads(integrity.CITATIONS.read_text(encoding="utf-8"))["commits"]
    return next(iter(sorted(recorded.items())))


def test_a_cited_commit_that_stopped_resolving_is_reported(tmp_path, monkeypatch) -> None:
    """The failure this check exists for: the citation still reads, and nothing resolves it."""
    vanished = "0" * 40
    monkeypatch.setattr(
        integrity,
        "CITATIONS",
        _manifest(
            tmp_path,
            {
                vanished: {
                    "subject": "freeze(m094): bind the eligible set",
                    "preserved_by": "provenance/dd79665",
                    "cited_in": ["SCIENTIFIC_HYPOTHESES.md"],
                }
            },
        ),
    )
    lost = [problem for problem in check_citations() if "no longer reachable" in problem]
    assert len(lost) == 1
    assert vanished[:12] in lost[0]
    assert "SCIENTIFIC_HYPOTHESES.md" in lost[0], "the report must name where the citation reads"
    assert "provenance/dd79665" in lost[0], "the report must name the ref that used to preserve it"


def test_a_commit_cited_but_absent_from_the_manifest_is_reported(tmp_path, monkeypatch) -> None:
    """A citation added later is a citation nothing is protecting yet."""
    sha, entry = _one_real_citation()
    keeper = "1" * 39 + "a"
    monkeypatch.setattr(
        integrity,
        "CITATIONS",
        _manifest(tmp_path, {keeper: {"subject": "placeholder", "preserved_by": "main"}}),
    )
    problems = check_citations()
    assert any(sha[:12] in problem and "absent from" in problem for problem in problems), (
        f"{sha[:12]}, cited in {entry.get('cited_in', ['?'])[0]}, was not reported as unrecorded"
    )


def test_a_shallow_clone_is_reported_rather_than_passing(monkeypatch) -> None:
    """Reachability is unanswerable without history, and unanswerable is not the same as fine."""
    monkeypatch.setattr(
        integrity,
        "_git",
        lambda *arguments: "true\n" if arguments[:2] == ("rev-parse", "--is-shallow-repository") else None,
    )
    problems = check_citations()
    assert problems == [
        "this is a shallow clone, so reachability cannot be established; "
        "check out with fetch-depth: 0"
    ]


def test_a_missing_manifest_is_reported(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(integrity, "CITATIONS", tmp_path / "absent.json")
    problems = check_citations()
    assert len(problems) == 1
    assert problems[0].endswith("absent.json is missing")
