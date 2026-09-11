from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected exactly one replacement target, found {text.count(old)}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "genesis/program_forms.py",
    "from genesis.artifacts import ConfiguredBody\nfrom genesis.programs import PROGRAM_SCHEMA, program_operations_of\nfrom genesis.probe import resolve_registry\n",
    "from genesis.artifacts import ConfiguredBody\nfrom genesis.programs import PROGRAM_SCHEMA, program_operations_of\nfrom genesis.probe import resolve_registry\nfrom genesis.trust_root import artifact_digest_of\n",
)

replace_once(
    "genesis/program_forms.py",
    '''def portable_target_for(source_form: str) -> str:\n''',
    '''# Freeze the admitted interpreter identity at module import. A later rebinding of the symbol\n# under the same textual target must not turn a relabel into a form change.\nPORTABLE_PROGRAM_ARTIFACT = artifact_digest_of(portable_program_body)\n\n\ndef portable_target_for(source_form: str) -> str:\n''',
)

replace_once(
    "genesis/program_forms.py",
    '''    if target != "genesis.program_forms:portable_program_body":\n        raise PortableProgramError("discovered rebind capability returned an unsupported form")\n    return ConfiguredBody(\n''',
    '''    if target != PORTABLE_PROGRAM_TARGET:\n        raise PortableProgramError("discovered rebind capability returned an unsupported form")\n    # A target string is not executable identity. Resolve the symbol now and compare it with the\n    # interpreter artifact admitted when this module loaded. This rejects a host/runtime that keeps\n    # the portable target label but rebinds that label to the old interpreter (or anything else).\n    actual_target_artifact = artifact_digest_of(ConfiguredBody(target=str(target)).resolve())\n    if actual_target_artifact != PORTABLE_PROGRAM_ARTIFACT:\n        raise PortableProgramError(\n            "discovered rebind capability relabelled a different executable as the portable form"\n        )\n    return ConfiguredBody(\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''def _stage_record(genesis, stage: ObjectiveStage | FormMigrationStage) -> dict[str, Any]:\n''',
    '''def _configured_target_artifact(record: Mapping[str, Any], *, what: str) -> dict[str, Any]:\n    if record.get("kind") != "configured_artifact":\n        raise MetamorphicCampaignError(f"{what} is not a reconstructible configured executable")\n    configured = record.get("configuration")\n    if not isinstance(configured, Mapping):\n        raise MetamorphicCampaignError(f"{what} carries no configured executable identity")\n    target = configured.get("target_artifact")\n    if not isinstance(target, Mapping):\n        raise MetamorphicCampaignError(f"{what} carries no interpreter artifact identity")\n    return dict(target)\n\n\ndef _stage_record(genesis, stage: ObjectiveStage | FormMigrationStage) -> dict[str, Any]:\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''            "strategy": FORM_REBIND_STRATEGY,\n            "required_operation": program_forms.REBIND_OPERATION,\n''',
    '''            "strategy": FORM_REBIND_STRATEGY,\n            "required_operation": program_forms.REBIND_OPERATION,\n            "destination_form_artifact": dict(program_forms.PORTABLE_PROGRAM_ARTIFACT),\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''def _validate_cursor(genesis, campaign: Mapping[str, Any]) -> dict[str, Any] | None:\n''',
    '''def _validate_cursor_progress_journal(\n    genesis, campaign: Mapping[str, Any], artifact: Mapping[str, Any], next_stage: int\n) -> None:\n    """Require the persisted cursor to be backed by every runtime transition that reached it."""\n    evidence: list[Mapping[str, Any]] = []\n    for entry in genesis.journal.of_kind("observation"):\n        payload = entry.get("payload") or {}\n        if not isinstance(payload, Mapping):\n            continue\n        if payload.get("arm") != "metamorphic_campaign_cursor":\n            continue\n        if str(payload.get("campaign_digest") or "") != str(campaign["campaign_digest"]):\n            continue\n        evidence.append(payload)\n\n    actual_indices: list[int] = []\n    for payload in evidence:\n        try:\n            actual_indices.append(int(payload.get("next_stage", -1)))\n        except (TypeError, ValueError) as problem:\n            raise MetamorphicCampaignError(\n                "campaign cursor journal carries a malformed stage index"\n            ) from problem\n    expected_indices = list(range(int(next_stage) + 1))\n    if actual_indices != expected_indices:\n        raise MetamorphicCampaignError(\n            "campaign cursor progression is not backed by an exact journal transition sequence"\n        )\n    if not evidence or str(evidence[-1].get("cursor_digest") or "") != str(\n        artifact.get("cursor_digest") or ""\n    ):\n        raise MetamorphicCampaignError(\n            "campaign cursor head is not backed by its journaled transition"\n        )\n    stage_digests = list(campaign["stage_digests"])\n    for index, payload in enumerate(evidence):\n        expected_completed = "" if index == 0 else str(stage_digests[index - 1])\n        if str(payload.get("completed_stage_digest") or "") != expected_completed:\n            raise MetamorphicCampaignError(\n                "campaign cursor journal does not bind the stage it claims to have completed"\n            )\n\n\ndef _validate_cursor(genesis, campaign: Mapping[str, Any]) -> dict[str, Any] | None:\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''    if payload["completed_stage_digests"] != stage_digests[:next_stage]:\n        raise MetamorphicCampaignError(\n            "campaign cursor does not describe an exact completed prefix of its stage sequence"\n        )\n    payload["migration"] = _validate_migration_record(genesis, payload["migration"])\n''',
    '''    if payload["completed_stage_digests"] != stage_digests[:next_stage]:\n        raise MetamorphicCampaignError(\n            "campaign cursor does not describe an exact completed prefix of its stage sequence"\n        )\n    _validate_cursor_progress_journal(genesis, campaign, artifact, next_stage)\n    payload["migration"] = _validate_migration_record(genesis, payload["migration"])\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''            "next_stage": int(next_stage),\n            "cursor_digest": cursor["cursor_digest"],\n            "new_state_digest": genesis.state["state_digest"],\n''',
    '''            "next_stage": int(next_stage),\n            "completed_stage_digest": ""\n            if int(next_stage) == 0\n            else str(stage_digests[int(next_stage) - 1]),\n            "cursor_digest": cursor["cursor_digest"],\n            "new_state_digest": genesis.state["state_digest"],\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''def _run_form_migration(genesis, stage: FormMigrationStage) -> dict[str, Any]:\n    if not programs.program_operations_of(genesis.body_factory):\n        raise MetamorphicCampaignError(\n            "fixed form-rebind strategy requires a reconstructible generated-program current body"\n        )\n    substrate = stage.world.substrates.get(stage.substrate)\n''',
    '''def _run_form_migration(genesis, stage: FormMigrationStage) -> dict[str, Any]:\n    if not programs.program_operations_of(genesis.body_factory):\n        raise MetamorphicCampaignError(\n            "fixed form-rebind strategy requires a reconstructible generated-program current body"\n        )\n    departure_artifact = artifact_digest_of(genesis.body_factory)\n    departure_target = _configured_target_artifact(\n        departure_artifact, what="campaign migration departure body"\n    )\n    destination_target = dict(program_forms.PORTABLE_PROGRAM_ARTIFACT)\n    if departure_target == destination_target:\n        raise MetamorphicCampaignError(\n            "fixed form-rebind strategy would not change the executable interpreter artifact"\n        )\n    substrate = stage.world.substrates.get(stage.substrate)\n''',
)

