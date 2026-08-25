"""M110 - restored machinery against a consumer family that never produced it.

These tests exercise the mechanism, the three lemmas and the adapter boundary on small authored
worlds. They never touch the canonical population, the frozen protocol or the preserved result.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from metamorphosis import m109_runtime as producer
from metamorphosis import m110_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
PRODUCER_RESULT = ROOT / "experiments" / "M109" / "RESULT.json"


def _world(seed: int) -> dict:
    rng = random.Random(seed)
    documents = []
    side: dict[str, dict] = {}
    for index in range(runtime.DOCUMENT_COUNT):
        key = "k%d" % index
        document = {field: rng.choice(runtime.VALUES) for field in runtime.VISIBLE_FIELDS}
        document[runtime.REFERENCE_FIELD] = key
        documents.append(document)
        side[key] = {"zeta": rng.choice(runtime.VALUES), "note": "n%d" % index}
    return runtime.consumer_world("test-%04d" % seed, documents, side)


def _restored_rules() -> tuple[dict, dict]:
    evidence = json.loads(PRODUCER_RESULT.read_text(encoding="ascii"))["scientific_evidence"]
    return (
        producer.decode_rule(evidence["generation_one"]["acquisition"]["adopted_rule"]),
        producer.decode_rule(evidence["generation_two"]["acquisition"]["adopted_rule"]),
    )


@pytest.fixture(scope="module")
def arms() -> dict[str, dict]:
    first, second = _restored_rules()
    return {
        "M0": runtime.create_state(),
        "M1": runtime.create_state(rules=[first]),
        "M2": runtime.create_state(rules=[first, second]),
    }


# ---------------------------------------------------------------------------------------------
# Provenance: the arms are the producer's states, not equivalents.
# ---------------------------------------------------------------------------------------------


def test_restored_states_reproduce_the_frozen_producer_digests() -> None:
    evidence = json.loads(PRODUCER_RESULT.read_text(encoding="ascii"))["scientific_evidence"]
    first, second = _restored_rules()
    base = producer.create_state()
    assert base["state_digest"] == evidence["m0"]["state_digest"]
    generation_one = producer.create_state(
        base["operators"],
        signal_width=base["signal_width"],
        candidate_space=base["candidate_space"],
        rules=[first],
    )
    assert generation_one["state_digest"] == evidence["generation_one"]["state_digest"]
    stage_one = evidence["stage_one_resolution"]
    generation_two = producer.create_state(
        base["operators"],
        signal_width=stage_one["final_signal_width"],
        candidate_space=stage_one["final_candidate_space"],
        rules=[first, second],
    )
    assert generation_two["state_digest"] == evidence["generation_two"]["state_digest"]


def test_the_shared_vocabulary_is_imported_rather_than_restated() -> None:
    assert runtime.COMPONENTS is producer.COMPONENTS
    assert runtime.FEATURE_NAMES is producer.FEATURE_NAMES
    assert runtime.FEATURE_ROWS is producer.FEATURE_ROWS


def test_attribution_is_the_producer_cascade_on_every_row(arms: dict[str, dict]) -> None:
    for state in arms.values():
        for row in range(len(runtime.FEATURE_ROWS)):
            features = {"row_index": row}
            assert (
                runtime.attribute(state, features)
                == producer.attribute({"rules": state["rules"]}, features)
            )


# ---------------------------------------------------------------------------------------------
# The adapter is identical across arms, and non-informative about the answer.
# ---------------------------------------------------------------------------------------------


def test_arms_differ_only_in_the_rule_cascade(arms: dict[str, dict]) -> None:
    projections = {runtime.canonical_json(runtime.adapter_projection(s)) for s in arms.values()}
    assert len(projections) == 1
    keys = {tuple(sorted(state)) for state in arms.values()}
    assert len(keys) == 1


def test_row_five_is_where_the_first_feature_does_not_determine_the_component() -> None:
    """`g0` is true at rows 5 and 7, and the correct component differs between them."""
    assert runtime.FEATURE_ROWS[5] == (True, False, True)
    assert runtime.FEATURE_ROWS[7] == (True, True, True)


# ---------------------------------------------------------------------------------------------
# The three lemmas.
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 4])
def test_monotone_candidate_space_is_closed(seed: int) -> None:
    world = _world(seed)
    certificate = runtime.monotone_closure_certificate(runtime.create_state(), world)
    assert certificate["confirmed"] is True
    assert certificate["everything_reachable_is_monotone"] is True


@pytest.mark.parametrize("seed", [0, 4])
def test_every_image_member_is_a_function_of_the_visible_signals(seed: int) -> None:
    certificate = runtime.visible_function_certificate(_world(seed))
    assert certificate["confirmed"] is True
    assert set(certificate["violations_by_width"].values()) == {0}


@pytest.mark.parametrize("seed", [0, 4])
def test_the_image_is_a_fixed_point_across_the_declared_bounds(seed: int) -> None:
    certificate = runtime.fixed_point_certificate(_world(seed))
    assert certificate["confirmed"] is True
    assert certificate["bounds"] == list(runtime.FIXED_POINT_BOUNDS)


# ---------------------------------------------------------------------------------------------
# The two execution paths agree.
# ---------------------------------------------------------------------------------------------


def test_the_interpreter_and_the_rendered_python_agree() -> None:
    world = _world(0)
    state = runtime.create_state()
    image = runtime.state_image(state, world)
    assert image
    for values, witness in image.items():
        assert runtime.evaluate(state["operators"], witness, world) == values
        assert runtime.execute_rendered(state["operators"], witness, world) == values


def test_the_rendered_source_is_a_compilable_module() -> None:
    world = _world(0)
    state = runtime.create_state()
    witness = next(iter(runtime.state_image(state, world).values()))
    source = runtime.render_python(state["operators"], witness)
    assert source.startswith("def transform(document, side):")
    compile(source, "<test>", "exec")


# ---------------------------------------------------------------------------------------------
# Identity, decoding and failing closed.
# ---------------------------------------------------------------------------------------------


def test_state_round_trips_and_rejects_a_tampered_digest(arms: dict[str, dict]) -> None:
    payload = json.loads(runtime.encode_state(arms["M2"]).decode("ascii"))
    assert runtime.decode_state(payload)["state_digest"] == arms["M2"]["state_digest"]
    payload["interface_width"] = runtime.MAX_INTERFACE_WIDTH
    with pytest.raises(ValueError):
        runtime.decode_state(payload)


def test_a_tampered_rule_identity_fails_closed(arms: dict[str, dict]) -> None:
    payload = json.loads(runtime.encode_state(arms["M2"]).decode("ascii"))
    payload["rules"][-1]["rule_id"] = "rule-0000000000000000"
    with pytest.raises(ValueError):
        runtime.decode_state(payload)


def test_a_changed_feature_vocabulary_fails_closed(arms: dict[str, dict]) -> None:
    payload = json.loads(runtime.encode_state(arms["M0"]).decode("ascii"))
    payload["feature_vocabulary"] = list(payload["feature_vocabulary"])[::-1]
    with pytest.raises(ValueError):
        runtime.decode_state(payload)


def test_a_world_whose_reference_does_not_resolve_is_refused() -> None:
    world = _world(0)
    documents = [dict(item) for item in world["documents"]]
    documents[0][runtime.REFERENCE_FIELD] = "missing"
    with pytest.raises(ValueError):
        runtime.consumer_world("broken", documents, world["side"])


def test_a_demand_outside_the_value_chain_is_refused() -> None:
    with pytest.raises(ValueError):
        runtime.consumer_demand("bad", [0, 1, 2, 3, 9])


# ---------------------------------------------------------------------------------------------
# The chain the milestone exists to measure, on a small authored world.
# ---------------------------------------------------------------------------------------------


def test_the_transfer_chain_holds_on_an_authored_world(arms: dict[str, dict]) -> None:
    world = _world(0)
    census = runtime.attribution_census(world)
    assert census["ambiguous_rows"] == []
    for row in (7, 3, 5, 1):
        assert str(row) in census["canonical_targets"]

    def outcome(row: int, arm: str) -> bool:
        demand = runtime.consumer_demand(
            "row-%d" % row, census["canonical_targets"][str(row)]
        )
        report = runtime.resolve(arms[arm], world, demand)
        return bool(
            report["confirmed"]
            and report["construction"]["executes_to_target"]
            and report["construction"]["rendered_python_agrees"]
        )

    # inside the producer's reachable census: the restored cascades strictly add capability
    assert not outcome(7, "M0")
    assert outcome(7, "M1") and outcome(7, "M2")
    assert not outcome(3, "M0") and not outcome(3, "M1")
    assert outcome(3, "M2")
    # outside it: the restored cascades strictly remove capability
    assert outcome(5, "M0")
    assert not outcome(5, "M1") and not outcome(5, "M2")
    # and nothing the unmodified predecessor could already do is lost
    assert all(outcome(1, arm) for arm in ("M0", "M1", "M2"))


def test_reach_improve_is_strict_while_realized_competence_is_not(arms: dict[str, dict]) -> None:
    """The dissociation: capacity rises across the chain while row-5 competence falls."""
    world = _world(0)
    sets = {
        name: set(runtime.reach_improve(state, world, 2)["tables"])
        for name, state in arms.items()
    }
    assert sets["M0"] < sets["M1"] < sets["M2"]


def test_the_ground_truth_trial_reads_no_rule(arms: dict[str, dict]) -> None:
    """The consumer's trial must give the same answer whichever cascade the state holds."""
    world = _world(0)
    census = runtime.attribution_census(world)
    for row in (7, 3, 5, 1):
        target = census["canonical_targets"][str(row)]
        components = {
            runtime.component_trial(state, world, target)["component"]
            for state in arms.values()
        }
        assert len(components) == 1
