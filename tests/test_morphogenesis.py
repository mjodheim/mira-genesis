from metamorphosis.morphogenesis import (
    GATE_GRAPH_CATALOG,
    QUANTIZED_RECURRENT_CATALOG,
    REGISTER_CATALOG,
    GenericMorphogenesisEngine,
    NativeBody,
    PrimitiveCatalog,
    TransitionConstraint,
)


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
    engine = GenericMorphogenesisEngine(QUANTIZED_RECURRENT_CATALOG)
    result = engine.synthesize(toggle_constraints(), 1)
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
    keys = set(REGISTER_CATALOG.__dict__)
    assert not (keys & forbidden)
