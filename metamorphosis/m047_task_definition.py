from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json
from metamorphosis.m047_search import ModularResourceBudget
from metamorphosis.m047_software_body import SoftwareBody, SoftwareCase

class ModularTaskError(ValueError):
    """Raised when an M047 hidden software task or validation contract is malformed."""

def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')

def _domain_digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()

class StopAction(str, Enum):
    ADOPT = 'adopt'
    TERMINATE_INSUFFICIENT_EVIDENCE = 'terminate_insufficient_evidence'

@dataclass(frozen=True)
class PublicSoftwareTask:
    task_id: str
    family: str
    parent_body_digest: str
    public_cases: tuple[SoftwareCase, ...]
    expected_changed_modules: tuple[str, ...]
    required_tool_name: str | None

    def to_dict(self) -> dict[str, object]:
        return {'task_id': self.task_id, 'family': self.family, 'parent_body_digest': self.parent_body_digest, 'public_cases': [case.to_dict() for case in self.public_cases], 'expected_changed_modules': list(self.expected_changed_modules), 'required_tool_name': self.required_tool_name, 'hidden_cases_exposed': False, 'target_source_exposed': False, 'witness_patch_exposed': False}

    def digest(self) -> str:
        return _domain_digest(b'm047-public-software-task-v1\x00', self.to_dict())

@dataclass(frozen=True)
class HiddenSoftwareTask:
    public: PublicSoftwareTask
    hidden_cases: tuple[SoftwareCase, ...]
    terminal: bool = False

    @property
    def family(self) -> str:
        return self.public.family

    def evaluator_mapping(self) -> dict[str, object]:
        return {'public': self.public.to_dict(), 'hidden_cases': [case.to_dict() for case in self.hidden_cases], 'terminal': self.terminal}

    def digest(self) -> str:
        return _domain_digest(b'm047-hidden-software-task-v1\x00', self.evaluator_mapping())

def _case(case_id: str, request: str, expected: object, origin: str) -> SoftwareCase:
    return SoftwareCase(case_id, request, expected, origin)

def _task_id(parent: SoftwareBody, family: str, ordinal: int, protocol_digest: str) -> str:
    identity = _domain_digest(b'm047-task-id-v1\x00', {'parent_body_digest': parent.digest(), 'family': family, 'ordinal': ordinal, 'protocol_digest': protocol_digest})
    return f'm047_task_{identity[:20]}'

def build_hidden_modular_task(parent: SoftwareBody, *, ordinal: int, protocol_digest: str) -> HiddenSoftwareTask:
    if ordinal == 1:
        family = 'alias_sum'
        public_cases = (_case('public_sum_positive', 'sum 2 3', 5, family), _case('public_sum_signed', 'sum -4 7', 3, family))
        hidden_cases = (_case('hidden_sum_mixed', 'sum 11 -6', 5, family), _case('hidden_sum_zero', 'sum 0 0', 0, family))
        modules = ('interpretation',)
        required_tool = None
    elif ordinal == 2:
        family = 'recursive_planning'
        public_cases = (_case('public_nested_add_mul', 'add 2 mul 3 4', 14, family), _case('public_nested_mul_add', 'mul add 1 2 5', 15, family))
        hidden_cases = (_case('hidden_depth_two_add', 'add mul 2 add 1 2 4', 10, family), _case('hidden_depth_two_mul', 'mul add 1 mul 2 3 2', 14, family))
        modules = ('planning',)
        required_tool = None
    elif ordinal == 3:
        family = 'synthesize_mean_tool'
        public_cases = (_case('public_mean_symmetric', 'mean 2 4 6', 4.0, family), _case('public_mean_zero', 'mean -3 0 3', 0.0, family))
        hidden_cases = (_case('hidden_mean_asymmetric_a', 'mean 1 2 9', 4.0, family), _case('hidden_mean_asymmetric_b', 'mean 2 4 9', 5.0, family))
        modules = ('selection', 'tool_mean')
        required_tool = None
    elif ordinal == 4:
        family = 'critic_round_two'
        public_cases = (_case('public_round_two_a', 'mean 1 2 2', 1.67, family), _case('public_round_two_b', 'mean 0 1 1', 0.67, family))
        hidden_cases = (_case('hidden_round_two_a', 'mean 2 2 3', 2.33, family), _case('hidden_round_two_b', 'mean 1 1 2', 1.33, family))
        modules = ('critique',)
        required_tool = 'mean'
    elif ordinal == 5:
        family = 'dynamic_plan_budget'
        public_cases = (_case('public_budget_depth_five_a', 'add mean 1 2 3 mul add 1 2 mul 2 3', 20.0, family), _case('public_budget_depth_five_b', 'mul add mean 1 2 3 mul 2 3 add 1 1', 16.0, family))
        hidden_cases = (_case('hidden_budget_depth_six', 'add mul add 1 2 mul 2 3 add mean 3 6 9 4', 28.0, family), _case('hidden_budget_depth_seven', 'mul add mean 1 2 3 mul 2 3 add mean 3 6 9 add 1 1', 64.0, family))
        modules = ('allocation',)
        required_tool = 'mean'
    elif ordinal == 6:
        family = 'alias_average'
        public_cases = (_case('public_average_exact', 'average 3 6 9', 6.0, family), _case('public_average_rounded', 'average 1 2 2', 1.67, family))
        hidden_cases = (_case('hidden_average_fraction', 'average 2 3 8', 4.33, family), _case('hidden_average_nested', 'add average 1 2 3 4', 6.0, family))
        modules = ('interpretation',)
        required_tool = 'mean'
    elif ordinal == 7:
        family = 'rollback_alias_total'
        public_cases = (_case('public_total_positive', 'total 2 5', 7, family), _case('public_total_signed', 'total -2 5', 3, family))
        hidden_cases = (_case('hidden_total_zero', 'total 0 0', 0, family), _case('hidden_total_mixed', 'total 10 -3', 7, family))
        modules = ('interpretation',)
        required_tool = None
    elif ordinal == 8:
        family = 'terminal_compound_maximum'
        public_cases = (_case('public_maximum_positive', 'maximum 2 5', 5, family), _case('public_maximum_negative', 'maximum -1 -3', -1, family))
        hidden_cases = (_case('hidden_maximum_equal', 'maximum 4 4', 4, family), _case('hidden_maximum_mixed', 'maximum -8 3', 3, family))
        modules = ('interpretation', 'selection', 'tool_max')
        required_tool = None
    else:
        raise ModularTaskError('unsupported M047 task ordinal')
    task_id = _task_id(parent, family, ordinal, protocol_digest)
    public = PublicSoftwareTask(task_id=task_id, family=family, parent_body_digest=parent.digest(), public_cases=public_cases, expected_changed_modules=modules, required_tool_name=required_tool)
    return HiddenSoftwareTask(public, hidden_cases, terminal=ordinal == 8)