replace_once(
    "genesis/metamorphic_campaign.py",
    '''    record = migration.migrate(\n        genesis,\n        substrate,\n        program_forms.translate_current_program,\n        used_operations=[program_forms.REBIND_OPERATION],\n        tasks=stage.world.tasks,\n        translation_provenance=provenance(\n            "host_written",\n            produced_by="fixed metamorphic campaign form-rebind adapter",\n            detail=FORM_REBIND_STRATEGY,\n        ),\n    )\n    return {\n        "type": "form_migration",\n        "strategy": FORM_REBIND_STRATEGY,\n        "probing": probing,\n        "migration": record,\n    }\n''',
    '''    record = migration.migrate(\n        genesis,\n        substrate,\n        program_forms.translate_current_program,\n        used_operations=[program_forms.REBIND_OPERATION],\n        tasks=stage.world.tasks,\n        translation_provenance=provenance(\n            "host_written",\n            produced_by="fixed metamorphic campaign form-rebind adapter",\n            detail=FORM_REBIND_STRATEGY,\n        ),\n    )\n    arrival_artifact = artifact_digest_of(genesis.body_factory)\n    arrival_target = _configured_target_artifact(\n        arrival_artifact, what="campaign migration arrival body"\n    )\n    if arrival_target != destination_target:\n        raise MetamorphicCampaignError(\n            "campaign migration arrived under an executable interpreter other than the admitted form"\n        )\n    if arrival_target == departure_target:\n        raise MetamorphicCampaignError(\n            "campaign migration changed a label but not the executable interpreter artifact"\n        )\n    return {\n        "type": "form_migration",\n        "strategy": FORM_REBIND_STRATEGY,\n        "probing": probing,\n        "migration": record,\n        "form_transition": {\n            "departure_target_artifact": departure_target,\n            "arrival_target_artifact": arrival_target,\n            "destination_form_artifact": destination_target,\n            "executable_target_changed": True,\n            "destination_matches_admitted_artifact": True,\n        },\n    }\n''',
)

