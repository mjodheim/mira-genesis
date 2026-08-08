// M060 execution runtime.
//
// There is almost nothing here, and that is the result. In M056 through M059 this file held a
// JavaScript shell — tokenising, routing, planning, orchestration — and called into WebAssembly
// only for arithmetic. The whole shell now lives in the module, so all that remains is writing
// request bytes into linear memory and reading a number back.
//
// The module is instantiated with **no import object at all**. It cannot call outward, and the
// check is structural rather than a promise.
const RESPONSE_SCHEMA = 'm060-node-response-v1';

const REQUEST_PTR = 0;
const REQUEST_LEN_PTR = 256;

function load(base64) {
  const module = new WebAssembly.Module(Buffer.from(base64, 'base64'));
  const imports = WebAssembly.Module.imports(module);
  if (imports.length !== 0) throw new Error('module_declares_imports:' + imports.length);
  return {module, imports, instance: new WebAssembly.Instance(module)};
}

function inspect(request) {
  const {module, imports} = load(request.wasm);
  return {
    schema: RESPONSE_SCHEMA,
    import_count: imports.length,
    exports: WebAssembly.Module.exports(module).map(item => item.name).sort(),
    function_exports: WebAssembly.Module.exports(module)
      .filter(item => item.kind === 'function').map(item => item.name).sort(),
  };
}

function execute(request) {
  const {instance} = load(request.wasm);
  const memory = new Uint8Array(instance.exports.memory.buffer);
  const view = new DataView(instance.exports.memory.buffer);
  const results = [];
  for (const item of request.cases) {
    const payload = Buffer.from(item.request, 'ascii');
    memory.fill(0, REQUEST_PTR, REQUEST_PTR + 256);
    memory.set(payload, REQUEST_PTR);
    view.setInt32(REQUEST_LEN_PTR, payload.length, true);
    let output = null;
    let refused = false;
    try {
      output = instance.exports.run();
    } catch (error) {
      refused = true;
    }
    results.push({
      case_id: item.case_id,
      request: item.request,
      expected: item.expected,
      output,
      refused,
      passed: !refused && output === item.expected,
    });
  }
  return {
    schema: RESPONSE_SCHEMA,
    runtime: 'webassembly',
    worker_pid: process.pid,
    passed_count: results.filter(item => item.passed).length,
    all_passed: results.every(item => item.passed),
    case_results: results,
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
  try { request = JSON.parse(raw); }
  catch (error) {
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, fatal_error: 'malformed_request'}));
    return;
  }
  try {
    let result;
    if (mode === 'inspect') result = inspect(request);
    else if (mode === 'execute') result = execute(request);
    else throw new Error('unknown_mode:' + mode);
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, result}));
  } catch (error) {
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, mode, fatal_error: String(error && error.message ? error.message : error)}));
  }
}

await main();
