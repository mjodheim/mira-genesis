// M055 native construction runtime.
//
// M048 proposes by selecting a template: `renderTool(name, expressionId)` picks one of four
// hard-coded expressions, chosen by a hard-coded branch on the unknown token. That is
// catalogue selection inside the migrated runtime.
//
// M055 constructs the tool body instead. A tool is rendered from an expression tree built
// out of two atoms and five operators, searched bottom-up against public evidence. The
// admissible space at the declared depth is far larger than the budget, and the number of
// candidates actually constructed is reported so a run that enumerated cannot present itself
// as one that built.
//
// The accepted expression then becomes an ATOM for the next construction. That is the
// second-order reuse requirement: what the lineage acquired becomes material, not an answer.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const RESPONSE_SCHEMA = 'm055-node-response-v1';
const ATOMS = ['previous', 'current'];
const OPERATORS = ['add', 'subtract', 'minimum', 'maximum', 'multiply'];
const BEHAVIOUR_DOMAIN = [];
for (let a = -4; a <= 4; a += 1) for (let b = -4; b <= 4; b += 1) BEHAVIOUR_DOMAIN.push([a, b]);

function header(name, meta) {
  const value = {module: name, ...meta};
  return `// M055_META ${JSON.stringify(value, Object.keys(value).sort())}\n`;
}

function spaceSize(depth) {
  let count = ATOMS.length;
  for (let i = 0; i < depth; i += 1) count = ATOMS.length + OPERATORS.length * count * count;
  return count;
}

function exprDepth(node) {
  if (node.atom !== undefined) return 0;
  if (node.acquired !== undefined) return 0;
  return 1 + Math.max(exprDepth(node.left), exprDepth(node.right));
}

function evaluate(node, previous, current, acquired) {
  if (node.atom !== undefined) return node.atom === 'previous' ? previous : current;
  if (node.acquired !== undefined) {
    if (!acquired) throw new Error('acquired_primitive_unavailable');
    return evaluate(acquired, previous, current, null);
  }
  const left = evaluate(node.left, previous, current, acquired);
  const right = evaluate(node.right, previous, current, acquired);
  if (node.operator === 'add') return left + right;
  if (node.operator === 'subtract') return left - right;
  if (node.operator === 'minimum') return Math.min(left, right);
  if (node.operator === 'maximum') return Math.max(left, right);
  if (node.operator === 'multiply') return left * right;
  throw new Error('unknown_operator_node:' + node.operator);
}

function canonical(node) {
  if (node.atom !== undefined) return node.atom;
  if (node.acquired !== undefined) return 'ACQUIRED';
  return `${node.operator}(${canonical(node.left)},${canonical(node.right)})`;
}

function behaviour(node, acquired) {
  return BEHAVIOUR_DOMAIN.map(([a, b]) => evaluate(node, a, b, acquired)).join(',');
}

// Render the expression as inline JavaScript so the emitted tool carries executable
// semantics, not an interpreter over a data structure the tool would have to be handed.
function renderExpression(node, acquired) {
  if (node.atom !== undefined) return node.atom === 'previous' ? 'p' : 'c';
  if (node.acquired !== undefined) return renderExpression(acquired, null);
  const left = renderExpression(node.left, acquired);
  const right = renderExpression(node.right, acquired);
  if (node.operator === 'add') return `(${left}+${right})`;
  if (node.operator === 'subtract') return `(${left}-${right})`;
  if (node.operator === 'minimum') return `Math.min(${left},${right})`;
  if (node.operator === 'maximum') return `Math.max(${left},${right})`;
  return `(${left}*${right})`;
}

function renderReduction(reduction) {
  if (reduction === 'sum') return 'return values.reduce((a,b)=>a+b,0);';
  if (reduction === 'maximum') return 'return Math.max(...values);';
  if (reduction === 'minimum') return 'return Math.min(...values);';
  throw new Error('unsupported_reduction:' + reduction);
}

function renderConstructedTool(toolName, node, reduction, acquired, passes) {
  const inner = renderExpression(node, acquired);
  const meta = {
    kind: 'constructed_tool',
    tool_name: toolName,
    expression: canonical(node),
    reduction,
    formation_depth: exprDepth(node),
    pair_passes: passes,
  };
  return header(`tool_${toolName}`, meta) +
    `function pair(p,c){return ${inner};}\n` +
    `export function ${toolName}(args){if(args.length<${passes + 1})throw new Error('tool_requires_arguments');` +
    `let values=args;for(let round=0;round<${passes};round+=1){const next=[];` +
    `for(let i=1;i<values.length;i+=1)next.push(pair(values[i-1],values[i]));values=next;}` +
    `${renderReduction(reduction)}}\n` +
    `export const TOOLS={${toolName}};\n`;
}

