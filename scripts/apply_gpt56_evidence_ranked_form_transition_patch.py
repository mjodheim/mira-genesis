from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one target, found {text.count(old)}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "genesis/metamorphic_campaign.py",
    "from genesis import controller\n",
    "from genesis import controller\nfrom genesis.artifacts import ConfiguredBody\n",
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''@dataclass(frozen=True)\nclass FormMigrationStage:\n    """An environmental requirement to continue on another admitted substrate/form."""\n\n    world: controller.World\n    substrate: str\n    name: str = ""\n\n\ndef objective(world: controller.World, *, name: str = "") -> ObjectiveStage:\n''',
    '''@dataclass(frozen=True)\nclass FormMigrationStage:\n    """An explicit host-authored form transition kept for backwards-compatible DEVELOPMENT runs."""\n\n    world: controller.World\n    substrate: str\n    name: str = ""\n\n\n@dataclass(frozen=True)\nclass FormRequirementStage:\n    """Environmental form constraint; the runtime chooses whether to stay or migrate."""\n\n    world: controller.World\n    allowed_targets: tuple[str, ...]\n    name: str = ""\n\n\ndef objective(world: controller.World, *, name: str = "") -> ObjectiveStage:\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''def form_migration(\n    world: controller.World, substrate: str, *, name: str = ""\n) -> FormMigrationStage:\n    return FormMigrationStage(world=world, substrate=str(substrate), name=str(name))\n\n\ndef _assert_world_registry_matches_policy(genesis, world: controller.World, seed_policy=None) -> None:\n''',
    '''def form_migration(\n    world: controller.World, substrate: str, *, name: str = ""\n) -> FormMigrationStage:\n    return FormMigrationStage(world=world, substrate=str(substrate), name=str(name))\n\n\ndef require_form(\n    world: controller.World, allowed_targets: Sequence[str], *, name: str = ""\n) -> FormRequirementStage:\n    targets = tuple(sorted({str(target) for target in allowed_targets if str(target)}))\n    if not targets:\n        raise MetamorphicCampaignError("a form requirement admits no executable target")\n    return FormRequirementStage(world=world, allowed_targets=targets, name=str(name))\n\n\ndef _assert_world_registry_matches_policy(genesis, world: controller.World, seed_policy=None) -> None:\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''def _configured_target_artifact(record: Mapping[str, Any], *, what: str) -> dict[str, Any]:\n''',
    '''def _target_artifact(reference: str) -> dict[str, Any]:\n    try:\n        resolved = ConfiguredBody(target=str(reference)).resolve()\n    except Exception as problem:\n        raise MetamorphicCampaignError(\n            "form requirement names an executable target that cannot be resolved: %s" % reference\n        ) from problem\n    return artifact_digest_of(resolved)\n\n\ndef _configured_target_artifact(record: Mapping[str, Any], *, what: str) -> dict[str, Any]:\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''def _stage_record(genesis, stage: ObjectiveStage | FormMigrationStage) -> dict[str, Any]:\n''',
    '''def _stage_record(\n    genesis, stage: ObjectiveStage | FormMigrationStage | FormRequirementStage\n) -> dict[str, Any]:\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''    elif isinstance(stage, FormMigrationStage):\n        substrate = stage.world.substrates.get(stage.substrate)\n        if substrate is None:\n            raise MetamorphicCampaignError(\n                "campaign migration stage names absent substrate %r" % stage.substrate\n            )\n        payload = {\n            "schema": STAGE_SCHEMA,\n            "type": "form_migration",\n            "name": stage.name,\n            "verification_objective": opc.objective_record(genesis, stage.world),\n            "probe_registry": str(stage.world.probe_registry),\n            "substrate": _substrate_identity(substrate),\n            "strategy": FORM_REBIND_STRATEGY,\n            "required_operation": program_forms.REBIND_OPERATION,\n            "destination_form_artifact": dict(program_forms.PORTABLE_PROGRAM_ARTIFACT),\n        }\n    else:  # pragma: no cover - public typing plus explicit runtime refusal\n''',
    '''    elif isinstance(stage, FormMigrationStage):\n        substrate = stage.world.substrates.get(stage.substrate)\n        if substrate is None:\n            raise MetamorphicCampaignError(\n                "campaign migration stage names absent substrate %r" % stage.substrate\n            )\n        payload = {\n            "schema": STAGE_SCHEMA,\n            "type": "form_migration",\n            "name": stage.name,\n            "verification_objective": opc.objective_record(genesis, stage.world),\n            "probe_registry": str(stage.world.probe_registry),\n            "substrate": _substrate_identity(substrate),\n            "strategy": FORM_REBIND_STRATEGY,\n            "required_operation": program_forms.REBIND_OPERATION,\n            "destination_form_artifact": dict(program_forms.PORTABLE_PROGRAM_ARTIFACT),\n        }\n    elif isinstance(stage, FormRequirementStage):\n        allowed = [\n            {"target": target, "artifact": _target_artifact(target)}\n            for target in stage.allowed_targets\n        ]\n        allowed.sort(key=lambda item: (item["artifact"]["artifact_digest"], item["target"]))\n        substrates = [_substrate_identity(value) for value in stage.world.substrates.values()]\n        substrates.sort(key=lambda item: item["substrate_identity_digest"])\n        payload = {\n            "schema": STAGE_SCHEMA,\n            "type": "form_requirement",\n            "name": stage.name,\n            "verification_objective": opc.objective_record(genesis, stage.world),\n            "probe_registry": str(stage.world.probe_registry),\n            "allowed_forms": allowed,\n            "substrates": substrates,\n            "strategy": FORM_REBIND_STRATEGY,\n            "required_operation": program_forms.REBIND_OPERATION,\n        }\n    else:  # pragma: no cover - public typing plus explicit runtime refusal\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''def campaign_record(\n    genesis, stages: Sequence[ObjectiveStage | FormMigrationStage]\n) -> dict[str, Any]:\n''',
    '''def campaign_record(\n    genesis, stages: Sequence[ObjectiveStage | FormMigrationStage | FormRequirementStage]\n) -> dict[str, Any]:\n''',
)

