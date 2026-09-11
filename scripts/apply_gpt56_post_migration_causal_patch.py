from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one replacement site, found {count}")
    file.write_text(text.replace(old, new, 1))


# programs.py: carry a strict generated-program extension's exact predecessor as an executable
# dependency. The active binding is context-local, so another lineage cannot inherit it accidentally.
replace_once(
    "genesis/programs.py",
    '''_ACTIVE_INTERPRETER_TARGET: ContextVar[str] = ContextVar(
    "genesis_program_interpreter_target", default=PROGRAM_TARGET
)
''',
    '''_ACTIVE_INTERPRETER_TARGET: ContextVar[str] = ContextVar(
    "genesis_program_interpreter_target", default=PROGRAM_TARGET
)
_ACTIVE_PARENT_PROGRAM_OPERATIONS: ContextVar[tuple[str, ...]] = ContextVar(
    "genesis_parent_program_operations", default=()
)
_ACTIVE_PARENT_DEPENDENCY: ContextVar[str] = ContextVar(
    "genesis_parent_program_dependency", default=""
)
_ACTIVE_PARENT_ARTIFACT_DIGEST: ContextVar[str] = ContextVar(
    "genesis_parent_program_artifact_digest", default=""
)
''',
)
replace_once(
    "genesis/programs.py",
    '''        operations: Sequence[str],
        input_field: str,
        capabilities: Iterable[str] = (),
    ) -> None:
''',
    '''        operations: Sequence[str],
        input_field: str,
        required_capabilities: Sequence[str] = (),
        parent_body_artifact_digest: str = "",
        capabilities: Iterable[str] = (),
    ) -> None:
''',
)
replace_once(
    "genesis/programs.py",
    '''        self.registry_reference = registry_reference
        self.operations = names
        self.input_field = input_field
        self.capabilities = frozenset(str(name) for name in capabilities)
        self._registry = registry

    def attempt(self, task: Mapping[str, Any]) -> Any:
        value = task[self.input_field]
''',
    '''        self.registry_reference = registry_reference
        self.operations = names
        self.input_field = input_field
        self.required_capabilities = frozenset(str(name) for name in required_capabilities)
        self.parent_body_artifact_digest = str(parent_body_artifact_digest or "")
        self.capabilities = frozenset(str(name) for name in capabilities)
        self._registry = registry

    def attempt(self, task: Mapping[str, Any]) -> Any:
        missing = self.required_capabilities - self.capabilities
        if missing:
            raise RuntimeError(
                "generated program is missing retained predecessor capability: %s"
                % ", ".join(sorted(missing))
            )
        value = task[self.input_field]
''',
)
replace_once(
    "genesis/programs.py",
    '''    operations: Sequence[str],
    input_field: str = "input",
    capabilities: Iterable[str] = (),
) -> ProgramBody:
''',
    '''    operations: Sequence[str],
    input_field: str = "input",
    required_capabilities: Sequence[str] = (),
    parent_body_artifact_digest: str = "",
    capabilities: Iterable[str] = (),
) -> ProgramBody:
''',
)
replace_once(
    "genesis/programs.py",
    '''        operations=operations,
        input_field=input_field,
        capabilities=capabilities,
    )


def interpreter_target_of(body_factory: Any) -> str:
''',
    '''        operations=operations,
        input_field=input_field,
        required_capabilities=required_capabilities,
        parent_body_artifact_digest=parent_body_artifact_digest,
        capabilities=capabilities,
    )


def program_operations_of(body_factory: Any) -> tuple[str, ...]:
    """Return canonical operations only for a reconstructible generated-program body."""
    if not isinstance(body_factory, ConfiguredBody):
        return ()
    configuration = body_factory.configuration
    operations = configuration.get("operations")
    if (
        configuration.get("program_schema") != PROGRAM_SCHEMA
        or not isinstance(configuration.get("registry_reference"), str)
        or not isinstance(configuration.get("input_field"), str)
        or not isinstance(operations, (list, tuple))
        or not operations
    ):
        return ()
    return tuple(str(name) for name in operations)


def interpreter_target_of(body_factory: Any) -> str:
''',
)
replace_once(
    "genesis/programs.py",
    '''    if isinstance(body_factory, ConfiguredBody):
        configuration = body_factory.configuration
        if (
            configuration.get("program_schema") == PROGRAM_SCHEMA
            and isinstance(configuration.get("registry_reference"), str)
            and configuration.get("operations")
            and isinstance(configuration.get("input_field"), str)
        ):
            return str(body_factory.target)
    return PROGRAM_TARGET


@contextmanager
def inherit_interpreter_form(body_factory: Any):
    """Use one lineage body's program form for every nested generated candidate construction.

    ``ContextVar`` keeps the binding scoped to this runtime call and safe across independent async
    contexts. It is reset unconditionally on exit, so evaluating one migrated lineage cannot change
    the default form later used by another lineage in the same process.
    """
    token = _ACTIVE_INTERPRETER_TARGET.set(interpreter_target_of(body_factory))
    try:
        yield _ACTIVE_INTERPRETER_TARGET.get()
    finally:
        _ACTIVE_INTERPRETER_TARGET.reset(token)
''',
    '''    if isinstance(body_factory, ConfiguredBody) and program_operations_of(body_factory):
        return str(body_factory.target)
    return PROGRAM_TARGET


@contextmanager
def inherit_interpreter_form(body_factory: Any, *, dependency: str = ""):
    """Scope generated descendants to the current form and, for strict extensions, predecessor.

    The dependency is inert lineage identity supplied by the runtime from its current acquisition
    history. It is inherited only when a candidate's canonical operation sequence is a *strict
    extension* of the current generated program. A sibling or replacement program therefore cannot
    manufacture causal ancestry merely because a predecessor exists.
    """
    from genesis.trust_root import artifact_digest_of

    parent_operations = program_operations_of(body_factory)
    dependency_name = str(dependency or "") if parent_operations else ""
    parent_digest = (
        artifact_digest_of(body_factory)["artifact_digest"]
        if dependency_name
        else ""
    )
    target_token = _ACTIVE_INTERPRETER_TARGET.set(interpreter_target_of(body_factory))
    operations_token = _ACTIVE_PARENT_PROGRAM_OPERATIONS.set(parent_operations)
    dependency_token = _ACTIVE_PARENT_DEPENDENCY.set(dependency_name)
    digest_token = _ACTIVE_PARENT_ARTIFACT_DIGEST.set(parent_digest)
    try:
        yield _ACTIVE_INTERPRETER_TARGET.get()
    finally:
        _ACTIVE_PARENT_ARTIFACT_DIGEST.reset(digest_token)
        _ACTIVE_PARENT_DEPENDENCY.reset(dependency_token)
        _ACTIVE_PARENT_PROGRAM_OPERATIONS.reset(operations_token)
        _ACTIVE_INTERPRETER_TARGET.reset(target_token)
''',
)
replace_once(
    "genesis/programs.py",
    '''    names = tuple(str(name) for name in operations)
    if not names:
        raise ProgramError("cannot build an empty generated program")
    return ConfiguredBody(
        target=str(interpreter_target or _ACTIVE_INTERPRETER_TARGET.get()),
        configuration={
            "program_schema": PROGRAM_SCHEMA,
            "registry_reference": str(registry_reference),
            "operations": list(names),
            "input_field": str(input_field),
        },
        dependencies=frozenset(str(name) for name in dependencies),
    )
''',
    '''    names = tuple(str(name) for name in operations)
    if not names:
        raise ProgramError("cannot build an empty generated program")

    dependency_names = frozenset(str(name) for name in dependencies)
    parent_operations = _ACTIVE_PARENT_PROGRAM_OPERATIONS.get()
    parent_dependency = _ACTIVE_PARENT_DEPENDENCY.get()
    inherited_parent = bool(
        not dependency_names
        and parent_dependency
        and parent_operations
        and len(names) > len(parent_operations)
        and names[: len(parent_operations)] == parent_operations
    )
    if inherited_parent:
        dependency_names = frozenset((parent_dependency,))

    configuration: dict[str, Any] = {
        "program_schema": PROGRAM_SCHEMA,
        "registry_reference": str(registry_reference),
        "operations": list(names),
        "input_field": str(input_field),
    }
    if dependency_names:
        configuration["required_capabilities"] = sorted(dependency_names)
    if inherited_parent:
        configuration["parent_body_artifact_digest"] = _ACTIVE_PARENT_ARTIFACT_DIGEST.get()

    return ConfiguredBody(
        target=str(interpreter_target or _ACTIVE_INTERPRETER_TARGET.get()),
        configuration=configuration,
        dependencies=dependency_names,
    )
''',
)

