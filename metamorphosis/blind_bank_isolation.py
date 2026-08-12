"""Construct and audit the technical boundary a blind generator must run behind.

Blindness asserted in prose is worth nothing. This module turns it into two artifacts that can be
checked after the fact by someone who does not trust the person who ran the generator:

* an **invocation plan** — the exact container argv, derived from a request rather than typed, so
  the boundary is a consequence of the code rather than of care;
* an **attestation** — what actually ran, digested into the public bank commitment.

The audit is deliberately hostile. It resolves every mount source against the repository root
instead of matching strings, because `../Mira Genesis` and a symlink both defeat a substring test.
It rejects any environment variable whose value looks like a path into this repository even when
its name is allowlisted, because `HOME` pointing at the checkout is the same leak as `MIRA_ROOT`.
"""
from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from metamorphosis.blind_bank_protocol import (
    BlindBankError,
    ISOLATION_SCHEMA,
    canonical_bytes,
    contamination_hits,
    sha256_hex,
)


# Everything the generator container is allowed to see in its environment. The list is short by
# design: each entry is one more thing a future reader must be convinced carries no project
# context.
PERMITTED_ENVIRONMENT_KEYS = frozenset({
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TZ",
    "BLIND_BANK_INPUT",
    "BLIND_BANK_OUTPUT",
    "BLIND_BANK_SEED",
    "OMP_NUM_THREADS",
})

# Fixed locations inside the container. They are constants rather than parameters so that the
# recorded attestation cannot drift from the plan that produced it.
CONTAINER_INPUT_PATH = PurePosixPath("/blind/input/request.json")
CONTAINER_OUTPUT_DIRECTORY = PurePosixPath("/blind/output")
CONTAINER_WORKDIR = PurePosixPath("/blind/work")

REQUIRED_DOCKER_FLAGS = (
    "--network=none",
    "--read-only",
    "--cap-drop=ALL",
    "--security-opt=no-new-privileges",
    "--pids-limit=512",
)

_PATHISH = re.compile(r"[\\/]")


class IsolationError(BlindBankError):
    """Raised when a generator invocation or attestation crosses the isolation boundary."""


