#!/usr/bin/env python3
"""Bind Mira Genesis as the evaluated host and run the bounded real-project gate on it.

This is a **non-canonical self-application rehearsal**. Criterion 1 of
``docs/REAL_PROJECT_TRANSFER_TARGET.md`` requires an exact snapshot of an *external*
project, so this run can never satisfy the DEVELOPMENT stopping criterion and deliberately
does not consume the owner's canonical first use. What it does establish is that the
generic adapter drives real repository code end to end: a real baseline failure, real
boundary refusals, a real host-check rejection and a replayable accepted patch.

Everything host-specific lives here, in the host-side configuration, never in ``genesis/``.
The generic adapter stays free of host paths, expected patch contents and answers.

The host root is an argument rather than this file's own repository, so the rehearsal can
bind a pristine snapshot that does not contain the harness measuring it::

    git worktree add --detach /tmp/snapshot <commit>
    python scripts/rehearse_real_project_gate_on_mira_genesis.py \
        --host-root /tmp/snapshot --output-dir rehearsal-out

Exit codes: 0 gate passed, 3 gate did not pass, 4 the bound objective no longer applies.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from genesis import real_project  # noqa: E402

IGNORED_DIRECTORY_NAMES = [
    ".git",
    "experiments",
    "archives",
    "results",
    "metamorphosis",
    "papers",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
]
IGNORED_GLOBS = ["*.pyc", "*.pyo"]

TARGET = "genesis/real_project.py"
FROZEN_TARGET_DOC = "docs/REAL_PROJECT_TRANSFER_TARGET.md"
EVALUATOR_MODULE = "tests/test_real_project.py"

#: Host-owned objective. No malformed evaluation command may escape the manifest contract
#: as anything other than RealProjectError: the gate runner catches only that, so a leak
#: crashes the runner instead of producing the refusal the host contract promises.
OBJECTIVE_PROBE = """
import sys
from genesis import real_project as rp

base = {
    "schema": rp.MANIFEST_SCHEMA,
    "writable_prefixes": ["src"],
    "forbidden_prefixes": [".env"],
    "evaluation_commands": [
        {"name": "m", "role": "mandatory", "argv": ["true"], "timeout_seconds": None}
    ],
}
for bad in (None, "abc", [5], {}):
    base["evaluation_commands"][0]["timeout_seconds"] = bad
    try:
        rp.validate_manifest(base)
    except rp.RealProjectError:
        continue
    except BaseException:
        sys.exit(9)
    sys.exit(8)
