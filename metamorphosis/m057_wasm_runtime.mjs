// M057 synthesis runtime.
//
// Synthesis evaluates every candidate by CALLING THE SUBSTRATE. The opaque handles are real
// WebAssembly exports, invoked through `instance.exports[name](a, b)`. Nothing here holds a
// table of what a handle means; the only way to learn what `h4` does is to run it.
//
// An earlier draft evaluated candidates in Python against a table of the opcodes' semantics.
// That would have let the lineage synthesize using knowledge it was supposed to discover, and
// the experiment would have measured nothing.
//
// Enumeration is bottom-up by expression size, deduplicating candidates whose observed values
// coincide on the probe domain. That is M052's equivalence argument used as infrastructure.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const RESPONSE_SCHEMA = 'm057-node-response-v1';

function instantiate(base64) {
  const module = new WebAssembly.Module(Buffer.from(base64, 'base64'));
  const imports = WebAssembly.Module.imports(module);
  if (imports.length !== 0) throw new Error('module_declares_imports:' + imports.length);
  return {
    instance: new WebAssembly.Instance(module, {}),
    importCount: imports.length,
    exported: WebAssembly.Module.exports(module).filter(e => e.kind === 'function').map(e => e.name).sort(),
  };
}

// Probing: run each opaque handle on shared input pairs and report what came back.
function probe(request) {
  const {probe_wasm, pairs} = request;
  const loaded = instantiate(probe_wasm);
  const observations = {};
  for (const name of loaded.exported) {
    const fn = loaded.instance.exports[name];
    observations[name] = pairs.map(([a, b]) => {
      const value = fn(a, b);
      return Number.isFinite(value) ? value : null;
    });
  }
  return {schema: RESPONSE_SCHEMA, handles: loaded.exported, import_count: loaded.importCount, observations};
}

function keyOf(values) {
  // Round to a fixed precision so f64 noise does not split one behaviour into many classes.
  return values.map(v => (v === null ? 'x' : v.toPrecision(15))).join('|');
}

function synthesize(request) {
  const {probe_wasm, observations, arity, max_size, budget, allow_composition} = request;
  const loaded = instantiate(probe_wasm);
  const handles = loaded.exported;
  const call = {};
  for (const name of handles) call[name] = loaded.instance.exports[name];

  const atoms = [];
  for (let i = 0; i < arity; i += 1) atoms.push('p' + i);
  atoms.push('k');

  const target = observations.map(item => item.expected);
  const envs = observations.map(item => {
    const env = {k: arity};
    item.args.forEach((value, index) => { env['p' + index] = value; });
    return env;
  });

  const matches = values => values.every((v, i) => v !== null && Math.abs(v - target[i]) < 1e-12);

  const bySize = new Map([[1, new Map()]]);
  const behaviours = new Map();
  let constructed = 0;

  for (const atom of atoms) {
    const values = envs.map(env => env[atom]);
    const key = keyOf(values);
    constructed += 1;
    if (!behaviours.has(key)) {
      const entry = {values, node: {atom}};
      behaviours.set(key, entry);
      bySize.get(1).set(key, entry);
      if (matches(values)) {
        return {schema: RESPONSE_SCHEMA, status: 'synthesized', expression: entry.node,
                expression_size: 1, candidates_constructed: constructed, behaviour_classes: behaviours.size};
      }
    }
  }

  if (!allow_composition) {
    return {schema: RESPONSE_SCHEMA, status: 'composition_denied', expression: null, expression_size: 0,
            candidates_constructed: constructed, behaviour_classes: behaviours.size};
  }

  for (let size = 3; size <= max_size; size += 2) {
    bySize.set(size, new Map());
    for (let leftSize = 1; leftSize < size - 1; leftSize += 2) {
      const rightSize = size - 1 - leftSize;
      const left = bySize.get(leftSize);
      const right = bySize.get(rightSize);
      if (!left || !right) continue;
      for (const leftEntry of left.values()) {
        for (const rightEntry of right.values()) {
          for (const name of handles) {
            if (constructed >= budget) {
              return {schema: RESPONSE_SCHEMA, status: 'budget_exhausted', expression: null, expression_size: 0,
                      candidates_constructed: constructed, behaviour_classes: behaviours.size};
            }
            constructed += 1;
            const values = [];
            let usable = true;
            for (let i = 0; i < envs.length; i += 1) {
              const l = leftEntry.values[i];
              const r = rightEntry.values[i];
              if (l === null || r === null) { usable = false; break; }
              const value = call[name](l, r);          // the substrate answers, not a table
              if (!Number.isFinite(value)) { usable = false; break; }
              values.push(value);
            }
            if (!usable) continue;
            const key = keyOf(values);
            if (behaviours.has(key)) continue;
            const entry = {values, node: {handle: name, left: leftEntry.node, right: rightEntry.node}};
            behaviours.set(key, entry);
            bySize.get(size).set(key, entry);
            if (matches(values)) {
              return {schema: RESPONSE_SCHEMA, status: 'synthesized', expression: entry.node,
                      expression_size: size, candidates_constructed: constructed, behaviour_classes: behaviours.size};
            }
          }
        }
      }
    }
  }
  return {schema: RESPONSE_SCHEMA, status: 'insufficient_evidence', expression: null, expression_size: 0,
          candidates_constructed: constructed, behaviour_classes: behaviours.size};
}

