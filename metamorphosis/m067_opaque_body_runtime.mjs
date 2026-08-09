/**
 * M067 opaque body host.
 *
 * The host owns four committed body contracts.  Callers receive opaque handles and may submit
 * byte frames, but no mode returns a contract descriptor.  Candidate construction and result
 * decoding live outside this process; this file is the independently executed body boundary.
 */
import { createHash } from "node:crypto";

const RESPONSE_SCHEMA = "m067-opaque-body-response-v1";
const SKILLS = ["add", "max", "mean", "mul"];

const BODY_BANK = [
  {
    handle: "body-0d62a9c8",
    family: "register",
    checksum: "sum",
    opcodes: { add: 0x29, max: 0x67, mean: 0x11, mul: 0x43 },
    resultOffset: 1,
    resultEndian: "big",
    resultTransform: "xor_a5a5",
  },
  {
    handle: "body-3f91e574",
    family: "stack",
    checksum: "xor",
    opcodes: { add: 0x67, max: 0x29, mean: 0x43, mul: 0x11 },
    resultOffset: 2,
    resultEndian: "little",
    resultTransform: "identity",
  },
  {
    handle: "body-71bc406e",
    family: "mailbox",
    checksum: "sum",
    opcodes: { add: 0x43, max: 0x11, mean: 0x29, mul: 0x67 },
    resultOffset: 0,
    resultEndian: "big",
    resultTransform: "identity",
  },
  {
    handle: "body-c4a28f13",
    family: "register",
    checksum: "xor",
    opcodes: { add: 0x43, max: 0x67, mean: 0x29, mul: 0x11 },
    resultOffset: 2,
    resultEndian: "little",
    resultTransform: "xor_a5a5",
  },
];

function bankCommitment() {
  return createHash("sha256")
    .update("m067-body-bank-v1\0", "utf8")
    .update(JSON.stringify(BODY_BANK), "utf8")
    .digest("hex");
}

function bodyDigest(body) {
  return createHash("sha256")
    .update("m067-body-contract-v1\0", "utf8")
    .update(JSON.stringify(body), "utf8")
    .digest("hex");
}

function checksum(kind, opcode, arity, args) {
  const bytes = [opcode, arity, ...args];
  if (kind === "xor") {
    return bytes.reduce((value, item) => value ^ item, 0x5a) & 0xff;
  }
  if (kind === "sum") {
    return bytes.reduce((value, item) => value + item, 0x17) & 0xff;
  }
  throw new Error("unknown checksum rule");
}

function parseRegister(frame) {
  if (frame.length < 7 || frame[0] !== 0xa7 || frame.at(-1) !== 0x7a) return null;
  const arity = frame[1];
  if (frame.length !== arity + 5) return null;
  return {
    arity,
    opcode: frame[2],
    args: frame.slice(3, 3 + arity),
    check: frame.at(-2),
  };
}

function parseStack(frame) {
  if (frame.length < 9 || frame[0] !== 0xb1 || frame.at(-1) !== 0x0f) return null;
  const arity = frame.at(-3);
  if (frame.length !== 1 + 2 * arity + 4) return null;
  const args = [];
  for (let index = 0; index < arity; index += 1) {
    if (frame[1 + index * 2] !== 0x05) return null;
    args.push(frame[2 + index * 2]);
  }
  return {
    arity,
    opcode: frame[1 + 2 * arity],
    args,
    check: frame.at(-2),
  };
}

function parseMailbox(frame) {
  if (frame.length < 10 || frame[0] !== 0xc3 || frame.at(-1) !== 0x64) return null;
  const arity = frame[1];
  if (frame.length !== 2 + 2 * arity + 4) return null;
  const args = [];
  for (let index = 0; index < arity; index += 1) {
    if (frame[2 + index * 2] !== 0x60 + index) return null;
    args.push(frame[3 + index * 2]);
  }
  const cursor = 2 + 2 * arity;
  if (frame[cursor] !== 0x6f) return null;
  return {
    arity,
    opcode: frame[cursor + 1],
    args,
    check: frame[cursor + 2],
  };
}

