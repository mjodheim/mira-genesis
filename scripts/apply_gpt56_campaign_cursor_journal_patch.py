from pathlib import Path

campaign_path = Path('genesis/metamorphic_campaign.py')
text = campaign_path.read_text()
needle = '''    if payload["completed_stage_digests"] != stage_digests[:next_stage]:
        raise MetamorphicCampaignError(
            "campaign cursor does not describe an exact completed prefix of its stage sequence"
        )
    payload["migration"] = _validate_migration_record(genesis, payload["migration"])
'''
replacement = '''    if payload["completed_stage_digests"] != stage_digests[:next_stage]:
        raise MetamorphicCampaignError(
            "campaign cursor does not describe an exact completed prefix of its stage sequence"
        )

    # A self-consistent cursor is not evidence that the runtime actually completed those stages.
    # Reconstruct the cursor progression from the append-only descent journal.  This closes the
    # DEVELOPMENT hole where a host could reseal next_stage=N and skip objective stages while still
    # presenting the exact campaign prefix.  Mid-stage process death remains resumable: only cursor
    # transitions are checked, not equality with the current mutable lineage state.
    progress = []
    for entry in genesis.journal.of_kind("observation"):
        record = entry.get("payload") or {}
        if (
            record.get("arm") == "metamorphic_campaign_cursor"
            and record.get("campaign_digest") == campaign["campaign_digest"]
        ):
            progress.append(record)
    expected_progress = list(range(next_stage + 1))
    actual_progress = [int(record.get("next_stage", -1)) for record in progress]
    if actual_progress != expected_progress:
        raise MetamorphicCampaignError(
            "campaign cursor progress is not backed by contiguous lineage-journal evidence"
        )
    if not progress or progress[-1].get("cursor_digest") != artifact.get("cursor_digest"):
        raise MetamorphicCampaignError(
            "current campaign cursor is not the cursor committed by the lineage journal"
        )

    payload["migration"] = _validate_migration_record(genesis, payload["migration"])
'''
if needle not in text:
    raise SystemExit('campaign validation anchor not found')
campaign_path.write_text(text.replace(needle, replacement, 1))

test_path = Path('tests/test_genesis_persistent_metamorphic_campaign.py')
tests = test_path.read_text()
append = r'''


def _forge_cursor(genesis, stages, *, next_stage):
    admitted = campaign.campaign_record(genesis, stages)
    stage_digests = list(admitted["stage_digests"])
    payload = {
        "schema": campaign.CURSOR_SCHEMA,
        "campaign_digest": admitted["campaign_digest"],
        "stage_digests": stage_digests,
        "completed_stage_digests": stage_digests[:next_stage],
        "next_stage": next_stage,
        "migration": None,
        "acquisition_count_at_migration": None,
    }
    forged = {**payload, "cursor_digest": tr.digest_of(payload)}
    tools = []
    for tool in genesis.state["tools"]:
        if tool.get("name") == campaign.CURSOR_TOOL_NAME and tool.get("role") == campaign.CURSOR_ROLE:
            tools.append({**tool, "artifact": forged})
        else:
            tools.append(tool)
    genesis.state = st.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"],
        generation=genesis.state["generation"],
    )


def test_campaign_refuses_resealed_cursor_that_skips_objective_without_journal_evidence():
    genesis = _genesis()
    stages = _stages()
    admitted = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_stages=0,
    )
    assert admitted["next_stage"] == 0

    # Structurally exact prefix + freshly recomputed cursor digest.  Before this repair the cursor
    # was accepted and stage 0 could be skipped because objective stages had no journal binding.
    _forge_cursor(genesis, stages, next_stage=1)
    with pytest.raises(campaign.MetamorphicCampaignError, match="journal evidence"):
        campaign.run(genesis, stages, max_stages=0)


def test_campaign_refuses_resealed_cursor_rollback_despite_valid_prefix():
    genesis = _genesis()
    stages = _stages()
    progressed = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        max_stages=1,
    )
    assert progressed["next_stage"] == 1

    # The forged cursor is internally valid for stage zero, but the journal proves that stage one
    # was already committed.  Rollback cannot erase spent work or reopen an earlier campaign path.
    _forge_cursor(genesis, stages, next_stage=0)
    with pytest.raises(campaign.MetamorphicCampaignError, match="journal evidence"):
        campaign.run(genesis, stages, max_stages=0)
'''
if '_forge_cursor(genesis, stages' in tests:
    raise SystemExit('cursor forgery tests already present')
test_path.write_text(tests + append)
