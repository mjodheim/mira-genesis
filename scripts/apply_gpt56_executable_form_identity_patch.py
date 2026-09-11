from pathlib import Path

migration_path = Path('genesis/migration.py')
text = migration_path.read_text()
text = text.replace(
'''    permit_capability_loss: bool = False,\n    translation_provenance: Mapping[str, Any] | None = None,\n) -> dict[str, Any]:''',
'''    permit_capability_loss: bool = False,\n    translation_provenance: Mapping[str, Any] | None = None,\n    require_executable_target_change: bool = False,\n) -> dict[str, Any]:''',
1,
)
needle = '''    if not callable(body_factory):\n        raise MigrationError("the translation did not produce a body factory")\n\n    # Derived from what the translation actually invoked, not from what its caller declared.\n'''
replacement = '''    if not callable(body_factory):\n        raise MigrationError("the translation did not produce a body factory")\n\n    executable_form_change = None\n    if require_executable_target_change:\n        # A different configured target *string* is not evidence of a different executable form.\n        # Bind the claim to the resolved target artifacts that ConfiguredBody already content-addresses.\n        # This is checked before capability measurement or state assignment, so a relabel-only\n        # translation fails closed without half-migrating the lineage.\n        departure_artifact = artifact_digest_of(genesis.body_factory)\n        candidate_artifact = artifact_digest_of(body_factory)\n\n        def resolved_target(artifact):\n            if artifact.get("kind") != "configured_artifact":\n                return None\n            configuration = artifact.get("configuration")\n            if not isinstance(configuration, Mapping):\n                return None\n            target = configuration.get("target_artifact")\n            return dict(target) if isinstance(target, Mapping) else None\n\n        departure_target = resolved_target(departure_artifact)\n        arrival_target = resolved_target(candidate_artifact)\n        if departure_target is None or arrival_target is None:\n            raise MigrationError(\n                "an executable-form change requires reconstructible configured target identities"\n            )\n        if departure_target.get("artifact_digest") == arrival_target.get("artifact_digest"):\n            raise MigrationError(\n                "the translation changed the form label but not the resolved executable target artifact"\n            )\n        executable_form_change = {\n            "required": True,\n            "verified": True,\n            "identity_basis": "resolved_target_artifact_v1",\n            "departure_target_artifact": departure_target,\n            "arrival_target_artifact": arrival_target,\n        }\n\n    # Derived from what the translation actually invoked, not from what its caller declared.\n'''
if needle not in text:
    raise SystemExit('migration callable anchor not found')
text = text.replace(needle, replacement, 1)
needle = '''        "arrived_body_artifact": arrival_artifact,\n        "evolved_after_migration": False,\n    }\n    record["migration_digest"] = digest_of(record)\n'''
replacement = '''        "arrived_body_artifact": arrival_artifact,\n        "evolved_after_migration": False,\n    }\n    if executable_form_change is not None:\n        record["executable_form_change"] = executable_form_change\n    record["migration_digest"] = digest_of(record)\n'''
if needle not in text:
    raise SystemExit('migration record anchor not found')
text = text.replace(needle, replacement, 1)
migration_path.write_text(text)

campaign_path = Path('genesis/metamorphic_campaign.py')
text = campaign_path.read_text()
needle = '''        translation_provenance=provenance(\n            "host_written",\n            produced_by="fixed metamorphic campaign form-rebind adapter",\n            detail=FORM_REBIND_STRATEGY,\n        ),\n    )\n'''
replacement = '''        translation_provenance=provenance(\n            "host_written",\n            produced_by="fixed metamorphic campaign form-rebind adapter",\n            detail=FORM_REBIND_STRATEGY,\n        ),\n        require_executable_target_change=True,\n    )\n'''
if needle not in text:
    raise SystemExit('campaign migration call anchor not found')
campaign_path.write_text(text.replace(needle, replacement, 1))

test_path = Path('tests/test_genesis_persistent_metamorphic_campaign.py')
tests = test_path.read_text()
needle = '''    assert prefix["migration"]["capability"]["preserved"] is True\n    assert prefix["metamorphosis"]["succeeded"] is False\n'''
replacement = '''    assert prefix["migration"]["capability"]["preserved"] is True\n    form_change = prefix["migration"]["executable_form_change"]\n    assert form_change["verified"] is True\n    assert form_change["identity_basis"] == "resolved_target_artifact_v1"\n    assert (\n        form_change["departure_target_artifact"]["artifact_digest"]\n        != form_change["arrival_target_artifact"]["artifact_digest"]\n    )\n    assert prefix["metamorphosis"]["succeeded"] is False\n'''
if needle not in tests:
    raise SystemExit('positive campaign assertion anchor not found')
tests = tests.replace(needle, replacement, 1)
append = r'''


def test_campaign_refuses_form_relabel_when_resolved_interpreter_artifact_is_unchanged(monkeypatch, tmp_path):
    genesis = _genesis()
    stages = _stages()
    first = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=1,
    )
    assert first["next_stage"] == 1
    assert genesis.body_factory.target == programs.PROGRAM_TARGET
    generation_before = genesis.state["generation"]

    # Keep the admitted portable target *name* but bind that module attribute to the canonical
    # interpreter itself.  A string-only form check accepts this relabel.  The repaired migration
    # compares the content-addressed resolved target artifacts before committing any arrival state.
    monkeypatch.setattr(program_forms, "portable_program_body", programs.program_body)
    with pytest.raises(migration.MigrationError, match="resolved executable target artifact"):
        campaign.run(genesis, stages, checkpoint_directory=tmp_path, max_stages=1)

    assert genesis.body_factory.target == programs.PROGRAM_TARGET
    assert genesis.state["generation"] == generation_before
    cursor = campaign._validate_cursor(genesis, campaign.campaign_record(genesis, stages))
    assert cursor is not None and cursor["next_stage"] == 1
'''
if 'test_campaign_refuses_form_relabel_when_resolved_interpreter_artifact_is_unchanged' in tests:
    raise SystemExit('form relabel test already present')
test_path.write_text(tests + append)