marker = '''def _run_form_migration(genesis, stage: FormMigrationStage) -> dict[str, Any]:\n'''
insert = '''def _select_form_transition(\n    genesis, stage: FormRequirementStage, identity: Mapping[str, Any]\n) -> dict[str, Any]:\n    """Select stay vs admitted substrate migration by canonical unique strict maximum.\n\n    This is deliberately a tiny first architectural decision. The environment supplies a form\n    compatibility constraint, not the action. The runtime constructs every admitted action, scores\n    exact executable-target compatibility under one fixed rule, measures the complete set, and\n    refuses ties. Migration itself still goes through substrate discovery and capability-preservation\n    measurement before adoption.\n    """\n    current = _configured_target_artifact(\n        artifact_digest_of(genesis.body_factory), what="architectural transition current body"\n    )\n    allowed = [dict(item["artifact"]) for item in identity.get("allowed_forms", [])]\n    candidates: list[dict[str, Any]] = []\n\n    stay_payload = {\n        "kind": "stay",\n        "target_artifact": current,\n        "substrate": "",\n        "stage_digest": identity["stage_digest"],\n    }\n    candidates.append(\n        {\n            **stay_payload,\n            "candidate_digest": digest_of(stay_payload),\n            "compatibility_score": 1 if current in allowed else 0,\n        }\n    )\n\n    destination = dict(program_forms.PORTABLE_PROGRAM_ARTIFACT)\n    for substrate in identity.get("substrates", []):\n        payload = {\n            "kind": "migrate",\n            "target_artifact": destination,\n            "substrate": str(substrate["name"]),\n            "substrate_identity_digest": str(substrate["substrate_identity_digest"]),\n            "strategy": FORM_REBIND_STRATEGY,\n            "stage_digest": identity["stage_digest"],\n        }\n        candidates.append(\n            {\n                **payload,\n                "candidate_digest": digest_of(payload),\n                "compatibility_score": 1\n                if destination in allowed and destination != current\n                else 0,\n            }\n        )\n\n    candidates.sort(key=lambda item: item["candidate_digest"])\n    best = max(int(item["compatibility_score"]) for item in candidates)\n    winners = [item for item in candidates if int(item["compatibility_score"]) == best]\n    if best <= 0:\n        selected = None\n        reason = "no_viable_architectural_transition"\n    elif len(winners) != 1:\n        selected = None\n        reason = "ambiguous_no_strict_maximum"\n    else:\n        selected = winners[0]\n        reason = "unique_strict_maximum"\n\n    record = {\n        "schema": "genesis-architectural-transition-selection-v1",\n        "stage_digest": identity["stage_digest"],\n        "selection_rule": "unique_strict_maximum_form_compatibility_v1",\n        "candidates": candidates,\n        "selection_reason": reason,\n        "accepted": selected is not None,\n        "selected_candidate_digest": "" if selected is None else selected["candidate_digest"],\n        "selected_kind": "" if selected is None else selected["kind"],\n        "selected_substrate": "" if selected is None else selected.get("substrate", ""),\n    }\n    record["selection_digest"] = digest_of(record)\n    genesis.journal.append(\n        "observation",\n        genesis.state["generation"],\n        {\n            "arm": "architectural_transition_selection",\n            "stage_digest": identity["stage_digest"],\n            "selection_digest": record["selection_digest"],\n            "selection_rule": record["selection_rule"],\n            "selection_reason": reason,\n            "selected_candidate_digest": record["selected_candidate_digest"],\n            "candidate_digests": [item["candidate_digest"] for item in candidates],\n        },\n    )\n    return record\n\n\n'''
replace_once("genesis/metamorphic_campaign.py", marker, insert + marker)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''    stages: Sequence[ObjectiveStage | FormMigrationStage],\n''',
    '''    stages: Sequence[ObjectiveStage | FormMigrationStage | FormRequirementStage],\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''        elif isinstance(stage, FormMigrationStage):\n            if migration_record is not None:\n                raise MetamorphicCampaignError(\n                    "v1 persistent metamorphic campaign admits one form transition only"\n                )\n            _assert_world_registry_matches_policy(genesis, stage.world, seed_policy=seed_policy)\n            migration_result = _run_form_migration(genesis, stage)\n            migration_record = migration_result["migration"]\n            acquisition_frontier = len(genesis.state.get("acquisitions", []))\n            executed.append(\n                {\n                    "index": index,\n                    "stage_digest": identity["stage_digest"],\n                    **migration_result,\n                }\n            )\n        else:  # pragma: no cover\n            raise MetamorphicCampaignError("campaign contains an unrecognised stage")\n\n        cursor = _write_cursor(\n''',
    '''        elif isinstance(stage, FormMigrationStage):\n            if migration_record is not None:\n                raise MetamorphicCampaignError(\n                    "v1 persistent metamorphic campaign admits one form transition only"\n                )\n            _assert_world_registry_matches_policy(genesis, stage.world, seed_policy=seed_policy)\n            migration_result = _run_form_migration(genesis, stage)\n            migration_record = migration_result["migration"]\n            acquisition_frontier = len(genesis.state.get("acquisitions", []))\n            executed.append(\n                {\n                    "index": index,\n                    "stage_digest": identity["stage_digest"],\n                    **migration_result,\n                }\n            )\n        elif isinstance(stage, FormRequirementStage):\n            _assert_world_registry_matches_policy(genesis, stage.world, seed_policy=seed_policy)\n            selection = _select_form_transition(genesis, stage, identity)\n            entry: dict[str, Any] = {\n                "index": index,\n                "stage_digest": identity["stage_digest"],\n                "type": "form_requirement",\n                "transition_selection": selection,\n            }\n            executed.append(entry)\n            if not selection["accepted"]:\n                entry["stopped"] = True\n                entry["reason"] = selection["selection_reason"]\n                if checkpoint_path is not None:\n                    entry["campaign_checkpoint_digest"] = genesis.persist(checkpoint_path)["checkpoint"]\n                    entry["durable_before_next_stage"] = True\n                else:\n                    entry["campaign_checkpoint_digest"] = ""\n                    entry["durable_before_next_stage"] = False\n                break\n            if selection["selected_kind"] == "migrate":\n                if migration_record is not None:\n                    raise MetamorphicCampaignError(\n                        "v1 persistent metamorphic campaign admits one form transition only"\n                    )\n                selected_substrate = str(selection["selected_substrate"])\n                migration_stage = FormMigrationStage(\n                    world=stage.world, substrate=selected_substrate, name=stage.name\n                )\n                migration_result = _run_form_migration(genesis, migration_stage)\n                migration_record = migration_result["migration"]\n                acquisition_frontier = len(genesis.state.get("acquisitions", []))\n                entry["migration_result"] = migration_result\n                entry["selected_action"] = "migrate:%s" % selected_substrate\n            elif selection["selected_kind"] == "stay":\n                entry["selected_action"] = "stay"\n            else:  # pragma: no cover - selected kinds are constructed above\n                raise MetamorphicCampaignError("transition selector returned an unknown action")\n        else:  # pragma: no cover\n            raise MetamorphicCampaignError("campaign contains an unrecognised stage")\n\n        cursor = _write_cursor(\n''',
)

