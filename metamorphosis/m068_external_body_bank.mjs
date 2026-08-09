/**
 * M068 frozen external body bank.
 *
 * The public boundary exposes opaque action handles and raw behavioural observations.  It never
 * returns the command words or their semantic assignments.  This file is committed before the
 * discovery engine and is subsequently protected by a recorded SHA-256.
 */
import { createHash } from "node:crypto";

const RESPONSE_SCHEMA = "m068-external-body-response-v1";
const MAX_WORD_LENGTH = 5;
const MAX_BATCH_ATTEMPTS = 50000;
const ACTIONS = [
  "signal-0b", "signal-1f", "signal-34", "signal-49",
  "signal-62", "signal-78", "signal-95", "signal-ac",
];

const BODY_BANK = [
  {
    handle: "vessel-18c7e2a4",
    commands: {
      add: [1, 4],
      max: [3, 0, 6],
      mean: [7, 2, 5, 1],
      mul: [2, 6, 4, 0, 7],
    },
  },
  {
    handle: "vessel-4a91d603",
    commands: {
      add: [6, 2, 0, 5],
      max: [1, 7],
      mean: [4, 3, 6, 2, 1],
      mul: [0, 5, 3],
    },
  },
  {
    handle: "vessel-7e30b8f1",
    commands: {
      add: [2, 1, 7, 4, 0],
      max: [6, 3, 5, 2],
      mean: [0, 4],
      mul: [7, 1, 6],
    },
  },
  {
    handle: "vessel-c5d2649a",
    commands: {
      add: [5, 0, 2],
      max: [7, 4, 1, 6, 3],
      mean: [3, 2, 5, 0],
      mul: [1, 6],
    },
  },
];

function canonicalBody(body) {
  return {
    handle: body.handle,
    commands: Object.fromEntries(
      Object.entries(body.commands).map(([skill, word]) => [
        skill,
        word.map((index) => ACTIONS[index]),
      ]),
    ),
  };
}

function digest(domain, value) {
  return createHash("sha256")
    .update(`${domain}\0`, "utf8")
    .update(JSON.stringify(value), "utf8")
    .digest("hex");
}

function bodyBankCommitment() {
  return digest("m068-body-bank-v1", BODY_BANK.map(canonicalBody));
}

function bodyDigest(body) {
  return digest("m068-body-v1", canonicalBody(body));
}

function evaluate(skill, args) {
  if (skill === "add") return args[0] + args[1];
  if (skill === "max") return Math.max(args[0], args[1]);
  if (skill === "mean") return (args[0] + args[1] + args[2]) / 3;
  if (skill === "mul") return args[0] * args[1];
  throw new Error("body bank carries an unknown semantic operation");
}

function validArguments(args) {
  return Array.isArray(args)
    && args.length === 3
    && args.every((value) => Number.isInteger(value) && value >= -128 && value <= 127);
}

function transact(body, actions, args) {
  if (!Array.isArray(actions) || actions.length === 0 || actions.length > MAX_WORD_LENGTH) {
    return { accepted: false, observation: null };
  }
  if (!actions.every((action) => ACTIONS.includes(action)) || !validArguments(args)) {
    return { accepted: false, observation: null };
  }
  const skill = Object.entries(body.commands).find(([_name, word]) => (
    word.length === actions.length && word.every((index, position) => ACTIONS[index] === actions[position])
  ))?.[0];
  if (!skill) return { accepted: false, observation: null };
  return { accepted: true, observation: evaluate(skill, args) };
}

function evaluateBatch(request) {
  const body = BODY_BANK.find((candidate) => candidate.handle === request.body_handle);
  if (!body) throw new Error("unknown opaque body handle");
  if (!Array.isArray(request.attempts) || request.attempts.length > MAX_BATCH_ATTEMPTS) {
    throw new Error("invalid or excessive attempt batch");
  }
  return {
    records: request.attempts.map((attempt) => {
      const result = transact(body, attempt.actions, attempt.args);
      return {
        id: String(attempt.id),
        accepted: result.accepted,
        observation: result.observation,
      };
    }),
  };
}

function handle(mode, request) {
  if (mode === "attest") {
    return {
      body_count: BODY_BANK.length,
      body_handles: BODY_BANK.map((body) => body.handle),
      action_handles: ACTIONS,
      max_word_length: MAX_WORD_LENGTH,
      complete_word_count: sumWords(ACTIONS.length, MAX_WORD_LENGTH),
      max_batch_attempts: MAX_BATCH_ATTEMPTS,
      body_bank_commitment: bodyBankCommitment(),
      body_digests: BODY_BANK.map(bodyDigest),
      command_words_disclosed: false,
      semantic_assignments_disclosed: false,
      descriptor_grammar_disclosed: false,
    };
  }
  if (mode === "public" || mode === "hidden") return evaluateBatch(request);
  throw new Error("unknown mode");
}

function sumWords(alphabetSize, maxLength) {
  let total = 0;
  for (let length = 1; length <= maxLength; length += 1) total += alphabetSize ** length;
  return total;
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
