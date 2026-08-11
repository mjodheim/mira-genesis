"""A real browser as a third environment under the unchanged M081 interface.

M081 drove a container shell and an HTTP service with four abstract actions. This module adds a real
Chromium browser, running offline in a container, driven through the same vocabulary.

The page exposes no HTTP API for its store. State lives in localStorage and the driver reaches it
only by filling inputs, clicking and reading rendered DOM nodes, so an HTTP client cannot touch it.
That is what stops this from being the M081 service in a costume, and the crossed-driver arm
demonstrates it rather than asserting it.

M081's agent, shell environment and service environment are imported unchanged. A three-environment
claim means the same interface object drives all three; re-implementing it here would let it quietly
diverge.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m081_two_real_environments import (
    Action,
    Agent,
    EnvironmentError_,
    ServiceEnvironment,
    ShellEnvironment,
    Task,
    TASKS_PER_ENVIRONMENT,
    build_tasks,
    docker_available,
)


PROTOCOL_SCHEMA = "m082-browser-environment-protocol-v1"
GENERATOR_VERSION = 1

BROWSER_IMAGE = "mira-m082-browser:1"
BROWSER_BASE_DIGEST = (
    "mcr.microsoft.com/playwright@sha256:"
    "98b1ad488de36b22d41fdd1b0c5b9cceaa78a8d2661c6ab02d2108a07c182338"
)

ENVIRONMENTS = ("shell", "service", "browser")
ARMS = ("shared_interface", "crossed_drivers", "self_report_scored")

# The store lives only here. There is no HTTP route that reads or writes it.
PAGE_SOURCE = """<!doctype html><meta charset="utf-8"><title>store</title>
<input id="name"><input id="value"><button id="save">save</button>
<button id="drop">drop</button><ul id="items"></ul><div id="status"></div>
<script>
const KEY = 'm082';
const load = () => JSON.parse(localStorage.getItem(KEY) || '{}');
const render = () => {
  const store = load();
  document.getElementById('items').innerHTML = Object.keys(store).sort()
    .map(n => '<li data-name="' + n + '" data-value="' + store[n] + '">' + n + '</li>').join('');
};
document.getElementById('save').onclick = () => {
  const name = document.getElementById('name').value;
  const value = document.getElementById('value').value;
  const store = load();
  // Sealed names are validated, confirmed to the user, and then not persisted. A real page can
  // report a save it later declines; only the rendered list tells the truth.
  if (!name.startsWith('sealed-')) { store[name] = value; localStorage.setItem(KEY, JSON.stringify(store)); }
  render();
  document.getElementById('status').textContent = 'saved';
};
document.getElementById('drop').onclick = () => {
  const name = document.getElementById('name').value;
  const store = load();
  delete store[name];
  localStorage.setItem(KEY, JSON.stringify(store));
  render();
  document.getElementById('status').textContent = 'dropped';
};
window.onload = render;
</script>
"""

DRIVER_SOURCE = """
import http from 'http';
import fs from 'fs';
import { chromium } from 'playwright';
// Read from disk rather than an environment variable. Passing the page through the environment
// meant flattening it to one line, which turned a `//` comment into a comment over the whole
// script and silently disabled the save handler.
const PAGE = fs.readFileSync('/agent/page.html', 'utf8');
const server = http.createServer((_, res) => {
  res.writeHead(200, {'Content-Type': 'text/html; charset=utf-8'});
  res.end(PAGE);
});
await new Promise(resolve => server.listen(9911, '127.0.0.1', resolve));
// A persistent profile so localStorage survives between actions. Without it every action would
// meet a blank browser and the harness would have to hold the state itself, which would empty the
// claim that the browser is the environment.
const context = await chromium.launchPersistentContext('/agent/profile', {});
const page = context.pages()[0] || await context.newPage();
await page.goto('http://127.0.0.1:9911/');