# Alternate migrated form consumes the same dependency-bearing canonical configuration.
replace_once(
    "genesis/program_forms.py",
    '''        operations: Sequence[str],
        input_field: str,
        capabilities: Iterable[str] = (),
    ) -> None:
''',
    '''        operations: Sequence[str],
        input_field: str,
        required_capabilities: Sequence[str] = (),
        parent_body_artifact_digest: str = "",
        capabilities: Iterable[str] = (),
    ) -> None:
''',
)
replace_once(
    "genesis/program_forms.py",
    '''        self.operations = names
        self.input_field = input_field
        self.capabilities = frozenset(str(name) for name in capabilities)
        # This is the executable-form difference: resolve once and retain the compiled route rather
''',
    '''        self.operations = names
        self.input_field = input_field
        self.required_capabilities = frozenset(str(name) for name in required_capabilities)
        self.parent_body_artifact_digest = str(parent_body_artifact_digest or "")
        self.capabilities = frozenset(str(name) for name in capabilities)
        # This is the executable-form difference: resolve once and retain the compiled route rather
''',
)
replace_once(
    "genesis/program_forms.py",
    '''    def attempt(self, task: Mapping[str, Any]) -> Any:
        value = task[self.input_field]
''',
    '''    def attempt(self, task: Mapping[str, Any]) -> Any:
        missing = self.required_capabilities - self.capabilities
        if missing:
            raise RuntimeError(
                "portable generated program is missing retained predecessor capability: %s"
                % ", ".join(sorted(missing))
            )
        value = task[self.input_field]
''',
)
replace_once(
    "genesis/program_forms.py",
    '''    operations: Sequence[str],
    input_field: str = "input",
    capabilities: Iterable[str] = (),
) -> PortableProgramBody:
''',
    '''    operations: Sequence[str],
    input_field: str = "input",
    required_capabilities: Sequence[str] = (),
    parent_body_artifact_digest: str = "",
    capabilities: Iterable[str] = (),
) -> PortableProgramBody:
''',
)
replace_once(
    "genesis/program_forms.py",
    '''        operations=operations,
        input_field=input_field,
        capabilities=capabilities,
    )
''',
    '''        operations=operations,
        input_field=input_field,
        required_capabilities=required_capabilities,
        parent_body_artifact_digest=parent_body_artifact_digest,
        capabilities=capabilities,
    )
''',
)

