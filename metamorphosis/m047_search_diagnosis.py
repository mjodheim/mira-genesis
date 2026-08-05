from __future__ import annotations
from typing import Mapping, Sequence
from metamorphosis.m047_runtime_sandbox import CaseExecution
from metamorphosis.m047_search_patch import ModuleDiagnosis

def _clean_error_message(message: str | None) -> str:
    if message is None:
        return ''
    return message.strip().strip("'").strip('"')

def diagnose_limiting_module(executions: Sequence[CaseExecution]) -> ModuleDiagnosis:
    failures = [execution for execution in executions if not execution.passed]
    if not failures:
        return ModuleDiagnosis(None, 'public cases already pass', ())
    stages = {failure.error_stage for failure in failures if not failure.ok}
    evidence = tuple((failure.case_id for failure in failures))
    if stages == {'interpretation'}:
        tokens: set[str] = set()
        for failure in failures:
            message = _clean_error_message(failure.error_message)
            if message.startswith('unknown_operator:'):
                tokens.add(message.split(':', 1)[1])
        if len(tokens) == 1:
            return ModuleDiagnosis('interpretation', 'unknown lexical operator blocks otherwise parseable requests', evidence, unknown_token=next(iter(tokens)))
    if stages == {'planning'}:
        return ModuleDiagnosis('planning', 'the interpreter produced structured input but the planner rejected nesting', evidence)
    if stages == {'execution'}:
        messages = {_clean_error_message(failure.error_message) for failure in failures}
        if messages == {'budget_exceeded'}:
            return ModuleDiagnosis('allocation', "the produced plan exceeds the allocator's explicit execution budget", evidence)
        missing: set[str] = set()
        for message in messages:
            if 'route_missing:' in message:
                missing.add(message.split('route_missing:', 1)[1].strip('\'"'))
        if len(missing) == 1:
            return ModuleDiagnosis('selection', 'the planner emitted an operation with no selected executable tool', evidence, missing_operation=next(iter(missing)))
    if not stages:
        critic_matches = True
        for failure in failures:
            raw_value: object | None = None
            for trace_item in failure.trace:
                if trace_item.get('stage') == 'execution':
                    value = trace_item.get('value')
                    if isinstance(value, Mapping):
                        raw_value = value.get('value')
            if not isinstance(raw_value, float) or not isinstance(failure.expected, (int, float)) or round(raw_value, 2) != failure.expected:
                critic_matches = False
                break
        if critic_matches:
            return ModuleDiagnosis('critique', 'execution is numerically correct but final result normalization is insufficient', evidence)
    return ModuleDiagnosis(None, 'public evidence does not isolate one safely patchable module', evidence)