# Extend the existing end-to-end regression with the two hostile cases from Hati's integrated audit.
path = Path("tests/test_genesis_persistent_metamorphic_campaign.py")
text = path.read_text(encoding="utf-8")
append = r'''


def test_campaign_refuses_forged_cursor_jump_without_journal_evidence(tmp_path):
    genesis = _genesis()
    campaign.run(
        genesis,
        _stages(),
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        checkpoint_directory=tmp_path,
        max_stages=0,
    )

    tools = []
    forged_cursor = None
    for tool in genesis.state["tools"]:
        if tool.get("name") == campaign.CURSOR_TOOL_NAME and tool.get("role") == campaign.CURSOR_ROLE:
            artifact = dict(tool["artifact"])
            artifact["next_stage"] = 2
            artifact["completed_stage_digests"] = list(artifact["stage_digests"][:2])
            payload = {key: value for key, value in artifact.items() if key != "cursor_digest"}
            artifact["cursor_digest"] = tr.digest_of(payload)
            forged_cursor = artifact
            tools.append({**tool, "artifact": artifact})
        else:
            tools.append(tool)
    assert forged_cursor is not None
    genesis.state = st.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"],
        generation=genesis.state["generation"],
    )

    with pytest.raises(campaign.MetamorphicCampaignError, match="journal transition sequence"):
        campaign.run(genesis, _stages(), checkpoint_directory=tmp_path)


def test_campaign_refuses_portable_label_rebound_to_old_interpreter(monkeypatch, tmp_path):
    genesis = _genesis()
    # The textual migration target remains genesis.program_forms:portable_program_body, but resolving
    # that symbol now yields the old per-request interpreter. The pre-repair string check accepted
    # exactly this relabel. The frozen executable artifact identity must refuse it before adoption.
    monkeypatch.setattr(program_forms, "portable_program_body", programs.program_body)
    with pytest.raises(Exception, match="relabelled a different executable"):
        campaign.run(
            genesis,
            _stages(),
            seed_policy=_seed_policy(),
            seed_meta_policy=_seed_meta(),
            max_rounds_per_objective=96,
            checkpoint_directory=tmp_path,
            max_stages=2,
        )
    assert genesis.body_factory.target != program_forms.PORTABLE_PROGRAM_TARGET
'''
if "test_campaign_refuses_forged_cursor_jump_without_journal_evidence" in text:
    raise SystemExit("campaign hostile tests already present")
path.write_text(text + append, encoding="utf-8")
