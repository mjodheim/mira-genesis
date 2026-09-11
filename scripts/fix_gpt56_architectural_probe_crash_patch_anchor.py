from pathlib import Path

path = Path('genesis/metamorphic_campaign.py')
text = path.read_text()

wrong = '''    if cursor is None:\n        if isinstance(stage, FormRequirementStage):\n            _complete_transition_probe_round(\n                genesis,\n                str(selection.get("durable_probe_round_digest") or ""),\n                selection,\n            )\n\n        cursor = _write_cursor(\n            genesis,\n            campaign,\n'''
right = '''    if cursor is None:\n        cursor = _write_cursor(\n            genesis,\n            campaign,\n'''
if wrong not in text:
    raise SystemExit('misplaced initial-cursor block not found')
text = text.replace(wrong, right, 1)

tail = '''        else:  # pragma: no cover\n            raise MetamorphicCampaignError("campaign contains an unrecognised stage")\n\n        cursor = _write_cursor(\n            genesis,\n            campaign,\n            next_stage=index + 1,\n'''
replacement = '''        else:  # pragma: no cover\n            raise MetamorphicCampaignError("campaign contains an unrecognised stage")\n\n        if isinstance(stage, FormRequirementStage):\n            _complete_transition_probe_round(\n                genesis,\n                str(selection.get("durable_probe_round_digest") or ""),\n                selection,\n            )\n\n        cursor = _write_cursor(\n            genesis,\n            campaign,\n            next_stage=index + 1,\n'''
if tail not in text:
    raise SystemExit('run-loop cursor tail anchor not found')
text = text.replace(tail, replacement, 1)

path.write_text(text)