# The form runtime derives predecessor identity from lineage state at objective entry. No launcher
# chooses which earlier acquisition a candidate claims to need.
replace_once(
    "genesis/metamorphic_form_runtime.py",
    '''from genesis import metamorphic_policy_loop as base
from genesis import programs


def run_objective(
''',
    '''from genesis import metamorphic_policy_loop as base
from genesis import programs


def _latest_acquisition_name(genesis) -> str:
    acquisitions = list(genesis.state.get("acquisitions") or [])
    if not acquisitions:
        return ""
    latest = acquisitions[-1]
    if not isinstance(latest, Mapping):
        return ""
    return str(latest.get("name") or "")


def run_objective(
''',
)
replace_once(
    "genesis/metamorphic_form_runtime.py",
    '''    """Run one integrated objective without reverting a migrated generated-program form."""
    with programs.inherit_interpreter_form(genesis.body_factory):
        result = base.run_objective(
''',
    '''    """Run one integrated objective without reverting form or severing strict ancestry."""
    with programs.inherit_interpreter_form(
        genesis.body_factory,
        dependency=_latest_acquisition_name(genesis),
    ):
        result = base.run_objective(
''',
)

# The host executor derives the causal name back out of the executable artifact when the inert policy
# did not author one. A paper-only rationale therefore cannot create this link.
replace_once(
    "genesis/controller.py",
    '''    except programs.ProgramError as problem:
        raise ControllerError(str(problem)) from problem
    proposal = Proposal(
        name=intent.name,
        body_factory=body,
        provenance=LINEAGE,
        rationale={
            **dict(intent.rationale),
            "generated_program": {
                "schema": programs.PROGRAM_SCHEMA,
                "operations": list(intent.operations),
                "input_field": intent.input_field,
            },
        },
        depends_on=intent.depends_on,
    )
''',
    '''    except programs.ProgramError as problem:
        raise ControllerError(str(problem)) from problem

    body_dependencies = tuple(sorted(body.dependencies))
    if intent.depends_on:
        proposal_dependency = intent.depends_on
    elif len(body_dependencies) == 1:
        proposal_dependency = body_dependencies[0]
    else:
        proposal_dependency = ""

    proposal = Proposal(
        name=intent.name,
        body_factory=body,
        provenance=LINEAGE,
        rationale={
            **dict(intent.rationale),
            "generated_program": {
                "schema": programs.PROGRAM_SCHEMA,
                "operations": list(intent.operations),
                "input_field": intent.input_field,
            },
            "runtime_derived_dependency": proposal_dependency
            if proposal_dependency and not intent.depends_on
            else "",
        },
        depends_on=proposal_dependency,
    )
''',
)
replace_once(
    "genesis/controller.py",
    '''        "generated_body_artifact": artifact_digest_of(body),
        "selected_from_world_artifacts": False,
''',
    '''        "generated_body_artifact": artifact_digest_of(body),
        "generated_dependency": proposal_dependency,
        "selected_from_world_artifacts": False,
''',
)

