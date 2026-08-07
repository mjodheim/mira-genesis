// M056 second-migration runtime.
//
// The accepted M048 body executes its capabilities through JavaScript tool modules. Here the
// tools come from a WebAssembly module instead: the arithmetic lives in wasm bytecode, the
// module declares no imports, and it therefore cannot call back out for its semantics.
//
// What remains in JavaScript is the request shell — tokenising, routing, orchestration — and the
// calling convention. `adapt` spreads an array into positional f64 arguments and performs no
// arithmetic of its own. The protocol states this boundary rather than claiming the whole body
// moved.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const RESPONSE_SCHEMA = 'm056-node-response-v1';

function moduleMap(body) {
  return Object.fromEntries(body.modules.map(module => [module.name, module]));
}

function isToolModule(name) {
  return name === 'tool_core' || name.startsWith('tool_');
}

// Calling convention only: array in, positional f64 out. No arithmetic.
function adapt(exported) {
  return args => exported(...args);
}

async function instantiate(wasmBase64) {
  const bytes = Buffer.from(wasmBase64, 'base64');
  const module = new WebAssembly.Module(bytes);
  const imports = WebAssembly.Module.imports(module);
  if (imports.length !== 0) {
    throw new Error('wasm_module_declares_imports:' + imports.length);
  }
  const instance = new WebAssembly.Instance(module, {});
  const tools = {};
  for (const item of WebAssembly.Module.exports(module)) {
    if (item.kind === 'function') tools[item.name] = adapt(instance.exports[item.name]);
  }
  return {tools, importCount: imports.length, exported: Object.keys(tools).sort()};
}

async function loadShell(body) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'm056-wasm-shell-'));
  const modules = {};
  try {
    const shell = body.modules.filter(item => !isToolModule(item.name));
    for (const item of shell) await fs.writeFile(path.join(directory, `${item.name}.mjs`), item.source, 'utf8');
    for (const item of shell) {
      const url = pathToFileURL(path.join(directory, `${item.name}.mjs`));
      url.searchParams.set('identity', `${process.pid}-${Date.now()}-${item.name}`);
      modules[item.name] = await import(url.href);
    }
    return {directory, modules};
  } catch (error) {
    await fs.rm(directory, {recursive: true, force: true});
    throw error;
  }
}

async function executeOnWasm(body, wasmBase64, cases) {
  const runtime = await instantiate(wasmBase64);
  const shell = await loadShell(body);
  try {
    const results = [];
    for (const item of cases) {
      let result;
      try {
        result = shell.modules.orchestration.run(item.request, shell.modules, runtime.tools);
      } catch (error) {
        result = {ok: false, error_stage: 'orchestration', error_message: String(error && error.message ? error.message : error)};
      }
      results.push({
        case_id: item.case_id,
        request: item.request,
        expected: item.expected,
        passed: Boolean(result.ok && result.output === item.expected),
        result,
      });
    }
    return {
      runtime: 'webassembly',
      worker_pid: process.pid,
      wasm_import_count: runtime.importCount,
      wasm_exported_tools: runtime.exported,
      shell_module_count: Object.keys(shell.modules).length,
      all_passed: results.every(item => item.passed),
      case_results: results,
    };
  } finally {
    await fs.rm(shell.directory, {recursive: true, force: true});
  }
}

// Removing the wasm module must break every migrated capability. If the shell still answers,
// the semantics never left JavaScript and the migration claim is false.
async function executeWithoutWasm(body, cases) {
  const shell = await loadShell(body);
  try {
    const results = [];
    for (const item of cases) {
      let passed = false;
      try {
        const result = shell.modules.orchestration.run(item.request, shell.modules, {});
        passed = Boolean(result.ok && result.output === item.expected);
      } catch (error) {
        passed = false;
      }
      results.push({case_id: item.case_id, passed});
    }
    return {any_passed: results.some(item => item.passed), passed_count: results.filter(i => i.passed).length, total: results.length};
  } finally {
    await fs.rm(shell.directory, {recursive: true, force: true});
  }
}

// Post-migration learning, in the migrated substrate. The proposer sees public cases only.
async function proposeInWasm(request) {
  const {body, wasm, candidate_wasm, public_cases, tool_name} = request;
  const incumbent = await executeOnWasm(body, wasm, public_cases);
  const failures = incumbent.case_results.filter(item => !item.passed);
  const tokens = new Set();
  for (const failure of failures) {
    const message = String(failure.result.error_message ?? '');
    if (message.startsWith('unknown_operator:')) tokens.add(message.slice('unknown_operator:'.length));
    if (message.startsWith('route_missing:')) tokens.add(message.slice('route_missing:'.length));
  }
  const diagnosed = tokens.size === 1 ? [...tokens][0] : null;
  if (!diagnosed) {
    return {schema: RESPONSE_SCHEMA, status: 'insufficient_diagnosis', diagnosed_token: diagnosed, incumbent};
  }
  const candidate = await instantiate(candidate_wasm);
  const exposes = Object.prototype.hasOwnProperty.call(candidate.tools, tool_name);
  return {
    schema: RESPONSE_SCHEMA,
    status: exposes ? 'ready' : 'candidate_missing_tool',
    diagnosed_token: diagnosed,
    candidate_exports: candidate.exported,
    candidate_import_count: candidate.importCount,
    incumbent,
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
    if (mode === 'execute') result = await executeOnWasm(request.body, request.wasm, request.cases);
    else if (mode === 'without_wasm') result = await executeWithoutWasm(request.body, request.cases);
    else if (mode === 'propose') result = await proposeInWasm(request);
    else throw new Error('unknown_mode:' + mode);
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, result}));
  } catch (error) {
    const detail = String(error && error.message ? error.message : error);
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, fatal_error: detail}));
  }
}

await main();