function renderInterpretation(aliases, arities) {
  const orderedAliases = Object.fromEntries(Object.entries(aliases).sort(([a], [b]) => a.localeCompare(b)));
  const orderedArities = Object.fromEntries(Object.entries(arities).sort(([a], [b]) => a.localeCompare(b)));
  return header('interpretation', {kind: 'recursive_prefix_parser', aliases: orderedAliases}) +
    `export const ALIASES=${JSON.stringify(orderedAliases)};\n` +
    `export const ARITIES=${JSON.stringify(orderedArities)};\n` +
    `function number(token){const value=Number(token);return Number.isFinite(value)?value:null;}\n` +
    `function parse(tokens,index){if(index>=tokens.length)throw new Error('unexpected_end');const token=tokens[index].toLowerCase();const value=number(token);if(value!==null)return [{kind:'number',value},index+1];const canonical=ALIASES[token];if(!canonical)throw new Error('unknown_operator:'+token);const args=[];let cursor=index+1;for(let i=0;i<ARITIES[canonical];i++){const parsed=parse(tokens,cursor);args.push(parsed[0]);cursor=parsed[1];}return [{kind:'call',op:canonical,args},cursor];}\n` +
    `export function interpret(text){const tokens=text.trim().split(/\\s+/).filter(Boolean);if(!tokens.length)throw new Error('empty_request');const [node,cursor]=parse(tokens,0);if(cursor!==tokens.length)throw new Error('trailing_tokens');return node;}\n`;
}

function renderSelection(routes) {
  const ordered = Object.fromEntries(Object.entries(routes).sort(([a], [b]) => a.localeCompare(b)));
  return header('selection', {kind: 'route_table', routes: ordered}) +
    `export const ROUTES=${JSON.stringify(ordered)};\n` +
    `export function select(step){const route=ROUTES[step.op];if(!route)throw new Error('route_missing:'+step.op);return route;}\n`;
}

function moduleMap(body) {
  return Object.fromEntries(body.modules.map(module => [module.name, module]));
}

function replaceModules(body, replacements, addedCases = []) {
  const byName = moduleMap(body);
  for (const [name, module] of Object.entries(replacements)) byName[name] = module;
  const existing = new Set(body.regression_cases.map(item => item.case_id));
  const regression = [...body.regression_cases];
  for (const item of addedCases) if (!existing.has(item.case_id)) { regression.push(item); existing.add(item.case_id); }
  return {schema: 'm048-js-body-v1', modules: Object.values(byName).sort((a, b) => a.name.localeCompare(b.name)), regression_cases: regression};
}

async function loadBody(body) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'm055-node-body-'));
  const modules = {};
  const tools = {};
  try {
    for (const item of body.modules) await fs.writeFile(path.join(directory, `${item.name}.mjs`), item.source, 'utf8');
    for (const item of body.modules) {
      const url = pathToFileURL(path.join(directory, `${item.name}.mjs`));
      url.searchParams.set('identity', `${process.pid}-${Date.now()}-${item.name}`);
      modules[item.name] = await import(url.href);
    }
    for (const [name, module] of Object.entries(modules)) {
      if (name === 'tool_core' || name.startsWith('tool_')) {
        if (!module.TOOLS || typeof module.TOOLS !== 'object') throw new Error(`tool_registry_missing:${name}`);
        for (const [toolName, tool] of Object.entries(module.TOOLS)) {
          if (toolName in tools) throw new Error(`duplicate_tool:${toolName}`);
          if (typeof tool !== 'function') throw new Error(`invalid_tool:${toolName}`);
          tools[toolName] = tool;
        }
      }
    }
    return {directory, modules, tools};
  } catch (error) {
    await fs.rm(directory, {recursive: true, force: true});
    throw error;
  }
}

async function executeBody(body, cases) {
  const loaded = await loadBody(body);
  try {
    const results = [];
    for (const item of cases) {
      const result = loaded.modules.orchestration.run(item.request, loaded.modules, loaded.tools);
      results.push({case_id: item.case_id, request: item.request, expected: item.expected, passed: Boolean(result.ok && result.output === item.expected), result});
    }
    return {runtime: 'node-esm', worker_pid: process.pid, module_count: body.modules.length, regression_case_count: body.regression_cases.length, all_passed: results.every(item => item.passed), case_results: results};
  } finally {
    await fs.rm(loaded.directory, {recursive: true, force: true});
  }
}

