from __future__ import annotations

import inspect

from metamorphosis import m040_engine


def test_pre_adoption_hook_is_optional_and_default_disabled():
    execute = inspect.signature(m040_engine._execute)
    public = inspect.signature(m040_engine.run_m040_development)

    assert execute.parameters["pre_adoption_validator"].default is None
    assert public.parameters["pre_adoption_validator"].default is None


def test_validator_call_precedes_the_candidate_adoption_event():
    source = inspect.getsource(m040_engine._execute)

    validator_index = source.index("pre_adoption_validator(")
    adoption_index = source.index('journal.append(\n        "CandidateAdopted"')

    assert validator_index < adoption_index


def test_public_runner_forwards_the_hook_to_first_and_replay_executions():
    source = inspect.getsource(m040_engine.run_m040_development)

    assert source.count("pre_adoption_validator=pre_adoption_validator") == 2
    assert source.index("first = _execute") < source.index("replayed = _execute")


def test_default_m040_result_surface_does_not_include_m041_fields():
    fields = set(m040_engine.M040DevelopmentResult.__dataclass_fields__)

    assert "isolated_validation" not in fields
    assert "pre_adoption_validator" not in fields
    assert m040_engine.M040DevelopmentResult.schema == "m040-development-result/2"
