from __future__ import annotations
import json
from typing import Mapping
from metamorphosis.m047_software_core import MODULE_META_PREFIX, SoftwareBodyError, _safe_identifier

def _meta(module: str, **values: object) -> str:
    mapping = {'module': module, **values}
    return MODULE_META_PREFIX + json.dumps(mapping, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

def render_interpretation(aliases: Mapping[str, str]) -> str:
    arities = {'add': 2, 'max': 2, 'mean': 3, 'mul': 2}
    aliases_value = {str(key): str(value) for key, value in sorted(aliases.items())}
    for key, value in aliases_value.items():
        _safe_identifier(key, 'alias token')
        if value not in arities:
            raise SoftwareBodyError('alias points to an unknown canonical operation')
    return _meta('interpretation', kind='recursive_prefix_parser', aliases=aliases_value) + '\n' + f'ALIASES = {aliases_value!r}\n' + f'ARITIES = {arities!r}\n' + '\n' + 'def _number(token):\n' + '    try:\n' + '        return int(token)\n' + '    except ValueError:\n' + '        try:\n' + '            return float(token)\n' + '        except ValueError:\n' + '            return None\n' + '\n' + 'def _parse(tokens, index):\n' + '    if index >= len(tokens):\n' + "        raise ValueError('unexpected_end')\n" + '    token = tokens[index].lower()\n' + '    number = _number(token)\n' + '    if number is not None:\n' + "        return {'kind': 'number', 'value': number}, index + 1\n" + '    canonical = ALIASES.get(token)\n' + '    if canonical is None:\n' + "        raise ValueError('unknown_operator:' + token)\n" + '    arguments = []\n' + '    cursor = index + 1\n' + '    for _ in range(ARITIES[canonical]):\n' + '        argument, cursor = _parse(tokens, cursor)\n' + '        arguments.append(argument)\n' + "    return {'kind': 'call', 'op': canonical, 'args': arguments}, cursor\n" + '\n' + 'def interpret(text):\n' + '    tokens = text.strip().split()\n' + '    if not tokens:\n' + "        raise ValueError('empty_request')\n" + '    node, cursor = _parse(tokens, 0)\n' + '    if cursor != len(tokens):\n' + "        raise ValueError('trailing_tokens')\n" + '    return node\n'

def render_planning(strategy: str) -> str:
    if strategy not in {'root_only', 'one_level', 'recursive_postorder'}:
        raise SoftwareBodyError('unknown planning strategy')
    header = _meta('planning', kind='planner', strategy=strategy) + '\n'
    if strategy == 'root_only':
        body = "def plan(ir):\n    if ir.get('kind') != 'call':\n        raise ValueError('root_must_be_call')\n    values = []\n    for argument in ir['args']:\n        if argument.get('kind') != 'number':\n            raise RuntimeError('nested_arguments_unsupported')\n        values.append({'literal': argument['value']})\n    return {'steps': [{'op': ir['op'], 'args': values}], 'root': 0}\n"
    elif strategy == 'one_level':
        body = "def _emit_child(node, steps):\n    if node.get('kind') == 'number':\n        return {'literal': node['value']}\n    values = []\n    for argument in node['args']:\n        if argument.get('kind') != 'number':\n            raise RuntimeError('planner_depth_exceeded')\n        values.append({'literal': argument['value']})\n    index = len(steps)\n    steps.append({'op': node['op'], 'args': values})\n    return {'ref': index}\n\ndef plan(ir):\n    if ir.get('kind') != 'call':\n        raise ValueError('root_must_be_call')\n    steps = []\n    arguments = [_emit_child(argument, steps) for argument in ir['args']]\n    root = len(steps)\n    steps.append({'op': ir['op'], 'args': arguments})\n    return {'steps': steps, 'root': root}\n"
    else:
        body = "def _emit(node, steps):\n    if node.get('kind') == 'number':\n        return {'literal': node['value']}\n    arguments = [_emit(argument, steps) for argument in node['args']]\n    index = len(steps)\n    steps.append({'op': node['op'], 'args': arguments})\n    return {'ref': index}\n\ndef plan(ir):\n    if ir.get('kind') != 'call':\n        raise ValueError('root_must_be_call')\n    steps = []\n    root_ref = _emit(ir, steps)\n    return {'steps': steps, 'root': root_ref['ref']}\n"
    return header + body

def render_selection(routes: Mapping[str, str]) -> str:
    routes_value = {str(key): str(value) for key, value in sorted(routes.items())}
    for key, value in routes_value.items():
        _safe_identifier(key, 'operation route')
        _safe_identifier(value, 'tool route')
    return _meta('selection', kind='route_table', routes=routes_value) + '\n' + f'ROUTES = {routes_value!r}\n' + '\n' + 'def select(step):\n' + "    operation = step['op']\n" + '    if operation not in ROUTES:\n' + "        raise KeyError('route_missing:' + operation)\n" + '    return ROUTES[operation]\n'

def render_execution() -> str:
    return _meta('execution', kind='stack_executor') + '\n' + 'def execute(plan, select, tools, budget):\n' + "    steps = plan['steps']\n" + '    if len(steps) > budget:\n' + "        raise RuntimeError('budget_exceeded')\n" + '    results = []\n' + '    used_tools = []\n' + '    for step in steps:\n' + '        route = select(step)\n' + '        if route not in tools:\n' + "            raise KeyError('tool_missing:' + route)\n" + '        arguments = []\n' + "        for argument in step['args']:\n" + "            if 'literal' in argument:\n" + "                arguments.append(argument['literal'])\n" + '            else:\n' + "                arguments.append(results[argument['ref']])\n" + '        results.append(tools[route](arguments))\n' + '        used_tools.append(route)\n' + "    return {'value': results[plan['root']], 'used_tools': used_tools}\n"

def render_critique(policy: str) -> str:
    if policy not in {'identity', 'round_one', 'round_two', 'round_three'}:
        raise SoftwareBodyError('unknown critique policy')
    digits = {'round_one': 1, 'round_two': 2, 'round_three': 3}.get(policy)
    body = 'def critique(value):\n'
    if digits is None:
        body += '    return value\n'
    else:
        body += f'    if isinstance(value, float):\n        return round(value, {digits})\n    return value\n'
    return _meta('critique', kind='result_critic', policy=policy) + '\n' + body

def render_allocation(policy: str) -> str:
    if policy not in {'fixed_one', 'fixed_four', 'fixed_five', 'plan_length', 'double_plan_length'}:
        raise SoftwareBodyError('unknown allocation policy')
    body = 'def allocate(ir, plan):\n'
    if policy == 'fixed_one':
        body += '    return 1\n'
    elif policy == 'fixed_four':
        body += '    return 4\n'
    elif policy == 'fixed_five':
        body += '    return 5\n'
    elif policy == 'plan_length':
        body += "    return max(1, len(plan['steps']))\n"
    else:
        body += "    return max(1, len(plan['steps']) * 2)\n"
    return _meta('allocation', kind='resource_allocator', policy=policy) + '\n' + body

def render_orchestration() -> str:
    return _meta('orchestration', kind='pipeline_orchestrator') + '\n' + 'def _failure(stage, error, trace):\n' + '    return {\n' + "        'ok': False,\n" + "        'output': None,\n" + "        'error_stage': stage,\n" + "        'error_type': type(error).__name__,\n" + "        'error_message': str(error),\n" + "        'trace': trace,\n" + '    }\n' + '\n' + 'def run(request, modules, tools):\n' + '    trace = []\n' + '    try:\n' + "        ir = modules['interpretation'].interpret(request)\n" + "        trace.append({'stage': 'interpretation', 'value': ir})\n" + '    except Exception as error:\n' + "        return _failure('interpretation', error, trace)\n" + '    try:\n' + "        plan = modules['planning'].plan(ir)\n" + "        trace.append({'stage': 'planning', 'value': plan})\n" + '    except Exception as error:\n' + "        return _failure('planning', error, trace)\n" + '    try:\n' + "        budget = modules['allocation'].allocate(ir, plan)\n" + "        trace.append({'stage': 'allocation', 'value': budget})\n" + '    except Exception as error:\n' + "        return _failure('allocation', error, trace)\n" + '    try:\n' + "        executed = modules['execution'].execute(\n" + "            plan, modules['selection'].select, tools, budget\n" + '        )\n' + "        trace.append({'stage': 'execution', 'value': executed})\n" + '    except Exception as error:\n' + "        return _failure('execution', error, trace)\n" + '    try:\n' + "        output = modules['critique'].critique(executed['value'])\n" + "        trace.append({'stage': 'critique', 'value': output})\n" + '    except Exception as error:\n' + "        return _failure('critique', error, trace)\n" + '    return {\n' + "        'ok': True,\n" + "        'output': output,\n" + "        'error_stage': None,\n" + "        'error_type': None,\n" + "        'error_message': None,\n" + "        'trace': trace,\n" + '    }\n'
