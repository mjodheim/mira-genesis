// M063 checksum runtime. Candidate generation and admission remain in Python; this process owns
// only WebAssembly validation and observation, with no repository or network authority.
import fs from "node:fs";

const RESPONSE_SCHEMA = "m063-checksum-response-v1";

function write(value) {
  process.stdout.write(JSON.stringify(value));
}

async function observe(candidate, cases) {
  let instance;
  let importCount;
  try {
    const bytes = Buffer.from(candidate.wasm, "base64");
    const module = new WebAssembly.Module(bytes);
    importCount = WebAssembly.Module.imports(module).length;
    instance = new WebAssembly.Instance(module, {});
  } catch (error) {
    return { outcome: "refused", error: error?.constructor?.name ?? "Error", cases: {} };
  }

  const fn = instance.exports.f;
  const memory = instance.exports.memory;
  if (typeof fn !== "function" || !(memory instanceof WebAssembly.Memory)) {
    return { outcome: "refused", error: "missing_exports", cases: {} };
  }

  const observations = {};
  for (const item of cases) {
    const view = new Uint8Array(memory.buffer);
    view.fill(item.background);
    view.set(item.payload, item.source);
    const before = Buffer.from(view);
    try {
      const returnValue = fn(item.source, item.count);
      observations[item.name] = {
        outcome: "observed",
        return_value: returnValue,
        memory_unchanged: before.equals(Buffer.from(view)),
        source_after: Array.from(view.slice(item.source, item.source + item.payload.length)),
      };
    } catch (error) {
      observations[item.name] = {
        outcome: "trapped",
        error: error?.constructor?.name ?? "Error",
      };
    }
  }
  return { outcome: "observed", import_count: importCount, cases: observations };
}

async function main() {
  let request;
  try {
    request = JSON.parse(fs.readFileSync(0, "utf8"));
  } catch (error) {
    write({ schema: RESPONSE_SCHEMA, outcome: "malformed_request", results: {} });
    return;
  }
  if (request.schema !== "m063-checksum-request-v1") {
    write({ schema: RESPONSE_SCHEMA, outcome: "identity_mismatch", results: {} });
    return;
  }

  const results = {};
  for (const candidate of request.candidates ?? []) {
    results[candidate.digest] = await observe(candidate, request.cases ?? []);
  }
  write({ schema: RESPONSE_SCHEMA, outcome: "observed", results });
}

await main();
