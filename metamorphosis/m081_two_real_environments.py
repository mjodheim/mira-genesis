"""One agent interface across two real isolated environments.

G6 asks for the same agent interface in isolated but real software environments, with completion
measured from environment state and never from the agent's self-report. M071 supplied one terminal
task; the register records that broad environment coverage remains absent.

Here one unchanged agent emits four abstract actions — put, read, remove, list — into two materially
different real systems: a POSIX shell inside an Alpine container over a real filesystem, and a real
Python HTTP server process inside a separate container answering over a socket. Neither environment
is modelled in this module. The harness learns their state only by executing a fresh read against
them.

This delivers no browser and no desktop VM. Those G6 clauses stay untouched.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping, Sequence


PROTOCOL_SCHEMA = "m081-two-real-environments-protocol-v1"
GENERATOR_VERSION = 1

ALPINE_IMAGE = (
    "alpine@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc"
)
PYTHON_IMAGE = (
    "python@sha256:9662417aace5ae7b8e2609cce472b72a8958e134ba372808abe9cc1a0c0125e6"
)

ENVIRONMENTS = ("shell", "service")
TASKS_PER_ENVIRONMENT = 6
ARMS = ("shared_interface", "crossed_drivers", "self_report_scored")

ACTIONS = ("put", "read", "remove", "list")
WORK_DIR = "/work"
READONLY_DIR = "/sealed"
SERVICE_PORT = 18099

SERVICE_SOURCE = """
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
STORE = {}
SEALED = "sealed"
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b""):
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path == "/list":
            return self._send(200, json.dumps(sorted(STORE)).encode())
        name = self.path.lstrip("/")
        return self._send(200, STORE[name].encode()) if name in STORE else self._send(404)
    def do_PUT(self):
        name = self.path.lstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        if name.startswith(SEALED):
            # Accepts and reports success without storing, the way a real service can accept a
            # write it later discards. Self-report cannot detect this; a state read can.
            return self._send(204)
        STORE[name] = body
        self._send(204)
    def do_DELETE(self):
        STORE.pop(self.path.lstrip("/"), None)
        self._send(204)
    def log_message(self, *args):
        pass
HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
"""


class EnvironmentError_(RuntimeError):
    """Raised when a real environment cannot be created or reached."""


class NotRunnable(RuntimeError):
    """Raised when Docker is unavailable; the experiment is inconclusive, not negative."""


def _digest(salt: bytes, environment: str, index: int) -> bytes:
    return hashlib.sha256(
        salt + environment.encode("utf-8") + index.to_bytes(4, "big"),
    ).digest()


def _docker(*args: str, check: bool = True, timeout: float = 60.0) -> str:
    completed = subprocess.run(
        ["docker", *args], capture_output=True, timeout=timeout, check=False,
    )
    if check and completed.returncode != 0:
        raise EnvironmentError_(
            f"docker {' '.join(args[:2])} failed: {completed.stderr.decode('utf-8', 'replace')}"
        )
    return completed.stdout.decode("utf-8", "replace")


def docker_available() -> bool:
    try:
        _docker("info", "--format", "{{.ServerVersion}}", timeout=20.0)
    except (EnvironmentError_, OSError, subprocess.SubprocessError):
        return False
    return True


@dataclass(frozen=True)
class Action:
    kind: str
    name: str = ""
    content: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ACTIONS:
            raise EnvironmentError_(f"unknown action {self.kind!r}")


@dataclass(frozen=True)
class Task:
    environment: str
    index: int
    actions: tuple[Action, ...]
    expected: Mapping[str, str]
    targets_sealed: bool

    def commitment(self) -> str:
        payload = "|".join([
            self.environment, str(self.index),
            ";".join(f"{a.kind}:{a.name}:{a.content}" for a in self.actions),
            ",".join(f"{k}={v}" for k, v in sorted(self.expected.items())),
            f"sealed={self.targets_sealed}",
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_tasks(salt: bytes, environment: str) -> tuple[Task, ...]:
    """One task per index; the last one writes where the environment silently discards it."""

    tasks: list[Task] = []
    for index in range(TASKS_PER_ENVIRONMENT):
        digest = _digest(salt, environment, index)
        sealed = index == TASKS_PER_ENVIRONMENT - 1
        first = f"res{digest[0] % 90:02d}"
        second = f"res{digest[1] % 90 + 100:03d}"
        content = f"v{digest[2] % 1000:03d}"
        other = f"v{digest[3] % 1000:03d}"

        if sealed:
            name = "sealed-" + first
            actions = (Action("put", name, content),)
            # The task asks for the resource. The environment accepts the write and discards it,
            # so the claim says success and the state read says otherwise.
            expected: dict[str, str] = {name: content}
        elif index % 2 == 0:
            actions = (Action("put", first, content), Action("put", second, other))
            expected = {first: content, second: other}
        else:
            actions = (
                Action("put", first, content),
                Action("put", second, other),
                Action("remove", second),
            )
            expected = {first: content}
        tasks.append(Task(
            environment=environment, index=index, actions=actions,
            expected=expected, targets_sealed=sealed,
        ))
    return tuple(tasks)


def build_bank(salt: bytes) -> tuple[Task, ...]:
    bank = tuple(task for env in ENVIRONMENTS for task in build_tasks(salt, env))
    if len(bank) != TASKS_PER_ENVIRONMENT * len(ENVIRONMENTS):
        raise EnvironmentError_("materialized bank size drifted from the frozen protocol")
    return bank


class ShellEnvironment:
    """A POSIX shell inside a network-disabled Alpine container over a real filesystem."""

    kind = "shell"

    def __init__(self) -> None:
        self.container = _docker(
            "run", "-d", "--network", "none", "--read-only",
            "--tmpfs", f"{WORK_DIR}:rw,size=8m",
            ALPINE_IMAGE, "sleep", "300",
        ).strip()

    def apply(self, action: Action) -> bool:
        """Returns the action's own claim of success, which is never scored."""

        if action.kind == "put":
            target = (
                f"{READONLY_DIR}/{action.name}" if action.name.startswith("sealed-")
                else f"{WORK_DIR}/{action.name}"
            )
            # The trailing `true` swallows the failure, the way real deployment scripts do.
            script = f"printf '%s' '{action.content}' > '{target}' 2>/dev/null; true"
        elif action.kind == "remove":
            script = f"rm -f '{WORK_DIR}/{action.name}' 2>/dev/null; true"
        elif action.kind == "read":
            script = f"cat '{WORK_DIR}/{action.name}' 2>/dev/null; true"
        else:
            script = f"ls -1 '{WORK_DIR}' 2>/dev/null; true"
        completed = subprocess.run(
            ["docker", "exec", self.container, "sh", "-c", script],
            capture_output=True, timeout=60.0, check=False,
        )
        return completed.returncode == 0

    def state(self) -> dict[str, str]:
        """Independent read, executed fresh after the action sequence."""

        listing = _docker("exec", self.container, "sh", "-c", f"ls -1 {WORK_DIR} 2>/dev/null")
        names = [line.strip() for line in listing.splitlines() if line.strip()]
        return {
            name: _docker("exec", self.container, "sh", "-c", f"cat '{WORK_DIR}/{name}'")
            for name in names
        }

    def close(self) -> None:
        _docker("rm", "-f", self.container, check=False)


class ServiceEnvironment:
    """A real Python HTTP server process inside its own container, reached over a socket."""

    kind = "service"

    def __init__(self, port: int = SERVICE_PORT) -> None:
        self.port = port
        self.container = _docker(
            "run", "-d", "-p", f"127.0.0.1:{port}:8080",
            PYTHON_IMAGE, "python", "-c", SERVICE_SOURCE,
        ).strip()
        self._await_ready()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}/{path}"

    def _await_ready(self, attempts: int = 40) -> None:
        for _ in range(attempts):
            try:
                urllib.request.urlopen(self._url("list"), timeout=2).read()
                return
            except (urllib.error.URLError, OSError):
                time.sleep(0.25)
        raise EnvironmentError_("the service container never became reachable")

    def apply(self, action: Action) -> bool:
        try:
            if action.kind == "put":
                request = urllib.request.Request(
                    self._url(action.name), data=action.content.encode("utf-8"), method="PUT",
                )
            elif action.kind == "remove":
                request = urllib.request.Request(self._url(action.name), method="DELETE")
            elif action.kind == "read":
                request = urllib.request.Request(self._url(action.name), method="GET")
            else:
                request = urllib.request.Request(self._url("list"), method="GET")
            with urllib.request.urlopen(request, timeout=10) as response:
                return 200 <= response.status < 300
        except urllib.error.HTTPError as error:
            return 200 <= error.code < 300
        except (urllib.error.URLError, OSError) as error:
            raise EnvironmentError_(f"service unreachable: {error}") from error

    def state(self) -> dict[str, str]:
        with urllib.request.urlopen(self._url("list"), timeout=10) as response:
            names = json.loads(response.read().decode("utf-8"))
        found: dict[str, str] = {}
        for name in names:
            with urllib.request.urlopen(self._url(name), timeout=10) as response:
                found[name] = response.read().decode("utf-8")
        return found

    def close(self) -> None:
        _docker("rm", "-f", self.container, check=False)


