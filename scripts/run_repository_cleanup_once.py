"""One-shot repository maintenance invoked only by the temporary CI cleanup hook."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

KEEP_NEWEST_RUNS = 50
MAX_ARTIFACT_DELETES = 500
MAX_RUN_DELETES = 500

# Runtime-only values. They deliberately remain inert at import time because repository integrity
# imports every module without GitHub Actions credentials.
REPO = ""
CURRENT_RUN = 0
HEADERS: dict[str, str] = {}


def configure_runtime() -> None:
    """Load the GitHub Actions context only when the one-shot entry point is executed."""
    global REPO, CURRENT_RUN, HEADERS
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    current_run = int(os.environ["GITHUB_RUN_ID"])
    REPO = repo
    CURRENT_RUN = current_run
    HEADERS = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "mira-genesis-repository-cleanup",
    }


def request(path: str, method: str = "GET"):
    if not REPO or not HEADERS:
        raise RuntimeError("repository cleanup runtime is not configured")
    url = path if path.startswith("http") else f"https://api.github.com/repos/{REPO}/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"{method} {url} -> HTTP {exc.code}: {body[:500]}") from exc


def paged(path: str, key: str):
    page = 1
    out = []
    separator = "&" if "?" in path else "?"
    while True:
        payload = request(f"{path}{separator}per_page=100&page={page}")
        items = payload[key] if isinstance(payload, dict) else payload
        if not items:
            break
        out.extend(items)
        if len(items) < 100:
            break
        page += 1
    return out


def extract_run_ids(text: str) -> set[int]:
    if not text:
        return set()
    ids = {int(value) for value in re.findall(r"actions/runs/(\d+)", text)}
    ids.update(int(value) for value in re.findall(r"(?i)\brun(?:\s+|[`#:_-]+)(\d{8,})\b", text))
    return ids


def load_all_prs() -> list[dict]:
    all_prs: list[dict] = []
    page = 1
    while True:
        prs = request(f"pulls?state=all&per_page=100&page={page}")
        if not prs:
            break
        all_prs.extend(prs)
        if len(prs) < 100:
            break
        page += 1
    return all_prs


def cleanup_branches(all_prs: list[dict]) -> tuple[list[str], list[str]]:
    open_heads = {
        pr["head"]["ref"]
        for pr in all_prs
        if pr.get("state") == "open"
        and pr.get("head", {}).get("repo", {}).get("full_name") == REPO
    }
    subprocess.run(
        ["git", "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--prune"],
        check=True,
    )
    refs = subprocess.check_output(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"],
        text=True,
    ).splitlines()
    deleted: list[str] = []
    kept: list[str] = []
    for remote_ref in sorted(set(refs)):
        branch = remote_ref.removeprefix("origin/")
        if branch in {"HEAD", "main"}:
            continue
        if branch in open_heads:
            kept.append(f"{branch} (open PR)")
            continue
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", f"origin/{branch}", "origin/main"],
            check=False,
        ).returncode == 0
        if not ancestor:
            kept.append(f"{branch} (contains non-main history)")
            continue
        result = subprocess.run(["git", "push", "origin", "--delete", branch], check=False)
        if result.returncode == 0:
            deleted.append(branch)
        else:
            kept.append(f"{branch} (delete refused)")
    return deleted, kept


def cleanup_actions(all_prs: list[dict]) -> dict[str, object]:
    protected = {CURRENT_RUN}
    completed_runs = paged("actions/runs?status=completed", "workflow_runs")
    completed_runs.sort(key=lambda run: run.get("created_at", ""), reverse=True)
    protected.update(run["id"] for run in completed_runs[:KEEP_NEWEST_RUNS])

    try:
        tracked_text = subprocess.check_output(
            ["git", "grep", "-I", "-h", "-e", "actions/runs/", "-e", "run "],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        tracked_text = ""
    protected.update(extract_run_ids(tracked_text))

    for pr in all_prs:
        protected.update(extract_run_ids(pr.get("body") or ""))

    open_heads = {
        pr["head"]["ref"]
        for pr in all_prs
        if pr.get("state") == "open"
        and pr.get("head", {}).get("repo", {}).get("full_name") == REPO
    }
    for run in completed_runs:
        if run.get("head_branch") in open_heads:
            protected.add(run["id"])

    artifacts = paged("actions/artifacts", "artifacts")
    live_artifacts = [artifact for artifact in artifacts if not artifact.get("expired", False)]
    live_artifacts.sort(key=lambda artifact: artifact.get("size_in_bytes", 0), reverse=True)

    deleted_artifacts: list[int] = []
    freed_bytes = 0
    for artifact in live_artifacts:
        if len(deleted_artifacts) >= MAX_ARTIFACT_DELETES:
            break
        run_id = (artifact.get("workflow_run") or {}).get("id")
        if run_id in protected:
            continue
        request(f"actions/artifacts/{artifact['id']}", method="DELETE")
        deleted_artifacts.append(artifact["id"])
        freed_bytes += int(artifact.get("size_in_bytes") or 0)

    deleted_runs: list[int] = []
    for run in sorted(completed_runs, key=lambda item: item.get("created_at", "")):
        if len(deleted_runs) >= MAX_RUN_DELETES:
            break
        run_id = run["id"]
        if run_id in protected:
            continue
        request(f"actions/runs/{run_id}", method="DELETE")
        deleted_runs.append(run_id)

    return {
        "completed_runs_inspected": len(completed_runs),
        "protected_run_ids": len(protected),
        "live_artifacts_inspected": len(live_artifacts),
        "deleted_artifacts": len(deleted_artifacts),
        "freed_artifact_bytes": freed_bytes,
        "deleted_runs": len(deleted_runs),
        "open_pr_heads": sorted(open_heads),
    }


def main() -> int:
    configure_runtime()
    all_prs = load_all_prs()
    deleted_branches, kept_branches = cleanup_branches(all_prs)
    actions = cleanup_actions(all_prs)
    result = {
        "deleted_branches": deleted_branches,
        "kept_branches": kept_branches,
        **actions,
    }
    print(json.dumps(result, indent=2))

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write("## One-shot repository cleanup\n\n")
            summary.write(f"- Fully merged branches deleted: **{len(deleted_branches)}**\n")
            summary.write(f"- Branches retained: **{len(kept_branches)}**\n")
            summary.write(f"- Completed runs inspected: **{actions['completed_runs_inspected']}**\n")
            summary.write(f"- Protected run IDs: **{actions['protected_run_ids']}**\n")
            summary.write(f"- Old completed runs deleted: **{actions['deleted_runs']}**\n")
            summary.write(f"- Old artifacts deleted: **{actions['deleted_artifacts']}**\n")
            summary.write(
                f"- Artifact payload freed: **{actions['freed_artifact_bytes'] / (1024 * 1024):.1f} MiB**\n"
            )
            if deleted_branches:
                summary.write("\nDeleted branches:\n")
                for branch in deleted_branches:
                    summary.write(f"- `{branch}`\n")
            if kept_branches:
                summary.write("\nRetained branches:\n")
                for branch in kept_branches:
                    summary.write(f"- `{branch}`\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
