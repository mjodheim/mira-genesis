from __future__ import annotations
from metamorphosis.m047_software_core import SoftwareBodyError, SoftwareCase, SourceModule, _safe_identifier
from metamorphosis.m047_software_model import SoftwareBody
from metamorphosis.m047_software_pipeline import _meta, render_allocation, render_critique, render_execution, render_interpretation, render_orchestration, render_planning, render_selection

def render_tool_core() -> str:
    return _meta('tool_core', kind='tool_module', tools=['add', 'mul']) + '\n' + 'def add(arguments):\n' + '    return arguments[0] + arguments[1]\n' + '\n' + 'def mul(arguments):\n' + '    return arguments[0] * arguments[1]\n' + '\n' + "TOOLS = {'add': add, 'mul': mul}\n"

def render_tool_module(tool_name: str, expression_id: str) -> str:
    _safe_identifier(tool_name, 'tool name')
    if expression_id not in {'mean', 'midpoint', 'sum', 'maximum', 'minimum'}:
        raise SoftwareBodyError('unknown synthesized tool expression')
    module_name = f'tool_{tool_name}'
    if expression_id == 'mean':
        expression = 'sum(arguments) / len(arguments)'
    elif expression_id == 'midpoint':
        expression = '(arguments[0] + arguments[-1]) / 2'
    elif expression_id == 'sum':
        expression = 'sum(arguments)'
    elif expression_id == 'maximum':
        expression = 'max(arguments)'
    else:
        expression = 'min(arguments)'
    return _meta(module_name, kind='synthesized_tool', tool_name=tool_name, expression_id=expression_id) + '\n' + f'def {tool_name}(arguments):\n' + '    if not arguments:\n' + "        raise ValueError('tool_requires_arguments')\n" + f'    return {expression}\n' + '\n' + f'TOOLS = {{{tool_name!r}: {tool_name}}}\n'

def founder_software_body() -> SoftwareBody:
    modules = (SourceModule('allocation', render_allocation('fixed_four')), SourceModule('critique', render_critique('identity')), SourceModule('execution', render_execution()), SourceModule('interpretation', render_interpretation({'add': 'add', 'mean': 'mean', 'mul': 'mul'})), SourceModule('orchestration', render_orchestration()), SourceModule('planning', render_planning('root_only')), SourceModule('selection', render_selection({'add': 'add', 'mul': 'mul'})), SourceModule('tool_core', render_tool_core()))
    return SoftwareBody(tuple(sorted(modules, key=lambda item: item.name)))

BASELINE_CASES = (SoftwareCase('baseline_add_positive', 'add 2 3', 5, 'baseline'), SoftwareCase('baseline_add_negative', 'add -4 7', 3, 'baseline'), SoftwareCase('baseline_mul_positive', 'mul 3 4', 12, 'baseline'), SoftwareCase('baseline_mul_signed', 'mul -2 5', -10, 'baseline'))