function isToolModule(name) {
  return name === 'tool_core' || name.startsWith('tool_');
}

async function loadShell(body) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'm057-shell-'));
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

// Execute the lineage through tools the lineage itself synthesized.
async function executeSynthesized(request) {
  const {body, tool_modules, cases} = request;
  const tools = {};
  let importCount = 0;
  for (const [name, base64] of Object.entries(tool_modules)) {
    const loaded = instantiate(base64);
    importCount += loaded.importCount;
    const exported = loaded.instance.exports[name];
    tools[name] = args => exported(...args);
  }
  const shell = await loadShell(body);
  try {
    const results = [];
    for (const item of cases) {
      let result;
      try {
        result = shell.modules.orchestration.run(item.request, shell.modules, tools);
      } catch (error) {
        result = {ok: false, error_stage: 'orchestration', error_message: String(error && error.message ? error.message : error)};
      }
      results.push({case_id: item.case_id, request: item.request, expected: item.expected,
                    passed: Boolean(result.ok && result.output === item.expected), result});
    }
    return {schema: RESPONSE_SCHEMA, runtime: 'webassembly', worker_pid: process.pid,
            import_count: importCount, tool_count: Object.keys(tools).length,
            all_passed: results.every(item => item.passed), case_results: results};
  } finally {
    await fs.rm(shell.directory, {recursive: true, force: true});
  }
}

// The lineage observing its own accepted tools in the substrate it currently runs in. This is
// where the synthesis targets come from: it knows what `mean` does because it can run `mean`,
// not because anyone described it.
async function observeTools(request) {
  const {body, samples} = request;
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'm057-observe-'));
  try {
    const toolModules = body.modules.filter(item => isToolModule(item.name));
    const tools = {};
    for (const item of toolModules) await fs.writeFile(path.join(directory, `${item.name}.mjs`), item.source, 'utf8');
    for (const item of toolModules) {
      const url = pathToFileURL(path.join(directory, `${item.name}.mjs`));
      url.searchParams.set('identity', `${process.pid}-${Date.now()}-${item.name}`);
      const loaded = await import(url.href);
      for (const [name, fn] of Object.entries(loaded.TOOLS ?? {})) tools[name] = fn;
    }
    const observations = {};
    for (const [name, argumentLists] of Object.entries(samples)) {
      if (!tools[name]) throw new Error('tool_absent_from_body:' + name);
      observations[name] = argumentLists.map(args => {
        const value = tools[name](args);
        return Number.isFinite(value) ? value : null;
      });
    }
    return {schema: RESPONSE_SCHEMA, tools: Object.keys(tools).sort(), observations};
  } finally {
    await fs.rm(directory, {recursive: true, force: true});
  }
}

// Run a synthesized module on arguments the synthesis never saw.
function verifyHidden(request) {
  const {tool_modules, checks} = request;
  const verified = {};
  for (const [name, base64] of Object.entries(tool_modules)) {
    const loaded = instantiate(base64);
    const fn = loaded.instance.exports[name];
    if (typeof fn !== 'function') { verified[name] = false; continue; }
    verified[name] = (checks[name] ?? []).every(item => {
      const value = fn(...item.args);
      return Number.isFinite(value) && Math.abs(value - item.expected) < 1e-12;
    });
  }
  return {schema: RESPONSE_SCHEMA, verified};
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
    if (mode === 'probe') result = probe(request);
    else if (mode === 'synthesize') result = synthesize(request);
    else if (mode === 'observe') result = await observeTools(request);
    else if (mode === 'verify') result = verifyHidden(request);
    else if (mode === 'execute') result = await executeSynthesized(request);
    else throw new Error('unknown_mode:' + mode);
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, result}));
  } catch (error) {
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, fatal_error: String(error && error.message ? error.message : error)}));
  }
}

await main();
