import pytest

from metamorphosis.m040_engine import M040EngineError, run_m040_development


def test_consumed_seed_400043_has_no_admissible_exact_continuation_task():
    with pytest.raises(
        M040EngineError,
        match="no transported continuation frontier produced an admissible task",
    ):
        run_m040_development(
            master_seed=400043, require_replay=False, task_family="exact_frontier"
        )
