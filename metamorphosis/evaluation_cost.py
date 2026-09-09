"""Cost and efficiency accounting for G9.

G9 requires that results report quality, reliability, latency, energy or compute proxies and
monetary cost where applicable. The repository already has the integrity half of that gate — frozen
protocols, preserved negatives, byte-stable replay. This module supplies the efficiency half.

The design follows M120's lesson rather than repeating its defect. A checker that recomputes a
number *from the record the runner wrote* has authenticated a file, not measured anything. So a cost
record here is split in two, and the split is the whole point:

* **deterministic components** — request counts, token counts, episodes, budget units — are a pure
  function of committed evidence. A checker recomputes them independently and requires exact
  equality. A fabricated count is not a file that must be caught by a rule someone remembered to
  write; it is a file that does not reproduce.
* **environment-dependent components** — wall clock, CPU seconds, peak memory — cannot reproduce on
  a different host and must never be asserted to. They are recorded with the environment that
  produced them and are explicitly marked non-reproducible.

Two refusals matter more than any measurement here:

* monetary cost is **never estimated**. Without a committed rate card the field is null and carries
  the reason. A price this module invented would be a fabricated result wearing a number.
* CPU seconds are a **compute proxy**, never energy. Nothing here measures watts, and a record that
  claims to is refused.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from contextlib import contextmanager
from typing import Any, Iterator, Mapping

try:  # pragma: no cover - the fallback is exercised only on platforms without resource
    import resource
except ImportError:  # pragma: no cover
    resource = None  # type: ignore[assignment]

COST_SCHEMA = "mira-evaluation-cost-v1"
RATE_CARD_SCHEMA = "mira-model-rate-card-v1"

#: Components a checker must be able to recompute exactly from committed evidence.
DETERMINISTIC_FIELDS = (
    "budget_units_spent",
    "candidate_evaluations",
    "completion_tokens",
    "episodes",
    "model_calls",
    "network_requests",
    "prompt_tokens",
    "work_items",
)

#: Components that depend on the host and may never be required to reproduce.
ENVIRONMENT_FIELDS = ("cpu_seconds", "peak_rss_bytes", "wall_clock_seconds")

#: The dimensions G9 asks a result to report. `monetary_cost` may be null, but only with a reason.
REQUIRED_REPORT_DIMENSIONS = (
    "quality",
    "reliability",
    "latency",
    "compute_proxy",
    "monetary_cost",
)


class CostError(ValueError):
    """Raised when a cost record claims more than its evidence supports."""


def _environment() -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "implementation": platform.python_implementation(),
    }


@contextmanager
def measured() -> Iterator[dict[str, Any]]:
    """Capture environment-dependent cost around a block.

    The mapping is filled on exit. Its values describe *this host on this run* and are marked
    non-reproducible, because they are.
    """
    captured: dict[str, Any] = {}
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    try:
        yield captured
    finally:
        wall = time.perf_counter() - started_wall
        cpu = time.process_time() - started_cpu
        peak = None
        if resource is not None:
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # Linux reports kilobytes, macOS reports bytes.
            peak = usage * 1024 if sys.platform.startswith("linux") else usage
        captured.update(
            {
                "wall_clock_seconds": round(wall, 6),
                "cpu_seconds": round(cpu, 6),
                "peak_rss_bytes": peak,
                "reproducible": False,
                "cpu_seconds_is_a_compute_proxy_not_energy": True,
                "environment": _environment(),
            }
        )


def monetary_cost(
    rate_card: Mapping[str, Any] | None,
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict[str, Any]:
    """Price a run, or refuse and say why. This never guesses a rate."""

    if prompt_tokens == 0 and completion_tokens == 0:
        # Zero billable tokens costs zero at every rate, so this is arithmetic rather than an
        # estimate, and an offline run should say so rather than hide behind "unpriced".
        return {
            "amount": 0.0,
            "currency": rate_card.get("currency") if isinstance(rate_card, Mapping) else None,
            "reason": None,
            "no_billable_usage": True,
        }
    if rate_card is None:
        return {
            "amount": None,
            "currency": None,
            "reason": "no committed rate card; monetary cost is not estimated",
        }
    if rate_card.get("schema") != RATE_CARD_SCHEMA:
        raise CostError("rate card uses an unrecognized schema")
    currency = rate_card.get("currency")
    if not isinstance(currency, str) or not currency:
        raise CostError("rate card declares no currency")
    rates = rate_card.get("rates")
    if not isinstance(rates, Mapping) or model not in rates:
        return {
            "amount": None,
            "currency": currency,
            "reason": "rate card does not price model %r; monetary cost is not estimated" % model,
        }
    entry = rates[model]
    try:
        prompt_rate = float(entry["prompt_per_million"])
        completion_rate = float(entry["completion_per_million"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CostError("rate card entry for %r is malformed" % model) from exc
    amount = (
        prompt_tokens * prompt_rate + completion_tokens * completion_rate
    ) / 1_000_000
    return {
        "amount": round(amount, 8),
        "currency": currency,
        "reason": None,
        "rate_card_version": rate_card.get("version"),
    }


def cost_record(
    *,
    milestone: str,
    deterministic: Mapping[str, Any],
    environment_costs: Mapping[str, Any],
    quality: Mapping[str, Any],
    reliability: Mapping[str, Any],
    monetary: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble a G9 cost record. Unknown or missing deterministic components are refused."""

    unknown = sorted(set(deterministic) - set(DETERMINISTIC_FIELDS))
    if unknown:
        raise CostError("unknown deterministic components: %s" % ", ".join(unknown))
    missing = sorted(set(DETERMINISTIC_FIELDS) - set(deterministic))
    if missing:
        raise CostError("deterministic components omitted: %s" % ", ".join(missing))
    for name, value in sorted(deterministic.items()):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise CostError("deterministic component %r must be a non-negative integer" % name)
    for name in ENVIRONMENT_FIELDS:
        if name not in environment_costs:
            raise CostError("environment component %r is missing" % name)
    if environment_costs.get("reproducible") is not False:
        raise CostError("environment costs must declare themselves non-reproducible")
    if "energy_joules" in environment_costs or "watts" in environment_costs:
        raise CostError("nothing here measures energy; report a compute proxy instead")

    record = {
        "schema": COST_SCHEMA,
        "milestone": milestone,
        "deterministic": dict(sorted(deterministic.items())),
        "environment_costs": dict(sorted(environment_costs.items())),
        "report": {
            "quality": dict(quality),
            "reliability": dict(reliability),
            "latency": {
                "wall_clock_seconds": environment_costs["wall_clock_seconds"],
                "reproducible": False,
            },
            "compute_proxy": {
                "cpu_seconds": environment_costs["cpu_seconds"],
                "peak_rss_bytes": environment_costs["peak_rss_bytes"],
                "is_energy": False,
            },
            "monetary_cost": dict(monetary),
        },
    }
    assert_reports_required_dimensions(record)
    return record


