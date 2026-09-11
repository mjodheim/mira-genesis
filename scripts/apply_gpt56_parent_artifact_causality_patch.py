from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one replacement site, found {count}")
    file.write_text(text.replace(old, new, 1))


replace_once(
    "genesis/programs.py",
    '''_ACTIVE_PARENT_ARTIFACT_DIGEST: ContextVar[str] = ContextVar(
    "genesis_parent_program_artifact_digest", default=""
)
''',
    '''_ACTIVE_PARENT_ARTIFACT: ContextVar[Mapping[str, Any] | None] = ContextVar(
    "genesis_parent_program_artifact", default=None
)
''',
)
replace_once(
    "genesis/programs.py",
    '''        required_capabilities: Sequence[str] = (),
        parent_body_artifact_digest: str = "",
        capabilities: Iterable[str] = (),
''',
    '''        required_capabilities: Sequence[str] = (),
        parent_body_artifact: Mapping[str, Any] | None = None,
        parent_prefix_length: int = 0,
        capabilities: Iterable[str] = (),
''',
)
replace_once(
    "genesis/programs.py",
    '''        self.required_capabilities = frozenset(str(name) for name in required_capabilities)
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
        for name in self.operations:
            value = self._registry[name](value)
        return value
''',
    '''        self.required_capabilities = frozenset(str(name) for name in required_capabilities)
        self.capabilities = frozenset(str(name) for name in capabilities)
        self._registry = registry
        self._parent_body = None
        self._suffix_names = names
        if parent_body_artifact is not None:
            from genesis.artifacts import reconstruct

            if len(self.required_capabilities) != 1:
                raise ProgramError("a composed generated descendant must name exactly one predecessor")
            prefix_length = int(parent_prefix_length)
            if prefix_length <= 0 or prefix_length >= len(names):
                raise ProgramError("generated descendant carries an invalid parent prefix length")
            parent_factory = reconstruct(parent_body_artifact)
            parent_operations = program_operations_of(parent_factory)
            if parent_operations != names[:prefix_length]:
                raise ProgramError(
                    "generated descendant parent artifact is not the canonical program prefix it claims"
                )
            self._parent_body = parent_factory()
            self._suffix_names = names[prefix_length:]
        elif int(parent_prefix_length):
            raise ProgramError("generated program names a parent prefix without a parent artifact")

    def attempt(self, task: Mapping[str, Any]) -> Any:
        missing = self.required_capabilities - self.capabilities
        if missing:
            raise RuntimeError(
                "generated program is missing retained predecessor capability: %s"
                % ", ".join(sorted(missing))
            )
        if self._parent_body is None:
            value = task[self.input_field]
        else:
            value = self._parent_body.attempt(task)
        for name in self._suffix_names:
            value = self._registry[name](value)
        return value
''',
)
replace_once(
    "genesis/programs.py",
    '''    required_capabilities: Sequence[str] = (),
    parent_body_artifact_digest: str = "",
    capabilities: Iterable[str] = (),
''',
    '''    required_capabilities: Sequence[str] = (),
    parent_body_artifact: Mapping[str, Any] | None = None,
    parent_prefix_length: int = 0,
    capabilities: Iterable[str] = (),
''',
)
replace_once(
    "genesis/programs.py",
    '''        required_capabilities=required_capabilities,
        parent_body_artifact_digest=parent_body_artifact_digest,
        capabilities=capabilities,
''',
    '''        required_capabilities=required_capabilities,
        parent_body_artifact=parent_body_artifact,
        parent_prefix_length=parent_prefix_length,
        capabilities=capabilities,
''',
)
replace_once(
    "genesis/programs.py",
    '''    parent_digest = (
        artifact_digest_of(body_factory)["artifact_digest"]
        if dependency_name
        else ""
    )
''',
    '''    parent_artifact = artifact_digest_of(body_factory) if dependency_name else None
''',
)
replace_once(
    "genesis/programs.py",
    '''    digest_token = _ACTIVE_PARENT_ARTIFACT_DIGEST.set(parent_digest)
    try:
        yield _ACTIVE_INTERPRETER_TARGET.get()
    finally:
        _ACTIVE_PARENT_ARTIFACT_DIGEST.reset(digest_token)
''',
    '''    artifact_token = _ACTIVE_PARENT_ARTIFACT.set(parent_artifact)
    try:
        yield _ACTIVE_INTERPRETER_TARGET.get()
    finally:
        _ACTIVE_PARENT_ARTIFACT.reset(artifact_token)
''',
)
replace_once(
    "genesis/programs.py",
    '''    if inherited_parent:
        configuration["parent_body_artifact_digest"] = _ACTIVE_PARENT_ARTIFACT_DIGEST.get()
''',
    '''    if inherited_parent:
        parent_artifact = _ACTIVE_PARENT_ARTIFACT.get()
        if not isinstance(parent_artifact, Mapping):
            raise ProgramError("generated descendant lost the executable artifact of its predecessor")
        configuration["parent_body_artifact"] = dict(parent_artifact)
        configuration["parent_prefix_length"] = len(parent_operations)
''',
)