function parseFrame(family, frame) {
  if (family === "register") return parseRegister(frame);
  if (family === "stack") return parseStack(frame);
  if (family === "mailbox") return parseMailbox(frame);
  return null;
}

function signedByte(value) {
  return value >= 0x80 ? value - 0x100 : value;
}

function evaluateSkill(skill, args) {
  if (skill === "add" && args.length === 2) return args[0] + args[1];
  if (skill === "mul" && args.length === 2) return args[0] * args[1];
  if (skill === "max" && args.length === 2) return Math.max(...args);
  if (skill === "mean" && args.length === 3) {
    return (args[0] + args[1] + args[2]) / 3;
  }
  return null;
}

function encodeResponse(body, value) {
  // A denominator divisible by three preserves the inherited ternary mean exactly for the
  // integer observation domain while keeping every declared result inside signed 16 bits.
  let raw = Math.round(value * 300);
  if (raw < -32768 || raw > 32767) throw new Error("result outside signed fixed-point range");
  raw &= 0xffff;
  if (body.resultTransform === "xor_a5a5") raw ^= 0xa5a5;
  const low = raw & 0xff;
  const high = (raw >>> 8) & 0xff;
  const pair = body.resultEndian === "little" ? [low, high] : [high, low];
  const response = [0xd1, 0x3c, 0xe7, 0x89];
  response[body.resultOffset] = pair[0];
  response[body.resultOffset + 1] = pair[1];
  return Buffer.from(response);
}

function transactOpaque(body, frame) {
  const parsed = parseFrame(body.family, frame);
  if (!parsed || parsed.check !== checksum(body.checksum, parsed.opcode, parsed.arity, parsed.args)) {
    return { accepted: false, output: null };
  }
  const skill = SKILLS.find((name) => body.opcodes[name] === parsed.opcode);
  if (!skill) return { accepted: false, output: null };
  // Buffer#map coerces negative callback results back to unsigned bytes.  Array.from keeps the
  // signed values, so register frames have the same numeric semantics as the array parsers.
  const value = evaluateSkill(skill, Array.from(parsed.args, signedByte));
  if (value === null) return { accepted: false, output: null };
  return { accepted: true, output: encodeResponse(body, value) };
}

function evaluateBatch(request) {
  const body = BODY_BANK.find((candidate) => candidate.handle === request.body_handle);
  if (!body) throw new Error("unknown opaque body handle");
  if (!Array.isArray(request.attempts) || request.attempts.length > 50000) {
    throw new Error("invalid or excessive attempt batch");
  }
  return {
    records: request.attempts.map((attempt) => {
      const frame = Buffer.from(String(attempt.frame), "base64");
      const outcome = transactOpaque(body, frame);
      return {
        id: String(attempt.id),
        accepted: outcome.accepted,
        output: outcome.output ? outcome.output.toString("base64") : null,
      };
    }),
  };
}

function handle(mode, request) {
  if (mode === "attest") {
    return {
      body_count: BODY_BANK.length,
      body_handles: BODY_BANK.map((body) => body.handle),
      body_bank_commitment: bankCommitment(),
      body_digests: BODY_BANK.map(bodyDigest),
      contract_descriptors_disclosed: false,
    };
  }
  if (mode === "public" || mode === "hidden") return evaluateBatch(request);
  throw new Error("unknown mode");
}

const mode = process.argv[2];
let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => { input += chunk; });
process.stdin.on("end", () => {
  try {
    const request = input ? JSON.parse(input) : {};
    const result = handle(mode, request);
    process.stdout.write(JSON.stringify({ schema: RESPONSE_SCHEMA, mode, result }));
  } catch (error) {
    process.stdout.write(JSON.stringify({
      schema: RESPONSE_SCHEMA,
      mode,
      fatal_error: error instanceof Error ? error.message : String(error),
    }));
    process.exitCode = 1;
  }
});
