from pathlib import Path

campaign_path = Path("genesis/metamorphic_campaign.py")
text = campaign_path.read_text()
start = text.index("def _select_form_transition(")
end = text.index("\ndef _run_form_migration", start)
new_selector = '''def _select_form_transition(
    genesis, stage: FormRequirementStage, identity: Mapping[str, Any]
) -> dict[str, Any]:
    """Select stay vs admitted substrate migration by complete capability-aware comparison.

    Target compatibility alone is not migration viability.  Every migration whose target would
    otherwise score positively must first establish the fixed ``rebind_program`` capability through
    the ordinary probe mechanism.  The complete relevant probe cost is checked before the first
    probe so host/container ordering cannot decide which candidate gets measured when budget is
    tight.  Candidates whose target is already incompatible need no probe because the missing
    capability cannot change their zero score.
    """
    current = _configured_target_artifact(
        artifact_digest_of(genesis.body_factory), what="architectural transition current body"
    )
    allowed = [dict(item["artifact"]) for item in identity.get("allowed_forms", [])]
    candidates: list[dict[str, Any]] = []

    stay_payload = {
        "kind": "stay",
        "target_artifact": current,
        "substrate": "",
        "stage_digest": identity["stage_digest"],
    }
    candidates.append(
        {
            **stay_payload,
            "candidate_digest": digest_of(stay_payload),
            "capability_probe": None,
            "required_capability_available": None,
            "compatibility_score": 1 if current in allowed else 0,
        }
    )

    destination = dict(program_forms.PORTABLE_PROGRAM_ARTIFACT)
    migration_target_relevant = destination in allowed and destination != current
    substrate_records = [dict(item) for item in identity.get("substrates", [])]
    probe_cost_required = (
        sum(int(item.get("probe_cost", 0)) for item in substrate_records)
        if migration_target_relevant
        else 0
    )
    if probe_cost_required:
        remaining = genesis.budget.remaining("probes")
        if remaining < probe_cost_required:
            raise MetamorphicCampaignError(
                "complete architectural transition comparison requires %d probe units but only %d remain"
                % (probe_cost_required, remaining)
            )

    probe_results: dict[str, dict[str, Any]] = {}
    if migration_target_relevant:
        # ``identity['substrates']`` is already canonicalised by substrate identity digest.  Verify
        # that the executable World still reproduces those identities before spending anything on
        # each candidate, then probe every relevant candidate exactly once.
        for substrate_record in substrate_records:
            name = str(substrate_record.get("name") or "")
            substrate = stage.world.substrates.get(name)
            if substrate is None:
                raise MetamorphicCampaignError(
                    "architectural transition candidate substrate %r disappeared before scoring" % name
                )
            if _substrate_identity(substrate) != substrate_record:
                raise MetamorphicCampaignError(
                    "architectural transition candidate substrate %r no longer matches campaign identity"
                    % name
                )
            probe_results[name] = migration.discover(
                substrate,
                [program_forms.REBIND_OPERATION],
                genesis.budget,
            )

    for substrate_record in substrate_records:
        name = str(substrate_record["name"])
        payload = {
            "kind": "migrate",
            "target_artifact": destination,
            "substrate": name,
            "substrate_identity_digest": str(substrate_record["substrate_identity_digest"]),
            "strategy": FORM_REBIND_STRATEGY,
            "stage_digest": identity["stage_digest"],
        }
        probing = probe_results.get(name)
        capability_available = (
            probing is not None
            and probing.get("probed") == [program_forms.REBIND_OPERATION]
            and probing.get("found") == [program_forms.REBIND_OPERATION]
        )
        candidates.append(
            {
                **payload,
                "candidate_digest": digest_of(payload),
                "capability_probe": probing,
                "required_capability_available": capability_available
                if migration_target_relevant
                else None,
                "compatibility_score": 1
                if migration_target_relevant and capability_available
                else 0,
            }
        )

    candidates.sort(key=lambda item: item["candidate_digest"])
    best = max(int(item["compatibility_score"]) for item in candidates)
    winners = [item for item in candidates if int(item["compatibility_score"]) == best]
    if best <= 0:
        selected = None
        reason = "no_viable_architectural_transition"
    elif len(winners) != 1:
        selected = None
        reason = "ambiguous_no_strict_maximum"
    else:
        selected = winners[0]
        reason = "unique_strict_maximum"

    record = {
        "schema": "genesis-architectural-transition-selection-v2",
        "stage_digest": identity["stage_digest"],
        "selection_rule": "unique_strict_maximum_form_compatibility_with_capability_probe_v1",
        "candidates": candidates,
        "complete_relevant_candidate_set_probed": True,
        "probe_cost_required": probe_cost_required,
        "selection_reason": reason,
        "accepted": selected is not None,
        "selected_candidate_digest": "" if selected is None else selected["candidate_digest"],
        "selected_kind": "" if selected is None else selected["kind"],
        "selected_substrate": "" if selected is None else selected.get("substrate", ""),
    }
    record["selection_digest"] = digest_of(record)
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "architectural_transition_selection",
            "stage_digest": identity["stage_digest"],
            "selection_digest": record["selection_digest"],
            "selection_rule": record["selection_rule"],
            "selection_reason": reason,
            "selected_candidate_digest": record["selected_candidate_digest"],
            "candidate_digests": [item["candidate_digest"] for item in candidates],
            "probe_cost_required": probe_cost_required,
        },
    )
    return record
'''
text = text[:start] + new_selector + text[end:]

