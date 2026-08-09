from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_software_and_research_licences_are_complete_and_declared() -> None:
    agpl = _read("LICENSE")
    cc_by = _read("LICENSES/CC-BY-4.0.txt")
    policy = _read("LICENSE_POLICY.md")

    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in agpl
    assert "Version 3, 19 November 2007" in agpl
    assert "END OF TERMS AND CONDITIONS" in agpl
    assert "Creative Commons Attribution 4.0 International Public License" in cc_by
    assert "Section 3 – License Conditions." in cc_by
    assert "AGPL-3.0-only" in policy
    assert "CC-BY-4.0" in policy

    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    assert project["license"] == "AGPL-3.0-only"
    assert project["license-files"] == [
        "LICENSE",
        "NOTICE",
        "LICENSES/CC-BY-4.0.txt",
    ]
    assert project["authors"] == [{"name": "Anthony Mets"}]


def test_public_attribution_and_citation_preserve_the_project_origin() -> None:
    required_surfaces = [
        "AUTHORS.md",
        "LICENSE_POLICY.md",
        "NOTICE",
        "PROVENANCE.md",
        "README.md",
        "TRADEMARKS.md",
    ]
    for path in required_surfaces:
        text = _read(path)
        assert "Anthony Mets" in text, path
        assert "Mira Genesis" in text, path

    citation = _read("CITATION.cff")
    assert 'family-names: "Mets"' in citation
    assert 'given-names: "Anthony"' in citation
    assert 'license: "AGPL-3.0-only"' in citation
    assert "https://github.com/mjodheim/mira-genesis" in citation


def test_provenance_binds_the_positive_canonical_closure() -> None:
    provenance = _read("PROVENANCE.md")
    anchors = {
        "canonical marker": "2cf454ca4e393a319f89ae5afbcd5e3f9250182c",
        "canonical result": "eaf6fee975bddaae583e0f739d0a5ad050209b303d304eddc81bb6320c642ace",
        "reproduction": "b990efa4c85c808349de046b7b7ed7477138b77c5111f7385e913f7583ab77cc",
        "evidence commit": "248163fa91261b517623bed218e21a562e1cc097",
        "closure merge": "2994f86b0e5fe671e322f4b1a5a8367a913a0dc2",
    }
    for label, digest in anchors.items():
        assert digest in provenance, label

    assert "31291899534" in provenance
    assert "results/artifacts/" in provenance
