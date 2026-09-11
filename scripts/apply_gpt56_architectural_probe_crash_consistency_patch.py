from pathlib import Path

campaign_path = Path('genesis/metamorphic_campaign.py')
text = campaign_path.read_text()

constants_anchor = '''CURSOR_ROLE = "persistent_campaign_progress"\nFORM_REBIND_STRATEGY = "rebind_current_generated_program_v1"\n'''
constants_replacement = '''CURSOR_ROLE = "persistent_campaign_progress"\nFORM_REBIND_STRATEGY = "rebind_current_generated_program_v1"\nTRANSITION_PROBE_ROUND_SCHEMA = "genesis-architectural-transition-probe-round-v1"\nTRANSITION_PROBE_ROUND_KIND = "architectural_transition_probe_round"\n_TRANSITION_RESERVED = "reserved"\n_TRANSITION_CHARGED = "charged"\n_TRANSITION_COMPLETED = "completed"\n_TRANSITION_CRASH_INCOMPLETE = "crash_incomplete"\n'''
if constants_anchor not in text:
    raise SystemExit('constants anchor not found')
text = text.replace(constants_anchor, constants_replacement, 1)

error_anchor = '''class MetamorphicCampaignError(RuntimeError):\n    """Raised when a campaign cannot continue as the same admitted lineage/program."""\n\n\n@dataclass(frozen=True)\nclass ObjectiveStage:\n'''
error_replacement = '''class MetamorphicCampaignError(RuntimeError):\n    """Raised when a campaign cannot continue as the same admitted lineage/program."""\n\n\nclass _PrepaidProbeBudget:\n    """Consume probe slots that were already durably charged to the real lineage budget."""\n\n    def __init__(self, base, allowance: int):\n        self._base = base\n        self._allowance = int(allowance)\n        self.limits = base.limits\n        self.spent = base.spent\n\n    def remaining(self, dimension: str) -> int:\n        if dimension == "probes":\n            return self._allowance\n        return self._base.remaining(dimension)\n\n    def spend(self, dimension: str, amount: int = 1) -> int:\n        if amount < 0:\n            raise MetamorphicCampaignError("cannot spend a negative prepaid probe amount")\n        if dimension != "probes":\n            return self._base.spend(dimension, amount)\n        if self._allowance < amount:\n            raise MetamorphicCampaignError(\n                "architectural transition exhausted its durably prepaid probe reservation"\n            )\n        self._allowance -= amount\n        return self._allowance\n\n    def record(self) -> dict[str, Any]:\n        return self._base.record()\n\n    def unused(self) -> int:\n        return self._allowance\n\n\n@dataclass(frozen=True)\nclass ObjectiveStage:\n'''
if error_anchor not in text:
    raise SystemExit('error anchor not found')
text = text.replace(error_anchor, error_replacement, 1)

