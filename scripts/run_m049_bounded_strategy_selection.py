"""Print the deterministic M049 development manifest."""
from __future__ import annotations

import json

from metamorphosis.m049_strategy_selection import run_m049_bounded_strategy_selection

manifest = run_m049_bounded_strategy_selection()
print(json.dumps(manifest, sort_keys=True, indent=2))