function unknownToken(execution) {
  const tokens = new Set();
  for (const failure of execution.case_results.filter(item => !item.passed)) {
    const message = String(failure.result.error_message ?? '');
    if (failure.result.error_stage === 'interpretation' && message.startsWith('unknown_operator:')) {
      tokens.add(message.slice('unknown_operator:'.length));
    }
  }
  return tokens.size === 1 ? [...tokens][0] : null;
}

// Evidence for construction is the public cases only: each carries the argument list and the
// answer. The hidden bank never reaches this function.
function publicEvidence(cases) {
  return cases.map(item => {
    const tokens = item.request.trim().split(/\s+/).slice(1).map(Number);
    return {args: tokens, expected: item.expected};
  });
}

function programError(node, reduction, passes, evidence, acquired) {
  let total = 0;
  for (const sample of evidence) {
    let values = sample.args;
    if (values.length < passes + 1) return null;
    try {
      for (let round = 0; round < passes; round += 1) {
        const next = [];
        for (let i = 1; i < values.length; i += 1) next.push(evaluate(node, values[i - 1], values[i], acquired));
        values = next;
      }
      let output;
      if (reduction === 'sum') output = values.reduce((a, b) => a + b, 0);
      else if (reduction === 'maximum') output = Math.max(...values);
      else output = Math.min(...values);
      if (!Number.isFinite(output)) return null;
      total += Math.abs(output - sample.expected);
    } catch (error) {
      return null;
    }
  }
  return total;
}

// Bottom-up construction. Nothing materialises the admissible space; `constructed` counts
// every distinct expression ever scored, so the claim "built, not enumerated" is checkable.
function construct(evidence, options) {
  const {budget, beamWidth, maxDepth, passes, reductions, acquired} = options;
  const scored = new Map();

  function consider(node) {
    const key = canonical(node);
    if (scored.has(key)) return null;
    let best = null;
    for (const reduction of reductions) {
      const error = programError(node, reduction, passes, evidence, acquired);
      if (error === null) continue;
      if (best === null || error < best.error) best = {error, node, reduction, depth: exprDepth(node)};
    }
    if (best === null) best = {error: Number.MAX_SAFE_INTEGER, node, reduction: reductions[0], depth: exprDepth(node)};
    scored.set(key, best);
    return best;
  }

  function settle() {
    const solving = [...scored.values()].filter(entry => entry.error === 0);
    if (!solving.length) return null;
    const classes = new Map();
    for (const entry of solving) {
      const signature = behaviour(entry.node, acquired);
      const incumbent = classes.get(signature);
      if (!incumbent || entry.depth < incumbent.depth ||
          (entry.depth === incumbent.depth && canonical(entry.node) < canonical(incumbent.node))) {
        classes.set(signature, entry);
      }
    }
    if (classes.size > 1) {
      return {status: 'insufficient_evidence', constructed: scored.size, behavioural_classes: classes.size};
    }
    const chosen = [...classes.values()][0];
    return {status: 'constructed', constructed: scored.size, behavioural_classes: 1, expression: chosen.node, reduction: chosen.reduction, depth: chosen.depth};
  }

  let beam = ATOMS.map(atom => ({atom}));
  if (acquired) beam = [...beam, {acquired: true}];
  for (const node of beam) consider(node);
  let settled = settle();
  if (settled) return settled;

  for (let level = 0; level < maxDepth; level += 1) {
    const grown = [];
    for (const left of beam) {
      for (const right of beam) {
        for (const operator of OPERATORS) {
          if (scored.size >= budget) {
            return settle() || {status: 'budget_exhausted', constructed: scored.size, behavioural_classes: 0};
          }
          const node = {operator, left, right};
          if (exprDepth(node) > maxDepth) continue;
          const found = consider(node);
          if (found) grown.push(found);
        }
      }
    }
    settled = settle();
    if (settled) return settled;
    if (!grown.length) break;
    const pool = [...grown, ...beam.map(node => scored.get(canonical(node)))].filter(Boolean);
    pool.sort((a, b) => a.error - b.error || a.depth - b.depth || canonical(a.node).localeCompare(canonical(b.node)));
    beam = pool.slice(0, beamWidth).map(entry => entry.node);
  }
  return settle() || {status: 'insufficient_evidence', constructed: scored.size, behavioural_classes: 0};
}

