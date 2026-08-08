// M061 copy runtime: prove the discovered instructions compute, not merely that they were named.
//
// Recovering an opcode by probe says a byte behaved a certain way in one shape. It does not say
// the byte is usable inside a loop, addressing memory the caller wrote. This runs the emitted
// loop over a phrase and reports what came out the other side.
const RESPONSE_SCHEMA = 'm061-copy-response-v1';

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
    process.stdout.write(JSON.stringify({schema: RESPONSE_SCHEMA, error: 'malformed_request'}));
    return;
  }

  try {
    const module = new WebAssembly.Module(Buffer.from(request.wasm, 'base64'));
    const imports = WebAssembly.Module.imports(module);
    if (imports.length !== 0) throw new Error('module_declares_imports:' + imports.length);
    const instance = new WebAssembly.Instance(module, {});
    const memory = new Uint8Array(instance.exports.memory.buffer);

    const payload = Buffer.from(request.phrase, 'ascii');
    memory.fill(0, request.source, request.source + payload.length);
    memory.fill(0, request.destination, request.destination + payload.length);
    memory.set(payload, request.source);

    instance.exports.f(request.source, request.destination, payload.length);

    const copied = Buffer.from(
      memory.slice(request.destination, request.destination + payload.length)
    ).toString('ascii');

    process.stdout.write(JSON.stringify({
      schema: RESPONSE_SCHEMA,
      import_count: imports.length,
      copied,
      correct: copied === request.phrase,
    }));
  } catch (error) {
    process.stdout.write(JSON.stringify({
      schema: RESPONSE_SCHEMA,
      error: String(error && error.message ? error.message : error),
      correct: false,
    }));
  }
}

await main();