def assert_reports_required_dimensions(record: Mapping[str, Any]) -> None:
    """Refuse a record that omits a dimension G9 asks for, or that prices a run it cannot price."""

    if record.get("schema") != COST_SCHEMA:
        raise CostError("cost record uses an unrecognized schema")
    report = record.get("report")
    if not isinstance(report, Mapping):
        raise CostError("cost record carries no report")
    missing = sorted(set(REQUIRED_REPORT_DIMENSIONS) - set(report))
    if missing:
        raise CostError("report omits required dimensions: %s" % ", ".join(missing))
    for name in ("quality", "reliability"):
        section = report[name]
        if not isinstance(section, Mapping) or not section:
            raise CostError("report section %r is empty" % name)
    monetary = report["monetary_cost"]
    if not isinstance(monetary, Mapping):
        raise CostError("monetary cost is not a record")
    if monetary.get("amount") is None and not monetary.get("reason"):
        raise CostError("an unpriced run must state why it is unpriced")
    if monetary.get("amount") is not None and monetary.get("reason"):
        raise CostError("a priced run must not also carry an excuse for being unpriced")
    if report["compute_proxy"].get("is_energy") is not False:
        raise CostError("the compute proxy must not be presented as energy")


def verify_cost_record(
    record: Mapping[str, Any], *, recomputed_deterministic: Mapping[str, Any]
) -> list[str]:
    """Check a record against independently recomputed deterministic components.

    Environment costs are deliberately not compared: requiring them to reproduce on another host
    would either fail honestly every time or invite a tolerance wide enough to hide a real change.
    """
    problems: list[str] = []
    try:
        assert_reports_required_dimensions(record)
    except CostError as exc:
        problems.append(str(exc))
    committed = record.get("deterministic")
    if not isinstance(committed, Mapping):
        return problems + ["cost record carries no deterministic components"]
    for name in DETERMINISTIC_FIELDS:
        expected = recomputed_deterministic.get(name)
        if expected is None:
            problems.append("no independent recomputation for %r" % name)
        elif committed.get(name) != expected:
            problems.append(
                "%s: recorded %r, recomputed %r" % (name, committed.get(name), expected)
            )
    return problems


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
