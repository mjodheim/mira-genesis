"""Regressions for the bounded G2 multimodal grounding harness."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from metamorphosis.m076_multimodal_grounding import (
    ARMS,
    BLIND_GUESS_MAX_PER_FAMILY,
    BLIND_GUESS_MAX_TOTAL,
    DECISIVE_CHANNEL,
    EPISODES_PER_FAMILY,
    FAMILIES,
    GRID_HEIGHT,
    GRID_WIDTH,
    MARKER_EFFECTOR,
    MARKER_TARGET,
    NEAR_MISS_TRIPLES,
    RASTER_BYTES,
    AgentOutput,
    BlindGuessAgent,
    GroundingAgent,
    GroundingError,
    Observation,
    _locate_uniform_cell,
    ablated_raster,
    apply_moves,
    evaluate_dissociation,
    materialize_suite,
    observe,
    run_arm,
    score_episode,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "experiments/M076/PROTOCOL.json"
COMMITMENT_PATH = ROOT / "experiments/M076/EPISODE_COMMITMENT.json"
RESULT_PATH = ROOT / "experiments/M076/RESULT.json"


@pytest.fixture(scope="module")
def protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def salt(protocol: dict) -> bytes:
    return bytes.fromhex(protocol["episode_generation"]["salt_hex"])


@pytest.fixture(scope="module")
def suite(salt: bytes) -> tuple:
    return materialize_suite(salt)


def test_suite_shape_and_ordering(suite: tuple) -> None:
    assert len(suite) == EPISODES_PER_FAMILY * len(FAMILIES)
    for family in FAMILIES:
        digests = [ep.selection_digest for ep in suite if ep.family == family]
        assert len(digests) == EPISODES_PER_FAMILY
        assert digests == sorted(digests)


def test_suite_is_deterministic(salt: bytes, suite: tuple) -> None:
    replay = materialize_suite(salt)
    assert [ep.commitment() for ep in replay] == [ep.commitment() for ep in suite]


def test_every_raster_has_the_frozen_length(suite: tuple) -> None:
    assert {len(ep.raster) for ep in suite} == {RASTER_BYTES}


def test_only_the_pixel_family_carries_markers(suite: tuple) -> None:
    for episode in suite:
        has_target = _locate_uniform_cell(episode.raster, MARKER_TARGET) is not None
        has_effector = _locate_uniform_cell(episode.raster, MARKER_EFFECTOR) is not None
        assert has_target == has_effector == (episode.family == "pixel_target")


def test_pixel_family_target_is_absent_from_other_channels(suite: tuple) -> None:
    """The destination must not leak into structured state or the instruction."""

    for episode in (ep for ep in suite if ep.family == "pixel_target"):
        row, col = episode.target_cell
        assert row not in episode.structured.values() or "row" not in episode.structured
        assert str(row) not in episode.instruction
        assert str(col) not in episode.instruction
        assert "target" not in episode.structured


def test_marker_decoding_is_exact_not_approximate(suite: tuple) -> None:
    """Near-miss triples differ by one byte and must never be read as a marker."""

    for triple in NEAR_MISS_TRIPLES:
        assert triple not in (MARKER_TARGET, MARKER_EFFECTOR)
        for episode in (ep for ep in suite if ep.family == "pixel_target"):
            located = _locate_uniform_cell(episode.raster, triple)
            if located is not None:
                assert located != episode.target_cell
                assert located != episode.effector_origin


def test_pixel_ablation_preserves_length_and_drops_markers(salt: bytes) -> None:
    raster = ablated_raster(salt)
    assert len(raster) == RASTER_BYTES
    assert _locate_uniform_cell(raster, MARKER_TARGET) is None
    assert _locate_uniform_cell(raster, MARKER_EFFECTOR) is None


@pytest.mark.parametrize("arm", [a for a in ARMS if a != "blind_guess"])
def test_ablations_are_matched(arm: str, suite: tuple, salt: bytes) -> None:
    """Byte length, key order and token count must survive every ablation."""

    for episode in suite:
        observation = observe(episode, arm, salt)
        assert len(observation.pixels) == len(episode.raster)
        assert list(observation.structured) == list(episode.structured)
        assert len(observation.language.split()) == len(episode.instruction.split())


def test_blind_arm_rejects_any_channel(salt: bytes) -> None:
    agent = BlindGuessAgent(salt)
    with pytest.raises(GroundingError):
        agent.act("pixel_target", Observation("hint", {"a": 1}, bytes(RASTER_BYTES)))


def test_embodied_scoring_ignores_the_agent_claim(suite: tuple) -> None:
    """A truthful claim with no moves must fail: success comes from terminal state only."""

    episode = next(ep for ep in suite if ep.family == "pixel_target")
    assert episode.target_cell != episode.effector_origin
    liar = AgentOutput(tool_call=None, moves=(), claimed_terminal_cell=episode.target_cell)
    assert score_episode(episode, liar) is False


def test_apply_moves_clamps_at_the_border() -> None:
    assert apply_moves((0, 0), ["step_north"] * 5) == (0, 0)
    assert apply_moves((0, 0), ["step_west"] * 5) == (0, 0)
    corner = apply_moves((0, 0), ["step_south"] * 99 + ["step_east"] * 99)
    assert corner == (GRID_HEIGHT - 1, GRID_WIDTH - 1)


def test_apply_moves_rejects_unknown_actions() -> None:
    with pytest.raises(GroundingError):
        apply_moves((0, 0), ["teleport"])


def test_full_arm_reaches_exact_success(suite: tuple, salt: bytes) -> None:
    record = run_arm(suite, "full", salt)
    assert record["successes_total"] == EPISODES_PER_FAMILY * len(FAMILIES)
    assert record["emitted_tool_calls"] > 0
    assert record["emitted_move_sequences"] > 0


def test_double_dissociation_holds_exactly(suite: tuple, salt: bytes) -> None:
    arms = {arm: run_arm(suite, arm, salt) for arm in ARMS}
    full = arms["full"]["successes_per_family"]
    ablation_for = {
        "pixels": "pixel_ablated",
        "structured": "structure_ablated",
        "language": "language_ablated",
    }
    for family in FAMILIES:
        scores = arms[ablation_for[DECISIVE_CHANNEL[family]]]["successes_per_family"]
        assert scores[family] == 0
        for other in FAMILIES:
            if other != family:
                assert scores[other] == full[other]
    verdict = evaluate_dissociation(arms)
    assert verdict.positive, verdict.reasons


def test_blind_floor_stays_inside_its_bound(suite: tuple, salt: bytes) -> None:
    record = run_arm(suite, "blind_guess", salt)
    assert record["successes_total"] <= BLIND_GUESS_MAX_TOTAL
    for family in FAMILIES:
        assert record["successes_per_family"][family] <= BLIND_GUESS_MAX_PER_FAMILY


def test_blind_floor_is_low_across_alternative_salts(suite: tuple, salt: bytes) -> None:
    """A guessing policy must stay far below the informed arm on many independent draws."""

    totals = [
        run_arm(suite, "blind_guess", hashlib.sha256(
            salt + b"floor" + index.to_bytes(2, "big"),
        ).digest())["successes_total"]
        for index in range(50)
    ]
    assert max(totals) <= BLIND_GUESS_MAX_TOTAL
    assert sum(totals) / len(totals) < EPISODES_PER_FAMILY


def test_dissociation_rejects_a_uniformly_degrading_arm() -> None:
    """An arm that loses every family must not be reported as a dissociation."""

    full = {family: EPISODES_PER_FAMILY for family in FAMILIES}
    flat = {family: 0 for family in FAMILIES}
    arms = {
        "full": {"successes_per_family": dict(full), "successes_total": 36},
        "pixel_ablated": {"successes_per_family": dict(flat), "successes_total": 0},
        "structure_ablated": {"successes_per_family": dict(flat), "successes_total": 0},
        "language_ablated": {"successes_per_family": dict(flat), "successes_total": 0},
        "blind_guess": {"successes_per_family": dict(flat), "successes_total": 0},
    }
    verdict = evaluate_dissociation(arms)
    assert verdict.positive is False
    assert any("non-dependent" in reason for reason in verdict.reasons)


def test_grounding_agent_fails_closed_on_sentinel_structure(suite: tuple, salt: bytes) -> None:
    agent = GroundingAgent()
    episode = next(ep for ep in suite if ep.family == "structured_dial")
    output = agent.act(episode.family, observe(episode, "structure_ablated", salt))
    assert output.tool_call is None


def test_bound_suite_matches_the_replayed_suite(suite: tuple) -> None:
    commitment = json.loads(COMMITMENT_PATH.read_text(encoding="utf-8"))
    assert [ep.commitment() for ep in suite] == [
        record["commitment"] for record in commitment["episodes"]
    ]


def test_preserved_result_is_reproducible(suite: tuple, salt: bytes) -> None:
    preserved = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    arms = {arm: run_arm(suite, arm, salt) for arm in ARMS}
    for arm in ARMS:
        assert preserved["arms"][arm]["successes_per_family"] == arms[arm][
            "successes_per_family"
        ]
    assert preserved["dissociation_positive"] is True
    assert preserved["attempt"] == 1
    assert preserved["retried"] is False
    assert preserved["external_model_called"] is False


def test_result_claim_boundary_stays_bounded() -> None:
    preserved = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    boundary = preserved["claim_boundary"]
    assert boundary["agi_evidence"] is False
    assert boundary["closes_generality_gate_g2"] is False
    assert boundary["genesis_gate_2_evidence"] is False
    assert boundary["establishes_cross_domain_transfer"] is False


def test_grid_constants_match_the_protocol(protocol: dict) -> None:
    grid = protocol["grid"]
    assert grid["width_cells"] == GRID_WIDTH
    assert grid["height_cells"] == GRID_HEIGHT
    assert grid["cell_count"] == GRID_WIDTH * GRID_HEIGHT


def test_amendment_is_recorded_as_pre_materialization(protocol: dict) -> None:
    amendments = protocol["amendments"]
    assert amendments, "the recorded threshold amendment must remain visible"
    for amendment in amendments:
        assert amendment["applied_before_episode_materialization"] is True
        assert amendment["applied_before_any_recorded_result"] is True
        assert amendment["reason"]
