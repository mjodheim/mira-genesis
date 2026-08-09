from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Mapping, Sequence

import pytest

from mira_core import (
    Action, Authority, CommandSpec, Goal, GovernedTerminalBody, MiraAgent, Observation,
    SafetyPolicy, TerminalBodyError, TerminalLimits,
)
from mira_core.contracts import JsonValue


READ = (Authority.FILESYSTEM_READ.value,)
WRITE = (Authority.FILESYSTEM_WRITE.value,)
RUN = (Authority.COMPUTE.value, Authority.FILESYSTEM_READ.value)
TERMINAL_SAFETY = SafetyPolicy.from_authorities({
    Authority.COMPUTE, Authority.FILESYSTEM_READ, Authority.FILESYSTEM_WRITE,
})


class ScriptedPolicy:
    policy_id = "scripted-terminal-policy"

    def __init__(self, actions: Sequence[Action]) -> None:
        self.actions = tuple(actions)
        self.index = 0

    def propose(
        self, goal: Goal, observation: Observation, history: Sequence[Mapping[str, JsonValue]],
    ) -> Action | None:
        if self.index >= len(self.actions):
            return None
        action = self.actions[self.index]
        self.index += 1
        return action


def _command_script(root: Path, name: str, source: str) -> str:
    path = root / name
    path.write_text(source, encoding="utf-8")
    return name


def test_real_workspace_episode_reads_writes_and_passes_evaluator(tmp_path: Path) -> None:
    (tmp_path / "answer.txt").write_text("wrong\n", encoding="utf-8")
    script = _command_script(
        tmp_path, "verify.py",
        "from pathlib import Path\nraise SystemExit(0 if Path('answer.txt').read_text() == 'correct\\n' else 7)\n",
    )
    body = GovernedTerminalBody("terminal-fixture", tmp_path, (
        CommandSpec("verify", (sys.executable, "-I", script), terminal_on_success=True),
    ))
    policy = ScriptedPolicy((
        Action("read", "read_text", {"path": "answer.txt"}, READ),
        Action("write", "write_text", {"path": "answer.txt", "content": "correct\n"}, WRITE),
        Action("verify", "run_command", {"command_id": "verify"}, RUN),
    ))
    agent = MiraAgent(policy, body, safety=TERMINAL_SAFETY, max_steps=4)
    result = agent.run(Goal("repair-answer", "make the governed verifier pass"))
    assert result.succeeded is True
    assert result.steps == 3
    assert (tmp_path / "answer.txt").read_text(encoding="utf-8") == "correct\n"
    assert result.final_observation.state["command_id"] == "verify"
    assert result.final_observation.state["returncode"] == 0
    assert result.final_observation.state["output"] == ""
    agent.memory.verify()


def test_terminal_authorities_are_enforced_by_body_and_safety(tmp_path: Path) -> None:
    (tmp_path / "value.txt").write_text("value", encoding="utf-8")
    read = Action("read", "read_text", {"path": "value.txt"}, READ)
    body = GovernedTerminalBody("authority-terminal", tmp_path)
    assert MiraAgent(ScriptedPolicy((read,)), body).run(
        Goal("default-denial", "attempt a filesystem read")
    ).status == "safety_refused"

    underdeclared = Action("read", "read_text", {"path": "value.txt"})
    body = GovernedTerminalBody("underdeclared-terminal", tmp_path)
    result = MiraAgent(
        ScriptedPolicy((underdeclared,)), body, safety=TERMINAL_SAFETY,
    ).run(Goal("underdeclared", "attempt an underdeclared filesystem read"))
    assert result.status == "action_contract_refused"
    assert result.steps == 0