selector_anchor = '''def _select_form_transition(\n    genesis, stage: FormRequirementStage, identity: Mapping[str, Any]\n) -> dict[str, Any]:\n'''
helpers = r'''def _replace_observations(genesis, observations) -> None:
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=observations,
        generation=genesis.state["generation"],
    )


def _transition_probe_round_payload(
    genesis,
    *,
    identity: Mapping[str, Any],
    current: Mapping[str, Any],
    destination: Mapping[str, Any],
    substrate_records: Sequence[Mapping[str, Any]],
    probe_cost_required: int,
) -> dict[str, Any]:
    return {
        "schema": TRANSITION_PROBE_ROUND_SCHEMA,
        "stage_digest": str(identity["stage_digest"]),
        "body_artifact_digest": artifact_digest_of(genesis.body_factory)["artifact_digest"],
        "current_target_artifact_digest": str(current["artifact_digest"]),
        "destination_target_artifact_digest": str(destination["artifact_digest"]),
        "substrate_identity_digests": [
            str(item["substrate_identity_digest"]) for item in substrate_records
        ],
        "required_operation": program_forms.REBIND_OPERATION,
        "probe_cost_required": int(probe_cost_required),
    }


def _transition_probe_round_digest(payload: Mapping[str, Any]) -> str:
    return digest_of(dict(payload))


def _transition_probe_round_records(genesis, round_digest: str) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in genesis.state.get("observations", [])
        if isinstance(item, Mapping)
        and item.get("kind") == TRANSITION_PROBE_ROUND_KIND
        and item.get("round_digest") == round_digest
    ]


def _transition_probe_round_record(
    payload: Mapping[str, Any],
    *,
    status: str,
    budget_before: int,
    budget_after: int | None = None,
    selection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "kind": TRANSITION_PROBE_ROUND_KIND,
        **dict(payload),
        "round_digest": _transition_probe_round_digest(payload),
        "status": status,
        "budget_before": int(budget_before),
        "budget_after": None if budget_after is None else int(budget_after),
        "selection": dict(selection) if selection is not None else None,
    }
    record["record_digest"] = digest_of(record)
    return record


def _validate_transition_probe_round_record(
    item: Mapping[str, Any], expected_payload: Mapping[str, Any]
) -> dict[str, Any]:
    record = dict(item)
    recorded_digest = record.pop("record_digest", "")
    if recorded_digest != digest_of(record):
        raise MetamorphicCampaignError(
            "architectural transition probe round does not reproduce its record digest"
        )
    if record.get("kind") != TRANSITION_PROBE_ROUND_KIND:
        raise MetamorphicCampaignError("architectural transition probe round has wrong kind")
    for key, value in expected_payload.items():
        if record.get(key) != value:
            raise MetamorphicCampaignError(
                "architectural transition probe round does not reproduce current %s" % key
            )
    if record.get("round_digest") != _transition_probe_round_digest(expected_payload):
        raise MetamorphicCampaignError("architectural transition probe round identity changed")
    if record.get("status") not in {
        _TRANSITION_RESERVED,
        _TRANSITION_CHARGED,
        _TRANSITION_COMPLETED,
        _TRANSITION_CRASH_INCOMPLETE,
    }:
        raise MetamorphicCampaignError("architectural transition probe round has unknown status")
    if record.get("status") == _TRANSITION_COMPLETED:
        selection = record.get("selection")
        if not isinstance(selection, Mapping):
            raise MetamorphicCampaignError(
                "completed architectural transition probe round carries no selection"
            )
        selection_copy = dict(selection)
        selection_digest = selection_copy.pop("selection_digest", "")
        if selection_digest != digest_of(selection_copy):
            raise MetamorphicCampaignError(
                "persisted architectural transition selection does not reproduce its digest"
            )
        if selection.get("stage_digest") != expected_payload["stage_digest"]:
            raise MetamorphicCampaignError(
                "persisted architectural transition selection names another stage"
            )
        if selection.get("durable_probe_round_digest") != record.get("round_digest"):
            raise MetamorphicCampaignError(
                "persisted architectural transition selection names another probe round"
            )
    return dict(item)


def _install_transition_probe_round(genesis, record: Mapping[str, Any]) -> None:
    target = str(record["round_digest"])
    observations = []
    replaced = False
    for item in genesis.state.get("observations", []):
        if (
            isinstance(item, Mapping)
            and item.get("kind") == TRANSITION_PROBE_ROUND_KIND
            and item.get("round_digest") == target
        ):
            if replaced:
                raise MetamorphicCampaignError(
                    "lineage carries duplicate architectural transition probe rounds"
                )
            observations.append(dict(record))
            replaced = True
        else:
            observations.append(item)
    if not replaced:
        observations.append(dict(record))
    _replace_observations(genesis, observations)


def _prepare_transition_probe_round(
    genesis,
    *,
    identity: Mapping[str, Any],
    current: Mapping[str, Any],
    destination: Mapping[str, Any],
    substrate_records: Sequence[Mapping[str, Any]],
    probe_cost_required: int,
    checkpoint_directory: Path | None,
) -> dict[str, Any]:
    if checkpoint_directory is None or probe_cost_required <= 0:
        if probe_cost_required > genesis.budget.remaining("probes"):
            raise MetamorphicCampaignError(
                "complete architectural transition comparison requires %d probe units but only %d remain"
                % (probe_cost_required, genesis.budget.remaining("probes"))
            )
        return {
            "budget": genesis.budget,
            "round_digest": "",
            "replay_selection": None,
            "durable": False,
        }

    payload = _transition_probe_round_payload(
        genesis,
        identity=identity,
        current=current,
        destination=destination,
        substrate_records=substrate_records,
        probe_cost_required=probe_cost_required,
    )
    round_digest = _transition_probe_round_digest(payload)
    existing = _transition_probe_round_records(genesis, round_digest)
    if len(existing) > 1:
        raise MetamorphicCampaignError(
            "lineage carries duplicate architectural transition probe rounds"
        )

    if not existing:
        remaining = genesis.budget.remaining("probes")
        if remaining < probe_cost_required:
            raise MetamorphicCampaignError(
                "complete architectural transition comparison requires %d probe units but only %d remain"
                % (probe_cost_required, remaining)
            )
        before = int(genesis.budget.spent.get("probes", 0))
        reserved = _transition_probe_round_record(
            payload,
            status=_TRANSITION_RESERVED,
            budget_before=before,
        )
        _install_transition_probe_round(genesis, reserved)
        genesis.persist(Path(checkpoint_directory))
        record = reserved
    else:
        record = _validate_transition_probe_round_record(existing[0], payload)

    status = record["status"]
    if status == _TRANSITION_COMPLETED:
        return {
            "budget": genesis.budget,
            "round_digest": round_digest,
            "replay_selection": dict(record["selection"]),
            "durable": True,
        }
    if status == _TRANSITION_CRASH_INCOMPLETE:
        raise MetamorphicCampaignError(
            "prior architectural transition crashed after its probe budget was charged; redraw is refused"
        )
    if status == _TRANSITION_CHARGED:
        crashed = dict(record)
        crashed.pop("record_digest", None)
        crashed["status"] = _TRANSITION_CRASH_INCOMPLETE
        crashed["record_digest"] = digest_of(crashed)
        _install_transition_probe_round(genesis, crashed)
        genesis.persist(Path(checkpoint_directory))
        raise MetamorphicCampaignError(
            "prior architectural transition crashed after its probe budget was charged; redraw is refused"
        )
    if status != _TRANSITION_RESERVED:
        raise MetamorphicCampaignError("architectural transition probe round cannot be charged")

    genesis.budget.spend("probes", probe_cost_required)
    after = int(genesis.budget.spent.get("probes", 0))
    charged = _transition_probe_round_record(
        payload,
        status=_TRANSITION_CHARGED,
        budget_before=int(record["budget_before"]),
        budget_after=after,
    )
    _install_transition_probe_round(genesis, charged)
    genesis.persist(Path(checkpoint_directory))
    return {
        "budget": _PrepaidProbeBudget(genesis.budget, probe_cost_required),
        "round_digest": round_digest,
        "replay_selection": None,
        "durable": True,
    }


def _complete_transition_probe_round(
    genesis, round_digest: str, selection: Mapping[str, Any]
) -> None:
    if not round_digest:
        return
    records = _transition_probe_round_records(genesis, round_digest)
    if len(records) != 1:
        raise MetamorphicCampaignError(
            "architectural transition completion has no unique durable probe round"
        )
    record = dict(records[0])
    recorded_digest = record.pop("record_digest", "")
    if recorded_digest != digest_of(record):
        raise MetamorphicCampaignError(
            "architectural transition completion found a corrupt probe round"
        )
    selection_copy = dict(selection)
    selection_digest = selection_copy.pop("selection_digest", "")
    if selection_digest != digest_of(selection_copy):
        raise MetamorphicCampaignError(
            "architectural transition completion received a selection whose digest does not reproduce"
        )
    if selection.get("durable_probe_round_digest") != round_digest:
        raise MetamorphicCampaignError(
            "architectural transition selection does not belong to its durable probe round"
        )
    if record.get("status") == _TRANSITION_COMPLETED:
        stored = record.get("selection")
        if not isinstance(stored, Mapping) or stored.get("selection_digest") != selection.get(
            "selection_digest"
        ):
            raise MetamorphicCampaignError(
                "completed architectural transition probe round names another selection"
            )
        return
    if record.get("status") != _TRANSITION_CHARGED:
        raise MetamorphicCampaignError(
            "architectural transition probe round completed from a non-charged state"
        )
    record["status"] = _TRANSITION_COMPLETED
    record["selection"] = dict(selection)
    record["record_digest"] = digest_of(record)
    _install_transition_probe_round(genesis, record)


'''
if selector_anchor not in text:
    raise SystemExit('selector anchor not found')
