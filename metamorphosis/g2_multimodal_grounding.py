"""Bounded multimodal state grounding with matched per-channel ablation.

The harness answers the G2 question in the endogenous track: can one persistent agent consume
language, structured state and pixels, emit both symbolic tool calls and embodied effector actions,
and show that each channel is causally required by exactly the family that depends on it?

Nothing here calls a foundation model, opens a network socket, writes outside the caller's chosen
path or touches a physical actuator. The effector is a coordinate inside an in-memory grid.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


PROTOCOL_SCHEMA = "g2-multimodal-grounding-protocol-v1"
GENERATOR_VERSION = 1

GRID_WIDTH = 6
GRID_HEIGHT = 6
CELL_PIXELS = 4
RASTER_WIDTH = GRID_WIDTH * CELL_PIXELS
RASTER_HEIGHT = GRID_HEIGHT * CELL_PIXELS
RASTER_BYTES = RASTER_WIDTH * RASTER_HEIGHT * 3

MARKER_TARGET = (255, 0, 255)
MARKER_EFFECTOR = (0, 255, 255)
NEAR_MISS_TRIPLES = (
    (255, 0, 254),
    (254, 0, 255),
    (0, 254, 255),
    (0, 255, 254),
)

FAMILIES = ("pixel_target", "structured_dial", "language_route")
EPISODES_PER_FAMILY = 12
ARMS = ("full", "pixel_ablated", "structure_ablated", "language_ablated", "blind_guess")

DECISIVE_CHANNEL = {
    "pixel_target": "pixels",
    "structured_dial": "structured",
    "language_route": "language",
}

STRUCTURE_SENTINEL = 0
LANGUAGE_ABLATION_TOKEN = "proceed"
DIAL_NAME = "alignment"

# Amended before episode materialization; see PROTOCOL.json "amendments". A guessing floor over a
# 7..12 modulus range is expected to land roughly one episode per twelve, so the original bound of
# one success across all 36 episodes was arithmetically unreachable for a faithful chance policy.
BLIND_GUESS_MAX_TOTAL = 8
BLIND_GUESS_MAX_PER_FAMILY = 4

NUMBER_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty",
)
WORD_TO_NUMBER = {word: index for index, word in enumerate(NUMBER_WORDS)}
LANGUAGE_OPERATIONS = ("add", "subtract", "multiply")

MOVES = ("step_north", "step_south", "step_east", "step_west")


class GroundingError(ValueError):
    """Raised when a channel, episode or arm contract is violated."""


def _digest(salt: bytes, family: str, index: int) -> bytes:
    return hashlib.sha256(salt + family.encode("utf-8") + index.to_bytes(4, "big")).digest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class Observation:
    """One arm's view of an episode. Absent channels are None only for the blind floor arm."""

    language: str | None
    structured: Mapping[str, int] | None
    pixels: bytes | None


@dataclass(frozen=True)
class AgentOutput:
    """Both required output classes, emitted every episode regardless of family."""

    tool_call: tuple[str, int] | None
    moves: tuple[str, ...]
    claimed_terminal_cell: tuple[int, int] | None


@dataclass(frozen=True)
class Episode:
    family: str
    index: int
    selection_digest: str
    instruction: str
    structured: Mapping[str, int]
    raster: bytes
    effector_origin: tuple[int, int]
    target_cell: tuple[int, int] | None
    expected_dial: int | None

    def commitment(self) -> str:
        return hashlib.sha256(_canonical_json({
            "family": self.family,
            "index": self.index,
            "selection_digest": self.selection_digest,
            "instruction": self.instruction,
            "structured": dict(self.structured),
            "raster_sha256": hashlib.sha256(self.raster).hexdigest(),
            "effector_origin": list(self.effector_origin),
            "target_cell": list(self.target_cell) if self.target_cell else None,
            "expected_dial": self.expected_dial,
        })).hexdigest()


def _blank_raster(base: tuple[int, int, int]) -> bytearray:
    raster = bytearray(RASTER_BYTES)
    for offset in range(0, RASTER_BYTES, 3):
        raster[offset:offset + 3] = bytes(base)
    return raster


