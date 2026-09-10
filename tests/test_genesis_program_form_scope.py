"""Hostile checks for generated-program form inheritance boundaries."""
from genesis import development_bodies as bodies
from genesis import program_forms, programs
from genesis.artifacts import ConfiguredBody


def _artifact(*, target=None):
    return programs.artifact(
        registry_reference=bodies.PROBE_REGISTRY,
        operations=("square",),
        interpreter_target=target,
    )


def test_migrated_form_is_inherited_only_inside_runtime_scope():
    migrated = _artifact(target=program_forms.PORTABLE_PROGRAM_TARGET)
    assert programs.interpreter_target_of(migrated) == program_forms.PORTABLE_PROGRAM_TARGET

    before = _artifact()
    assert before.target == programs.PROGRAM_TARGET

    with programs.inherit_interpreter_form(migrated):
        generated = _artifact()
        enumerated = next(
            programs.enumerate_artifacts(
                registry_reference=bodies.PROBE_REGISTRY,
                operation_names=("square",),
                max_length=1,
                max_candidates=1,
            )
        )
        assert generated.target == program_forms.PORTABLE_PROGRAM_TARGET
        assert enumerated.target == program_forms.PORTABLE_PROGRAM_TARGET

    # No ambient process memory is allowed to make an unrelated later lineage portable by accident.
    after = _artifact()
    assert after.target == programs.PROGRAM_TARGET


def test_unrelated_configured_artifact_cannot_redefine_generated_program_form():
    unrelated = ConfiguredBody(
        target=program_forms.PORTABLE_PROGRAM_TARGET,
        configuration={"not_a_generated_program": True},
    )
    assert programs.interpreter_target_of(unrelated) == programs.PROGRAM_TARGET

    with programs.inherit_interpreter_form(unrelated):
        assert _artifact().target == programs.PROGRAM_TARGET
