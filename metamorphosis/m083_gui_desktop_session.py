"""A GUI desktop session as a fourth environment under the unchanged M081 interface.

The shell is addressed by filesystem paths, the service by HTTP routes, the browser by DOM
selectors. This environment is addressed only by screen coordinates, and its state is legible only
as rendered pixels: a real X server, a real window manager and a real GUI application in an offline
container, clicked at coordinates and read back by decoding exact palette colours from a screenshot.

This is **not** a virtual machine. A container shares the host kernel, and no hypervisor is available
here. G6's desktop-VM clause remains unmet; see PROTOCOL.md.

Nothing here models the window layout. The client-area origin is discovered at run time from the X
server, because the window manager places the window where it chooses and a hard-coded origin
silently addresses the wrong cells.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m081_two_real_environments import (
    Action,
    Agent,
    EnvironmentError_,
    ServiceEnvironment,
    ShellEnvironment,
    Task,
)
from metamorphosis.m082_browser_environment import BrowserEnvironment


PROTOCOL_SCHEMA = "m083-gui-desktop-session-protocol-v1"
GENERATOR_VERSION = 1

DESKTOP_IMAGE = "mira-m083-desktop:1"
ENVIRONMENTS = ("shell", "service", "browser", "desktop")
ARMS = ("shared_interface", "crossed_drivers", "self_report_scored")

CELL = 40
COLUMNS = 6
ROWS = 4
SWATCH = 40
DISPLAY = ":99"
SCREEN = "320x280x24"

PALETTE = {"cyan": "#00c8ff", "magenta": "#ff00c8", "lime": "#c8ff00"}
PALETTE_ORDER = ("cyan", "magenta", "lime")
EMPTY_COLOUR = "#101010"
LOCKED_CELL = (3, 5)

TASKS_PER_ENVIRONMENT = 6

APPLICATION_SOURCE = f"""
import tkinter as tk
CELL, COLUMNS, ROWS, SWATCH = {CELL}, {COLUMNS}, {ROWS}, {SWATCH}
PALETTE = {json.dumps(PALETTE)}
ORDER = {json.dumps(list(PALETTE_ORDER))}
LOCKED = tuple({json.dumps(list(LOCKED_CELL))})
state, selected = {{}}, [ORDER[0]]
root = tk.Tk()
root.geometry(f"{{COLUMNS*CELL}}x{{ROWS*CELL+SWATCH}}")
root.title("store")
grid = tk.Canvas(root, width=COLUMNS*CELL, height=ROWS*CELL,
                 highlightthickness=0, bg="{EMPTY_COLOUR}")
grid.pack()
bar = tk.Canvas(root, width=COLUMNS*CELL, height=SWATCH,
                highlightthickness=0, bg="{EMPTY_COLOUR}")
bar.pack()

def render():
    grid.delete("all")
    for (r, c), name in state.items():
        grid.create_rectangle(c*CELL, r*CELL, (c+1)*CELL, (r+1)*CELL,
                              fill=PALETTE[name], outline="")
    bar.delete("all")
    for index, name in enumerate(ORDER):
        bar.create_rectangle(index*SWATCH, 0, (index+1)*SWATCH, SWATCH,
                             fill=PALETTE[name], outline="")

