"""Continual acquisition under genuine capacity and conflict interference.

The register says M073 tested "one homogeneous authored family and no forgetting". Retention has
never been at risk here, so it has never been measured.

Six skills share one bounded 24-slot table. Entries are shared by context set, so a later skill that
induces the same rule as an earlier one costs no new slot — that is where positive transfer and
sublinear memory growth come from. The interference comes from the same sharing: some later skills
need a *different* output for an exception key an earlier skill already owns. Taking the cheap path
and rewriting that entry in place destroys the earlier capability.

A design giving each skill private slots would guarantee retention by construction and measure
nothing. Here the cheap path is always available and always wrong, and the `no_consolidation` arm
takes it.

The table is the policy. Behaviour is fully determined by it and acquisition rewrites it, so this is
bounded policy learning over a finite structure — not retrieval from a side store consulted
alongside a fixed policy, and not weight learning.
"""
from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from typing import Mapping, Sequence


PROTOCOL_SCHEMA = "m080-continual-retention-protocol-v1"
GENERATOR_VERSION = 1

TABLE_SLOTS = 24
KEY_SPACE = 64
OUTPUT_ALPHABET = 8
SKILL_COUNT = 6
KEYS_PER_SKILL = 22
EXAMPLES_PER_SKILL = 10
HOLDOUTS_PER_SKILL = 12
IRREGULARS_PER_SKILL = 3

ARMS = ("lineage", "no_consolidation", "no_rollback", "no_replay")


class RetentionError(ValueError):
    """Raised when a table, skill or arm contract is violated."""


class CapacityExhausted(RuntimeError):
    """Raised when no slot is free and eviction is forbidden."""


def _digest(index: int, salt: bytes, tag: bytes = b"") -> bytes:
    return hashlib.sha256(salt + tag + index.to_bytes(4, "big")).digest()