def _paint_cell(raster: bytearray, row: int, col: int, triple: tuple[int, int, int]) -> None:
    if not (0 <= row < GRID_HEIGHT and 0 <= col < GRID_WIDTH):
        raise GroundingError(f"cell ({row}, {col}) is outside the frozen grid")
    for pixel_row in range(row * CELL_PIXELS, (row + 1) * CELL_PIXELS):
        for pixel_col in range(col * CELL_PIXELS, (col + 1) * CELL_PIXELS):
            offset = (pixel_row * RASTER_WIDTH + pixel_col) * 3
            raster[offset:offset + 3] = bytes(triple)


def _read_cell(raster: bytes, row: int, col: int) -> set[tuple[int, int, int]]:
    triples: set[tuple[int, int, int]] = set()
    for pixel_row in range(row * CELL_PIXELS, (row + 1) * CELL_PIXELS):
        for pixel_col in range(col * CELL_PIXELS, (col + 1) * CELL_PIXELS):
            offset = (pixel_row * RASTER_WIDTH + pixel_col) * 3
            triples.add(tuple(raster[offset:offset + 3]))
    return triples


def _locate_uniform_cell(raster: bytes, triple: tuple[int, int, int]) -> tuple[int, int] | None:
    """Return the single cell painted exactly and uniformly with ``triple``, else None."""

    found: list[tuple[int, int]] = []
    for row in range(GRID_HEIGHT):
        for col in range(GRID_WIDTH):
            if _read_cell(raster, row, col) == {triple}:
                found.append((row, col))
    if len(found) != 1:
        return None
    return found[0]


def _base_colour(digest: bytes) -> tuple[int, int, int]:
    # Kept dark so that no background byte can collide with a marker triple.
    return (digest[0] % 64, digest[1] % 64, digest[2] % 64)


def _distinct_cells(digest: bytes, count: int) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    cursor = 0
    while len(cells) < count:
        if cursor + 1 >= len(digest):
            digest = hashlib.sha256(digest).digest()
            cursor = 0
        candidate = (digest[cursor] % GRID_HEIGHT, digest[cursor + 1] % GRID_WIDTH)
        cursor += 2
        if candidate not in cells:
            cells.append(candidate)
    return cells


def _filler_instruction(token_count: int) -> str:
    return " ".join([LANGUAGE_ABLATION_TOKEN] * token_count)


def build_episode(salt: bytes, family: str, index: int) -> Episode:
    if family not in FAMILIES:
        raise GroundingError(f"unknown family {family!r}")
    digest = _digest(salt, family, index)
    raster = _blank_raster(_base_colour(digest))

    if family == "pixel_target":
        # Both the destination and the effector origin live only in the raster, so that the
        # structure and language ablations cannot touch this family.
        cells = _distinct_cells(digest, 2 + len(NEAR_MISS_TRIPLES))
        target_cell, origin = cells[0], cells[1]
        for offset, near_miss in enumerate(NEAR_MISS_TRIPLES):
            _paint_cell(raster, *cells[2 + offset], near_miss)
        _paint_cell(raster, *target_cell, MARKER_TARGET)
        _paint_cell(raster, *origin, MARKER_EFFECTOR)
        instruction = "move the effector onto the marked cell"
        structured = {
            "panel_id": digest[6] % 97,
            "frame_revision": digest[7] % 13,
            "channel_count": 3,
        }
        return Episode(
            family=family, index=index, selection_digest=digest.hex(),
            instruction=instruction, structured=structured, raster=bytes(raster),
            effector_origin=origin, target_cell=target_cell, expected_dial=None,
        )

    if family == "structured_dial":
        # The operands live only in structured state; the operation is standing agent competence
        # rather than an instruction, so the language ablation cannot touch this family.
        modulus = 7 + digest[3] % 6
        operand_a = digest[4] % 50
        operand_b = digest[5] % 50
        origin = _distinct_cells(digest, 1)[0]
        instruction = "read the panel and set the dial by the standing rule"
        structured = {
            "modulus": modulus,
            "operand_a": operand_a,
            "operand_b": operand_b,
            "panel_id": digest[6] % 97,
        }
        return Episode(
            family=family, index=index, selection_digest=digest.hex(),
            instruction=instruction, structured=structured, raster=bytes(raster),
            effector_origin=origin, target_cell=None,
            expected_dial=(operand_a + operand_b) % modulus,
        )

    # language_route: the operation and both operands are stated as words in the instruction and
    # appear nowhere else, so structure and pixel ablations cannot touch this family.
    operation = LANGUAGE_OPERATIONS[digest[3] % len(LANGUAGE_OPERATIONS)]
    left = digest[4] % len(NUMBER_WORDS)
    right = digest[5] % len(NUMBER_WORDS)
    modulus = 7 + digest[6] % 6
    origin = _distinct_cells(digest, 1)[0]
    instruction = (
        f"calibrate the {DIAL_NAME} dial {operation} {NUMBER_WORDS[left]} "
        f"and {NUMBER_WORDS[right]} modulo {NUMBER_WORDS[modulus]}"
    )
    structured = {
        "panel_id": digest[7] % 97,
        "decoy_operand": digest[8] % 50,
        "frame_revision": digest[9] % 13,
    }
    raw = {
        "add": left + right,
        "subtract": left - right,
        "multiply": left * right,
    }[operation]
    return Episode(
        family=family, index=index, selection_digest=digest.hex(),
        instruction=instruction, structured=structured, raster=bytes(raster),
        effector_origin=origin, target_cell=None, expected_dial=raw % modulus,
    )