start = text.index("def _run_form_migration(")
end = text.index("\ndef run(", start)
new_migration = '''def _run_form_migration(
    genesis,
    stage: FormMigrationStage,
    *,
    preflight_probe: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not programs.program_operations_of(genesis.body_factory):
        raise MetamorphicCampaignError(
            "fixed form-rebind strategy requires a reconstructible generated-program current body"
        )
    departure_artifact = artifact_digest_of(genesis.body_factory)
    departure_target = _configured_target_artifact(
        departure_artifact, what="campaign migration departure body"
    )
    destination_target = dict(program_forms.PORTABLE_PROGRAM_ARTIFACT)
    if departure_target == destination_target:
        raise MetamorphicCampaignError(
            "fixed form-rebind strategy would not change the executable interpreter artifact"
        )
    substrate = stage.world.substrates.get(stage.substrate)
    if substrate is None:
        raise MetamorphicCampaignError("migration substrate disappeared before execution")
    if preflight_probe is None:
        probing = migration.discover(
            substrate,
            [program_forms.REBIND_OPERATION],
            genesis.budget,
        )
    else:
        probing = dict(preflight_probe)
        if (
            probing.get("substrate") != substrate.name
            or probing.get("probed") != [program_forms.REBIND_OPERATION]
            or probing.get("found") != [program_forms.REBIND_OPERATION]
            or program_forms.REBIND_OPERATION not in substrate.discovered
        ):
            raise MetamorphicCampaignError(
                "selected migration has no matching capability probe from architectural scoring"
            )
    if probing["found"] != [program_forms.REBIND_OPERATION]:
        raise MetamorphicCampaignError(
            "target substrate does not expose the fixed generated-program rebind capability"
        )
    record = migration.migrate(
        genesis,
        substrate,
        program_forms.translate_current_program,
        used_operations=[program_forms.REBIND_OPERATION],
        tasks=stage.world.tasks,
        translation_provenance=provenance(
            "host_written",
            produced_by="fixed metamorphic campaign form-rebind adapter",
            detail=FORM_REBIND_STRATEGY,
        ),
    )
    arrival_artifact = artifact_digest_of(genesis.body_factory)
    arrival_target = _configured_target_artifact(
        arrival_artifact, what="campaign migration arrival body"
    )
    if arrival_target != destination_target:
        raise MetamorphicCampaignError(
            "campaign migration arrived under an executable interpreter other than the admitted form"
        )
    if arrival_target == departure_target:
        raise MetamorphicCampaignError(
            "campaign migration changed a label but not the executable interpreter artifact"
        )
    return {
        "type": "form_migration",
        "strategy": FORM_REBIND_STRATEGY,
        "probing": probing,
        "migration": record,
        "form_transition": {
            "departure_target_artifact": departure_target,
            "arrival_target_artifact": arrival_target,
            "destination_form_artifact": destination_target,
            "executable_target_changed": True,
            "destination_matches_admitted_artifact": True,
        },
    }
'''
text = text[:start] + new_migration + text[end:]

old = '''                migration_result = _run_form_migration(genesis, migration_stage)\n                migration_record = migration_result["migration"]\n'''
new = '''                selected_candidates = [\n                    item\n                    for item in selection["candidates"]\n                    if item["candidate_digest"] == selection["selected_candidate_digest"]\n                ]\n                if len(selected_candidates) != 1:\n                    raise MetamorphicCampaignError(\n                        "architectural selection does not identify exactly one measured candidate"\n                    )\n                migration_result = _run_form_migration(\n                    genesis,\n                    migration_stage,\n                    preflight_probe=selected_candidates[0].get("capability_probe"),\n                )\n                migration_record = migration_result["migration"]\n'''
if old not in text:
    raise SystemExit("adaptive migration call anchor not found")