replace_once(
    "genesis/program_forms.py",
    'from genesis.programs import PROGRAM_SCHEMA\n',
    'from genesis.programs import PROGRAM_SCHEMA, program_operations_of\n',
)
replace_once(
    "genesis/program_forms.py",
    '''        required_capabilities: Sequence[str] = (),
        parent_body_artifact_digest: str = "",
        capabilities: Iterable[str] = (),
''',
    '''        required_capabilities: Sequence[str] = (),
        parent_body_artifact: Mapping[str, Any] | None = None,
        parent_prefix_length: int = 0,
        capabilities: Iterable[str] = (),
''',
)
replace_once(
    "genesis/program_forms.py",
    '''        self.required_capabilities = frozenset(str(name) for name in required_capabilities)
        self.parent_body_artifact_digest = str(parent_body_artifact_digest or "")
        self.capabilities = frozenset(str(name) for name in capabilities)
        # This is the executable-form difference: resolve once and retain the compiled route rather
        # than looking up every operation by name on every task attempt.
        self._compiled = tuple(registry[name] for name in names)

    def attempt(self, task: Mapping[str, Any]) -> Any:
        missing = self.required_capabilities - self.capabilities
        if missing:
            raise RuntimeError(
                "portable generated program is missing retained predecessor capability: %s"
                % ", ".join(sorted(missing))
            )
        value = task[self.input_field]
        for operation in self._compiled:
            value = operation(value)
        return value
''',
    '''        self.required_capabilities = frozenset(str(name) for name in required_capabilities)
        self.capabilities = frozenset(str(name) for name in capabilities)
        self._parent_body = None
        suffix_names = names
        if parent_body_artifact is not None:
            from genesis.artifacts import reconstruct

            if len(self.required_capabilities) != 1:
                raise PortableProgramError(
                    "a composed portable descendant must name exactly one predecessor"
                )
            prefix_length = int(parent_prefix_length)
            if prefix_length <= 0 or prefix_length >= len(names):
                raise PortableProgramError("portable descendant carries an invalid parent prefix length")
            parent_factory = reconstruct(parent_body_artifact)
            parent_operations = program_operations_of(parent_factory)
            if parent_operations != names[:prefix_length]:
                raise PortableProgramError(
                    "portable descendant parent artifact is not the canonical program prefix it claims"
                )
            self._parent_body = parent_factory()
            suffix_names = names[prefix_length:]
        elif int(parent_prefix_length):
            raise PortableProgramError("portable program names a parent prefix without a parent artifact")
        # This is the executable-form difference: resolve once and retain the compiled suffix route.
        self._compiled = tuple(registry[name] for name in suffix_names)

    def attempt(self, task: Mapping[str, Any]) -> Any:
        missing = self.required_capabilities - self.capabilities
        if missing:
            raise RuntimeError(
                "portable generated program is missing retained predecessor capability: %s"
                % ", ".join(sorted(missing))
            )
        if self._parent_body is None:
            value = task[self.input_field]
        else:
            value = self._parent_body.attempt(task)
        for operation in self._compiled:
            value = operation(value)
        return value
''',
)
replace_once(
    "genesis/program_forms.py",
    '''    required_capabilities: Sequence[str] = (),
    parent_body_artifact_digest: str = "",
    capabilities: Iterable[str] = (),
''',
    '''    required_capabilities: Sequence[str] = (),
    parent_body_artifact: Mapping[str, Any] | None = None,
    parent_prefix_length: int = 0,
    capabilities: Iterable[str] = (),
''',
)
replace_once(
    "genesis/program_forms.py",
    '''        required_capabilities=required_capabilities,
        parent_body_artifact_digest=parent_body_artifact_digest,
        capabilities=capabilities,
''',
    '''        required_capabilities=required_capabilities,
        parent_body_artifact=parent_body_artifact,
        parent_prefix_length=parent_prefix_length,
        capabilities=capabilities,
''',
)