def open_environment(kind: str):
    if kind == "shell":
        return ShellEnvironment()
    if kind == "service":
        return ServiceEnvironment()
    raise EnvironmentError_(f"unknown environment {kind!r}")


class Agent:
    """One unchanged agent. It emits abstract actions and never learns which environment it is in."""

    def perform(self, task: Task, environment) -> bool:
        claimed = True
        for action in task.actions:
            claimed = environment.apply(action) and claimed
        return claimed


def run_arm(bank: Sequence[Task], arm: str) -> dict[str, object]:
    if arm not in ARMS:
        raise EnvironmentError_(f"unknown arm {arm!r}")
    if not docker_available():
        raise NotRunnable("Docker is unavailable; M081 is inconclusive rather than negative")

    agent = Agent()
    records: list[dict[str, object]] = []

    for kind in ENVIRONMENTS:
        crossed = arm == "crossed_drivers"
        driver_kind = ("service" if kind == "shell" else "shell") if crossed else kind
        environment = open_environment(kind)
        driver = open_environment(driver_kind) if crossed else environment
        try:
            for task in (t for t in bank if t.environment == kind):
                before = environment.state()
                try:
                    claimed = agent.perform(task, driver)
                except EnvironmentError_:
                    claimed = False
                observed = environment.state()
                reached = all(
                    observed.get(name) == value for name, value in task.expected.items()
                )
                records.append({
                    "environment": kind,
                    "driver": driver_kind,
                    "index": task.index,
                    "commitment": task.commitment(),
                    "claimed": claimed,
                    "state_reached": reached,
                    "targets_sealed": task.targets_sealed,
                    "state_changed": observed != before,
                })
        finally:
            if driver is not environment:
                driver.close()
            environment.close()

    scored_key = "claimed" if arm == "self_report_scored" else "state_reached"
    return {
        "arm": arm,
        "scored_from": "agent_claim" if arm == "self_report_scored" else "environment_state",
        "completed_per_environment": {
            kind: sum(
                1 for r in records if r["environment"] == kind and r[scored_key]
            )
            for kind in ENVIRONMENTS
        },
        "completed_total": sum(1 for r in records if r[scored_key]),
        "state_reached_total": sum(1 for r in records if r["state_reached"]),
        "claimed_total": sum(1 for r in records if r["claimed"]),
        "overcount": sum(
            1 for r in records if r["claimed"] and not r["state_reached"]
        ),
        "environments_covered": len({r["environment"] for r in records if r[scored_key]}),
        "records": records,
    }


@dataclass(frozen=True)
class EnvironmentVerdict:
    positive: bool
    reasons: tuple[str, ...] = ()


def evaluate(arms: Mapping[str, Mapping[str, object]]) -> EnvironmentVerdict:
    reasons: list[str] = []
    main = arms["shared_interface"]
    completed = main["completed_per_environment"]
    assert isinstance(completed, dict)

    completable = TASKS_PER_ENVIRONMENT - 1
    for kind in ENVIRONMENTS:
        if completed[kind] != completable:
            reasons.append(
                f"shared interface completed {completed[kind]}/{completable} completable "
                f"tasks in the {kind} environment"
            )
    if main["environments_covered"] != len(ENVIRONMENTS):
        reasons.append("the shared interface did not cover both environments")

    # Amendment A1: the sealed task must be seen to fail under environment-state scoring while
    # the agent claims it succeeded. Counting it as an ordinary success would hide the divergence
    # the whole self-report clause exists to expose.
    records = main["records"]
    assert isinstance(records, list)
    for record in records:
        if not record["targets_sealed"]:
            continue
        if record["state_reached"]:
            reasons.append(
                f"the sealed task in the {record['environment']} environment completed, so the "
                "environment did not actually discard the write"
            )
        if not record["claimed"]:
            reasons.append(
                f"the sealed task in the {record['environment']} environment reported failure, so "
                "self-report and state agree and the scoring rule is untested there"
            )

    if arms["crossed_drivers"]["completed_total"] != 0:
        reasons.append(
            f"crossed_drivers completed {arms['crossed_drivers']['completed_total']} tasks, so "
            "the two environments are not genuinely distinct"
        )
    if arms["self_report_scored"]["overcount"] < len(ENVIRONMENTS):
        reasons.append(
            "self_report_scored never diverged from environment state, so the scoring rule is "
            "untested"
        )

    return EnvironmentVerdict(positive=not reasons, reasons=tuple(reasons))