# Strengthen the post-migration regression: B2 must be a strict executable descendant of migrated B1,
# its runtime-derived ablation must lose the newly solved m1 task, and the migration criterion must
# therefore classify the continuation as transported acquisition capacity rather than output replay.
replace_once(
    "tests/test_genesis_post_migration_form_continuation.py",
    '''    assert b2["program"]["operations"] == ["square", "square"]
    assert b2["body_artifact"]["configuration"]["target"] == program_forms.PORTABLE_PROGRAM_TARGET
    assert restored.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(restored.body_factory.configuration["operations"]) == ("square", "square")
    assert second["generated_form_target"] == program_forms.PORTABLE_PROGRAM_TARGET
    assert len(retentive.bound_corpus(restored)["question_digests"]) == 2

    m2 = meta.bound_meta_policy(restored)
''',
    '''    assert b2["program"]["operations"] == ["square", "square"]
    assert b2["body_artifact"]["configuration"]["target"] == program_forms.PORTABLE_PROGRAM_TARGET
    b2_artifact = b2["body_artifact"]["configuration"]
    b2_program = b2_artifact["configuration"]
    assert b2_artifact["dependencies"] == [b1["name"]]
    assert tuple(b2_program["required_capabilities"]) == (b1["name"],)
    assert b2_program["parent_body_artifact_digest"] == arrival_artifact["artifact_digest"]
    assert restored.body_factory.target == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(restored.body_factory.configuration["operations"]) == ("square", "square")
    assert second["generated_form_target"] == program_forms.PORTABLE_PROGRAM_TARGET
    assert len(retentive.bound_corpus(restored)["question_digests"]) == 2

    causal = restored.state["acquisitions"][-1]["causal_dependency"]
    assert causal["established"] is True
    assert causal["depends_on"] == b1["name"]
    assert causal["newly_solved_with_acquisition"] == ["m1"]
    assert causal["newly_solved_lost_without_acquisition"] == ["m1"]
    metamorphosis = migration.metamorphosis_succeeded(
        moved,
        [{"accepted": True, "causal_dependency": causal}],
    )
    assert metamorphosis["succeeded"] is True
    assert metamorphosis["causally_established_after_migration"] == 1
    assert metamorphosis["is_transported_intelligence_rather_than_transported_output"] is True

    m2 = meta.bound_meta_policy(restored)
''',
)