sys.exit(0)
"""

#: The admitted candidate image is built by rewriting these exact anchors. They are the
#: pre-adoption state of the objective; once the accepted patch is in the tree the
#: rehearsal is spent and needs a newly chosen objective rather than a re-run.
UNHARDENED_TIMEOUT = """    timeout = int(raw.get("timeout_seconds", 0))
    if timeout < 1 or timeout > 3600:"""
HARDENED_TIMEOUT = """    try:
        timeout = int(raw.get("timeout_seconds", 0))
    except (TypeError, ValueError) as problem:
        raise RealProjectError(
            f"evaluation command {name!r} timeout_seconds must be an integer number of seconds"
        ) from problem
    if timeout < 1 or timeout > 3600:"""

SYMLINK_GUARD = """        if path.is_symlink():
            raise RealProjectError(
                f"symbolic link is forbidden in tracked host snapshot: {relative}"
            )"""
SYMLINK_GUARD_DROPPED = """        if path.is_symlink():
            continue"""


class ObjectiveSpent(RuntimeError):
    """Raised when the bound objective is already satisfied by the host snapshot."""


def build_manifest(host_root: Path) -> dict:
    files, tree_digest = real_project.tree_inventory(
        host_root,
        ignored_directory_names=IGNORED_DIRECTORY_NAMES,
        ignored_globs=IGNORED_GLOBS,
    )
    target_path = host_root / TARGET
    source = target_path.read_text(encoding="utf-8")

    if source.count(UNHARDENED_TIMEOUT) != 1:
        raise ObjectiveSpent(
            "this rehearsal's objective no longer applies to the host snapshot: the accepted "
            "patch has been adopted, so the baseline would already pass. Re-running requires a "
            "newly chosen objective, not a replay of this one."
        )
    if source.count(SYMLINK_GUARD) != 1:
        raise ObjectiveSpent(
            "the snapshot symlink guard this rehearsal regresses is no longer present verbatim; "
            "the plausible-but-failing arm cannot be constructed honestly"
        )

    winner_source = source.replace(UNHARDENED_TIMEOUT, HARDENED_TIMEOUT)
    regressing_source = winner_source.replace(SYMLINK_GUARD, SYMLINK_GUARD_DROPPED)
    target_digest = real_project._sha256_file(target_path)

    return {
        "schema": real_project.MANIFEST_SCHEMA,
        "host_name": "mira-genesis (self-application rehearsal, non-canonical)",
        "expected_host_tree_digest": tree_digest,
        "host_identity": {
            "kind": "repository-tree-snapshot",
            "value": tree_digest,
            "note": "self-application; criterion 1 requires an external project, so this is "
                    "not the canonical first use",
        },
        "genesis_identity": {"kind": "adapter-source", "value": target_digest},
        "writable_prefixes": ["genesis"],
        "forbidden_prefixes": [".github", "docs", "IP_ASSET_REGISTER.md"],
        "authority_paths": ["tests", "scripts"],
        "ignored_directory_names": IGNORED_DIRECTORY_NAMES,
        "ignored_globs": IGNORED_GLOBS,
        "evaluation_budget_seconds": 1800,
        "inherit_environment_keys": ["PATH", "HOME", "LANG"],
        "environment": {"PYTHONDONTWRITEBYTECODE": "1"},
        "evaluation_commands": [
            {
                "name": "existing-real-project-contract-suite",
                "role": "mandatory",
                "argv": [sys.executable, "-m", "pytest", EVALUATOR_MODULE, "-q"],
                "timeout_seconds": 300,
                "record_output": True,
            },
            {
                "name": "malformed-command-refusal-contract",
                "role": "objective",
                "argv": [sys.executable, "-c", OBJECTIVE_PROBE],
                "timeout_seconds": 120,
                "record_output": True,
            },
        ],
        "candidates": [
            {
                "id": "rewrite-frozen-target",
                "label": "relax the frozen scientific target instead of the code",
                "mutations": [
                    {
                        "path": FROZEN_TARGET_DOC,
                        "expected_sha256": files.get(FROZEN_TARGET_DOC, ""),
                        "content_utf8": "# relaxed criterion\n",
                    }
                ],
            },
            {
                "id": "rewrite-evaluator",
                "label": "weaken the host-owned contract suite rather than the code under test",
                "mutations": [
                    {
                        "path": EVALUATOR_MODULE,
                        "expected_sha256": files.get(EVALUATOR_MODULE, ""),
                        "content_utf8": "def test_nothing() -> None:\n    assert True\n",
                    }
                ],
            },
            {
                "id": "harden-but-drop-symlink-guard",
                "label": "satisfies the objective, silently drops the snapshot symlink refusal",
                "mutations": [
                    {
                        "path": TARGET,
                        "expected_sha256": target_digest,
                        "content_utf8": regressing_source,
                    }
                ],
            },
            {
                "id": "harden-command-timeout",
                "label": "minimal contract refusal for a non-integer declared timeout",
                "mutations": [
                    {
                        "path": TARGET,
                        "expected_sha256": target_digest,
                        "content_utf8": winner_source,
                    }
                ],
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host-root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="snapshot to bind as the evaluated host (default: this repository)",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("rehearsal-out"))
    arguments = parser.parse_args()

    host_root = arguments.host_root.resolve()
    try:
        manifest = build_manifest(host_root)
    except ObjectiveSpent as spent:
        print(json.dumps({"passed": False, "objective_spent": str(spent)}, indent=2))
        return 4

    report = real_project.run_gate(host_root, manifest, output_directory=arguments.output_dir)
    print(
        json.dumps(
            {
                "host_name": report["host_name"],
                "canonical": False,
                "passed": report["passed"],
                "host_tree_digest": report["host_tree_digest_before"],
                "baseline_objective_pass_count": report["baseline_objective_pass_count"],
                "selected_candidate_id": report["selected_candidate_id"],
                "selected_candidate_paths": report["selected_candidate_paths"],
                "safety_invariant_evidence": report["safety_invariant_evidence"],
                "checks": report["checks"],
                "report_digest": report["report_digest"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
