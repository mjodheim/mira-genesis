from __future__ import annotations
from typing import Mapping, Sequence
from metamorphosis.m047_software_body import SoftwareBody, SoftwareCase, module_metadata, render_allocation, render_critique, render_interpretation, render_planning, render_selection, render_tool_module
from metamorphosis.m047_search_memory import ModularSearchError
from metamorphosis.m047_search_patch import ModuleDiagnosis

def _regression_cases(task_id: str, public_cases: Sequence[SoftwareCase]) -> tuple[SoftwareCase, ...]:
    return tuple((SoftwareCase(f'case_{task_id}_{index}', case.request, case.expected, task_id) for index, case in enumerate(public_cases, start=1)))

def _candidate_sources(parent: SoftwareBody, diagnosis: ModuleDiagnosis) -> tuple[tuple[str, Mapping[str, str]], ...]:
    if diagnosis.module == 'interpretation' and diagnosis.unknown_token is not None:
        metadata = module_metadata(parent.source('interpretation'))
        aliases = metadata.get('aliases')
        if not isinstance(aliases, Mapping):
            raise ModularSearchError('interpretation source lacks aliases metadata')
        base_aliases = {str(key): str(value) for key, value in aliases.items()}
        proposals = []
        for canonical in ('add', 'max', 'mean', 'mul'):
            updated = dict(base_aliases)
            updated[diagnosis.unknown_token] = canonical
            proposals.append(('interpreter_add_alias', {'interpretation': render_interpretation(updated)}))
        return tuple(proposals)
    if diagnosis.module == 'planning':
        return (('planner_one_level', {'planning': render_planning('one_level')}), ('planner_recursive_postorder', {'planning': render_planning('recursive_postorder')}))
    if diagnosis.module == 'selection' and diagnosis.missing_operation is not None:
        operation = diagnosis.missing_operation
        metadata = module_metadata(parent.source('selection'))
        routes = metadata.get('routes')
        if not isinstance(routes, Mapping):
            raise ModularSearchError('selection source lacks routes metadata')
        base_routes = {str(key): str(value) for key, value in routes.items()}
        updated_routes = dict(base_routes)
        updated_routes[operation] = operation
        values = []
        for expression_id in ('midpoint', 'mean', 'sum', 'maximum', 'minimum'):
            values.append((f'synthesize_tool_{expression_id}', {'selection': render_selection(updated_routes), f'tool_{operation}': render_tool_module(operation, expression_id)}))
        return tuple(values)
    if diagnosis.module == 'critique':
        return tuple(((f'critic_{policy}', {'critique': render_critique(policy)}) for policy in ('round_one', 'round_two', 'round_three')))
    if diagnosis.module == 'allocation':
        return tuple(((f'allocator_{policy}', {'allocation': render_allocation(policy)}) for policy in ('fixed_five', 'plan_length', 'double_plan_length')))
    return ()