text = text.replace(selector_anchor, helpers + '''def _select_form_transition(\n    genesis,\n    stage: FormRequirementStage,\n    identity: Mapping[str, Any],\n    *,\n    checkpoint_directory: Path | None = None,\n) -> dict[str, Any]:\n''', 1)

probe_anchor = '''    if probe_cost_required:\n        remaining = genesis.budget.remaining("probes")\n        if remaining < probe_cost_required:\n            raise MetamorphicCampaignError(\n                "complete architectural transition comparison requires %d probe units but only %d remain"\n                % (probe_cost_required, remaining)\n            )\n\n    probe_results: dict[str, dict[str, Any]] = {}\n    if migration_target_relevant:\n'''
probe_replacement = '''    durable_round = {\n        "budget": genesis.budget,\n        "round_digest": "",\n        "replay_selection": None,\n        "durable": False,\n    }\n    if migration_target_relevant and probe_cost_required:\n        durable_round = _prepare_transition_probe_round(\n            genesis,\n            identity=identity,\n            current=current,\n            destination=destination,\n            substrate_records=substrate_records,\n            probe_cost_required=probe_cost_required,\n            checkpoint_directory=checkpoint_directory,\n        )\n        if durable_round["replay_selection"] is not None:\n            return dict(durable_round["replay_selection"])\n    elif probe_cost_required:\n        remaining = genesis.budget.remaining("probes")\n        if remaining < probe_cost_required:\n            raise MetamorphicCampaignError(\n                "complete architectural transition comparison requires %d probe units but only %d remain"\n                % (probe_cost_required, remaining)\n            )\n\n    probe_budget = durable_round["budget"]\n    probe_results: dict[str, dict[str, Any]] = {}\n    if migration_target_relevant:\n'''
if probe_anchor not in text:
    raise SystemExit('probe preflight anchor not found')
