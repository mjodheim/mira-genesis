from __future__ import annotations
from dataclasses import dataclass
import ast, hashlib, json, re
from typing import Mapping, Sequence

class SoftwareBodyError(ValueError):
    """Raised when an M047 software body or source module is malformed."""

BODY_SCHEMA = 'm047-modular-software-body-v1'

MODULE_META_PREFIX = '# M047_META '

REQUIRED_MODULES = ('interpretation', 'planning', 'selection', 'execution', 'critique', 'allocation', 'orchestration', 'tool_core')

MAX_MODULE_SOURCE_BYTES = 32768

FORBIDDEN_SOURCE_TOKENS = ('eval(', 'exec(', 'compile(', 'open(', '__import__', 'subprocess', 'socket', 'pathlib', 'os.', 'sys.')

def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')

def _domain_digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()

def _safe_identifier(value: str, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch('[a-z][a-z0-9_]*', value):
        raise SoftwareBodyError(f'{field} must be a lower-case Python identifier')
    return value

def _validate_source(name: str, source: str) -> None:
    _safe_identifier(name, 'module name')
    if not isinstance(source, str) or not source.endswith('\n'):
        raise SoftwareBodyError('module source must be newline-terminated text')
    if len(source.encode('utf-8')) > MAX_MODULE_SOURCE_BYTES:
        raise SoftwareBodyError(f'module {name} exceeds the source-size bound')
    try:
        tree = ast.parse(source, filename=f'{name}.py', mode='exec')
    except SyntaxError as exc:
        raise SoftwareBodyError(f'module {name} is not valid Python') from exc
    if not source.startswith(MODULE_META_PREFIX):
        raise SoftwareBodyError(f'module {name} lacks the M047 metadata header')
    for token in FORBIDDEN_SOURCE_TOKENS:
        if token in source:
            raise SoftwareBodyError(f'module {name} contains forbidden source token {token!r}')
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
            raise SoftwareBodyError(f'module {name} contains a forbidden statement')

def module_metadata(source: str) -> dict[str, object]:
    if not source.startswith(MODULE_META_PREFIX):
        raise SoftwareBodyError('source lacks an M047 metadata header')
    first = source.splitlines()[0][len(MODULE_META_PREFIX):]
    try:
        value = json.loads(first)
    except json.JSONDecodeError as exc:
        raise SoftwareBodyError('module metadata is not valid JSON') from exc
    if not isinstance(value, dict) or any((not isinstance(key, str) for key in value)):
        raise SoftwareBodyError('module metadata must be an object')
    return value

@dataclass(frozen=True)
class SourceModule:
    name: str
    source: str

    def __post_init__(self) -> None:
        _validate_source(self.name, self.source)
        metadata = module_metadata(self.source)
        if metadata.get('module') != self.name:
            raise SoftwareBodyError('module metadata identity mismatch')

    def to_dict(self) -> dict[str, str]:
        return {'name': self.name, 'source': self.source}

    def digest(self) -> str:
        return hashlib.sha256(b'm047-source-module-v1\x00' + _canonical_json(self.to_dict())).hexdigest()

@dataclass(frozen=True)
class SoftwareCase:
    case_id: str
    request: str
    expected: int | float | str | bool | None
    origin: str

    def __post_init__(self) -> None:
        _safe_identifier(self.case_id, 'case_id')
        if not isinstance(self.request, str) or not self.request.strip():
            raise SoftwareBodyError('software case request must be non-empty text')
        if not isinstance(self.origin, str) or not self.origin:
            raise SoftwareBodyError('software case origin must be non-empty')
        if isinstance(self.expected, (dict, list, tuple)):
            raise SoftwareBodyError('M047 expected values must be scalar')

    def to_dict(self) -> dict[str, object]:
        return {'case_id': self.case_id, 'request': self.request, 'expected': self.expected, 'origin': self.origin}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> 'SoftwareCase':
        if set(data) != {'case_id', 'request', 'expected', 'origin'}:
            raise SoftwareBodyError('invalid software case fields')
        return cls(str(data['case_id']), str(data['request']), data['expected'], str(data['origin']))

    def python_assertion(self) -> str:
        request = json.dumps(self.request, ensure_ascii=True)
        expected = json.dumps(self.expected, ensure_ascii=True)
        return f'def test_{self.case_id}(run):\n    actual = run({request})\n    assert actual == {expected}, (actual, {expected})\n'

def render_generated_tests(cases: Sequence[SoftwareCase]) -> str:
    lines = ['# M047_META {"module":"generated_tests","kind":"regression_suite"}', '']
    for case in cases:
        lines.append(case.python_assertion().rstrip())
        lines.append('')
    lines.append('TESTS = (')
    for case in cases:
        lines.append(f'    test_{case.case_id},')
    lines.append(')')
    lines.append('')
    lines.append('def run_tests(run):')
    lines.append('    for test in TESTS:')
    lines.append('        test(run)')
    lines.append('    return len(TESTS)')
    return '\n'.join(lines) + '\n'