replace_once(
    "genesis/metamorphic_policy_loop.py",
    '''                "body_artifact": outcome["generated_body_artifact"],
                "accepted": bool(outcome.get("accepted")),
                "reason": outcome.get("reason", ""),
''',
    '''                "body_artifact": outcome["generated_body_artifact"],
                "generated_dependency": outcome.get("generated_dependency", ""),
                "causal_dependency": dict(outcome.get("causal_dependency") or {}),
                "accepted": bool(outcome.get("accepted")),
                "reason": outcome.get("reason", ""),
''',
)

replace_once(
    "tests/test_genesis_post_migration_form_continuation.py",
    '''    assert b2_artifact["dependencies"] == [b1["name"]]
    assert tuple(b2_program["required_capabilities"]) == (b1["name"],)
    assert b2_program["parent_body_artifact_digest"] == arrival_artifact["artifact_digest"]
''',
    '''    assert b2_artifact["dependencies"] == [b1["name"]]
    assert tuple(b2_program["required_capabilities"]) == (b1["name"],)
    assert b2_program["parent_prefix_length"] == 1
    assert b2_program["parent_body_artifact"]["artifact_digest"] == arrival_artifact["artifact_digest"]
    parent_configuration = b2_program["parent_body_artifact"]["configuration"]
    assert parent_configuration["target"] == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(parent_configuration["configuration"]["operations"]) == ("square",)
''',
)
replace_once(
    "tests/test_genesis_post_migration_form_continuation.py",
    '''    metamorphosis = migration.metamorphosis_succeeded(
        moved,
        [{"accepted": True, "causal_dependency": causal}],
    )
''',
    '''    assert b2["causal_dependency"] == causal
    metamorphosis = migration.metamorphosis_succeeded(moved, [b2])
''',
)

replace_once(
    "tests/test_genesis_generated_parent_dependency.py",
    '''    assert tuple(descendant.configuration["required_capabilities"]) == (dependency,)
    assert descendant.configuration["parent_body_artifact_digest"] == parent_digest

    # This is executable dependence, not a certificate flag: the intact body computes the new work,
''',
    '''    assert tuple(descendant.configuration["required_capabilities"]) == (dependency,)
    assert descendant.configuration["parent_prefix_length"] == 1
    parent_record = descendant.configuration["parent_body_artifact"]
    assert parent_record["artifact_digest"] == parent_digest
    assert parent_record["configuration"]["target"] == program_forms.PORTABLE_PROGRAM_TARGET
    assert tuple(parent_record["configuration"]["configuration"]["operations"]) == ("square",)

    # This is executable composition, not a certificate flag: the descendant reconstructs and runs
    # its exact parent artifact, then executes only its newly appended suffix operation.
''',
)

with Path("tests/test_genesis_generated_parent_dependency.py").open("a") as handle:
    handle.write(
        '''\n\ndef test_tampered_embedded_parent_artifact_is_refused_at_execution_boundary():\n    parent = _portable_square()\n    dependency = "policy-program:older-objective:square"\n    with programs.inherit_interpreter_form(parent, dependency=dependency):\n        descendant = programs.artifact(\n            registry_reference=bodies.PROBE_REGISTRY,\n            operations=("square", "square"),\n        )\n\n    configuration = dict(descendant.configuration)\n    parent_record = dict(configuration["parent_body_artifact"])\n    parent_record["artifact_digest"] = "0" * 64\n    configuration["parent_body_artifact"] = parent_record\n    tampered = ConfiguredBody(\n        target=descendant.target,\n        configuration=configuration,\n        dependencies=descendant.dependencies,\n    )\n    with pytest.raises(Exception, match="reproduce its committed digest"):\n        tampered()\n'''
    )