def paint(event):
    cell = (event.y // CELL, event.x // CELL)
    if not (0 <= cell[0] < ROWS and 0 <= cell[1] < COLUMNS):
        return
    # The locked cell accepts the click and reports nothing wrong, but never changes. Only the
    # rendered pixels tell the truth.
    if cell != LOCKED:
        state[cell] = selected[0]
    render()

def pick(event):
    index = event.x // SWATCH
    if index < len(ORDER):
        selected[0] = ORDER[index]

grid.bind("<Button-1>", paint)
bar.bind("<Button-1>", pick)
render()
root.mainloop()
"""

_ABSOLUTE_X = re.compile(r"Absolute upper-left X:\s+(-?\d+)")
_ABSOLUTE_Y = re.compile(r"Absolute upper-left Y:\s+(-?\d+)")


def cell_label(row: int, column: int) -> str:
    return f"r{row}c{column}"


def parse_cell(label: str) -> tuple[int, int]:
    match = re.fullmatch(r"r(\d+)c(\d+)", label)
    if match is None:
        raise EnvironmentError_(f"{label!r} is not a cell label")
    return int(match.group(1)), int(match.group(2))


def image_present() -> bool:
    completed = subprocess.run(
        ["docker", "image", "inspect", DESKTOP_IMAGE],
        capture_output=True, timeout=30.0, check=False,
    )
    return completed.returncode == 0


def runnable() -> bool:
    docker = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        capture_output=True, timeout=20.0, check=False,
    )
    return docker.returncode == 0 and image_present()


class DesktopEnvironment:
    """A real X11 session. Acts by clicking coordinates, observes by decoding rendered pixels."""

    kind = "desktop"

    def __init__(self) -> None:
        if not image_present():
            raise EnvironmentError_(
                f"{DESKTOP_IMAGE} is absent; build it from experiments/M083/desktop-image"
            )
        self.container = self._docker(
            "run", "-d", "--network", "none", DESKTOP_IMAGE, "sleep", "900",
        ).strip()
        self._install_application()
        self._start_session()
        self.origin = self._discover_origin()

    @staticmethod
    def _docker(*args: str, timeout: float = 120.0) -> str:
        completed = subprocess.run(
            ["docker", *args], capture_output=True, timeout=timeout, check=False,
        )
        if completed.returncode != 0:
            raise EnvironmentError_(
                f"docker {args[0]} failed: {completed.stderr.decode('utf-8', 'replace')[:400]}"
            )
        return completed.stdout.decode("utf-8", "replace")

    def _shell(self, script: str, timeout: float = 120.0) -> str:
        # Always through `sh -c`. A bare /agent/... argument is rewritten by MSYS path conversion
        # on Windows, the defect class that produced the negative M070.
        completed = subprocess.run(
            ["docker", "exec", self.container, "sh", "-c", script],
            capture_output=True, timeout=timeout, check=False,
        )
        if completed.returncode != 0:
            raise EnvironmentError_(
                f"desktop command failed: {completed.stderr.decode('utf-8', 'replace')[:400]}"
            )
        return completed.stdout.decode("utf-8", "replace")

    def _install_application(self) -> None:
        completed = subprocess.run(
            ["docker", "exec", "-i", self.container, "sh", "-c", "cat > /agent/app.py"],
            input=APPLICATION_SOURCE.encode("utf-8"),
            capture_output=True, timeout=60.0, check=False,
        )
        if completed.returncode != 0:
            raise EnvironmentError_("could not install the desktop application")

    def _start_session(self) -> None:
        subprocess.run(
            [
                "docker", "exec", "-d", self.container, "sh", "-c",
                f"Xvfb {DISPLAY} -screen 0 {SCREEN} & sleep 2; "
                f"DISPLAY={DISPLAY} openbox & sleep 1; "
                f"DISPLAY={DISPLAY} python /agent/app.py",
            ],
            capture_output=True, timeout=60.0, check=False,
        )

    def _discover_origin(self, attempts: int = 30) -> tuple[int, int]:
        """Ask the X server where the window manager put the client area."""

        for _ in range(attempts):
            try:
                window = self._shell(
                    f"DISPLAY={DISPLAY} xdotool search --name store | head -1"
                ).strip()
                if window:
                    info = self._shell(f"DISPLAY={DISPLAY} xwininfo -id {window}")
                    x = _ABSOLUTE_X.search(info)
                    y = _ABSOLUTE_Y.search(info)
                    if x and y:
                        return int(x.group(1)), int(y.group(1))
            except EnvironmentError_:
                pass
            time.sleep(1.0)
        raise EnvironmentError_("the desktop session never presented its window")

    def _click(self, x: int, y: int) -> None:
        origin_x, origin_y = self.origin
        self._shell(
            f"DISPLAY={DISPLAY} xdotool mousemove {origin_x + x} {origin_y + y} click 1"
        )
        time.sleep(0.4)

    def _screenshot_colour(self, x: int, y: int) -> str:
        origin_x, origin_y = self.origin
        raw = self._shell(
            f"DISPLAY={DISPLAY} import -window root /tmp/screen.png && "
            f"convert /tmp/screen.png -format '%[hex:p{{{origin_x + x},{origin_y + y}}}]' info:"
        )
        return "#" + raw.strip().lower()[:6]

    def apply(self, action: Action) -> bool:
        """Returns the application's acceptance of the click, which is never scored."""

        if action.kind in ("read", "list"):
            return True
        try:
            row, column = parse_cell(action.name)
        except EnvironmentError_:
            return False
        if action.kind == "remove":
            # Removal is not expressible with a palette of solid colours; the grid has no eraser,
            # so the interface reports the action as unsupported here rather than pretending.
            return False
        if action.content not in PALETTE:
            return False
        swatch = PALETTE_ORDER.index(action.content)
        self._click(swatch * SWATCH + SWATCH // 2, ROWS * CELL + SWATCH // 2)
        self._click(column * CELL + CELL // 2, row * CELL + CELL // 2)
        return True

    def colour_at(self, label: str) -> str | None:
        """Decode one cell from a fresh screenshot; None when it carries no palette colour.

        Added for M084, which observes far more often than M083 did: reading the whole grid costs
        about 8.9 seconds against 0.3 for a single cell. `state` is unchanged and still decodes
        every cell, so the M083 result is untouched.
        """

        row, column = parse_cell(label)
        if not (0 <= row < ROWS and 0 <= column < COLUMNS):
            raise EnvironmentError_(f"{label!r} is outside the rendered grid")
        colour = self._screenshot_colour(column * CELL + CELL // 2, row * CELL + CELL // 2)
        inverse = {value: name for name, value in PALETTE.items()}
        return inverse.get(colour)

    def state(self) -> dict[str, str]:
        """Independent read: decode exact palette colours from a fresh screenshot."""

        inverse = {value: name for name, value in PALETTE.items()}
        observed: dict[str, str] = {}
        for row in range(ROWS):
            for column in range(COLUMNS):
                colour = self._screenshot_colour(
                    column * CELL + CELL // 2, row * CELL + CELL // 2,
                )
                if colour in inverse:
                    observed[cell_label(row, column)] = inverse[colour]
        return observed

    def close(self) -> None:
        subprocess.run(
            ["docker", "rm", "-f", self.container],
            capture_output=True, timeout=60.0, check=False,
        )


def build_desktop_tasks(salt: bytes) -> tuple[Task, ...]:
    """Grid-native resources with the same task shapes M081 uses. One task targets the locked cell."""

    tasks: list[Task] = []
    used: set[tuple[int, int]] = {LOCKED_CELL}
    for index in range(TASKS_PER_ENVIRONMENT):
        digest = hashlib.sha256(
            salt + b"desktop" + index.to_bytes(4, "big"),
        ).digest()
        locked = index == TASKS_PER_ENVIRONMENT - 1
        if locked:
            name = cell_label(*LOCKED_CELL)
            colour = PALETTE_ORDER[digest[0] % len(PALETTE_ORDER)]
            actions = (Action("put", name, colour),)
            expected = {name: colour}
        else:
            cells: list[tuple[int, int]] = []
            cursor = 0
            while len(cells) < 2:
                candidate = (digest[cursor] % ROWS, digest[cursor + 1] % COLUMNS)
                cursor += 2
                if candidate not in used and candidate not in cells:
                    cells.append(candidate)
                if cursor + 1 >= len(digest):
                    digest = hashlib.sha256(digest).digest()
                    cursor = 0
            used.update(cells)
            first, second = cells
            colour_a = PALETTE_ORDER[digest[2] % len(PALETTE_ORDER)]
            colour_b = PALETTE_ORDER[digest[3] % len(PALETTE_ORDER)]
            actions = (
                Action("put", cell_label(*first), colour_a),
                Action("put", cell_label(*second), colour_b),
            )
            expected = {
                cell_label(*first): colour_a,
                cell_label(*second): colour_b,
            }
        tasks.append(Task(
            environment="desktop", index=index, actions=actions,
            expected=expected, targets_sealed=locked,
        ))
    return tuple(tasks)


def open_environment(kind: str):
    if kind == "shell":
        return ShellEnvironment()
    if kind == "service":
        return ServiceEnvironment()
    if kind == "browser":
        return BrowserEnvironment()
    if kind == "desktop":
        return DesktopEnvironment()
    raise EnvironmentError_(f"unknown environment {kind!r}")


def run_desktop_arm(bank: Sequence[Task], arm: str) -> dict[str, object]:
    """Runs the desktop tasks. Crossed drivers use the browser, which has no access to pixels."""

    if arm not in ARMS:
        raise EnvironmentError_(f"unknown arm {arm!r}")
    if not runnable():
        raise EnvironmentError_("Docker or the desktop image is unavailable")

    agent = Agent()
    crossed = arm == "crossed_drivers"
    environment = open_environment("desktop")
    driver = open_environment("browser") if crossed else environment
    records: list[dict[str, object]] = []
    try:
        for task in bank:
            try:
                claimed = agent.perform(task, driver)
            except EnvironmentError_:
                claimed = False
            observed = environment.state()
            reached = all(
                observed.get(name) == value for name, value in task.expected.items()
            )
            records.append({
                "environment": "desktop",
                "driver": "browser" if crossed else "desktop",
                "index": task.index,
                "commitment": task.commitment(),
                "claimed": claimed,
                "state_reached": reached,
                "targets_locked_cell": task.targets_sealed,
            })
    finally:
        if driver is not environment:
            driver.close()
        environment.close()

    scored = "claimed" if arm == "self_report_scored" else "state_reached"
    return {
        "arm": arm,
        "scored_from": "agent_claim" if arm == "self_report_scored" else "environment_state",
        "completed": sum(1 for r in records if r[scored]),
        "state_reached_total": sum(1 for r in records if r["state_reached"]),
        "claimed_total": sum(1 for r in records if r["claimed"]),
        "overcount": sum(1 for r in records if r["claimed"] and not r["state_reached"]),
        "records": records,
    }


@dataclass(frozen=True)
class DesktopVerdict:
    positive: bool
    reasons: tuple[str, ...] = ()


def evaluate(arms: Mapping[str, Mapping[str, object]]) -> DesktopVerdict:
    reasons: list[str] = []
    main = arms["shared_interface"]
    completable = TASKS_PER_ENVIRONMENT - 1

    if main["completed"] != completable:
        reasons.append(
            f"the interface completed {main['completed']}/{completable} completable desktop tasks"
        )
    for record in main["records"]:
        if record["targets_locked_cell"]:
            if record["state_reached"]:
                reasons.append("the locked cell changed, so the application did not lock it")
            if not record["claimed"]:
                reasons.append(
                    "the locked cell reported failure, so the click and the pixels agree and the "
                    "scoring rule is untested"
                )
    if arms["crossed_drivers"]["completed"] != 0:
        reasons.append(
            f"crossed_drivers completed {arms['crossed_drivers']['completed']} tasks, so the "
            "rendered grid is reachable without the screen"
        )
    if arms["self_report_scored"]["overcount"] < 1:
        reasons.append(
            "the self-report arm never diverged, so the application's acceptance was honest and "
            "the scoring rule is untested"
        )

    return DesktopVerdict(positive=not reasons, reasons=tuple(reasons))
