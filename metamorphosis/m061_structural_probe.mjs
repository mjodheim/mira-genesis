// M061 structural probe: one candidate per process, so a non-terminating one cannot hang a scan.
//
// M058 scanned arithmetic and every candidate terminated. Structural instructions do not offer
// that courtesy. `0x12` is a tail call, and a scaffold that calls its own function through it
// recurses without growing the stack: it never traps, never returns, and a scan that executes
// candidates in one process stops there. `0x10`, an ordinary call, exhausts the stack and traps
// — the two differ only in whether the loop is observable as a failure.
//
// So termination is a third outcome, alongside refused-by-the-validator and observed. The parent
// enforces it with a timeout; nothing here can decide it, because deciding it is the halting
// problem.
const RESPONSE_SCHEMA = 'm061-node-response-v1';

async function main() {
  const raw = await new Promise(resolve => {
    let buffer = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => { buffer += chunk; });
    process.stdin.on('end', () => resolve(buffer));
  });

  let request;
  try { request = JSON.parse(raw); }
  catch (error) {
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, outcome: 'malformed_request'}));
    return;
  }

  let instance;
  try {
    const module = new WebAssembly.Module(Buffer.from(request.wasm, 'base64'));
    if (WebAssembly.Module.imports(module).length !== 0) {
      process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, outcome: 'declares_imports'}));
      return;
    }
    instance = new WebAssembly.Instance(module, {});
  } catch (error) {
    // The substrate refused it as a program. That refusal is the information.
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, outcome: 'refused'}));
    return;
  }

  const observations = [];
  for (const call of request.calls) {
    if (Array.isArray(call.memory)) {
      const view = new Uint8Array(instance.exports.memory.buffer);
      for (const [address, value] of call.memory) view[address] = value;
    }
    let value;
    try {
      value = instance.exports.f(...call.args);
    } catch (error) {
      process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, outcome: 'trapped'}));
      return;
    }
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, outcome: 'unusable'}));
      return;
    }
    if (Array.isArray(call.read)) {
      const view = new Uint8Array(instance.exports.memory.buffer);
      observations.push(call.read.map(address => view[address]));
    } else {
      observations.push(value);
    }
  }
  process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, outcome: 'observed', observations}));
}

await main();
