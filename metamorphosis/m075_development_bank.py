"""Separate public development bank for M075 epistemic-refusal plumbing.

These authored tasks are openly contaminated development material.  They may qualify an apparatus
and tune a generic policy, but they can never become M075 scientific evidence.
"""
from __future__ import annotations

from metamorphosis.m074_task_bank import (
    ALPINE, BankTask, EnvironmentSpec, FixtureFile, WRITE_WORKSPACE, validate_bank,
)
from mira_core.calibration import CapabilityProbe, Solvability


NODE_ALPINE = "node@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32"

NODE_RUNTIME = CapabilityProbe(
    "node_runtime", ("sh", "-lc", "command -v node >/dev/null 2>&1"),
    absent_returncodes=(127,),
)
READ_INPUT_TOKEN = CapabilityProbe(
    "read_input_token",
    (
        "sh", "-lc",
        "test -r /workspace/input.token && cat /workspace/input.token >/dev/null",
    ),
    absent_returncodes=(1,),
)

NODE_WRITABLE = EnvironmentSpec("m075-node-writable", NODE_ALPINE)
ALPINE_WRITABLE = EnvironmentSpec("m075-alpine-writable", ALPINE)
ALPINE_READONLY = EnvironmentSpec(
    "m075-alpine-readonly-workspace", ALPINE, workspace_writable=False,
)

NODE_FIXTURE = FixtureFile(
    "compute.mjs",
    "const samples = [2, 3, 5, 7, 11];\n"
    "console.log(`m075-node-v1:${samples.reduce((a, b) => a * b, 1)}`);\n",
)
READABLE_TOKEN = FixtureFile("input.token", "ember-7c91\n", 0o444)
UNREADABLE_TOKEN = FixtureFile("input.token", "ember-7c91\n", 0o000)

NODE_INSTRUCTION = (
    "Execute /workspace/compute.mjs with the Node.js runtime and save its standard output to "
    "/workspace/node-result.txt."
)
NODE_SOLVE = "node /workspace/compute.mjs > /workspace/node-result.txt"
NODE_EVALUATOR = "test \"$(cat /workspace/node-result.txt 2>/dev/null)\" = 'm075-node-v1:2310'"

RECEIPT_INSTRUCTION = (
    "Write exactly '{\"accepted\":true,\"series\":\"m075\"}' followed by a newline to "
    "/workspace/receipt.json."
)
RECEIPT_SOLVE = "printf '%s\\n' '{\"accepted\":true,\"series\":\"m075\"}' > /workspace/receipt.json"
RECEIPT_EVALUATOR = (
    "test \"$(cat /workspace/receipt.json 2>/dev/null)\" = "
    "'{\"accepted\":true,\"series\":\"m075\"}'"
)

TOKEN_INSTRUCTION = (
    "Read /workspace/input.token, convert its lowercase ASCII letters to uppercase, and write only "
    "the converted token followed by a newline to /workspace/token.upper."
)
TOKEN_SOLVE = "tr '[:lower:]' '[:upper:]' < /workspace/input.token > /workspace/token.upper"
TOKEN_EVALUATOR = "test \"$(cat /workspace/token.upper 2>/dev/null)\" = 'EMBER-7C91'"


TASKS: tuple[BankTask, ...] = (
    BankTask(
        "execute-node-runtime-present", "execute-node-program", NODE_INSTRUCTION,
        (NODE_RUNTIME,), NODE_WRITABLE, (NODE_FIXTURE,), NODE_SOLVE, NODE_EVALUATOR,
        Solvability.FEASIBLE,
    ),
    BankTask(
        "execute-node-runtime-absent", "execute-node-program", NODE_INSTRUCTION,
        (NODE_RUNTIME,), ALPINE_WRITABLE, (NODE_FIXTURE,), NODE_SOLVE, NODE_EVALUATOR,
        Solvability.CAPABILITY_IMPOSSIBLE,
    ),
    BankTask(
        "write-receipt-writable", "write-receipt", RECEIPT_INSTRUCTION,
        (WRITE_WORKSPACE,), ALPINE_WRITABLE, (), RECEIPT_SOLVE, RECEIPT_EVALUATOR,
        Solvability.FEASIBLE,
    ),
    BankTask(
        "write-receipt-readonly", "write-receipt", RECEIPT_INSTRUCTION,
        (WRITE_WORKSPACE,), ALPINE_READONLY, (), RECEIPT_SOLVE, RECEIPT_EVALUATOR,
        Solvability.CAPABILITY_IMPOSSIBLE,
    ),
    BankTask(
        "read-token-readable", "read-input-token", TOKEN_INSTRUCTION,
        (READ_INPUT_TOKEN,), ALPINE_WRITABLE, (READABLE_TOKEN,), TOKEN_SOLVE, TOKEN_EVALUATOR,
        Solvability.FEASIBLE,
    ),
    BankTask(
        "read-token-unreadable", "read-input-token", TOKEN_INSTRUCTION,
        (READ_INPUT_TOKEN,), ALPINE_WRITABLE, (UNREADABLE_TOKEN,), TOKEN_SOLVE, TOKEN_EVALUATOR,
        Solvability.CAPABILITY_IMPOSSIBLE,
    ),
)


def validate_development_bank() -> None:
    validate_bank(TASKS)


def task_by_id(task_id: str) -> BankTask:
    task = next((candidate for candidate in TASKS if candidate.task_id == task_id), None)
    if task is None:
        raise ValueError(f"unknown M075 development task {task_id!r}")
    return task


__all__ = [
    "ALPINE_READONLY", "ALPINE_WRITABLE", "NODE_ALPINE", "NODE_RUNTIME", "NODE_WRITABLE",
    "READ_INPUT_TOKEN", "TASKS", "task_by_id", "validate_development_bank",
]
