"""M060 falsifications for the Python-emitted body: every number comes back out of Node.

The claim under test is not "the emitter produces bytes" but "the Python compiler reproduces the
behaviour of the hand-written WAT". So nothing here inspects the binary for shape; each case
instantiates the real module with **no import object**, writes the request into exported memory
the way a host would, calls `run()`, and compares against a value observed from the compiled WAT
oracle — including the four refusals, which the oracle splits into three traps and one NaN.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from metamorphosis.m060_body_compiler import compile_body

NODE_TIMEOUT_SECONDS = 60.0

REQUEST_OFFSET = 0
LENGTH_OFFSET = 256

#: Instantiate once per request so no state leaks between cases, feed the request the way the
#: reference host does, and report a trap as a string rather than letting it kill the process.
_HARNESS = """
const fs = require('fs');
const bytes = fs.readFileSync(process.argv[1]);
const requests = JSON.parse(process.argv[2]);
const mod = new WebAssembly.Module(bytes);
const out = {
  imports: WebAssembly.Module.imports(mod).length,
  exports: WebAssembly.Module.exports(mod).map(e => [e.name, e.kind]),
  results: [],
};
for (const request of requests) {
  const exports = new WebAssembly.Instance(mod).exports;
  const view = new Uint8Array(exports.memory.buffer);
  const encoded = new TextEncoder().encode(request);
  view.set(encoded, __REQUEST__);
  new DataView(exports.memory.buffer).setInt32(__LENGTH__, encoded.length, true);
  try {
    const value = exports.run();
    out.results.push(Number.isNaN(value) ? 'NaN' : value);
  } catch (error) {
    out.results.push('TRAP:' + error.message);
  }
}
process.stdout.write(JSON.stringify(out));
"""


def run_requests(requests: list[str]) -> dict[str, Any]:
    """Run `requests` through the emitted module in Node, returning imports, exports and results."""
    handle, path = tempfile.mkstemp(suffix=".wasm")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(compile_body())
        script = _HARNESS.replace("__REQUEST__", str(REQUEST_OFFSET)).replace(
            "__LENGTH__", str(LENGTH_OFFSET)
        )
        completed = subprocess.run(
            ["node", "-e", script, path, json.dumps(requests)],
            capture_output=True,
            text=True,
            timeout=NODE_TIMEOUT_SECONDS,
            check=False,
        )
    finally:
        Path(path).unlink(missing_ok=True)
    if completed.returncode != 0:
        raise AssertionError(f"node rejected the module: {completed.stderr.strip()}")
    return json.loads(completed.stdout)


#: The 32 accepted requests. Every expectation here was read back from the compiled WAT oracle
#: before being written down, so this list records observed behaviour rather than intent.
CASES: list[tuple[str, float]] = [
    ("add 2 3", 5),
    ("add -4 7", 3),
    ("mul 3 4", 12),
    ("mul -2 5", -10),
    ("sum 2 3", 5),
    ("sum -4 7", 3),
    ("add 2 mul 3 4", 14),
    ("mul add 1 2 5", 15),
    ("mean 2 4 6", 4.0),
    ("mean -3 0 3", 0.0),
    ("mean 1 2 2", 1.67),
    ("mean 0 1 1", 0.67),
    ("add mean 1 2 3 mul add 1 2 mul 2 3", 20.0),
    ("mul add mean 1 2 3 mul 2 3 add 1 1", 16.0),
    ("average 3 6 9", 6.0),
    ("average 1 2 2", 1.67),
    ("sum 11 -6", 5),
    ("sum 0 0", 0),
    ("add mul 2 add 1 2 4", 10),
    ("mul add 1 mul 2 3 2", 14),
    ("mean 1 2 9", 4.0),
    ("mean 2 4 9", 5.0),
    ("mean 2 2 3", 2.33),
    ("mean 1 1 2", 1.33),
    ("add mul add 1 2 mul 2 3 add mean 3 6 9 4", 28.0),
    ("mul add mean 1 2 3 mul 2 3 add mean 3 6 9 add 1 1", 64.0),
    ("average 2 3 8", 4.33),
    ("add average 1 2 3 4", 6.0),
    ("maximum 2 5", 5),
    ("maximum -1 -3", -1),
    ("maximum 4 4", 4),
    ("maximum -8 3", 3),
]


def test_the_emitted_module_declares_no_imports():
    """A body that needs a host to run is not self-contained; the WAT needed none either."""
    assert run_requests([])["imports"] == 0


def test_every_exported_name_of_the_wat_is_present():
    exported = dict(run_requests([])["exports"])

    for stage in (
        "tokenize",
        "token_is_number",
        "token_number",
        "alias_index",
        "interpret",
        "plan",
        "allocate",
        "select",
        "execute",
        "critique",
        "run",
    ):
        assert exported.get(stage) == "function", f"{stage} is not exported as a function"
    assert exported.get("memory") == "memory"


def test_all_thirty_two_accepted_cases_return_their_expected_value():
    results = run_requests([request for request, _ in CASES])["results"]

    assert len(CASES) == 32
    assert results == [expected for _, expected in CASES]


def test_refusals_behave_as_the_oracle_does():
    """Three malformed requests trap on `unreachable`; leftover tokens refuse with NaN instead."""
    results = run_requests(["median 1 2", "add 2", "add 2 3 4", ""])["results"]

    assert results[0].startswith("TRAP:") and "unreachable" in results[0]
    assert results[1].startswith("TRAP:") and "unreachable" in results[1]
    assert results[2] == "NaN"
    assert results[3].startswith("TRAP:") and "unreachable" in results[3]


def test_non_integer_results_round_the_way_the_oracle_rounds():
    results = run_requests(["mean 1 2 2", "mean 0 1 1", "mean 2 2 3"])["results"]

    assert results == [1.67, 0.67, 2.33]


def test_a_deeply_nested_request_matches_the_oracle():
    """Nesting is where postorder step numbering matters: a preorder plan reads unwritten slots."""
    request = "mul add mean 1 2 3 mul 2 3 add mean 3 6 9 add 1 1"

    assert run_requests([request])["results"] == [64]


def test_compilation_is_deterministic():
    assert compile_body() == compile_body()