async function constructCandidate(request) {
  const {body, task_id, public_cases, token, tool_name, arity, passes, budget, beam_width, max_depth, reductions, acquired_expression} = request;
  const incumbent = await executeBody(body, public_cases);
  const diagnosed = unknownToken(incumbent);
  if (diagnosed !== token) {
    return {schema: RESPONSE_SCHEMA, status: 'insufficient_diagnosis', diagnosed_token: diagnosed, expected_token: token, incumbent};
  }
  const evidence = publicEvidence(public_cases);
  const outcome = construct(evidence, {
    budget, beamWidth: beam_width, maxDepth: max_depth, passes,
    reductions, acquired: acquired_expression ?? null,
  });
  if (outcome.status !== 'constructed') {
    return {
      schema: RESPONSE_SCHEMA, status: outcome.status, diagnosed_token: diagnosed,
      candidates_constructed: outcome.constructed, behavioural_classes: outcome.behavioural_classes,
      admissible_space: spaceSize(max_depth), incumbent,
    };
  }
  const byName = moduleMap(body);
  const aliases = {...byName.interpretation.meta.aliases, [token]: tool_name};
  const arities = {...JSON.parse(/export const ARITIES=(\{.*?\});/.exec(byName.interpretation.source)[1]), [tool_name]: arity};
  const routes = {...byName.selection.meta.routes, [tool_name]: tool_name};
  const generated = public_cases.map((item, index) => ({case_id: `case_${task_id}_${index + 1}`, request: item.request, expected: item.expected, origin: task_id}));
  const toolModule = {
    name: `tool_${tool_name}`,
    source: renderConstructedTool(tool_name, outcome.expression, outcome.reduction, acquired_expression ?? null, passes),
    meta: {kind: 'constructed_tool', tool_name, expression: canonical(outcome.expression), reduction: outcome.reduction, formation_depth: outcome.depth, pair_passes: passes},
  };
  const candidateBody = replaceModules(body, {
    interpretation: {name: 'interpretation', source: renderInterpretation(aliases, arities), meta: {kind: 'recursive_prefix_parser', aliases: Object.fromEntries(Object.entries(aliases).sort())}},
    selection: {name: 'selection', source: renderSelection(routes), meta: {kind: 'route_table', routes: Object.fromEntries(Object.entries(routes).sort())}},
    [`tool_${tool_name}`]: toolModule,
  }, generated);
  return {
    schema: RESPONSE_SCHEMA, status: 'constructed', diagnosed_token: diagnosed,
    candidates_constructed: outcome.constructed, behavioural_classes: 1,
    admissible_space: spaceSize(max_depth), expression: outcome.expression,
    expression_canonical: canonical(outcome.expression), reduction: outcome.reduction,
    formation_depth: outcome.depth, pair_passes: passes,
    changed_modules: ['interpretation', 'selection', `tool_${tool_name}`].sort(),
    candidate_body: candidateBody, incumbent,
  };
}

// The validator owns the hidden bank and the inherited regression bank. It has no authority
// to adopt: it returns a verdict, and the Python side decides.
async function validateCandidate(request) {
  const {candidate_body, retained_cases, public_cases, hidden_cases} = request;
  const retained = await executeBody(candidate_body, retained_cases);
  const publicRun = await executeBody(candidate_body, public_cases);
  const hidden = await executeBody(candidate_body, hidden_cases);
  return {
    schema: RESPONSE_SCHEMA,
    retained_passed: retained.case_results.filter(item => item.passed).length,
    retained_total: retained_cases.length,
    inherited_regression_passed: retained.all_passed,
    public_passed: publicRun.all_passed,
    hidden_passed: hidden.all_passed,
    accepted: Boolean(retained.all_passed && publicRun.all_passed && hidden.all_passed),
    worker_pid: process.pid,
  };
}

async function main() {
  const mode = process.argv[2];
  const raw = await new Promise(resolve => {
    let buffer = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => { buffer += chunk; });
    process.stdin.on('end', () => resolve(buffer));
  });
  let request;
  try {
    request = JSON.parse(raw);
  } catch (error) {
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, fatal_error: 'malformed_request'}));
    return;
  }
  try {
    let result;
    if (mode === 'construct') result = await constructCandidate(request);
    else if (mode === 'validate') result = await validateCandidate(request);
    else if (mode === 'execute') result = await executeBody(request.body, request.cases);
    else throw new Error('unknown_mode:' + mode);
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, result}));
  } catch (error) {
    const detail = String(error && error.message ? error.message : error);
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, fatal_error: detail}));
  }
}

await main();
