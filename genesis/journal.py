"""The descent journal: an append-only, hash-chained record of a lineage's whole history.

M072 causally validated tamper-evident audit chaining — matched non-executing ablations showed the
chaining causes its integrity invariant rather than accompanying it. This is that mechanism as a
runtime service instead of an experiment.

Every entry names its predecessor's digest, so an entry cannot be altered, removed or reordered
without breaking every digest after it. The chain covers rejections as well as adoptions: a lineage
that quietly dropped its failures would be reporting a different history than it lived, and under
the metamorphosis objective a rejected candidate is an observation the lineage keeps, not an
embarrassment it discards.
"""
from __future__ import annotations

import copy

import json
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from genesis.trust_root import canonical_bytes, digest_of

JOURNAL_SCHEMA = "genesis-descent-journal-v1"
ENTRY_SCHEMA = "genesis-descent-entry-v1"
GENESIS_DIGEST = "0" * 64

#: Kinds an entry may record. Rejections and refusals are first-class history.
ENTRY_KINDS = (
    "seed",
    "observation",
    "diagnosis",
    "candidate_proposed",
    "candidate_accepted",
    "candidate_rejected",
    "component_acquired",
    "vocabulary_extended",
    "rollback",
    "migration",
    "budget_exhausted",
    "instrument_abort",
    # A cycle asked to decide under a rule the admitted evaluation contract does not license. The
    # refusal is history: a caller reaching for a weaker measure is a fact about the run.
    "decision_rule_refused",
)


class JournalError(ValueError):
    """Raised when a chain does not reproduce, or an entry claims an unrecognised kind."""


def entry(
    *,
    kind: str,
    generation: int,
    payload: Mapping[str, Any],
    previous_digest: str,
) -> dict[str, Any]:
    if kind not in ENTRY_KINDS:
        raise JournalError("unrecognised journal entry kind %r" % (kind,))
    body = {
        "schema": ENTRY_SCHEMA,
        "kind": kind,
        "generation": int(generation),
        "previous_digest": previous_digest,
        "payload": json.loads(canonical_bytes(payload).decode("utf-8")),
    }
    return {**body, "entry_digest": digest_of(body)}


class Journal:
    """An append-only chain. Nothing removes or rewrites an entry."""

    def __init__(self, entries: Iterable[Mapping[str, Any]] = ()) -> None:
        self._entries: list[dict[str, Any]] = []
        for existing in entries:
            self._entries.append(dict(existing))
        if self._entries:
            problems = verify(self._entries)
            if problems:
                raise JournalError("; ".join(problems))

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self.entries())

    @property
    def head(self) -> str:
        return self._entries[-1]["entry_digest"] if self._entries else GENESIS_DIGEST

    def append(self, kind: str, generation: int, payload: Mapping[str, Any]) -> dict[str, Any]:
        record = entry(
            kind=kind, generation=generation, payload=payload, previous_digest=self.head
        )
        self._entries.append(record)
        # A deep copy, because the caller must not keep a handle on stored history. A hash chain
        # detects tampering by someone who cannot also rebuild the chain; code holding the live
        # Journal owns both, so the records it hands out must not be the records it keeps.
        return copy.deepcopy(record)

    def entries(self) -> list[dict[str, Any]]:
        """A deep snapshot. Copying only the outer dictionary left nested payloads shared."""
        return copy.deepcopy(self._entries)

    def of_kind(self, kind: str) -> list[dict[str, Any]]:
        return [copy.deepcopy(record) for record in self._entries if record["kind"] == kind]

    def record(self) -> dict[str, Any]:
        payload = {"schema": JOURNAL_SCHEMA, "entries": self.entries(), "head": self.head}
        return {**payload, "journal_digest": digest_of(payload)}

    def save(self, path: Path) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = canonical_bytes(self.record())
        temporary = path.with_suffix(path.suffix + ".partial")
        temporary.write_bytes(raw + b"\n")
        temporary.replace(path)
        return digest_of(self.record())

    @classmethod
    def load(cls, path: Path) -> "Journal":
        value = json.loads(Path(path).read_bytes().decode("utf-8"))
        if not isinstance(value, dict) or value.get("schema") != JOURNAL_SCHEMA:
            raise JournalError("journal payload is invalid")
        expected = digest_of({k: v for k, v in value.items() if k != "journal_digest"})
        if value.get("journal_digest") != expected:
            raise JournalError("journal digest does not reproduce")
        return cls(value.get("entries") or [])


def verify(entries: Iterable[Mapping[str, Any]]) -> list[str]:
    """Re-derive every digest and every link. An altered entry breaks everything after it."""
    problems: list[str] = []
    previous = GENESIS_DIGEST
    for index, record in enumerate(entries):
        if record.get("schema") != ENTRY_SCHEMA:
            problems.append("entry %d uses an unrecognised schema" % index)
            continue
        if record.get("kind") not in ENTRY_KINDS:
            problems.append("entry %d claims an unrecognised kind" % index)
        if record.get("previous_digest") != previous:
            problems.append(
                "entry %d does not follow its predecessor: expected %s, found %s"
                % (index, previous, record.get("previous_digest"))
            )
        recomputed = digest_of({k: v for k, v in record.items() if k != "entry_digest"})
        if record.get("entry_digest") != recomputed:
            problems.append("entry %d does not reproduce its own digest" % index)
        # Carry the *recomputed* digest forward, not the stored one. Trusting the stored value would
        # confine tampering to the entry that was tampered with, which is precisely the property a
        # hash chain exists to deny: an altered entry must break every link after it.
        previous = recomputed
    return problems