Path("tests/test_genesis_generated_parent_dependency.py").write_text(
    '''"""DEVELOPMENT regressions for runtime-derived ancestry of generated programs."""\nfrom __future__ import annotations\n\nimport pytest\n\nfrom genesis import development_bodies as bodies\nfrom genesis import program_forms, programs\nfrom genesis.artifacts import ConfiguredBody\nfrom genesis import trust_root as tr\n\n\ndef _portable_square():\n    return ConfiguredBody(\n        target=program_forms.PORTABLE_PROGRAM_TARGET,\n        configuration={\n            "program_schema": programs.PROGRAM_SCHEMA,\n            "registry_reference": bodies.PROBE_REGISTRY,\n            "operations": ["square"],\n            "input_field": "input",\n        },\n    )\n\n\ndef test_only_a_strict_program_extension_inherits_the_predecessor_dependency():\n    parent = _portable_square()\n    dependency = "policy-program:older-objective:square"\n    parent_digest = tr.artifact_digest_of(parent)["artifact_digest"]\n\n    with programs.inherit_interpreter_form(parent, dependency=dependency):\n        same = programs.artifact(\n            registry_reference=bodies.PROBE_REGISTRY,\n            operations=("square",),\n        )\n        sibling = programs.artifact(\n            registry_reference=bodies.PROBE_REGISTRY,\n            operations=("increment", "square"),\n        )\n        descendant = programs.artifact(\n            registry_reference=bodies.PROBE_REGISTRY,\n            operations=("square", "square"),\n        )\n\n    assert same.dependencies == frozenset()\n    assert sibling.dependencies == frozenset()\n    assert descendant.target == program_forms.PORTABLE_PROGRAM_TARGET\n    assert descendant.dependencies == frozenset((dependency,))\n    assert tuple(descendant.configuration["required_capabilities"]) == (dependency,)\n    assert descendant.configuration["parent_body_artifact_digest"] == parent_digest\n\n    # This is executable dependence, not a certificate flag: the intact body computes the new work,\n    # while the runtime-derived single-difference ablation cannot execute without its predecessor.\n    assert descendant().attempt({"input": 2}) == 16\n    ablated = descendant.without(dependency)\n    with pytest.raises(RuntimeError, match="retained predecessor capability"):\n        ablated().attempt({"input": 2})\n\n\ndef test_parent_dependency_context_does_not_leak_to_other_lineages():\n    parent = _portable_square()\n    with programs.inherit_interpreter_form(parent, dependency="prior"):\n        inherited = programs.artifact(\n            registry_reference=bodies.PROBE_REGISTRY,\n            operations=("square", "square"),\n        )\n    ordinary = programs.artifact(\n        registry_reference=bodies.PROBE_REGISTRY,\n        operations=("square", "square"),\n    )\n\n    assert inherited.dependencies == frozenset(("prior",))\n    assert ordinary.dependencies == frozenset()\n    assert ordinary.target == programs.PROGRAM_TARGET\n'''
)
