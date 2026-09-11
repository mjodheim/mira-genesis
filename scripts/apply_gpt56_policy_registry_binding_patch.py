from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one replacement site, found {count}")
    file.write_text(text.replace(old, new, 1))


replace_once(
    "genesis/controller.py",
    '''    rationale: Mapping[str, Any] = field(default_factory=dict)
    depends_on: str = ""
    input_field: str = "input"
''',
    '''    rationale: Mapping[str, Any] = field(default_factory=dict)
    depends_on: str = ""
    input_field: str = "input"
    registry_reference: str = ""
''',
)
replace_once(
    "genesis/controller.py",
    '''    """Build a body from lineage-supplied program data and judge it through the normal cycle."""
    dependencies = (intent.depends_on,) if intent.depends_on else ()
    try:
        body = programs.artifact(
            registry_reference=here.probe_registry,
''',
    '''    """Build a body from lineage-supplied program data and judge it through the normal cycle.

    A search policy's registry is part of its machinery identity. The old executor ignored that
    identity and rebound the candidate to ``World.probe_registry`` instead, so a host could keep the
    same policy digest while changing what its operation names meant. Policy-produced intents now
    carry the registry they were interpreted under, and a conflicting world is refused before any
    candidate execution or generation budget spend.
    """
    dependencies = (intent.depends_on,) if intent.depends_on else ()
    registry_reference = str(intent.registry_reference or here.probe_registry)
    if intent.registry_reference and registry_reference != str(here.probe_registry):
        raise ControllerError(
            "generated body intent was produced under registry %r but this world offers %r"
            % (registry_reference, here.probe_registry)
        )
    try:
        body = programs.artifact(
            registry_reference=registry_reference,
''',
)
replace_once(
    "genesis/controller.py",
    '''                "operations": list(intent.operations),
                "input_field": intent.input_field,
            },
''',
    '''                "operations": list(intent.operations),
                "input_field": intent.input_field,
                "registry_reference": registry_reference,
            },
''',
)
# There are two generated_program records; update the return record too.
replace_once(
    "genesis/controller.py",
    '''            "operations": list(intent.operations),
            "input_field": intent.input_field,
        },
        "generated_body_artifact": artifact_digest_of(body),
''',
    '''            "operations": list(intent.operations),
            "input_field": intent.input_field,
            "registry_reference": registry_reference,
        },
        "generated_body_artifact": artifact_digest_of(body),
''',
)
replace_once(
    "genesis/controller.py",
    '''            "depends_on": intent.depends_on,
            "input_field": intent.input_field,
        }
''',
    '''            "depends_on": intent.depends_on,
            "input_field": intent.input_field,
            "registry_reference": intent.registry_reference,
        }
''',
)
replace_once(
    "genesis/controller.py",
    '''            depends_on=str(record.get("depends_on") or ""),
            input_field=str(record.get("input_field") or "input"),
        )
''',
    '''            depends_on=str(record.get("depends_on") or ""),
            input_field=str(record.get("input_field") or "input"),
            registry_reference=str(record.get("registry_reference") or ""),
        )
''',
)

replace_once(
    "genesis/policies.py",
    '''            "operations": list(operations),
            "input_field": policy["input_field"],
            "depends_on": "",
''',
    '''            "operations": list(operations),
            "input_field": policy["input_field"],
            "registry_reference": policy["registry_reference"],
            "depends_on": "",
''',
)
replace_once(
    "genesis/objective_policy_controller.py",
    '''            "operations": list(operations),
            "input_field": policy["input_field"],
            "depends_on": "",
''',
    '''            "operations": list(operations),
            "input_field": policy["input_field"],
            "registry_reference": policy["registry_reference"],
            "depends_on": "",
''',
)

Path("tests/test_genesis_policy_registry_binding.py").write_text(
    '''"""DEVELOPMENT regressions binding generated candidates to held policy registry identity."""\nfrom __future__ import annotations\n\nimport pytest\n\nfrom genesis import controller, development_bodies as bodies, objective_policy_controller as opc\nfrom genesis import policies, policy_controller, state as st, trust_root as tr\nfrom genesis.loop import Genesis\n\nHOST = tr.provenance("host_written", produced_by="policy registry binding fixture")\nTASKS = ({"task_id": "r0", "input": 1, "expected": 2},)\n\ndef grade(task, answer):\n    return "solved" if answer == task["expected"] else "unsolved"\n\ndef seed_body():\n    class Body:\n        def attempt(self, task):\n            return None\n    return Body()\n\ndef genesis():\n    state = st.create_state(\n        body_digest=tr.artifact_digest_of(seed_body)["artifact_digest"],\n        components=[{"name": "operator_table", "origin": "seed", "certificate": None, "provenance": HOST}],\n        vocabulary=[{"name": "axis", "origin": "seed", "certificate": None}],\n    )\n    return Genesis(\n        state=state, body_factory=seed_body,\n        budget=tr.Budget(limits={"generations": 8}),\n        isolation=tr.Isolation(), grade=grade,\n    )\n\ndef seed_policy():\n    return policies.create(\n        registry_reference=bodies.PROBE_REGISTRY, operation_names=("increment",),\n        max_length=1, ceiling_length=1, max_candidates=4,\n    )\n\ndef world(registry):\n    return controller.world(\n        tasks=TASKS, demands={}, substrates={}, probe_registry=registry,\n        component_operations={}, artifacts={}, grade=grade,\n    )\n\ndef test_objective_policy_intent_carries_its_registry_and_conflicting_world_is_refused():\n    g = genesis()\n    policy_controller.admit_seed_policy(g, seed_policy())\n    before_state = g.state["state_digest"]\n    before_spent = dict(g.budget.spent)\n    with pytest.raises(controller.ControllerError, match="produced under registry"):\n        opc.run_policy(\n            g, world("genesis.development_bodies:SUBSTRATE_OPERATIONS"), max_steps=1\n        )\n    assert g.state["state_digest"] == before_state\n    assert dict(g.budget.spent) == before_spent\n\ndef test_policy_generated_candidate_records_the_same_registry_it_was_interpreted_under():\n    g = genesis()\n    run = opc.run_policy(g, world(bodies.PROBE_REGISTRY), seed_policy=seed_policy(), max_steps=1)\n    step = run["steps"][0]\n    assert step["program"]["registry_reference"] == bodies.PROBE_REGISTRY\n    assert step["body_artifact"]["configuration"]["configuration"]["registry_reference"] == bodies.PROBE_REGISTRY\n\ndef test_manual_generate_transform_without_bound_registry_keeps_legacy_world_binding():\n    g = genesis()\n    intent = controller.GenerateTransform(name="legacy", operations=("increment",))\n    outcome = controller._generate_transform(g, world(bodies.PROBE_REGISTRY), intent)\n    assert outcome["generated_program"]["registry_reference"] == bodies.PROBE_REGISTRY\n\ndef test_generate_transform_intent_roundtrip_preserves_registry_identity():\n    intent = controller.GenerateTransform(\n        name="bound", operations=("increment",), registry_reference=bodies.PROBE_REGISTRY\n    )\n    rebuilt = controller._intent_from_record(controller._intent_record(intent))\n    assert rebuilt == intent\n'''
)
