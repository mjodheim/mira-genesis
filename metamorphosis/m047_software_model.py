from __future__ import annotations
from dataclasses import dataclass
import hashlib
from typing import Mapping, Sequence
from metamorphosis.m047_software_core import BODY_SCHEMA, REQUIRED_MODULES, SoftwareBodyError, SoftwareCase, SourceModule, _canonical_json, _domain_digest, render_generated_tests

@dataclass(frozen=True)
class SoftwareBody:
    modules: tuple[SourceModule, ...]
    regression_cases: tuple[SoftwareCase, ...] = ()
    schema: str = BODY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != BODY_SCHEMA:
            raise SoftwareBodyError('unsupported software body schema')
        names = tuple((module.name for module in self.modules))
        if names != tuple(sorted(names)):
            raise SoftwareBodyError('software modules must be sorted by name')
        if len(set(names)) != len(names):
            raise SoftwareBodyError('software module names must be unique')
        missing = sorted(set(REQUIRED_MODULES) - set(names))
        if missing:
            raise SoftwareBodyError(f'software body lacks required modules: {missing}')
        case_ids = tuple((case.case_id for case in self.regression_cases))
        if len(set(case_ids)) != len(case_ids):
            raise SoftwareBodyError('regression case identities must be unique')
        render_generated_tests(self.regression_cases)

    def to_dict(self) -> dict[str, object]:
        return {'schema': self.schema, 'modules': [module.to_dict() for module in self.modules], 'regression_cases': [case.to_dict() for case in self.regression_cases]}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> 'SoftwareBody':
        if set(data) != {'schema', 'modules', 'regression_cases'}:
            raise SoftwareBodyError('invalid software body fields')
        raw_modules = data['modules']
        raw_cases = data['regression_cases']
        if not isinstance(raw_modules, Sequence) or isinstance(raw_modules, (str, bytes)):
            raise SoftwareBodyError('modules must be a sequence')
        if not isinstance(raw_cases, Sequence) or isinstance(raw_cases, (str, bytes)):
            raise SoftwareBodyError('regression_cases must be a sequence')
        modules: list[SourceModule] = []
        for raw in raw_modules:
            if not isinstance(raw, Mapping) or set(raw) != {'name', 'source'}:
                raise SoftwareBodyError('invalid source module mapping')
            modules.append(SourceModule(str(raw['name']), str(raw['source'])))
        cases: list[SoftwareCase] = []
        for raw in raw_cases:
            if not isinstance(raw, Mapping):
                raise SoftwareBodyError('invalid regression case mapping')
            cases.append(SoftwareCase.from_dict(raw))
        return cls(tuple(modules), tuple(cases), str(data['schema']))

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def digest(self) -> str:
        return hashlib.sha256(b'm047-modular-software-body-v1\x00' + self.to_bytes()).hexdigest()

    def source(self, name: str) -> str:
        for module in self.modules:
            if module.name == name:
                return module.source
        raise SoftwareBodyError(f'unknown software module: {name}')

    def module_names(self) -> tuple[str, ...]:
        return tuple((module.name for module in self.modules))

    def replace_modules(self, replacements: Mapping[str, str], *, added_regression_cases: Sequence[SoftwareCase]=()) -> 'SoftwareBody':
        unknown = set(replacements) - set(self.module_names())
        additions = {name for name in unknown if name.startswith('tool_')}
        forbidden = unknown - additions
        if forbidden:
            raise SoftwareBodyError(f'cannot add non-tool modules: {sorted(forbidden)}')
        updated: dict[str, SourceModule] = {module.name: module for module in self.modules}
        for name, source in replacements.items():
            updated[name] = SourceModule(name, source)
        existing_ids = {case.case_id for case in self.regression_cases}
        appended: list[SoftwareCase] = list(self.regression_cases)
        for case in added_regression_cases:
            if case.case_id in existing_ids:
                continue
            appended.append(case)
            existing_ids.add(case.case_id)
        return SoftwareBody(tuple((updated[name] for name in sorted(updated))), tuple(appended))

    @property
    def total_source_bytes(self) -> int:
        return sum((len(module.source.encode('utf-8')) for module in self.modules)) + len(render_generated_tests(self.regression_cases).encode('utf-8'))