const command = JSON.parse(process.env.M082_COMMAND);
let claimed = true;
try {
  if (command.kind === 'put') {
    await page.fill('#name', command.name);
    await page.fill('#value', command.content);
    await page.click('#save');
    await page.waitForFunction(() => document.getElementById('status').textContent !== '');
    claimed = (await page.textContent('#status')) === 'saved';
  } else if (command.kind === 'remove') {
    await page.fill('#name', command.name);
    await page.click('#drop');
    await page.waitForFunction(() => document.getElementById('status').textContent !== '');
    claimed = true;
  }
} catch (error) {
  claimed = false;
}

// State is read from the rendered list, never from localStorage directly.
const state = Object.fromEntries(await page.$$eval('li',
  nodes => nodes.map(n => [n.dataset.name, n.dataset.value])));
console.log(JSON.stringify({claimed, state}));
await context.close();
server.close();
"""


class BrowserEnvironment:
    """Real Chromium in an offline container. State lives in localStorage and is read from the DOM.

    Each action runs a fresh page load against a persisted profile directory, so state survives
    between actions exactly as browser state does.
    """

    kind = "browser"

    def __init__(self) -> None:
        if not image_present():
            raise EnvironmentError_(
                f"{BROWSER_IMAGE} is absent; build it from experiments/M082/browser-image"
            )
        self.container = self._run(
            "run", "-d", "--network", "none", BROWSER_IMAGE, "sleep", "900",
        ).strip()
        self._install_driver()

    @staticmethod
    def _run(*args: str, timeout: float = 180.0) -> str:
        completed = subprocess.run(
            ["docker", *args], capture_output=True, timeout=timeout, check=False,
        )
        if completed.returncode != 0:
            raise EnvironmentError_(
                f"docker {args[0]} failed: {completed.stderr.decode('utf-8', 'replace')[:400]}"
            )
        return completed.stdout.decode("utf-8", "replace")

    def _exec(self, script: str, environment: Mapping[str, str]) -> str:
        # Every argument is wrapped in `sh -c`. A bare /agent/... argument is rewritten by MSYS
        # path conversion on Windows, which is the defect class that produced the negative M070.
        arguments = ["docker", "exec"]
        for key, value in environment.items():
            arguments += ["-e", f"{key}={value}"]
        arguments += [self.container, "sh", "-c", script]
        completed = subprocess.run(
            arguments, capture_output=True, timeout=180.0, check=False,
        )
        if completed.returncode != 0:
            raise EnvironmentError_(
                "browser driver failed: "
                f"{completed.stderr.decode('utf-8', 'replace')[:400]}"
            )
        return completed.stdout.decode("utf-8", "replace")

    def _install_driver(self) -> None:
        for path, source in (
            ("/agent/driver.mjs", DRIVER_SOURCE),
            ("/agent/page.html", PAGE_SOURCE),
        ):
            completed = subprocess.run(
                ["docker", "exec", "-i", self.container, "sh", "-c", f"cat > {path}"],
                input=source.encode("utf-8"), capture_output=True, timeout=60.0, check=False,
            )
            if completed.returncode != 0:
                raise EnvironmentError_(f"could not install {path}")

    def _drive(self, command: Mapping[str, str]) -> tuple[bool, dict[str, str]]:
        payload = self._exec(
            "cd /agent && node driver.mjs",
            {
                "M082_PAGE": PAGE_SOURCE.replace("\n", " "),
                "M082_COMMAND": json.dumps(command, separators=(",", ":")),
            },
        )
        line = payload.strip().splitlines()[-1]
        parsed = json.loads(line)
        return bool(parsed["claimed"]), dict(parsed["state"])

    def apply(self, action: Action) -> bool:
        """Returns the page's own confirmation, which is never scored."""

        if action.kind in ("read", "list"):
            self._drive({"kind": "list"})
            return True
        claimed, _ = self._drive({
            "kind": action.kind, "name": action.name, "content": action.content,
        })
        return claimed

    def state(self) -> dict[str, str]:
        """Independent read from the rendered list. The browser holds the state, not the harness."""

        _, observed = self._drive({"kind": "list"})
        return observed

    def close(self) -> None:
        subprocess.run(
            ["docker", "rm", "-f", self.container],
            capture_output=True, timeout=60.0, check=False,
        )


