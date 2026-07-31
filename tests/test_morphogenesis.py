from metamorphosis.morphogenesis import (
    GATE_GRAPH_CATALOG,
    QUANTIZED_RECURRENT_CATALOG,
    REGISTER_CATALOG,
    AutonomousMorphogenesisEngine,
    CubeHeritage,
    GenericMorphogenesisEngine,
    NativeBody,
    PrimitiveCatalog,
    TransitionConstraint,
    learn_cube_heritage,
    native_body_to_dfa,
)
from metamorphosis.core import exact_equivalence, random_minimal_dfa
import random


def toggle_constraints():
    rows = []
    for state in (0, 1):
        for symbol in (0, 1):
            nxt = state ^ symbol
            rows.append(TransitionConstraint((state,), symbol, (nxt,), nxt))
    return rows


def monotone_constraints():
    rows = []
    for state in (0, 1):
        for symbol in (0, 1):
            nxt = state | symbol
            rows.append(TransitionConstraint((state,), symbol, (nxt,), nxt))
    return rows


def _development_heritage():
    dfas = [random_minimal_dfa(random.Random(11001 + i), 3, 8) for i in range(12)]
    return learn_cube_heritage(dfas, {"development_seeds": list(range(11001, 11013))})


def test_register_catalog_synthesizes_toggle():
    result = GenericMorphogenesisEngine(REGISTER_CATALOG).synthesize(toggle_constraints(), 1)
    assert result.reason == "exact"
    assert result.body is not None
    assert result.body.satisfies(toggle_constraints())


def test_gate_graph_catalog_synthesizes_toggle():
    result = GenericMorphogenesisEngine(GATE_GRAPH_CATALOG).synthesize(toggle_constraints(), 1)
    assert result.body is not None
    assert result.body.satisfies(toggle_constraints())


def test_quantized_catalog_can_compose_threshold_gates_for_toggle():
    result = GenericMorphogenesisEngine(QUANTIZED_RECURRENT_CATALOG).synthesize(toggle_constraints(), 1)
    assert result.body is not None
    assert result.body.satisfies(toggle_constraints())


def test_restricted_catalog_abstains_when_contract_is_unexpressible():
    restricted = PrimitiveCatalog(
        name="restricted_monotone",
        unary_ops=(),
        binary_ops=("and", "or"),
        costs={"input": 1, "state": 1, "const": 1, "and": 2, "or": 2},
        max_expression_cost=5,
    )
    impossible = GenericMorphogenesisEngine(restricted).synthesize(toggle_constraints(), 1)
    assert impossible.body is None
    assert impossible.reason == "unexpressible_under_catalog"
    possible = GenericMorphogenesisEngine(restricted).synthesize(monotone_constraints(), 1)
    assert possible.body is not None
    assert possible.body.satisfies(monotone_constraints())


def test_native_body_serialization_round_trip():
    body = GenericMorphogenesisEngine(REGISTER_CATALOG).synthesize(toggle_constraints(), 1).body
    assert body is not None
    restored = NativeBody.from_json(body.to_json())
    assert restored == body
    assert restored.run((1, 0, 1, 1))[1] == (1, 1, 0, 1)


def test_catalogue_is_task_agnostic_data():
    forbidden = {"dfa", "transition_table", "task_seed", "target"}
    assert not (set(REGISTER_CATALOG.__dict__) & forbidden)


def test_active_birth_discovers_opaque_dfa_and_grows_exact_body():
    target = random_minimal_dfa(random.Random(12011), 3, 8)
    birth = AutonomousMorphogenesisEngine(REGISTER_CATALOG, _development_heritage(), 7).birth(target.accepts)
    assert birth.status == "success"
    assert birth.discovered_dfa is not None
    assert exact_equivalence(target, birth.discovered_dfa)[0]
    assert birth.body is not None
    assert exact_equivalence(target, native_body_to_dfa(birth.body))[0]
    assert birth.behavioural_queries <= 10_000
    assert birth.native_components <= 256


def test_heritage_reduces_candidate_evaluations_without_encoding_target():
    target = random_minimal_dfa(random.Random(12071), 3, 8)
    inherited = AutonomousMorphogenesisEngine(REGISTER_CATALOG, _development_heritage(), 7).birth(target.accepts)
    fresh = AutonomousMorphogenesisEngine(REGISTER_CATALOG, None, 7).birth(target.accepts)
    assert inherited.status == fresh.status == "success"
    assert inherited.candidate_evaluations < fresh.candidate_evaluations
    raw = _development_heritage().to_json()
    assert "12071" not in raw
    assert "transitions" not in raw


def test_random_baseline_is_uninformed_in_same_cube_representation():
    target = random_minimal_dfa(random.Random(12049), 3, 8)
    inherited = AutonomousMorphogenesisEngine(REGISTER_CATALOG, _development_heritage(), 7).birth(target.accepts)
    random_birth = AutonomousMorphogenesisEngine(REGISTER_CATALOG, None, 7, random_search=True).birth(target.accepts)
    assert inherited.status == random_birth.status == "success"
    assert random_birth.candidate_evaluations >= 5 * inherited.candidate_evaluations


def test_inconsistent_contract_is_rejected_without_false_body():
    counts = {}
    def inconsistent(word):
        counts[word] = counts.get(word, 0) + 1
        if word == (1,):
            return counts[word] % 2 == 1
        return False
    birth = AutonomousMorphogenesisEngine(REGISTER_CATALOG, CubeHeritage(), 7).birth(inconsistent)
    assert birth.status == "abstained"
    assert "non_deterministic_contract" in birth.reason
    assert birth.body is None


def test_native_body_round_trip_preserves_exact_language():
    target = random_minimal_dfa(random.Random(12023), 3, 8)
    birth = AutonomousMorphogenesisEngine(GATE_GRAPH_CATALOG, _development_heritage(), 19).birth(target.accepts)
    assert birth.body is not None
    restored = NativeBody.from_json(birth.body.to_json())
    assert exact_equivalence(target, native_body_to_dfa(restored))[0]