@dataclass(frozen=True)
class Skill:
    index: int
    keys: tuple[int, ...]
    slope: int
    offset: int
    irregulars: Mapping[int, int]
    examples: tuple[int, ...]
    holdouts: tuple[int, ...]
    shares_rule_with: int | None
    conflicts_on_key: int | None

    def expected(self, key: int) -> int:
        if key in self.irregulars:
            return self.irregulars[key]
        return (self.slope * key + self.offset) % OUTPUT_ALPHABET

    def commitment(self) -> str:
        payload = "|".join([
            str(self.index), str(self.slope), str(self.offset),
            ",".join(str(k) for k in self.keys),
            ",".join(f"{k}:{v}" for k, v in sorted(self.irregulars.items())),
            ",".join(str(k) for k in self.examples),
            ",".join(str(k) for k in self.holdouts),
            f"share={self.shares_rule_with}", f"conflict={self.conflicts_on_key}",
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _key_set(salt: bytes, index: int) -> list[int]:
    digest = _digest(index, salt, b"keys")
    keys: list[int] = []
    cursor = 0
    while len(keys) < KEYS_PER_SKILL:
        if cursor >= len(digest):
            digest = hashlib.sha256(digest).digest()
            cursor = 0
        candidate = digest[cursor] % KEY_SPACE
        cursor += 1
        if candidate not in keys:
            keys.append(candidate)
    return sorted(keys)


def _split(salt: bytes, index: int, keys: Sequence[int], forced: Sequence[int]) -> tuple:
    seed = _digest(index, salt, b"split")
    ordered = sorted(keys, key=lambda k: hashlib.sha256(seed + k.to_bytes(2, "big")).hexdigest())
    examples = list(ordered[:EXAMPLES_PER_SKILL])
    holdouts = list(ordered[EXAMPLES_PER_SKILL:EXAMPLES_PER_SKILL + HOLDOUTS_PER_SKILL])
    # Every irregular must be visible in the examples, otherwise the skill is unlearnable rather
    # than merely hard and the experiment would measure the wrong thing.
    for key in forced:
        if key not in examples:
            examples.append(key)
            if key in holdouts:
                holdouts.remove(key)
    return tuple(sorted(examples)), tuple(sorted(holdouts))


def build_bank(salt: bytes) -> tuple[Skill, ...]:
    """Skills 0-2 are independent. Skills 3-5 reuse an earlier rule, and each conflicts with its
    donor on exactly one exception key, which is where the interference lives."""

    skills: list[Skill] = []
    for index in range(SKILL_COUNT):
        keys = _key_set(salt, index)
        seed = _digest(index, salt, b"rule")
        donor = skills[index - 3] if index >= 3 else None

        if donor is None:
            slope, offset = 1 + seed[0] % 5, seed[1] % OUTPUT_ALPHABET
        else:
            slope, offset = donor.slope, donor.offset

        irregulars: dict[int, int] = {}
        conflict_key: int | None = None
        if donor is not None:
            # Reuse one of the donor's exception keys with a different output. Both skills then
            # need that key, and one shared entry cannot serve both.
            conflict_key = sorted(donor.irregulars)[seed[2] % len(donor.irregulars)]
            if conflict_key not in keys:
                keys = sorted(set(keys) | {conflict_key})[:KEYS_PER_SKILL]
                if conflict_key not in keys:
                    keys[-1] = conflict_key
                    keys = sorted(keys)
            donor_output = donor.irregulars[conflict_key]
            irregulars[conflict_key] = (donor_output + 1 + seed[3] % 3) % OUTPUT_ALPHABET
            if irregulars[conflict_key] == donor_output:
                irregulars[conflict_key] = (donor_output + 1) % OUTPUT_ALPHABET

        while len(irregulars) < IRREGULARS_PER_SKILL:
            position = len(irregulars)
            key = keys[seed[4 + position] % len(keys)]
            if key in irregulars:
                key = keys[(seed[4 + position] + position + 1) % len(keys)]
            regular = (slope * key + offset) % OUTPUT_ALPHABET
            irregulars[key] = (regular + 1 + seed[8 + position] % (OUTPUT_ALPHABET - 1)) % (
                OUTPUT_ALPHABET
            )
            if irregulars[key] == regular:
                irregulars[key] = (regular + 1) % OUTPUT_ALPHABET

        examples, holdouts = _split(salt, index, keys, list(irregulars))
        skills.append(Skill(
            index=index, keys=tuple(keys), slope=slope, offset=offset,
            irregulars=irregulars, examples=examples, holdouts=holdouts,
            shares_rule_with=donor.index if donor else None,
            conflicts_on_key=conflict_key,
        ))
    if len(skills) != SKILL_COUNT:
        raise RetentionError("materialized bank size drifted from the frozen protocol")
    return tuple(skills)


@dataclass
class RuleEntry:
    contexts: frozenset[int]
    slope: int
    offset: int


@dataclass
class ExceptionEntry:
    contexts: frozenset[int]
    key: int
    output: int


@dataclass
class Table:
    """The policy. Bounded, shared by every skill, and rewritten by acquisition."""

    slots: list[RuleEntry | ExceptionEntry | None] = field(
        default_factory=lambda: [None] * TABLE_SLOTS,
    )

    def lookup(self, context: int, key: int) -> int | None:
        for slot in self.slots:
            if isinstance(slot, ExceptionEntry) and context in slot.contexts and slot.key == key:
                return slot.output
        for slot in self.slots:
            if isinstance(slot, RuleEntry) and context in slot.contexts:
                return (slot.slope * key + slot.offset) % OUTPUT_ALPHABET
        return None

    def used(self) -> int:
        return sum(1 for slot in self.slots if slot is not None)

    def allocate(self, entry: RuleEntry | ExceptionEntry) -> None:
        for index, slot in enumerate(self.slots):
            if slot is None:
                self.slots[index] = entry
                return
        raise CapacityExhausted("no free slot remains")

    def find_rule(self, slope: int, offset: int) -> RuleEntry | None:
        for slot in self.slots:
            if isinstance(slot, RuleEntry) and slot.slope == slope and slot.offset == offset:
                return slot
        return None

    def find_exception(self, key: int) -> ExceptionEntry | None:
        for slot in self.slots:
            if isinstance(slot, ExceptionEntry) and slot.key == key:
                return slot
        return None

    def digest(self) -> str:
        payload = ";".join(
            "empty" if slot is None
            else f"R{sorted(slot.contexts)}:{slot.slope}:{slot.offset}"
            if isinstance(slot, RuleEntry)
            else f"E{sorted(slot.contexts)}:{slot.key}:{slot.output}"
            for slot in self.slots
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def induce(skill: Skill) -> tuple[tuple[int, int], dict[int, int]]:
    """Recover a rule and its exceptions from the examples alone."""

    scores = {
        (slope, offset): sum(
            1 for key in skill.examples
            if (slope * key + offset) % OUTPUT_ALPHABET == skill.expected(key)
        )
        for slope in range(1, 6) for offset in range(OUTPUT_ALPHABET)
    }
    best = max(scores, key=lambda candidate: (scores[candidate], -candidate[0], -candidate[1]))
    exceptions = {
        key: skill.expected(key) for key in skill.examples
        if (best[0] * key + best[1]) % OUTPUT_ALPHABET != skill.expected(key)
    }
    return best, exceptions


@dataclass
class AcquisitionRecord:
    skill: int
    committed: bool
    slots_written: int
    slots_used_after: int
    reused_rule: bool
    rejected_cheap_path: bool
    rolled_back: bool
    rollback_exact: bool


class Lineage:
    def __init__(self, *, consolidation: bool, replay: bool, rollback: bool) -> None:
        self.table = Table()
        self.consolidation = consolidation
        self.replay = replay
        self.rollback = rollback
        self.acquired: list[Skill] = []
        self.records: list[AcquisitionRecord] = []

    def _retention_failures(self, skills: Sequence[Skill]) -> int:
        """Checked on examples only; holdouts belong to the evaluator."""

        return sum(
            1 for skill in skills
            if any(
                self.table.lookup(skill.index, key) != skill.expected(key)
                for key in skill.examples
            )
        )

    def _install(self, skill: Skill, *, cheap: bool) -> int:
        (slope, offset), exceptions = induce(skill)
        written = 0

        rule = self.table.find_rule(slope, offset)
        if rule is not None:
            rule.contexts = rule.contexts | {skill.index}
        else:
            self.table.allocate(RuleEntry(frozenset({skill.index}), slope, offset))
            written += 1

        for key, output in sorted(exceptions.items()):
            existing = self.table.find_exception(key)
            if existing is not None and existing.output == output:
                existing.contexts = existing.contexts | {skill.index}
                continue
            if existing is not None and cheap:
                # The cheap path: rewrite the shared entry in place. It serves this skill and
                # silently breaks whichever earlier skill relied on the old output.
                existing.output = output
                existing.contexts = existing.contexts | {skill.index}
                continue
            self.table.allocate(ExceptionEntry(frozenset({skill.index}), key, output))
            written += 1
        return written

    def acquire(self, skill: Skill) -> AcquisitionRecord:
        before = copy.deepcopy(self.table)
        before_digest = before.digest()
        rejected_cheap = False
        rolled_back = False

        try:
            written = self._install(skill, cheap=True)
        except CapacityExhausted:
            written = 0
            self.table = copy.deepcopy(before)

        # Compared against the live table after the rejection is handled, never against the
        # checkpoint's own digest: that comparison is a tautology and can never fail.
        restored_digest: str | None = None
        if self.consolidation:
            replayed = self.acquired if self.replay else []
            if self._retention_failures(replayed) > 0:
                rejected_cheap = True
                if self.rollback:
                    self.table = copy.deepcopy(before)
                    rolled_back = True
                restored_digest = self.table.digest()
                try:
                    written = self._install(skill, cheap=False)
                except CapacityExhausted:
                    written = 0

        rollback_exact = restored_digest is None or restored_digest == before_digest
        self.acquired.append(skill)
        record = AcquisitionRecord(
            skill=skill.index, committed=True, slots_written=written,
            slots_used_after=self.table.used(),
            reused_rule=self.table.find_rule(*induce(skill)[0]) is not None and skill.index >= 3,
            rejected_cheap_path=rejected_cheap, rolled_back=rolled_back,
            rollback_exact=rollback_exact,
        )
        self.records.append(record)
        return record


def evaluate_holdouts(table: Table, skill: Skill) -> int:
    """Generalization on held-out keys. Evaluator-owned; the lineage never reads these."""

    return sum(
        1 for key in skill.holdouts if table.lookup(skill.index, key) == skill.expected(key)
    )


def evaluate_capability(table: Table, skill: Skill) -> int:
    """Retention is measured over the complete key set.

    A retained capability is the whole mapping, not just its held-out slice. Damage often lands on
    an exception key, which the split forces into the examples so the skill stays learnable; scoring
    retention on holdouts alone would make exactly that damage invisible. The lineage still
    consolidates against examples only and never reads holdouts.
    """

    return sum(
        1 for key in skill.keys if table.lookup(skill.index, key) == skill.expected(key)
    )


def run_arm(bank: Sequence[Skill], arm: str) -> dict[str, object]:
    if arm not in ARMS:
        raise RetentionError(f"unknown arm {arm!r}")
    lineage = Lineage(
        consolidation=arm != "no_consolidation",
        replay=arm != "no_replay",
        rollback=arm != "no_rollback",
    )

    timeline: list[dict[str, object]] = []
    for skill in bank:
        record = lineage.acquire(skill)
        retained = {
            earlier.index: evaluate_capability(lineage.table, earlier)
            for earlier in bank[:skill.index]
        }
        timeline.append({
            "skill": skill.index,
            "slots_written": record.slots_written,
            "slots_used_after": record.slots_used_after,
            "reused_rule": record.reused_rule,
            "rejected_cheap_path": record.rejected_cheap_path,
            "rolled_back": record.rolled_back,
            "rollback_exact": record.rollback_exact,
            "own_holdouts": evaluate_holdouts(lineage.table, skill),
            "own_total": len(skill.holdouts),
            "earlier_holdouts": retained,
        })

    lost = sum(
        1 for row in timeline
        for index, passed in row["earlier_holdouts"].items()
        if passed < len(bank[index].keys)
    )
    return {
        "arm": arm,
        "own_holdout_perfect": sum(
            1 for row in timeline if row["own_holdouts"] == row["own_total"]
        ),
        "capabilities_lost": lost,
        "final_retention_failures": sum(
            1 for skill in bank
            if evaluate_capability(lineage.table, skill) < len(skill.keys)
        ),
        "slots_used_final": timeline[-1]["slots_used_after"] if timeline else 0,
        "total_slots_written": sum(int(row["slots_written"]) for row in timeline),
        "rules_reused": sum(1 for row in timeline if row["reused_rule"]),
        "cheap_paths_rejected": sum(1 for row in timeline if row["rejected_cheap_path"]),
        "rollbacks": sum(1 for row in timeline if row["rolled_back"]),
        "rollback_mismatches": sum(1 for row in timeline if not row["rollback_exact"]),
        "timeline": timeline,
    }


@dataclass(frozen=True)
class RetentionVerdict:
    positive: bool
    reasons: tuple[str, ...] = ()
    replay_dependence: str = "unmeasured"


def evaluate(arms: Mapping[str, Mapping[str, object]], bank: Sequence[Skill]) -> RetentionVerdict:
    reasons: list[str] = []
    main = arms["lineage"]

    if main["own_holdout_perfect"] != SKILL_COUNT:
        reasons.append(
            f"lineage passed all holdouts on only {main['own_holdout_perfect']}/{SKILL_COUNT} skills"
        )
    if main["capabilities_lost"] != 0:
        reasons.append(f"lineage lost {main['capabilities_lost']} earlier capabilities")
    if main["final_retention_failures"] != 0:
        reasons.append(
            f"lineage ends with {main['final_retention_failures']} skills below full quality"
        )
    if main["rollback_mismatches"] != 0:
        reasons.append(f"lineage rollback was not byte-identical {main['rollback_mismatches']} times")
    if main["rollbacks"] < 1:
        reasons.append("lineage never rolled back, so exact rollback is untested")
    if main["rules_reused"] < 1:
        reasons.append("lineage reused no rule, so positive transfer is untested")
    naive_ceiling = SKILL_COUNT * (1 + IRREGULARS_PER_SKILL)
    if main["slots_used_final"] >= naive_ceiling:
        reasons.append(
            f"memory growth is not sublinear: {main['slots_used_final']} slots against a "
            f"private-slot ceiling of {naive_ceiling}"
        )

    if arms["no_consolidation"]["capabilities_lost"] < 1:
        reasons.append(
            "no_consolidation lost no capability, so the interference is not real and the "
            "retention claim is empty"
        )
    if arms["no_rollback"]["rollback_mismatches"] < 1:
        reasons.append("no_rollback showed no checkpoint mismatch, so rollback is untested")

    # Measured, never thresholded. Both readings were named in the frozen protocol.
    without_replay = arms["no_replay"]["capabilities_lost"]
    assert isinstance(without_replay, int)
    dependence = "structural" if without_replay == 0 else "replay_dependent"

    return RetentionVerdict(
        positive=not reasons, reasons=tuple(reasons), replay_dependence=dependence,
    )