def image_present() -> bool:
    completed = subprocess.run(
        ["docker", "image", "inspect", BROWSER_IMAGE],
        capture_output=True, timeout=30.0, check=False,
    )
    return completed.returncode == 0


def runnable() -> bool:
    return docker_available() and image_present()


def open_environment(kind: str):
    if kind == "shell":
        return ShellEnvironment()
    if kind == "service":
        return ServiceEnvironment()
    if kind == "browser":
        return BrowserEnvironment()
    raise EnvironmentError_(f"unknown environment {kind!r}")


def build_bank(salt: bytes) -> tuple[Task, ...]:
    """Reuses M081's generator so the three environments receive comparable work."""

    bank = tuple(task for env in ENVIRONMENTS for task in build_tasks(salt, env))
    if len(bank) != TASKS_PER_ENVIRONMENT * len(ENVIRONMENTS):
        raise EnvironmentError_("materialized bank size drifted from the frozen protocol")
    return bank


def run_arm(bank: Sequence[Task], arm: str) -> dict[str, object]:
    if arm not in ARMS:
        raise EnvironmentError_(f"unknown arm {arm!r}")
    if not runnable():
        raise EnvironmentError_("Docker or the browser image is unavailable")

    agent = Agent()
    records: list[dict[str, object]] = []
    crossing = {"shell": "service", "service": "browser", "browser": "service"}

    for kind in ENVIRONMENTS:
        crossed = arm == "crossed_drivers"
        driver_kind = crossing[kind] if crossed else kind
        environment = open_environment(kind)
        driver = open_environment(driver_kind) if crossed else environment
        try:
            for task in (t for t in bank if t.environment == kind):
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
                })
        finally:
            if driver is not environment:
                driver.close()
            environment.close()

    scored = "claimed" if arm == "self_report_scored" else "state_reached"
    return {
        "arm": arm,
        "scored_from": "agent_claim" if arm == "self_report_scored" else "environment_state",
        "completed_per_environment": {
            kind: sum(1 for r in records if r["environment"] == kind and r[scored])
            for kind in ENVIRONMENTS
        },
        "completed_total": sum(1 for r in records if r[scored]),
        "environments_covered": len({r["environment"] for r in records if r[scored]}),
        "browser_overcount": sum(
            1 for r in records
            if r["environment"] == "browser" and r["claimed"] and not r["state_reached"]
        ),
        "records": records,
    }


@dataclass(frozen=True)
class BrowserVerdict:
    positive: bool
    reasons: tuple[str, ...] = ()


def evaluate(arms: Mapping[str, Mapping[str, object]]) -> BrowserVerdict:
    reasons: list[str] = []
    main = arms["shared_interface"]
    completed = main["completed_per_environment"]
    assert isinstance(completed, dict)
    completable = TASKS_PER_ENVIRONMENT - 1

    if completed["browser"] != completable:
        reasons.append(
            f"the interface completed {completed['browser']}/{completable} completable browser tasks"
        )
    if main["environments_covered"] != len(ENVIRONMENTS):
        reasons.append("the interface did not cover all three environments")
    for record in main["records"]:
        if record["environment"] == "browser" and record["targets_sealed"]:
            if record["state_reached"]:
                reasons.append("the sealed browser task persisted, so the page did not discard it")
            if not record["claimed"]:
                reasons.append(
                    "the sealed browser task reported failure, so the confirmation and the DOM "
                    "agree and the scoring rule is untested"
                )

    if arms["crossed_drivers"]["completed_total"] != 0:
        reasons.append(
            f"crossed_drivers completed {arms['crossed_drivers']['completed_total']} tasks, so the "
            "browser store is reachable without the DOM"
        )
    if arms["self_report_scored"]["browser_overcount"] < 1:
        reasons.append(
            "the self-report arm never diverged in the browser, so the page confirmation was honest "
            "and the scoring rule is untested there"
        )

    return BrowserVerdict(positive=not reasons, reasons=tuple(reasons))