def materialize_suite(salt: bytes) -> tuple[Episode, ...]:
    """Emit exactly 36 episodes, ascending by selection digest inside each frozen family."""

    suite: list[Episode] = []
    for family in FAMILIES:
        episodes = [
            build_episode(salt, family, index) for index in range(EPISODES_PER_FAMILY)
        ]
        episodes.sort(key=lambda episode: episode.selection_digest)
        suite.extend(episodes)
    if len(suite) != EPISODES_PER_FAMILY * len(FAMILIES):
        raise GroundingError("materialized suite size drifted from the frozen protocol")
    return tuple(suite)


def ablated_raster(salt: bytes) -> bytes:
    """A constant raster of identical length carrying neither marker triple."""

    filler = hashlib.sha256(salt + b"pixel-ablation").digest()
    raster = bytes(_blank_raster((filler[0] % 64, filler[1] % 64, filler[2] % 64)))
    if len(raster) != RASTER_BYTES:
        raise GroundingError("pixel ablation changed the raster byte length")
    for triple in (MARKER_TARGET, MARKER_EFFECTOR):
        if _locate_uniform_cell(raster, triple) is not None:
            raise GroundingError("pixel ablation leaked a marker triple")
    return raster


def observe(episode: Episode, arm: str, salt: bytes) -> Observation:
    """Project one episode through one arm, preserving length, key order and token count."""

    if arm not in ARMS:
        raise GroundingError(f"unknown arm {arm!r}")
    if arm == "blind_guess":
        return Observation(language=None, structured=None, pixels=None)

    language = episode.instruction
    structured: Mapping[str, int] = dict(episode.structured)
    pixels = episode.raster

    if arm == "pixel_ablated":
        pixels = ablated_raster(salt)
    elif arm == "structure_ablated":
        structured = {key: STRUCTURE_SENTINEL for key in episode.structured}
    elif arm == "language_ablated":
        language = _filler_instruction(len(episode.instruction.split()))

    observation = Observation(language=language, structured=structured, pixels=pixels)
    _assert_matched(episode, observation)
    return observation


def _assert_matched(episode: Episode, observation: Observation) -> None:
    if observation.pixels is None or len(observation.pixels) != len(episode.raster):
        raise GroundingError("ablation changed the raster byte length")
    if observation.structured is None or list(observation.structured) != list(episode.structured):
        raise GroundingError("ablation changed the structured key order")
    if observation.language is None:
        raise GroundingError("ablation removed the language channel entirely")
    if len(observation.language.split()) != len(episode.instruction.split()):
        raise GroundingError("ablation changed the instruction token count")