text = text.replace(probe_anchor, probe_replacement, 1)

spend_anchor = '''            probe_results[name] = migration.discover(\n                substrate,\n                [program_forms.REBIND_OPERATION],\n                genesis.budget,\n            )\n\n    for substrate_record in substrate_records:\n'''
spend_replacement = '''            probe_results[name] = migration.discover(\n                substrate,\n                [program_forms.REBIND_OPERATION],\n                probe_budget,\n            )\n\n    if isinstance(probe_budget, _PrepaidProbeBudget) and probe_budget.unused() != 0:\n        raise MetamorphicCampaignError(\n            "architectural transition did not consume its complete durably prepaid probe round"\n        )\n\n    for substrate_record in substrate_records:\n'''
if spend_anchor not in text:
    raise SystemExit('probe spend anchor not found')
text = text.replace(spend_anchor, spend_replacement, 1)

record_anchor = '''        "complete_relevant_candidate_set_probed": True,\n        "probe_cost_required": probe_cost_required,\n        "selection_reason": reason,\n'''
record_replacement = '''        "complete_relevant_candidate_set_probed": True,\n        "probe_cost_required": probe_cost_required,\n        "durable_probe_round_digest": str(durable_round["round_digest"]),\n        "probe_budget_precommitted": bool(durable_round["round_digest"]),\n        "selection_reason": reason,\n'''
if record_anchor not in text:
    raise SystemExit('selection record anchor not found')
text = text.replace(record_anchor, record_replacement, 1)