def _resolve(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve()


def _is_inside(candidate: Path, parent: Path) -> bool:
    return candidate == parent or parent in candidate.parents


def audit_environment(
    environment: Mapping[str, str], *, repository_root: str | os.PathLike[str],
) -> list[str]:
    """Return every reason an environment mapping would carry project context inward."""

    root = _resolve(repository_root)
    problems: list[str] = []
    for key, value in sorted(environment.items()):
        if key not in PERMITTED_ENVIRONMENT_KEYS:
            problems.append(f"environment key {key!r} is not on the allowlist")
        if not isinstance(value, str):
            problems.append(f"environment value for {key!r} is not a string")
            continue
        hits = contamination_hits(value)
        if hits:
            problems.append(
                f"environment value for {key!r} names project context: {', '.join(hits)}"
            )
        if _PATHISH.search(value):
            for candidate in value.split(os.pathsep):
                if not candidate.strip():
                    continue
                try:
                    resolved = _resolve(candidate)
                except (OSError, ValueError):
                    continue
                if _is_inside(resolved, root):
                    problems.append(
                        f"environment value for {key!r} resolves inside the repository"
                    )
                    break
    return problems


def audit_mounts(
    mounts: Sequence[Mapping[str, object]], *, repository_root: str | os.PathLike[str],
) -> list[str]:
    """Return every reason a mount set would expose this repository to the generator."""

    root = _resolve(repository_root)
    problems: list[str] = []
    for index, mount in enumerate(mounts):
        if set(mount) != {"source", "target", "mode"}:
            problems.append(f"mount {index} fields differ from the closed schema")
            continue
        source, target, mode = mount["source"], mount["target"], mount["mode"]
        if not isinstance(source, str) or not isinstance(target, str):
            problems.append(f"mount {index} source or target is not a string")
            continue
        if mode not in {"ro", "rw"}:
            problems.append(f"mount {index} mode {mode!r} is not ro or rw")
        try:
            resolved = _resolve(source)
        except (OSError, ValueError):
            problems.append(f"mount {index} source cannot be resolved")
            continue
        if _is_inside(resolved, root) or _is_inside(root, resolved):
            problems.append(
                f"mount {index} source {source!r} resolves into or above the repository"
            )
        # Only the container-visible target is scanned for project context. The host path is
        # never seen by the generator, and resolution above is the check that matters for it.
        if contamination_hits(target):
            problems.append(f"mount {index} target names project context")
        if not PurePosixPath(target).is_absolute():
            problems.append(f"mount {index} target is not an absolute container path")
    return problems


def plan_invocation(
    *,
    repository_root: str | os.PathLike[str],
    image_reference: str,
    image_digest_sha256: str,
    input_path: str | os.PathLike[str],
    output_directory: str | os.PathLike[str],
    environment: Mapping[str, str],
    command: Sequence[str],
) -> dict[str, object]:
    """Build the exact container invocation, refusing to emit one that leaks.

    The plan is returned rather than executed. Nothing in this module starts a process: the
    scientific run is a separate, human-authorized act and this repository must not contain a
    function that performs it as a side effect of validation.
    """

    root = _resolve(repository_root)
    resolved_input = _resolve(input_path)
    resolved_output = _resolve(output_directory)

    problems = audit_environment(environment, repository_root=root)
    mounts = [
        {"source": str(resolved_input), "target": str(CONTAINER_INPUT_PATH), "mode": "ro"},
        {"source": str(resolved_output), "target": str(CONTAINER_OUTPUT_DIRECTORY), "mode": "rw"},
    ]
    problems += audit_mounts(mounts, repository_root=root)
    if not resolved_input.is_file():
        problems.append("the single generator input is not a file")
    if resolved_output.exists() and any(resolved_output.iterdir()):
        problems.append("the generator output directory is not empty")
    if not re.fullmatch(r"[0-9a-f]{64}", str(image_digest_sha256)):
        problems.append("generator image digest is malformed")
    if not isinstance(command, Sequence) or isinstance(command, (str, bytes)) or not command:
        problems.append("generator command is malformed")
    if problems:
        raise IsolationError("; ".join(problems))

    argv: list[str] = ["docker", "run", "--rm", *REQUIRED_DOCKER_FLAGS]
    argv += ["--workdir", str(CONTAINER_WORKDIR)]
    argv += ["--tmpfs", f"{CONTAINER_WORKDIR}:rw,noexec,nosuid,size=256m"]
    for mount in mounts:
        specification = f"type=bind,source={mount['source']},target={mount['target']}"
        if mount["mode"] == "ro":
            specification += ",readonly"
        argv += ["--mount", specification]
    for key in sorted(environment):
        argv += ["--env", f"{key}={environment[key]}"]
    argv += [f"{image_reference}@sha256:{image_digest_sha256}", *command]

    return {
        "image_reference": image_reference,
        "image_digest_sha256": image_digest_sha256,
        "mounts": mounts,
        "environment": dict(sorted(environment.items())),
        "argv": argv,
        "input_path": str(resolved_input),
        "output_directory": str(resolved_output),
    }


_WINDOWS_DRIVE_PREFIX = re.compile(r"\A([A-Za-z]:[\\/][^:]*)(?::(.*))?\Z")


def _path_candidates(specification: str) -> list[str]:
    """Split a mount specification into every fragment that might be a host path.

    A Windows source is `C:\\...`, so splitting on `:` unconditionally would destroy the drive
    letter and turn an in-repository mount into an unresolvable fragment that silently passes the
    audit. The POSIX `src:dst:ro` form still needs that split. Both forms are handled: a
    drive-qualified prefix is taken whole and only the remainder is split again.
    """

    candidates: list[str] = []
    for piece in re.split(r"[,=]", specification):
        if not piece:
            continue
        drive = _WINDOWS_DRIVE_PREFIX.match(piece)
        if drive:
            candidates.append(drive.group(1))
            remainder = drive.group(2)
            if remainder:
                candidates.extend(part for part in remainder.split(":") if part)
        else:
            candidates.extend(part for part in piece.split(":") if part)
    return [candidate for candidate in candidates if _PATHISH.search(candidate)]


def audit_invocation_argv(
    argv: Sequence[str], *, repository_root: str | os.PathLike[str],
) -> list[str]:
    """Audit a recorded argv independently of the planner that produced it."""

    root = _resolve(repository_root)
    problems: list[str] = []
    tokens = list(argv)
    if tokens[:3] != ["docker", "run", "--rm"]:
        problems.append("invocation is not a disposable container run")
    for flag in REQUIRED_DOCKER_FLAGS:
        if flag not in tokens:
            problems.append(f"invocation is missing {flag}")
    for index, token in enumerate(tokens):
        following = tokens[index + 1] if index + 1 < len(tokens) else ""
        if token in {"-v", "--volume", "--mount"}:
            for candidate in _path_candidates(following):
                try:
                    resolved = _resolve(candidate)
                except (OSError, ValueError):
                    continue
                if _is_inside(resolved, root) or _is_inside(root, resolved):
                    problems.append(f"invocation mounts {candidate!r} from the repository")
        if token in {"-e", "--env"}:
            name, _, value = following.partition("=")
            if name not in PERMITTED_ENVIRONMENT_KEYS:
                problems.append(f"invocation passes non-allowlisted environment key {name!r}")
            if contamination_hits(value):
                problems.append(f"invocation environment value for {name!r} names project context")
        if token.startswith("--network") and token != "--network=none":
            problems.append("invocation enables a network")
        if token in {"--privileged", "--cap-add"} or token.startswith("--cap-add="):
            problems.append("invocation raises container privileges")
    return problems


def build_attestation(
    *,
    plan: Mapping[str, object],
    repository_root: str | os.PathLike[str],
    input_sha256: str,
    output_sha256: str,
    stdout_sha256: str,
    stderr_sha256: str,
    started_at: str,
    finished_at: str,
    exit_status: int,
    runtime_name: str,
    runtime_version: str,
) -> dict[str, object]:
    """Record what the generator run was actually permitted to see."""

    problems = audit_invocation_argv(
        list(plan["argv"]),  # type: ignore[arg-type]
        repository_root=repository_root,
    )
    if problems:
        raise IsolationError("; ".join(problems))
    attestation: dict[str, object] = {
        "schema": ISOLATION_SCHEMA,
        "runner": "container",
        "runtime_name": runtime_name,
        "runtime_version": runtime_version,
        "image_reference": plan["image_reference"],
        "image_digest_sha256": plan["image_digest_sha256"],
        "argv": list(plan["argv"]),  # type: ignore[arg-type]
        "environment_keys": sorted(plan["environment"]),  # type: ignore[arg-type]
        "network": "none",
        "repository_mounted": False,
        "secrets_mounted": False,
        "code_forge_credentials_present": False,
        "working_filesystem": "fresh-tmpfs",
        "input_sha256": input_sha256,
        "output_sha256": output_sha256,
        "stdout_sha256": stdout_sha256,
        "stderr_sha256": stderr_sha256,
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_status": exit_status,
        "attestation_sha256": "",
    }
    body = {key: value for key, value in attestation.items() if key != "attestation_sha256"}
    attestation["attestation_sha256"] = sha256_hex(canonical_bytes(body))
    return attestation


def validate_attestation(
    attestation: Mapping[str, object], *, repository_root: str | os.PathLike[str],
) -> None:
    """Validate a recorded attestation against the boundary it claims to have held."""

    expected = {
        "schema", "runner", "runtime_name", "runtime_version", "image_reference",
        "image_digest_sha256", "argv", "environment_keys", "network", "repository_mounted",
        "secrets_mounted", "code_forge_credentials_present", "working_filesystem",
        "input_sha256", "output_sha256", "stdout_sha256", "stderr_sha256", "started_at",
        "finished_at", "exit_status", "attestation_sha256",
    }
    if not isinstance(attestation, Mapping) or set(attestation) != expected:
        raise IsolationError("isolation attestation fields differ from the closed schema")
    if attestation.get("schema") != ISOLATION_SCHEMA:
        raise IsolationError("isolation attestation schema drifted")
    if attestation.get("runner") != "container":
        raise IsolationError("a blind generator runs in a container")
    if attestation.get("network") != "none":
        raise IsolationError("the generator run had network access")
    for field in ("repository_mounted", "secrets_mounted", "code_forge_credentials_present"):
        if attestation.get(field) is not False:
            raise IsolationError(f"isolation attestation admits {field}")
    if attestation.get("working_filesystem") != "fresh-tmpfs":
        raise IsolationError("the generator did not run on a fresh working filesystem")
    if attestation.get("exit_status") != 0:
        raise IsolationError("the generator run did not exit cleanly")
    for field in ("input_sha256", "output_sha256", "stdout_sha256", "stderr_sha256",
                  "image_digest_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(attestation.get(field))):
            raise IsolationError(f"isolation attestation {field} is malformed")
    keys = attestation.get("environment_keys")
    if not isinstance(keys, list) or any(
        key not in PERMITTED_ENVIRONMENT_KEYS for key in keys
    ):
        raise IsolationError("isolation attestation records a non-allowlisted environment key")
    argv = attestation.get("argv")
    if not isinstance(argv, list) or not all(isinstance(token, str) for token in argv):
        raise IsolationError("isolation attestation argv is malformed")
    problems = audit_invocation_argv(argv, repository_root=repository_root)
    if problems:
        raise IsolationError("; ".join(problems))
    body = {key: value for key, value in attestation.items() if key != "attestation_sha256"}
    if attestation.get("attestation_sha256") != sha256_hex(canonical_bytes(body)):
        raise IsolationError("isolation attestation digest drifted")


__all__ = [
    "CONTAINER_INPUT_PATH", "CONTAINER_OUTPUT_DIRECTORY", "CONTAINER_WORKDIR",
    "IsolationError", "PERMITTED_ENVIRONMENT_KEYS", "REQUIRED_DOCKER_FLAGS",
    "audit_environment", "audit_invocation_argv", "audit_mounts", "build_attestation",
    "plan_invocation", "validate_attestation",
]
