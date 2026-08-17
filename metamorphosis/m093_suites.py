"""Embedded sandbox suites for the M093 transformation experiment.

These are the test programs executed *inside* the disposable subprocess
sandbox.  They are deliberately independent of the host repository: each
one receives a single module under test on ``sys.path``.
"""

from __future__ import annotations

ORIGINAL_SANDBOX_SCRIPT = r"""
import sys
sys.path.insert(0, ".")
from mira_core.memory import MemoryLedger

assertions = 0
failed = 0

def check(name, ok):
    global assertions, failed
    assertions += 1
    if ok:
        print("ASSERT:OK:" + name)
    else:
        print("ASSERT:FAIL:" + name)
        failed += 1

# O1: empty ledger
l = MemoryLedger()
check("O1", l.digest == "0" * 64 and len(l.events) == 0)

# O2: append + digest chain
l.append("alpha", {"v": 1})
check("O2", len(l.events) == 1 and l.digest != "0" * 64)

# O3: verify integrity
l.append("beta", {"v": 2})
l.verify()
check("O3", True)

# O4: checkpoint / restore round-trip
cp = l.checkpoint()
r = MemoryLedger.restore(cp)
check("O4", r.checkpoint() == cp and r.digest == l.digest)

# O5: tamper detection
import json
v = json.loads(l.checkpoint())
v["events"][0]["payload"]["v"] = 99
try:
    MemoryLedger.restore(json.dumps(v).encode())
    check("O5", False)
except ValueError:
    check("O5", True)

# O6: manual kind filter works (current behaviour)
manual = tuple(e for e in l.events if e.kind == "alpha")
check("O6", len(manual) == 1 and manual[0].kind == "alpha")

print("RESULT:{'total': %d, 'failed': %d, 'passed': %d}" % (assertions, failed, assertions - failed))
sys.exit(1 if failed else 0)
"""

CANDIDATE_SANDBOX_SCRIPT = r"""
import sys
sys.path.insert(0, ".")
from mira_core.memory import MemoryLedger

assertions = 0
failed = 0

def check(name, ok):
    global assertions, failed
    assertions += 1
    if ok:
        print("ASSERT:OK:" + name)
    else:
        print("ASSERT:FAIL:" + name)
        failed += 1

# C1: new method on empty ledger
l = MemoryLedger()
check("C1", l.events_by_kind("anything") == ())

# C2: new method matches a single event
l.append("alpha", {"v": 1})
check("C2", len(l.events_by_kind("alpha")) == 1)

# C3: non-matching kind ignored
check("C3", l.events_by_kind("beta") == ())

# C4: multiple events, same kind
l.append("alpha", {"v": 2})
l.append("beta", {"v": 3})
check("C4", len(l.events_by_kind("alpha")) == 2)

# C5: empty kind rejected
try:
    l.events_by_kind("")
    check("C5", False)
except ValueError:
    check("C5", True)

# C6: functional equivalence with manual filter
kinds = ["x", "y", "x", "z"]
for k in kinds:
    l.append(k, {"idx": 1})
manual = tuple(e for e in l.events if e.kind == "x")
method = l.events_by_kind("x")
check("C6", list(manual) == list(method))

# C7: order preserved (fresh ledger)
l3 = MemoryLedger()
for k in ["x", "y", "x"]:
    l3.append(k, {"idx": 1})
check("C7", [e.index for e in l3.events_by_kind("x")] == [0, 2])

print("RESULT:{'total': %d, 'failed': %d, 'passed': %d}" % (assertions, failed, assertions - failed))
sys.exit(1 if failed else 0)
"""

VALIDATOR_SCRIPT = r"""
import sys
sys.path.insert(0, ".")
from mira_core.memory import MemoryLedger

assertions = 0
failed = 0

def check(name, ok):
    global assertions, failed
    assertions += 1
    if ok:
        print("ASSERT:OK:" + name)
    else:
        print("ASSERT:FAIL:" + name)
        failed += 1

# V1: held-out — events_by_kind across multiple distinct kinds
l = MemoryLedger()
for kind in ("start", "action", "observe", "action", "finish"):
    l.append(kind, {"i": 1})
check("V1", [e.kind for e in l.events_by_kind("action")] == ["action", "action"])

# V2: held-out — last matching event index
l2 = MemoryLedger()
for kind in ("a", "b", "a"):
    l2.append(kind, {"i": 1})
tail = l2.events_by_kind("a")[-1]
check("V2", tail.index == 2)

# V3: held-out — chain remains tamper-evident after query
l2.verify()
check("V3", True)

# V4: held-out — no matching events
check("V4", MemoryLedger().events_by_kind("ghost") == ())

print("RESULT:{'total': %d, 'failed': %d, 'passed': %d}" % (assertions, failed, assertions - failed))
sys.exit(1 if failed else 0)
"""