journal_anchor = '''            "candidate_digests": [item["candidate_digest"] for item in candidates],\n            "probe_cost_required": probe_cost_required,\n        },\n'''
journal_replacement = '''            "candidate_digests": [item["candidate_digest"] for item in candidates],\n            "probe_cost_required": probe_cost_required,\n            "durable_probe_round_digest": record["durable_probe_round_digest"],\n        },\n'''
if journal_anchor not in text:
    raise SystemExit('selection journal anchor not found')
text = text.replace(journal_anchor, journal_replacement, 1)

call_anchor = '''            selection = _select_form_transition(genesis, stage, identity)\n'''
call_replacement = '''            selection = _select_form_transition(\n                genesis, stage, identity, checkpoint_directory=checkpoint_path\n            )\n'''
if call_anchor not in text:
    raise SystemExit('selector call anchor not found')
text = text.replace(call_anchor, call_replacement, 1)

reject_anchor = '''            if not selection["accepted"]:\n                entry["stopped"] = True\n                entry["reason"] = selection["selection_reason"]\n                if checkpoint_path is not None:\n                    entry["campaign_checkpoint_digest"] = genesis.persist(checkpoint_path)["checkpoint"]\n'''
reject_replacement = '''            if not selection["accepted"]:\n                entry["stopped"] = True\n                entry["reason"] = selection["selection_reason"]\n                _complete_transition_probe_round(\n                    genesis,\n                    str(selection.get("durable_probe_round_digest") or ""),\n                    selection,\n                )\n                if checkpoint_path is not None:\n                    entry["campaign_checkpoint_digest"] = genesis.persist(checkpoint_path)["checkpoint"]\n'''
if reject_anchor not in text:
    raise SystemExit('rejected selection anchor not found')
text = text.replace(reject_anchor, reject_replacement, 1)

cursor_anchor = '''        cursor = _write_cursor(\n            genesis,\n            campaign,\n'''
cursor_replacement = '''        if isinstance(stage, FormRequirementStage):\n            _complete_transition_probe_round(\n                genesis,\n                str(selection.get("durable_probe_round_digest") or ""),\n                selection,\n            )\n\n        cursor = _write_cursor(\n            genesis,\n            campaign,\n'''
if cursor_anchor not in text:
    raise SystemExit('cursor completion anchor not found')
text = text.replace(cursor_anchor, cursor_replacement, 1)

campaign_path.write_text(text)

# Add regressions for the exact crash/refund window and no-redraw rejected selections.
test_path = Path('tests/test_genesis_persistent_metamorphic_campaign.py')
tests = test_path.read_text()
append = r'''


def test_architectural_probe_budget_survives_crash_after_selection_before_migration(
    monkeypatch, tmp_path
):
    genesis = _genesis()
    stages = _adaptive_stages()
    prefix = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=1,
    )
    assert prefix["next_stage"] == 1
    assert genesis.budget.spent["probes"] == 0

    def crash_after_selection(*args, **kwargs):
        raise RuntimeError("synthetic process death after architectural selection")

    monkeypatch.setattr(campaign, "_run_form_migration", crash_after_selection)
    with pytest.raises(RuntimeError, match="synthetic process death"):
        campaign.run(
            genesis,
            stages,
            max_rounds_per_objective=96,
            checkpoint_directory=tmp_path,
            max_stages=1,
        )

    # The complete physical probe round was charged and checkpointed *before* the probe/selection.
    assert genesis.budget.spent["probes"] == 1
    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    assert restored.budget.spent["probes"] == 1

    # The prior process may have physically probed after its charged checkpoint.  The conservative
    # restart policy therefore refuses a redraw rather than refunding or silently rerunning work.
    with pytest.raises(
        campaign.MetamorphicCampaignError,
        match="crashed after its probe budget was charged; redraw is refused",
    ):
        campaign.run(
            restored,
            stages,
            max_rounds_per_objective=96,
            checkpoint_directory=tmp_path,
            max_stages=1,
        )
    assert restored.budget.spent["probes"] == 1


def test_rejected_architectural_selection_replays_without_second_probe_spend(tmp_path):
    genesis = _genesis()
    bad = migration.Substrate("bad-portable", {})
    stages = (
        campaign.objective(_world(OBJECTIVE_ONE), name="learn-square"),
        campaign.require_form(
            _form_requirement_world_with_substrates((bad,)),
            (program_forms.PORTABLE_PROGRAM_TARGET,),
            name="durable-no-viable-transition",
        ),
    )
    first = campaign.run(
        genesis,
        stages,
        seed_policy=_seed_policy(),
        seed_meta_policy=_seed_meta(),
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
    )
    assert first["next_stage"] == 1
    assert first["executed"][-1]["transition_selection"]["accepted"] is False
    assert genesis.budget.spent["probes"] == 1

    restored = recovery.restore_lineage(tmp_path, grade=fixtures.grade_expected)
    second = campaign.run(
        restored,
        stages,
        max_rounds_per_objective=96,
        checkpoint_directory=tmp_path,
        max_stages=1,
    )
    assert second["next_stage"] == 1
    assert second["executed"][-1]["transition_selection"]["accepted"] is False
    assert second["executed"][-1]["transition_selection"]["durable_probe_round_digest"]
    assert restored.budget.spent["probes"] == 1
'''
if 'test_architectural_probe_budget_survives_crash_after_selection_before_migration' in tests:
    raise SystemExit('crash-consistency tests already present')