# Add integrated positive/negative regressions without changing the explicit migration tests.
path = Path("tests/test_genesis_persistent_metamorphic_campaign.py")
text = path.read_text(encoding="utf-8")
append = r'''


def _adaptive_stages(*, allowed_targets=(program_forms.PORTABLE_PROGRAM_TARGET,)):
    return (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.require_form(
            _world(OBJECTIVE_ONE, with_portable_substrate=True),
            allowed_targets,
            name="adapt-form-from-environmental-constraint",
        ),
        campaign.objective(_world(OBJECTIVE_TWO), name="extend-after-selected-transition"),
    )


def test_campaign_makes_first_architectural_form_decision_by_unique_strict_maximum(tmp_path):
    genesis = _genesis()
    prefix = campaign.run(
        genesis,
        _adaptive_stages(),
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=2,
    )
    assert prefix["next_stage"] == 2
    decision = prefix["executed"][1]
    assert decision["type"] == "form_requirement"
    assert decision["transition_selection"]["selection_reason"] == "unique_strict_maximum"
    assert decision["selected_action"] == "migrate:portable-generated-program"
    scores = {
        item["kind"]: item["compatibility_score"]
        for item in decision["transition_selection"]["candidates"]
    }
    assert scores["stay"] == 0
    assert scores["migrate"] == 1
    assert decision["migration_result"]["migration"]["capability"]["preserved"] is True

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    resumed = campaign.run(
        restored,
        _adaptive_stages(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
    )
    assert resumed["completed"] is True
    assert resumed["metamorphosis"]["succeeded"] is True
    assert restored.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(restored.body_factory.configuration["operations"]) == ("square", "square")
    selections = [
        entry for entry in restored.journal.of_kind("observation")
        if (entry.get("payload") or {}).get("arm") == "architectural_transition_selection"
    ]
    assert len(selections) == 1


def test_form_requirement_tie_adopts_no_architectural_transition_and_does_not_advance(tmp_path):
    genesis = _genesis()
    stages = _adaptive_stages(
        allowed_targets=(programs.PROGRAM_TARGET, program_forms.PORTABLE_PROGRAM_TARGET)
    )
    record = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=2,
    )
    assert record["next_stage"] == 1
    assert record["completed"] is False
    decision = record["executed"][-1]
    assert decision["type"] == "form_requirement"
    assert decision["transition_selection"]["accepted"] is False
    assert decision["transition_selection"]["selection_reason"] == "ambiguous_no_strict_maximum"
    assert len(genesis.journal.of_kind("migration")) == 0
    assert genesis.body_factory.target == programs.PROGRAM_TARGET


def test_form_requirement_can_select_stay_without_host_authored_migration(tmp_path):
    genesis = _genesis()
    stages = _adaptive_stages(allowed_targets=(programs.PROGRAM_TARGET,))
    record = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=2,
    )
    assert record["next_stage"] == 2
    decision = record["executed"][1]
    assert decision["selected_action"] == "stay"
    assert decision["transition_selection"]["selection_reason"] == "unique_strict_maximum"
    assert len(genesis.journal.of_kind("migration")) == 0
    assert genesis.body_factory.target == programs.PROGRAM_TARGET
'''
if "test_campaign_makes_first_architectural_form_decision_by_unique_strict_maximum" in text:
    raise SystemExit("architectural transition tests already present")
path.write_text(text + append, encoding="utf-8")