class GroundingAgent:
    """One persistent agent. Deterministic; it decodes channels and never guesses when blind.

    Persistence here is identity and audit, not adaptation: the agent records every decision but
    its policy does not change between episodes. No learning claim is attached to this harness.
    """

    def __init__(self) -> None:
        self.ledger: list[dict[str, object]] = []

    def act(self, episode_family: str, observation: Observation) -> AgentOutput:
        tool_call: tuple[str, int] | None = None
        moves: tuple[str, ...] = ()
        claimed: tuple[int, int] | None = None

        if observation.pixels is not None:
            origin = _locate_uniform_cell(observation.pixels, MARKER_EFFECTOR)
            target = _locate_uniform_cell(observation.pixels, MARKER_TARGET)
            if origin is not None and target is not None:
                moves = self._route(origin, target)
                claimed = target

        dial = self._read_dial(episode_family, observation)
        if dial is not None:
            tool_call = (DIAL_NAME, dial)

        self.ledger.append({
            "family": episode_family,
            "emitted_tool_call": tool_call is not None,
            "emitted_moves": len(moves),
        })
        return AgentOutput(tool_call=tool_call, moves=moves, claimed_terminal_cell=claimed)

    @staticmethod
    def _route(origin: tuple[int, int], target: tuple[int, int]) -> tuple[str, ...]:
        moves: list[str] = []
        row, col = origin
        while row > target[0]:
            moves.append("step_north")
            row -= 1
        while row < target[0]:
            moves.append("step_south")
            row += 1
        while col < target[1]:
            moves.append("step_east")
            col += 1
        while col > target[1]:
            moves.append("step_west")
            col -= 1
        return tuple(moves)

    @staticmethod
    def _read_dial(family: str, observation: Observation) -> int | None:
        if family == "structured_dial":
            fields = observation.structured
            if not fields:
                return None
            modulus = fields.get("modulus", STRUCTURE_SENTINEL)
            if modulus == STRUCTURE_SENTINEL:
                # Fail closed: a sentinel modulus is unreadable, not a licence to invent a value.
                return None
            return (fields.get("operand_a", 0) + fields.get("operand_b", 0)) % modulus
        if family == "language_route":
            if observation.language is None:
                return None
            return _parse_language_dial(observation.language)
        return None


def _parse_language_dial(instruction: str) -> int | None:
    tokens = instruction.split()
    operation = next((token for token in tokens if token in LANGUAGE_OPERATIONS), None)
    numbers = [WORD_TO_NUMBER[token] for token in tokens if token in WORD_TO_NUMBER]
    if operation is None or len(numbers) != 3:
        return None
    left, right, modulus = numbers
    if modulus == 0:
        return None
    raw = {"add": left + right, "subtract": left - right, "multiply": left * right}[operation]
    return raw % modulus


class BlindGuessAgent:
    """The measured chance floor: it knows which output class is scored and nothing else.

    It never receives language, structured state or pixels. For an embodied episode it drives the
    effector into the (0, 0) corner using the clamping rule and then walks to a salt-derived guessed
    cell, so its success probability is exactly 1/36 regardless of the true origin. For a dial
    episode it guesses uniformly over the frozen modulus range.
    """

    def __init__(self, salt: bytes) -> None:
        self.salt = salt
        self.counter = 0
        self.ledger: list[dict[str, object]] = []

    def act(self, episode_family: str, observation: Observation) -> AgentOutput:
        if any(
            channel is not None
            for channel in (observation.language, observation.structured, observation.pixels)
        ):
            raise GroundingError("the blind floor arm was handed an observation channel")
        digest = hashlib.sha256(
            self.salt + b"blind" + self.counter.to_bytes(4, "big"),
        ).digest()
        self.counter += 1

        tool_call: tuple[str, int] | None = None
        moves: tuple[str, ...] = ()
        if episode_family == "pixel_target":
            guess = (digest[0] % GRID_HEIGHT, digest[1] % GRID_WIDTH)
            reset = ["step_north"] * (GRID_HEIGHT - 1) + ["step_west"] * (GRID_WIDTH - 1)
            moves = tuple(
                reset + ["step_south"] * guess[0] + ["step_east"] * guess[1]
            )
        else:
            tool_call = (DIAL_NAME, digest[2] % (7 + 6))
        self.ledger.append({
            "family": episode_family,
            "emitted_tool_call": tool_call is not None,
            "emitted_moves": len(moves),
        })
        return AgentOutput(tool_call=tool_call, moves=moves, claimed_terminal_cell=None)