test_path.write_text(tests + append)

milestone = r'''# Genesis DEVELOPMENT metamorphosis target — first independently audited satisfaction

Date: 2026-09-11

## Frozen threshold event

The first commit independently reviewed as materially satisfying the prospective DEVELOPMENT stopping
criterion in `docs/METAMORPHOSIS_TARGET.md` is:

`c1e8f3cd30c314f55d511dc2409324ac7df343b8`

That commit is the head of PR #307 (`feat(genesis): select bounded form transitions by unique strict
maximum`). A fresh hostile Hati review, performed before reading earlier Hati conclusions, returned:

**A — YES. The DEVELOPMENT stopping criterion is materially satisfied.**

The review reported 404 tests passing and explicitly classified the result as bounded DEVELOPMENT
evidence. It did not move a scientific gate.

## What crossed the threshold

At the frozen point, one persistent executable lineage demonstrates the integrated bounded path:

`observe -> diagnose -> hypothesize -> construct -> isolate -> test -> compare -> adopt/reject -> persist -> continue`

The same lineage also retains prior acquisitions, changes body and acquisition machinery, survives
process death, changes content-addressed executable form, continues evolving after that form change,
and demonstrates runtime ablation dependence of later acquired work on a retained predecessor. The
runtime additionally makes a bounded architectural `stay` versus `migrate` choice from an admitted
candidate set under unique-strict-maximum selection.

## Claim boundary

This milestone does **not** claim AGI, generality, consciousness, open-ended evolution, arbitrary
self-programming, self-generated goals, or lineage-generated migration algorithms. Environmental
constraints, admitted candidate languages, the migration adapter, trust root, evaluator and search
bounds remain DEVELOPMENT apparatus.

The phrase justified by this milestone is deliberately narrow:

> Genesis materially satisfies its prospectively written bounded DEVELOPMENT metamorphosis target.

## Post-threshold hardening does not move the threshold

Later fixes improve the integrity of that apparatus without redefining the stopping criterion:

- PR #308 requires a migration candidate to demonstrate the required substrate capability before it
  can receive a positive architectural compatibility score.
- The immediate successor hardening durably reserves and charges architectural probe rounds before
  physical probing. If a process dies after that charged checkpoint but before stage commit, restart
  refuses to redraw the ambiguous physical work; completed rejected selections replay without a
  second probe spend.

These are post-threshold robustness changes. They do not retroactively change the first-satisfaction
commit and they do not move any scientific gate.
'''
Path('docs/milestones').mkdir(parents=True, exist_ok=True)
Path('docs/milestones/GENESIS_DEVELOPMENT_METAMORPHOSIS_TARGET_2026-09-11.md').write_text(milestone)