def test_paths_cannot_escape_workspace_and_writes_are_bounded(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("preserved", encoding="utf-8")
    body = GovernedTerminalBody(
        "contained-terminal", workspace, limits=TerminalLimits(max_write_bytes=4),
    )
    body.reset(Goal("containment", "remain inside the workspace"))
    with pytest.raises(TerminalBodyError, match="relative"):
        body.act(Action("escape", "write_text", {"path": "../outside.txt", "content": "bad"}, WRITE))
    with pytest.raises(TerminalBodyError, match="write size"):
        body.act(Action("large", "write_text", {"path": "large.txt", "content": "12345"}, WRITE))
    assert outside.read_text(encoding="utf-8") == "preserved"
    assert list(workspace.iterdir()) == []


def test_policy_cannot_supply_process_arguments_or_unknown_commands(tmp_path: Path) -> None:
    body = GovernedTerminalBody("immutable-command-terminal", tmp_path, (
        CommandSpec("known", (sys.executable, "-I", "-c", "print('known')")),
    ))
    body.reset(Goal("immutable-command", "use only registered commands"))
    with pytest.raises(TerminalBodyError, match="policy-supplied arguments"):
        body.required_authorities(Action(
            "known", "run_command", {"command_id": "known", "args": ["untrusted"]}, RUN,
        ))
    assert body.required_authorities(Action(
        "known", "run_command", {"command_id": "known"}, RUN,
    )) == RUN
    with pytest.raises(TerminalBodyError, match="unknown"):
        body.required_authorities(Action("unknown", "run_command", {"command_id": "other"}, RUN))


def test_child_environment_is_minimal_and_hidden_output_can_stay_hidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MIRA_PARENT_SECRET", "must-not-cross")
    visible = CommandSpec(
        "visible", (sys.executable, "-I", "-c", "import os;print(os.getenv('MIRA_PARENT_SECRET','absent'))"),
    )
    hidden = CommandSpec(
        "hidden", (sys.executable, "-I", "-c", "print('private evaluator detail')"),
        terminal_on_success=True, expose_output=False,
    )
    body = GovernedTerminalBody("environment-terminal", tmp_path, (visible, hidden))
    body.reset(Goal("environment", "do not inherit ambient secrets"))
    observed = body.act(Action("visible", "run_command", {"command_id": "visible"}, RUN))
    assert observed.state["output"] == "absent\n"
    terminal = body.act(Action("hidden", "run_command", {"command_id": "hidden"}, RUN))
    assert terminal.success is True
    assert terminal.state["output"] is None
    assert terminal.state["output_bytes"] > 0
    assert len(terminal.state["output_sha256"]) == 64


def test_process_timeout_and_output_limit_fail_closed(tmp_path: Path) -> None:
    limits = TerminalLimits(max_output_bytes=32)
    commands = (
        CommandSpec(
            "slow", (sys.executable, "-I", "-c", "import time;time.sleep(2)"),
            timeout_seconds=0.1, terminal_on_success=True,
        ),
        CommandSpec(
            "loud", (sys.executable, "-I", "-c", "print('x'*10000)"),
            terminal_on_success=True,
        ),
    )
    body = GovernedTerminalBody("bounded-process-terminal", tmp_path, commands, limits=limits)
    body.reset(Goal("bounded-process", "bound process resources"))
    slow = body.act(Action("slow", "run_command", {"command_id": "slow"}, RUN))
    assert slow.terminal is False
    assert slow.state["timed_out"] is True
    assert slow.error == "registered command exceeded its time limit"
    loud = body.act(Action("loud", "run_command", {"command_id": "loud"}, RUN))
    assert loud.terminal is False
    assert loud.state["output_truncated"] is True
    assert loud.state["output_bytes"] == 32


def test_workspace_snapshot_rejects_symlinks_or_excessive_files(tmp_path: Path) -> None:
    limits = TerminalLimits(max_files=1)
    (tmp_path / "one.txt").write_text("1", encoding="utf-8")
    (tmp_path / "two.txt").write_text("2", encoding="utf-8")
    with pytest.raises(TerminalBodyError, match="resource limits"):
        GovernedTerminalBody("too-large", tmp_path, limits=limits)

    if os.name != "nt":
        link_root = tmp_path / "links"
        link_root.mkdir()
        (link_root / "link").symlink_to(tmp_path / "one.txt")
        with pytest.raises(TerminalBodyError, match="symbolic links"):
            GovernedTerminalBody("symlinked", link_root)


@pytest.mark.skipif(os.name == "nt", reason="unprivileged Windows test sessions cannot create symlinks")
def test_terminal_actions_reject_contained_symlinks(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    limits = TerminalLimits(max_files=4)
    with pytest.raises(TerminalBodyError, match="symbolic links"):
        GovernedTerminalBody("contained-link", tmp_path, limits=limits)


def test_command_specs_require_absolute_executables() -> None:
    with pytest.raises(TerminalBodyError, match="absolute"):
        CommandSpec("relative", ("python", "-V"))