def apply_moves(origin: tuple[int, int], moves: Sequence[str]) -> tuple[int, int]:
    """Environment-owned transition. Out-of-grid steps are clamped, never wrapped."""

    row, col = origin
    for move in moves:
        if move not in MOVES:
            raise GroundingError(f"unknown embodied action {move!r}")
        if move == "step_north":
            row = max(0, row - 1)
        elif move == "step_south":
            row = min(GRID_HEIGHT - 1, row + 1)
        elif move == "step_east":
            col = min(GRID_WIDTH - 1, col + 1)
        else:
            col = max(0, col - 1)
    return (row, col)


def score_episode(episode: Episode, output: AgentOutput) -> bool:
    """Exact success. Embodied families are scored from terminal grid state only."""

    if episode.family == "pixel_target":
        terminal = apply_moves(episode.effector_origin, output.moves)
        return terminal == episode.target_cell
    if output.tool_call is None:
        return False
    name, value = output.tool_call
    return name == DIAL_NAME and value == episode.expected_dial


def run_arm(suite: Iterable[Episode], arm: str, salt: bytes) -> dict[str, object]:
    agent: GroundingAgent | BlindGuessAgent = (
        BlindGuessAgent(salt) if arm == "blind_guess" else GroundingAgent()
    )
    per_family: dict[str, int] = {family: 0 for family in FAMILIES}
    evaluated = 0
    for episode in suite:
        observation = (
            Observation(None, None, None) if arm == "blind_guess"
            else observe(episode, arm, salt)
        )
        output = agent.act(episode.family, observation)
        evaluated += 1
        if score_episode(episode, output):
            per_family[episode.family] += 1
    return {
        "arm": arm,
        "evaluated": evaluated,
        "successes_per_family": per_family,
        "successes_total": sum(per_family.values()),
        "emitted_tool_calls": sum(
            1 for record in agent.ledger if record["emitted_tool_call"]
        ),
        "emitted_move_sequences": sum(
            1 for record in agent.ledger if int(record["emitted_moves"]) > 0
        ),
    }


@dataclass(frozen=True)
class DissociationVerdict:
    positive: bool
    reasons: tuple[str, ...] = field(default=())


def evaluate_dissociation(arms: Mapping[str, Mapping[str, object]]) -> DissociationVerdict:
    """Check the preregistered double dissociation exactly, including the unchanged halves."""

    reasons: list[str] = []
    full = arms["full"]["successes_per_family"]
    assert isinstance(full, dict)

    for family in FAMILIES:
        if full[family] != EPISODES_PER_FAMILY:
            reasons.append(f"full arm scored {full[family]}/{EPISODES_PER_FAMILY} on {family}")

    ablation_for_channel = {
        "pixels": "pixel_ablated",
        "structured": "structure_ablated",
        "language": "language_ablated",
    }
    for family in FAMILIES:
        arm_name = ablation_for_channel[DECISIVE_CHANNEL[family]]
        scores = arms[arm_name]["successes_per_family"]
        assert isinstance(scores, dict)
        if scores[family] != 0:
            reasons.append(
                f"{arm_name} preserved its dependent family {family} at {scores[family]}"
            )
        for other in FAMILIES:
            if other == family:
                continue
            if scores[other] != full[other]:
                reasons.append(
                    f"{arm_name} changed non-dependent family {other}: "
                    f"{scores[other]} vs full {full[other]}"
                )

    blind_total = arms["blind_guess"]["successes_total"]
    blind_per_family = arms["blind_guess"]["successes_per_family"]
    assert isinstance(blind_total, int) and isinstance(blind_per_family, dict)
    if blind_total > BLIND_GUESS_MAX_TOTAL:
        reasons.append(
            f"blind_guess total {blind_total} exceeded the amended floor bound "
            f"{BLIND_GUESS_MAX_TOTAL}"
        )
    for family in FAMILIES:
        if blind_per_family[family] > BLIND_GUESS_MAX_PER_FAMILY:
            reasons.append(
                f"blind_guess {family} {blind_per_family[family]} exceeded the amended "
                f"per-family bound {BLIND_GUESS_MAX_PER_FAMILY}"
            )

    return DissociationVerdict(positive=not reasons, reasons=tuple(reasons))
