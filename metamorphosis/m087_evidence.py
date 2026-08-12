"""The two evidence spaces, kept apart by construction rather than by discipline.

M086-C's selection rule saw one number per candidate: how many public cases it passed. When two
candidates passed the same ones it kept whichever came first, and recorded nothing. The tie was
not merely broken badly — it was **invisible**, because the representation had no place to put it.

M087 makes the ambiguity representable, and then asks whether a lineage can acquire the
information that resolves it. That requires two spaces that must never touch:

* **E_acquired** — observations the lineage is allowed to obtain during its interaction, by
  running an authorized reference source on a request it constructed from a bounded experiment
  space. This is a membership query in the sense of active automata learning: the lineage chooses
  the input, the environment supplies the behaviour, and nobody hands over the answer.
* **E_hidden** — cases held by the final scientific evaluator. Never queryable, never reachable,
  never in the same request domain.

The separation is structural, not procedural. The acquirable domain and the hidden domain are
disjoint sets of request strings, `assert_domains_disjoint` proves it, and every acquisition is
logged with a monotone sequence number so that an acquisition after hidden evaluation is a
detectable violation rather than a matter of trust.

Why this is not an evaluator leak, stated precisely: the reference source answers *what this input
produces*, which is exactly what running the real system would tell anyone who ran it. The
evaluator answers *whether a candidate is correct on cases nobody may see*. The first is an
affordance of the environment; the second is the measurement. A lineage that queries the reference
on `mean 1 2 6` learns `3.0` and can eliminate a candidate predicting `3.5`; it learns nothing
about the hidden cases, which live in a disjoint domain, and it is never told which candidate is
right.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence


ACQUISITION_SCHEMA = "m087-acquisition-log-v1"


class EvidenceError(RuntimeError):
    """Raised when the acquired/hidden boundary is crossed or an observation is malformed."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def digest_of(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class Observation:
    """What running one request on one body produced.

    `ok` false with a message is as informative as a value: a candidate that raises where the
    reference returns a number is eliminated by that difference, which is how the planning family
    is discriminated at all.
    """

    request: str
    ok: bool
    output: object
    error: str | None = None

    def key(self) -> str:
        """The comparable form. Two candidates agree on a request iff their keys match."""

        if not self.ok:
            return f"error:{self.error or ''}"
        if isinstance(self.output, float):
            # Predictions are compared at a fixed precision so that float noise cannot
            # manufacture a distinction the environment does not really make.
            return f"value:{self.output:.9g}"
        return f"value:{self.output!r}"

    def to_dict(self) -> dict[str, object]:
        return {
            "request": self.request, "ok": self.ok, "output": self.output,
            "error": self.error, "key": self.key(),
        }


@dataclass(frozen=True)
class EvidenceSpaces:
    """The bounded experiment space and the disjoint hidden domain."""

    acquirable_requests: tuple[str, ...]
    hidden_requests: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.acquirable_requests:
            raise EvidenceError("the experiment space may not be empty")
        if len(set(self.acquirable_requests)) != len(self.acquirable_requests):
            raise EvidenceError("the experiment space contains duplicates")
        assert_domains_disjoint(self.acquirable_requests, self.hidden_requests)

    def digest(self) -> str:
        return digest_of({
            "acquirable": list(self.acquirable_requests),
            "hidden": list(self.hidden_requests),
        })


def assert_domains_disjoint(
    acquirable: Sequence[str], hidden: Sequence[str],
) -> None:
    """The structural guarantee. A shared request would make acquisition a hidden-case lookup."""

    overlap = sorted(set(acquirable) & set(hidden))
    if overlap:
        raise EvidenceError(
            "the acquirable and hidden request domains overlap: " + ", ".join(overlap)
        )


@dataclass
class AcquisitionLog:
    """Every observation the lineage obtained, in order, with the boundary enforced on write.

    The log is the artifact the no-leak checker reads. It is append-only through `record`, it
    refuses a request outside the frozen experiment space, and it refuses any acquisition once
    hidden evaluation has been sealed.
    """

    spaces: EvidenceSpaces
    budget: int
    entries: list[dict[str, object]] = field(default_factory=list)
    hidden_evaluation_sealed: bool = False

    def record(self, observation: Observation) -> None:
        if self.hidden_evaluation_sealed:
            raise EvidenceError("an observation was acquired after hidden evaluation was sealed")
        if observation.request in self.spaces.hidden_requests:
            raise EvidenceError("an acquisition targeted a hidden-domain request")
        if observation.request not in self.spaces.acquirable_requests:
            raise EvidenceError(
                "an acquisition targeted a request outside the frozen experiment space"
            )
        if len(self.entries) >= self.budget:
            raise EvidenceError("the acquisition budget is exhausted")
        self.entries.append({
            "sequence": len(self.entries),
            "observation": observation.to_dict(),
        })

    def seal(self) -> None:
        self.hidden_evaluation_sealed = True

    @property
    def observations(self) -> tuple[Observation, ...]:
        return tuple(
            Observation(
                str(entry["observation"]["request"]),  # type: ignore[index]
                bool(entry["observation"]["ok"]),  # type: ignore[index]
                entry["observation"]["output"],  # type: ignore[index]
                entry["observation"]["error"],  # type: ignore[index]
            )
            for entry in self.entries
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": ACQUISITION_SCHEMA,
            "budget": self.budget,
            "count": len(self.entries),
            "entries": list(self.entries),
            "hidden_evaluation_sealed": self.hidden_evaluation_sealed,
            "experiment_space_digest": self.spaces.digest(),
        }


ReferenceSource = Callable[[str], Observation]
Predictor = Callable[[str, str], Observation]


def leak_problems(
    log: Mapping[str, object], spaces: EvidenceSpaces, hidden_case_requests: Sequence[str],
) -> list[str]:
    """Every reason a recorded acquisition log would constitute an evaluator leak."""

    problems: list[str] = []
    if log.get("schema") != ACQUISITION_SCHEMA:
        problems.append("acquisition log schema drifted")
    entries = log.get("entries")
    if not isinstance(entries, list):
        return problems + ["acquisition log entries are malformed"]
    hidden = set(hidden_case_requests)
    allowed = set(spaces.acquirable_requests)
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping) or set(entry) != {"sequence", "observation"}:
            problems.append(f"acquisition entry {index} fields differ from the closed schema")
            continue
        if entry.get("sequence") != index:
            problems.append("acquisition log is not a monotone append-only sequence")
        observation = entry.get("observation")
        if not isinstance(observation, Mapping):
            problems.append(f"acquisition entry {index} carries no observation")
            continue
        request = observation.get("request")
        if request in hidden:
            problems.append(f"acquisition {index} targeted a hidden evaluation request")
        if request not in allowed:
            problems.append(f"acquisition {index} left the frozen experiment space")
    budget = log.get("budget")
    if isinstance(budget, int) and len(entries) > budget:
        problems.append("the acquisition budget was exceeded")
    if log.get("experiment_space_digest") != spaces.digest():
        problems.append("the acquisition log binds a different experiment space")
    return problems


__all__ = [
    "ACQUISITION_SCHEMA", "AcquisitionLog", "EvidenceError", "EvidenceSpaces", "Observation",
    "Predictor", "ReferenceSource", "assert_domains_disjoint", "digest_of", "leak_problems",
]
