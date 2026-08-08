// M059 judgement runtime.
//
// Two signature shapes are scanned, `f64` and `i32`, each over the whole single-byte opcode
// space. What each substrate contains is discovered, never supplied.
//
// Synthesis is M058's, with one addition the substrates forced: `i32.div_s` and `i32.rem_s`
// **trap** on a zero divisor rather than returning a non-finite value. A candidate that traps is
// unusable, and the trap has to be caught rather than allowed to abort the search. The f64 shape
// never traps — it yields Infinity — so this difference is itself something the two substrates
// do not share.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const RESPONSE_SCHEMA = 'm059-node-response-v1';

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

function scan(request) {
  const {candidates, pairs, export_name} = request;
  const valid = {};
  let rejected = 0;
  for (const [name, base64] of Object.entries(candidates)) {
    let fn;
    try {
      fn = new WebAssembly.Instance(new WebAssembly.Module(Buffer.from(base64, 'base64')), {}).exports[export_name];
    } catch (error) { rejected += 1; continue; }
    if (typeof fn !== 'function') { rejected += 1; continue; }
    const observations = [];
    let usable = true;
    for (const [a, b] of pairs) {
      let value;
      try { value = fn(a, b); } catch (error) { usable = false; break; }
      if (!Number.isFinite(value)) { usable = false; break; }
      observations.push(value);
    }
    if (!usable) { rejected += 1; continue; }
    valid[name] = observations;
  }
  return {schema: RESPONSE_SCHEMA, scanned: Object.keys(candidates).length, valid,
          valid_count: Object.keys(valid).length, rejected_count: rejected};
}

function keyOf(values) {
  return values.map(v => v.toPrecision(15)).join('|');
}

function synthesizeWith(operationsWasm, observations, arity, maxSize, budget) {
  const loaded = instantiate(operationsWasm);
  const names = loaded.exported;
  const call = {};
  for (const name of names) call[name] = loaded.instance.exports[name];

  const atoms = [];
  for (let i = 0; i < arity; i += 1) atoms.push('p' + i);
  atoms.push('k');

  const target = observations.map(item => item.expected);
  const envs = observations.map(item => {
    const env = {k: arity};
    item.args.forEach((value, index) => { env['p' + index] = value; });
    return env;
  });
  const matches = values => values.every((v, i) => Math.abs(v - target[i]) < 1e-12);

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
        return {status: 'synthesized', expression: entry.node, expression_size: 1,
                candidates_constructed: constructed, behaviour_classes: behaviours.size,
                operation_count: names.length};
      }
    }
  }

  for (let size = 3; size <= maxSize; size += 2) {
    bySize.set(size, new Map());
    for (let leftSize = 1; leftSize < size - 1; leftSize += 2) {
      const rightSize = size - 1 - leftSize;
      const left = bySize.get(leftSize);
      const right = bySize.get(rightSize);
      if (!left || !right) continue;
      for (const leftEntry of left.values()) {
        for (const rightEntry of right.values()) {
          for (const name of names) {
            if (constructed >= budget) {
              return {status: 'budget_exhausted', expression: null, expression_size: 0,
                      candidates_constructed: constructed, behaviour_classes: behaviours.size,
                      operation_count: names.length};
            }
            constructed += 1;
            const values = [];
            let usable = true;
            for (let i = 0; i < envs.length; i += 1) {
              let value;
              try { value = call[name](leftEntry.values[i], rightEntry.values[i]); }
              catch (error) { usable = false; break; }   // i32 division traps on zero
              if (!Number.isFinite(value)) { usable = false; break; }
              values.push(value);
            }
            if (!usable) continue;
            const key = keyOf(values);
            if (behaviours.has(key)) continue;
            const entry = {values, node: {operation: name, left: leftEntry.node, right: rightEntry.node}};
            behaviours.set(key, entry);
            bySize.get(size).set(key, entry);
            if (matches(values)) {
              return {status: 'synthesized', expression: entry.node, expression_size: size,
                      candidates_constructed: constructed, behaviour_classes: behaviours.size,
                      operation_count: names.length};
            }
          }
        }
      }
    }
  }
  return {status: 'insufficient_evidence', expression: null, expression_size: 0,
          candidates_constructed: constructed, behaviour_classes: behaviours.size,
          operation_count: names.length};
}

// One mechanism produces all three outcomes. The refusal is not a separate branch: it is what
// happens when the current substrate answers first.
function judge(request) {
  const {current, alternative, current_wasm, alternative_wasm, observations, arity, max_size, budget} = request;
  const here = synthesizeWith(current_wasm, observations, arity, max_size, budget);
  if (here.status === 'synthesized') {
    return {schema: RESPONSE_SCHEMA, decision: 'stay', substrate: current,
            reason: 'the current substrate expresses the capability',
            here, there: null};
  }
  const there = synthesizeWith(alternative_wasm, observations, arity, max_size, budget);
  if (there.status === 'synthesized') {
    return {schema: RESPONSE_SCHEMA, decision: 'migrate', substrate: alternative,
            reason: `the current substrate returned ${here.status}`,
            here, there};
  }
  return {schema: RESPONSE_SCHEMA, decision: 'insufficient_evidence', substrate: current,
          reason: `neither substrate expressed the capability: ${here.status} and ${there.status}`,
          here, there};
}

function verifyHidden(request) {
  const {tool_modules, checks} = request;
  const verified = {};
  for (const [name, base64] of Object.entries(tool_modules)) {
    const loaded = instantiate(base64);
    const fn = loaded.instance.exports[name];
    if (typeof fn !== 'function') { verified[name] = false; continue; }
    verified[name] = (checks[name] ?? []).every(item => {
      let value;
      try { value = fn(...item.args); } catch (error) { return false; }
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
  try { request = JSON.parse(raw); }
  catch (error) {
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, fatal_error: 'malformed_request'}));
    return;
  }
  try {
    let result;
    if (mode === 'scan') result = scan(request);
    else if (mode === 'judge') result = judge(request);
    else if (mode === 'verify') result = verifyHidden(request);
    else throw new Error('unknown_mode:' + mode);
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, result}));
  } catch (error) {
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, fatal_error: String(error && error.message ? error.message : error)}));
  }
}

await main();