text = text.replace(old, new, 1)
campaign_path.write_text(text)

test_path = Path("tests/test_genesis_persistent_metamorphic_campaign.py")
tests = test_path.read_text()
tests = tests.replace("def _genesis():\n", "def _genesis(*, probes: int = 8):\n", 1)
tests = tests.replace('                "probes": 8,\n', '                "probes": probes,\n', 1)
append = r'''


def _form_requirement_world_with_substrates(substrates):
    return controller.world(
        tasks=OBJECTIVE_ONE,
        demands={},
        substrates={item.name: item for item in substrates},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={},
        artifacts={},
        grade=fixtures.grade_expected,
    )


def test_form_transition_scores_only_substrates_that_really_expose_rebind(tmp_path):
    genesis = _genesis()
    bad = migration.Substrate("bad-portable", {})
    good = migration.Substrate(
        "portable-generated-program",
        {program_forms.REBIND_OPERATION: program_forms.portable_target_for},
    )
    transition_world = _form_requirement_world_with_substrates((bad, good))
    stages = (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.require_form(
            transition_world,
            (program_forms.PORTABLE_PROGRAM_TARGET,),
            name="choose-only-capable-substrate",
        ),
    )
    record = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
    )
    decision = record["executed"][1]
    assert decision["selected_action"] == "migrate:portable-generated-program"
    migrations = {
        item["substrate"]: item
        for item in decision["transition_selection"]["candidates"]
        if item["kind"] == "migrate"
    }
    assert migrations["bad-portable"]["required_capability_available"] is False
    assert migrations["bad-portable"]["compatibility_score"] == 0
    assert migrations["bad-portable"]["capability_probe"]["found"] == []
    assert migrations["portable-generated-program"]["required_capability_available"] is True
    assert migrations["portable-generated-program"]["compatibility_score"] == 1
    assert migrations["portable-generated-program"]["capability_probe"]["found"] == [
        program_forms.REBIND_OPERATION
    ]
    # Both relevant candidates were measured once; execution reuses the winning probe rather than
    # charging the selected substrate a second time.
    assert genesis.budget.spent["probes"] == 2


def test_form_transition_with_only_incapable_substrate_refuses_before_execution(tmp_path):
    genesis = _genesis()
    bad = migration.Substrate("bad-portable", {})
    stages = (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.require_form(
            _form_requirement_world_with_substrates((bad,)),
            (program_forms.PORTABLE_PROGRAM_TARGET,),
            name="no-capable-transition",
        ),
    )
    record = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
    )
    assert record["next_stage"] == 1
    decision = record["executed"][-1]
    assert decision["transition_selection"]["selection_reason"] == "no_viable_architectural_transition"
    assert decision["transition_selection"]["accepted"] is False
    assert len(genesis.journal.of_kind("migration")) == 0
    assert genesis.budget.spent["probes"] == 1


def test_form_transition_refuses_incomplete_probe_round_before_first_spend(tmp_path):
    genesis = _genesis(probes=1)
    first = migration.Substrate(
        "portable-a",
        {program_forms.REBIND_OPERATION: program_forms.portable_target_for},
    )
    second = migration.Substrate(
        "portable-b",
        {program_forms.REBIND_OPERATION: program_forms.portable_target_for},
    )
    stages = (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.require_form(
            _form_requirement_world_with_substrates((first, second)),
            (program_forms.PORTABLE_PROGRAM_TARGET,),
            name="complete-probe-round-required",
        ),
    )
    with pytest.raises(
        campaign.MetamorphicCampaignError,
        match="complete architectural transition comparison requires 2 probe units",
    ):
        campaign.run(
            genesis,
            stages,
            seed_policy=_seed_policy(),
            seed_meta_policy=_seed_meta(),
            max_rounds_per_objective=96,
            checkpoint_directory=tmp_path,
        )
    assert genesis.budget.spent["probes"] == 0
    selections = [
        entry
        for entry in genesis.journal.of_kind("observation")
        if (entry.get("payload") or {}).get("arm") == "architectural_transition_selection"
    ]
    assert selections == []
'''
if "test_form_transition_scores_only_substrates_that_really_expose_rebind" in tests:
    raise SystemExit("capability scoring tests already present")
test_path.write_text(tests + append)
