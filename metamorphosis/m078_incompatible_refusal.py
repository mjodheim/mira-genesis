"""Calibrated refusal when an opaque body cannot separate two inherited skills.

M068 induced adapters for four opaque bodies, all of them solvable. G1 also requires that an
*incompatible* body produce a calibrated refusal rather than an invented adapter, and that clause has
never been tested.

The hard part is making refusal non-trivial. A body with no fitting candidate would be refused by any
procedure that returns its best survivor, which measures nothing. Each incompatible body here
therefore carries one command whose behaviour is stitched together from two skills: it agrees with
skill *j* on every public input of *j* and with skill *k* on every public input of *k*, because those
public input sets are disjoint. Public evidence is then genuinely consistent with assigning that one
command to both skills, and only hidden inputs reveal the collapse.

A procedure that adopts the best public fit will emit a non-injective adapter and fail hidden
validation. A calibrated procedure notices that the best-fit assignment cannot be made injective and
refuses. Both outcomes are decided from public probing alone; hidden observations belong to the
evaluator and never reach the discoverer.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import permutations
from typing import Callable, Mapping, Sequence


PROTOCOL_SCHEMA = "m078-incompatible-refusal-protocol-v1"
GENERATOR_VERSION = 1

MODULUS = 251
COMMAND_SLOTS = 8
PUBLIC_INPUTS_PER_SKILL = 6
HIDDEN_OBSERVATIONS_PER_BODY = 12

BODY_CLASSES = ("compatible", "incompatible")
BODIES_PER_CLASS = 4

ARMS = ("discoverer", "always_refuse", "never_refuse")

REFUSED_UNDERDETERMINED = "refused_underdetermined"
REFUSED_EMPTY = "refused_empty_candidate_set"


def _alpha(value: int) -> int:
    return (value + 1) % MODULUS


def _beta(value: int) -> int:
    return (value * 3) % MODULUS


def _gamma(value: int) -> int:
    return (value ^ 0x5A) % MODULUS


def _delta(value: int) -> int:
    return (MODULUS - value) % MODULUS


SKILLS: Mapping[str, Callable[[int], int]] = {
    "alpha": _alpha,
    "beta": _beta,
    "gamma": _gamma,
    "delta": _delta,
}
SKILL_NAMES = tuple(SKILLS)


class RefusalError(ValueError):
    """Raised when a body, bank or arm contract is violated."""


def _digest(salt: bytes, body_class: str, index: int, tag: bytes = b"") -> bytes:
    return hashlib.sha256(
        salt + tag + body_class.encode("utf-8") + index.to_bytes(4, "big"),
    ).digest()


def _distinct_values(digest: bytes, count: int, modulus: int) -> list[int]:
    values: list[int] = []
    cursor = 0
    while len(values) < count:
        if cursor >= len(digest):
            digest = hashlib.sha256(digest).digest()
            cursor = 0
        candidate = digest[cursor] % modulus
        cursor += 1
        if candidate not in values:
            values.append(candidate)
    return values


@dataclass(frozen=True)
class SkillInputs:
    """Disjoint public and hidden input partitions, one per inherited skill."""

    public: Mapping[str, tuple[int, ...]]
    hidden: Mapping[str, tuple[int, ...]]

    @classmethod
    def build(cls, salt: bytes, body_class: str, index: int) -> "SkillInputs":
        digest = _digest(salt, body_class, index, b"inputs")
        needed = len(SKILL_NAMES) * (PUBLIC_INPUTS_PER_SKILL + 3)
        pool = _distinct_values(digest, needed, MODULUS)
        public: dict[str, tuple[int, ...]] = {}
        hidden: dict[str, tuple[int, ...]] = {}
        cursor = 0
        for name in SKILL_NAMES:
            public[name] = tuple(pool[cursor:cursor + PUBLIC_INPUTS_PER_SKILL])
            cursor += PUBLIC_INPUTS_PER_SKILL
            hidden[name] = tuple(pool[cursor:cursor + 3])
            cursor += 3
        return cls(public=public, hidden=hidden)

    def all_public(self) -> set[int]:
        return {value for values in self.public.values() for value in values}


@dataclass(frozen=True)
class Body:
    """An opaque body. The discoverer may only call it; it may not read these fields."""

    body_class: str
    index: int
    commands: tuple[int, ...]
    mask: int
    inputs: SkillInputs
    _operations: Mapping[int, Callable[[int], int]]
    aliased_pair: tuple[str, str] | None

    def call(self, command: int, value: int) -> int | None:
        """Public interface. Returns None for an unknown command, never raising."""

        operation = self._operations.get(command)
        if operation is None:
            return None
        return operation(value % MODULUS) ^ self.mask

    def commitment(self) -> str:
        payload = "|".join([
            self.body_class,
            str(self.index),
            ",".join(str(command) for command in self.commands),
            str(self.mask),
            ";".join(
                f"{name}:{','.join(str(v) for v in self.inputs.public[name])}"
                for name in SKILL_NAMES
            ),
            ";".join(
                f"{name}:{','.join(str(v) for v in self.inputs.hidden[name])}"
                for name in SKILL_NAMES
            ),
            "-".join(self.aliased_pair) if self.aliased_pair else "none",
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_compatible(salt: bytes, index: int) -> Body:
    digest = _digest(salt, "compatible", index, b"body")
    commands = tuple(_distinct_values(digest, len(SKILL_NAMES), COMMAND_SLOTS))
    mask = digest[16]
    inputs = SkillInputs.build(salt, "compatible", index)
    operations = {
        command: SKILLS[name] for command, name in zip(commands, SKILL_NAMES)
    }
    return Body(
        body_class="compatible", index=index, commands=commands, mask=mask,
        inputs=inputs, _operations=operations, aliased_pair=None,
    )


def _build_incompatible(salt: bytes, index: int) -> Body:
    """One command is stitched from two skills, so public evidence cannot separate them."""

    digest = _digest(salt, "incompatible", index, b"body")
    inputs = SkillInputs.build(salt, "incompatible", index)
    mask = digest[16]

    first = SKILL_NAMES[digest[17] % len(SKILL_NAMES)]
    remaining = [name for name in SKILL_NAMES if name != first]
    second = remaining[digest[18] % len(remaining)]
    intact = [name for name in SKILL_NAMES if name not in (first, second)]

    # Three commands only: one per intact skill, plus one shared stitched command.
    slots = _distinct_values(digest, 3, COMMAND_SLOTS)
    shared_command = slots[0]
    public_of_second = set(inputs.public[second])

    def stitched(value: int, _first: str = first, _second: str = second) -> int:
        # Agrees with the second skill exactly on that skill's public inputs, and with the first
        # everywhere else. Hidden inputs of the second skill therefore disagree.
        if value in public_of_second:
            return SKILLS[_second](value)
        return SKILLS[_first](value)

    operations: dict[int, Callable[[int], int]] = {shared_command: stitched}
    for command, name in zip(slots[1:], intact):
        operations[command] = SKILLS[name]

    return Body(
        body_class="incompatible", index=index, commands=tuple(slots), mask=mask,
        inputs=inputs, _operations=operations, aliased_pair=(first, second),
    )


def build_bank(salt: bytes) -> tuple[Body, ...]:
    """Emit exactly eight bodies, ascending by commitment inside each frozen class."""

    bank: list[Body] = []
    for body_class in BODY_CLASSES:
        builder = _build_compatible if body_class == "compatible" else _build_incompatible
        bodies = [builder(salt, index) for index in range(BODIES_PER_CLASS)]
        bodies.sort(key=lambda body: body.commitment())
        bank.extend(bodies)
    if len(bank) != len(BODY_CLASSES) * BODIES_PER_CLASS:
        raise RefusalError("materialized bank size drifted from the frozen protocol")
    return tuple(bank)


@dataclass(frozen=True)
class Adapter:
    mask: int
    assignment: Mapping[str, int]


@dataclass(frozen=True)
class Decision:
    """What one arm returned for one body. Refusal kinds are kept distinct on purpose."""

    adapter: Adapter | None
    refusal: str | None

    @property
    def refused(self) -> bool:
        return self.refusal is not None


def _fitting_commands(body: Body, mask: int, skill: str) -> list[int]:
    """Commands consistent with a skill on its public inputs only."""

    fits: list[int] = []
    for command in range(COMMAND_SLOTS):
        ok = True
        for value in body.inputs.public[skill]:
            reply = body.call(command, value)
            if reply is None or (reply ^ mask) != SKILLS[skill](value):
                ok = False
                break
        if ok:
            fits.append(command)
    return fits


def _injective_assignment(fits: Mapping[str, Sequence[int]]) -> dict[str, int] | None:
    for candidate in permutations(range(COMMAND_SLOTS), len(SKILL_NAMES)):
        assignment = dict(zip(SKILL_NAMES, candidate))
        if all(assignment[name] in fits[name] for name in SKILL_NAMES):
            return assignment
    return None


def discover(body: Body, *, refusal: str = "enabled") -> Decision:
    """Probe a body publicly and either adapt or refuse.

    Only `body.call` and the public inputs are consulted. Hidden observations, the body class and the
    aliased pair are never read, so a refusal is grounded in what probing revealed.
    """

    if refusal not in ("enabled", "forced", "disabled"):
        raise RefusalError(f"unknown refusal mode {refusal!r}")
    if refusal == "forced":
        return Decision(adapter=None, refusal=REFUSED_UNDERDETERMINED)

    viable: list[tuple[int, dict[str, list[int]]]] = []
    for mask in range(256):
        fits = {name: _fitting_commands(body, mask, name) for name in SKILL_NAMES}
        if all(fits[name] for name in SKILL_NAMES):
            viable.append((mask, fits))

    if not viable:
        # No command fits some skill under any transform. The protocol counts this as an empty
        # candidate set, not as a calibrated refusal.
        if refusal == "disabled":
            return Decision(adapter=Adapter(mask=0, assignment={
                name: 0 for name in SKILL_NAMES
            }), refusal=None)
        return Decision(adapter=None, refusal=REFUSED_EMPTY)

    for mask, fits in viable:
        assignment = _injective_assignment(fits)
        if assignment is not None:
            return Decision(adapter=Adapter(mask=mask, assignment=assignment), refusal=None)

    # Every skill has a public fit, yet no assignment separates them: the evidence is
    # under-determined rather than absent.
    if refusal == "disabled":
        mask, fits = viable[0]
        return Decision(adapter=Adapter(mask=mask, assignment={
            name: fits[name][0] for name in SKILL_NAMES
        }), refusal=None)
    return Decision(adapter=None, refusal=REFUSED_UNDERDETERMINED)


def validate_hidden(body: Body, adapter: Adapter) -> int:
    """Evaluator-owned. Counts hidden observations reproduced by an accepted adapter."""

    passed = 0
    for name in SKILL_NAMES:
        command = adapter.assignment[name]
        for value in body.inputs.hidden[name]:
            reply = body.call(command, value)
            if reply is not None and (reply ^ adapter.mask) == SKILLS[name](value):
                passed += 1
    return passed


def run_arm(bank: Sequence[Body], arm: str) -> dict[str, object]:
    if arm not in ARMS:
        raise RefusalError(f"unknown arm {arm!r}")
    mode = {
        "discoverer": "enabled", "always_refuse": "forced", "never_refuse": "disabled",
    }[arm]

    records: list[dict[str, object]] = []
    for body in bank:
        decision = discover(body, refusal=mode)
        hidden_passed = (
            validate_hidden(body, decision.adapter) if decision.adapter is not None else 0
        )
        records.append({
            "body_class": body.body_class,
            "commitment": body.commitment(),
            "refused": decision.refused,
            "refusal_kind": decision.refusal,
            "hidden_passed": hidden_passed,
            "hidden_total": HIDDEN_OBSERVATIONS_PER_BODY,
        })

    compatible = [r for r in records if r["body_class"] == "compatible"]
    incompatible = [r for r in records if r["body_class"] == "incompatible"]
    return {
        "arm": arm,
        "adapters_recovered": sum(1 for r in records if not r["refused"]),
        "compatible_adapters": sum(1 for r in compatible if not r["refused"]),
        "compatible_hidden_perfect": sum(
            1 for r in compatible
            if not r["refused"] and r["hidden_passed"] == HIDDEN_OBSERVATIONS_PER_BODY
        ),
        "false_refusals": sum(1 for r in compatible if r["refused"]),
        "true_refusals": sum(
            1 for r in incompatible if r["refusal_kind"] == REFUSED_UNDERDETERMINED
        ),
        "empty_set_refusals": sum(
            1 for r in records if r["refusal_kind"] == REFUSED_EMPTY
        ),
        "invented_adapters": sum(1 for r in incompatible if not r["refused"]),
        "incompatible_hidden_failures": sum(
            1 for r in incompatible
            if not r["refused"] and r["hidden_passed"] < HIDDEN_OBSERVATIONS_PER_BODY
        ),
        "records": records,
    }


@dataclass(frozen=True)
class RefusalVerdict:
    positive: bool
    reasons: tuple[str, ...] = ()


def evaluate(arms: Mapping[str, Mapping[str, object]]) -> RefusalVerdict:
    reasons: list[str] = []
    main = arms["discoverer"]

    if main["compatible_adapters"] != BODIES_PER_CLASS:
        reasons.append(
            f"discoverer adapted {main['compatible_adapters']}/{BODIES_PER_CLASS} compatible bodies"
        )
    if main["compatible_hidden_perfect"] != BODIES_PER_CLASS:
        reasons.append(
            f"only {main['compatible_hidden_perfect']} compatible adapters passed all hidden cases"
        )
    if main["false_refusals"] != 0:
        reasons.append(f"discoverer produced {main['false_refusals']} false refusals")
    if main["true_refusals"] != BODIES_PER_CLASS:
        reasons.append(
            f"discoverer produced {main['true_refusals']}/{BODIES_PER_CLASS} true refusals"
        )
    if main["invented_adapters"] != 0:
        reasons.append(f"discoverer invented {main['invented_adapters']} adapters")
    if main["empty_set_refusals"] != 0:
        reasons.append(
            f"{main['empty_set_refusals']} refusals came from an empty candidate set, "
            "which the protocol does not count as calibrated"
        )

    if arms["always_refuse"]["adapters_recovered"] != 0:
        reasons.append("always_refuse control recovered an adapter")
    if arms["never_refuse"]["incompatible_hidden_failures"] < 1:
        reasons.append(
            "never_refuse control did not fail hidden validation, so the public evidence "
            "was not actually insufficient"
        )

    return RefusalVerdict(positive=not reasons, reasons=tuple(reasons))
