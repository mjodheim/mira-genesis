"""Milestone-agnostic contract for a sealed task bank materialized outside this project.

M075 blocks on a person who does not exist yet: an independent human maintainer who writes a
private feasible/capability-absent bank and withholds it until the scientific protocol is frozen.
That requirement is correct and is not weakened here. This module builds a **different and
strictly weaker** instrument for the same shape of problem: a bank emitted by a model that was
never shown this repository, sealed before anyone reads it, and committed publicly by digest.

The distinction the whole design turns on is stated once, here, and repeated in every claim:

* **Context blindness is provable.** The generator receives one hashed input file in a container
  with no repository mount, no network and an allowlisted environment. What it was shown is a
  recorded fact.
* **Training-data independence is not provable.** A checkpoint published before this research line
  became public cannot have memorized *these* tasks, which is an antecedence argument about one
  corpus, not a proof of ignorance.
* **Human independence is not obtained at all.** No person outside the project authored or held
  anything. Nothing produced under this contract may be reported as independent human
  reproduction.

Nothing in this module reads, decrypts, lists or executes bank content, and nothing here may
produce a scientific bank: the payload schema this file names may never appear in a tracked file.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Mapping, Sequence


CONTRACT_VERSION = "mira-blind-bank-v1"

SPEC_SCHEMA = "mira-blind-bank-generator-spec-v1"
GENERATOR_SCHEMA = "mira-blind-bank-generator-v1"
PAYLOAD_SCHEMA = "mira-blind-bank-payload-v1"
DEVELOPMENT_PAYLOAD_SCHEMA = "mira-blind-bank-payload-development-v1"
COMMITMENT_SCHEMA = "mira-blind-bank-public-commitment-v1"
LEDGER_SCHEMA = "mira-blind-bank-generation-ledger-v1"
ISOLATION_SCHEMA = "mira-blind-bank-isolation-attestation-v1"
REVEAL_SCHEMA = "mira-blind-bank-reveal-authorization-v1"

REVEAL_SIGNATURE_NAMESPACE = "mira-blind-bank-reveal-v1"

# The ladder every claim under this contract must be placed on. Higher tiers are not implied by
# lower ones, and no tier below `human_maintained_sealed_bank` supports a hypothesis whose frozen
# protocol requires an independent human maintainer.
EVIDENCE_TIERS = (
    "project_authored_public_bank",
    "blind_generated_sealed_bank",
    "cross_generator_reproduced_sealed_bank",
    "human_maintained_sealed_bank",
    "independently_reproduced_human_maintained_sealed_bank",
)

PHASES = (
    "draft",
    "spec_frozen",
    "generated_sealed",
    "system_protocol_frozen",
    "reveal_authorized",
    "executed",
)

FEASIBILITY_CLASSES = ("feasible", "capability_absent")

# Evaluator kinds that are decided by inspecting terminal environment state. Anything requiring a
# reader's opinion, a rubric or another model is refused: a bank whose success depends on judgement
# cannot separate a refusal from a bad review of one.
PERMITTED_EVALUATOR_KINDS = (
    "terminal-file-content",
    "terminal-file-absence",
    "terminal-process-exit-status",
    "terminal-service-state",
    "terminal-stdout-exact-match",
)

# Tokens that must never appear anywhere in a payload. Their presence does not mean the bank is
# bad; it means the generator was not blind, which is a different and fatal problem.
CONTAMINATION_TOKENS = (
    "mira",
    "mjodheim",
    "genesis",
    "m074",
    "m075",
    "m085",
    "m086",
    "epistemic context",
    "refus",
    "self-evidence",
    "holdout",
    "hold-out",
    "gpt-5.6-sol",
    "codex",
    "metamorphosis",
    "lineage",
)

# Keys a payload may not carry at all. Each one would let the emitting process, or a later editor,
# record an expectation about how the system under test should behave on a task.
FORBIDDEN_TASK_KEYS = (
    "expected_agent_behavior",
    "expected_outcome",
    "should_refuse",
    "should_succeed",
    "difficulty_for_agent",
    "agent_hint",
    "tested_system",
    "solution",
    "answer",
)

# Words that turn a terminal predicate into an opinion.
SUBJECTIVE_PREDICATE_TOKENS = (
    "reasonable",
    "appropriate",
    "adequate",
    "high quality",
    "well written",
    "judge",
    "rubric",
    "llm",
    "grader model",
    "human review",
)

_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_OPAQUE_DOMAIN_RE = re.compile(r"\Aopaque-[0-9a-f]{16}\Z")
_IDENTIFIER_RE = re.compile(r"\A[a-z0-9][a-z0-9_-]{2,63}\Z")


class BlindBankError(ValueError):
    """Raised when a spec, payload, commitment or ledger weakens the sealed-bank contract."""


# --------------------------------------------------------------------------------------------
# canonical form
# --------------------------------------------------------------------------------------------


def canonical_bytes(value: Mapping[str, object] | Sequence[object]) -> bytes:
    """Return the one serialization every digest in this contract is taken over.

    Sorted keys, no insignificant whitespace, UTF-8, `\\n` never emitted because compact JSON
    contains no newline. M064 recorded a digest that matched only a CRLF working-tree copy; a
    single canonical form defined in one place is how that class of defect is kept out.
    """

    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def commitment_of(value: Mapping[str, object], *, omit: str) -> str:
    """Digest a document over every field except the one that will carry the digest."""

    body = {key: item for key, item in value.items() if key != omit}
    return sha256_hex(canonical_bytes(body))


def spec_commitment(spec: Mapping[str, object]) -> str:
    return commitment_of(spec, omit="spec_commitment_sha256")


def generator_commitment(generator: Mapping[str, object]) -> str:
    return sha256_hex(canonical_bytes(generator))


def opaque_domain_id(bank_nonce: str, domain_index: int) -> str:
    """Derive a content-free public identifier for a domain.

    Derived from a per-bank random nonce and the domain's position, never from its name. An
    identifier derived from the domain name would be a dictionary attack away from disclosing the
    bank's subject matter before reveal.
    """

    if not _SHA256_RE.match(bank_nonce):
        raise BlindBankError("bank nonce must be a sha256 hex string")
    if not isinstance(domain_index, int) or isinstance(domain_index, bool) or domain_index < 0:
        raise BlindBankError("domain index must be a non-negative integer")
    digest = hashlib.sha256(
        b"mira-blind-bank-domain-v1\0" + bank_nonce.encode("ascii")
        + b"\0" + str(domain_index).encode("ascii"),
    ).hexdigest()
    return f"opaque-{digest[:16]}"


# --------------------------------------------------------------------------------------------
# small shared predicates
# --------------------------------------------------------------------------------------------


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


def _is_identifier(value: object) -> bool:
    return isinstance(value, str) and bool(_IDENTIFIER_RE.match(value))


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _strings_in(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _strings_in(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings_in(item)


def _keys_in(value: object) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _keys_in(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _keys_in(item)


def _contract_identifiers() -> frozenset[str]:
    """Schema strings this contract writes into its own documents.

    They begin with the project prefix, so a naive scan would report every well-formed artifact as
    contaminated. They are exempted by exact match only: `mira-blind-bank-payload-v1` is skipped,
    while a task instruction that merely contains that substring is not.
    """

    return frozenset({
        SPEC_SCHEMA, GENERATOR_SCHEMA, PAYLOAD_SCHEMA, DEVELOPMENT_PAYLOAD_SCHEMA,
        COMMITMENT_SCHEMA, LEDGER_SCHEMA, ISOLATION_SCHEMA, REVEAL_SCHEMA,
        REVEAL_SIGNATURE_NAMESPACE, CONTRACT_VERSION,
        "sha256(mira-blind-bank-domain-v1||nonce||index)[:16]",
    })


def contamination_hits(value: object) -> list[str]:
    """Return the contamination tokens a document contains, in a normalized casefold."""

    exempt = _contract_identifiers()
    hits: set[str] = set()
    for text in _strings_in(value):
        if text in exempt:
            continue
        folded = unicodedata.normalize("NFKC", text).casefold()
        for token in CONTAMINATION_TOKENS:
            if token in folded:
                hits.add(token)
    return sorted(hits)


# --------------------------------------------------------------------------------------------
# generator descriptor
# --------------------------------------------------------------------------------------------


def validate_generator_descriptor(generator: Mapping[str, object]) -> None:
    """Validate a pinned generator identity without choosing one."""

    expected = {
        "descriptor_schema", "generator_id", "family", "weights_openness", "model_identifier",
        "checkpoint_revision", "weights_sha256", "weights_digest_available", "runtime",
        "checkpoint_published_on", "antecedence_reference_date", "antecedence_demonstrable",
        "context_blindness_enforced_by", "training_data_independence_proven",
    }
    if not isinstance(generator, Mapping) or set(generator) != expected:
        raise BlindBankError("generator descriptor fields differ from the closed schema")
    if generator.get("descriptor_schema") != GENERATOR_SCHEMA:
        raise BlindBankError("generator descriptor schema drifted")
    if not _is_identifier(generator.get("generator_id")) or not _is_identifier(
        generator.get("family")
    ):
        raise BlindBankError("generator identity is malformed")
    if generator.get("weights_openness") not in {"open-weight", "api-hosted"}:
        raise BlindBankError("generator weight openness is malformed")
    for field in ("model_identifier", "checkpoint_revision"):
        value = generator.get(field)
        if not isinstance(value, str) or not value.strip():
            raise BlindBankError(f"generator {field} is missing")
    # The single claim this contract may never make. A model cannot be shown to be ignorant of a
    # subject; it can only be shown not to have been told about it in this run.
    if generator.get("training_data_independence_proven") is not False:
        raise BlindBankError(
            "training-data independence may never be recorded as proven"
        )
    if generator.get("context_blindness_enforced_by") != "isolation-attestation":
        raise BlindBankError("context blindness must be enforced by a recorded attestation")
    digest_available = generator.get("weights_digest_available")
    weights_digest = generator.get("weights_sha256")
    if not isinstance(digest_available, bool):
        raise BlindBankError("weights digest availability must be a boolean")
    if digest_available and not _is_sha256(weights_digest):
        raise BlindBankError("a declared weights digest must be a sha256 hex string")
    if not digest_available and weights_digest is not None:
        raise BlindBankError("weights digest must be null when it is not available")
    if generator.get("weights_openness") == "api-hosted" and digest_available:
        raise BlindBankError("an api-hosted generator cannot carry a verifiable weights digest")
    runtime = generator.get("runtime")
    if not isinstance(runtime, Mapping) or set(runtime) != {
        "name", "version", "image_reference", "image_digest_sha256",
    }:
        raise BlindBankError("generator runtime fields differ from the closed schema")
    if not isinstance(runtime.get("name"), str) or not str(runtime.get("name")).strip():
        raise BlindBankError("generator runtime name is missing")
    if not isinstance(runtime.get("version"), str) or not str(runtime.get("version")).strip():
        raise BlindBankError("generator runtime version is missing")
    if not isinstance(runtime.get("image_reference"), str) or not str(
        runtime.get("image_reference")
    ).strip():
        raise BlindBankError("generator runtime image reference is missing")
    if not _is_sha256(runtime.get("image_digest_sha256")):
        raise BlindBankError("generator runtime image digest is malformed")
    antecedence = generator.get("antecedence_demonstrable")
    published = generator.get("checkpoint_published_on")
    reference = generator.get("antecedence_reference_date")
    if not isinstance(antecedence, bool):
        raise BlindBankError("antecedence demonstrability must be a boolean")
    if antecedence:
        if not _is_iso_date(published) or not _is_iso_date(reference):
            raise BlindBankError("demonstrable antecedence requires both dates")
        if str(published) >= str(reference):
            raise BlindBankError(
                "antecedence requires a checkpoint published strictly before the reference date"
            )
    elif published is not None and not _is_iso_date(published):
        raise BlindBankError("checkpoint publication date is malformed")


def _is_iso_date(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))


# --------------------------------------------------------------------------------------------
# generator spec
# --------------------------------------------------------------------------------------------


def validate_generator_spec(spec: Mapping[str, object]) -> None:
    """Validate everything that must be frozen before a bank exists."""

    expected = {
        "schema", "spec_id", "milestone", "status", "date_frozen", "evidence_tier", "prompt",
        "output_schema", "generator", "sampling", "normalization", "composition", "assembly",
        "structural_validation", "oracle", "failure_policy", "retry_policy", "isolation",
        "claim_boundary", "spec_commitment_sha256",
    }
    if not isinstance(spec, Mapping) or set(spec) != expected:
        raise BlindBankError("generator spec fields differ from the closed schema")
    if spec.get("schema") != SPEC_SCHEMA:
        raise BlindBankError("generator spec schema drifted")
    if spec.get("status") != "frozen_before_generation":
        raise BlindBankError("a generator spec is only valid frozen before generation")
    if not _is_identifier(spec.get("spec_id")):
        raise BlindBankError("generator spec identifier is malformed")
    if not isinstance(spec.get("milestone"), str) or not str(spec.get("milestone")).strip():
        raise BlindBankError("generator spec milestone is missing")
    if not _is_iso_date(spec.get("date_frozen")):
        raise BlindBankError("generator spec freeze date is malformed")
    if spec.get("evidence_tier") != "blind_generated_sealed_bank":
        raise BlindBankError("a blind generator spec claims exactly one evidence tier")
    if spec.get("spec_commitment_sha256") != spec_commitment(spec):
        raise BlindBankError("generator spec commitment drifted")

    _validate_prompt(spec.get("prompt"))
    _validate_output_schema(spec.get("output_schema"))
    validate_generator_descriptor(spec.get("generator"))  # type: ignore[arg-type]
    _validate_sampling(spec.get("sampling"))
    _validate_normalization(spec.get("normalization"))
    composition = _validate_composition(spec.get("composition"))
    _validate_assembly(spec.get("assembly"))
    _validate_structural_validation(spec.get("structural_validation"))
    _validate_oracle(spec.get("oracle"))
    _validate_failure_policy(spec.get("failure_policy"), composition)
    _validate_retry_policy(spec.get("retry_policy"))
    _validate_isolation_contract(spec.get("isolation"))
    _validate_claim_boundary(spec.get("claim_boundary"))


def _validate_prompt(prompt: object) -> None:
    expected = {
        "template_path", "template_sha256", "literal", "names_tested_system",
        "names_project_or_repository", "names_prior_results", "requests_a_desired_outcome",
        "describes_a_refusal_mechanism", "variables",
    }
    if not isinstance(prompt, Mapping) or set(prompt) != expected:
        raise BlindBankError("generator prompt fields differ from the closed schema")
    if not isinstance(prompt.get("template_path"), str) or not str(
        prompt.get("template_path")
    ).strip():
        raise BlindBankError("generator prompt path is missing")
    if not _is_sha256(prompt.get("template_sha256")):
        raise BlindBankError("generator prompt digest is malformed")
    # A literal prompt is the only kind whose digest means anything: with variables, the digest
    # covers the template and not the bytes the model actually received.
    if prompt.get("literal") is not True or prompt.get("variables") != []:
        raise BlindBankError("the frozen generator prompt must be literal and variable-free")
    for field in (
        "names_tested_system", "names_project_or_repository", "names_prior_results",
        "requests_a_desired_outcome", "describes_a_refusal_mechanism",
    ):
        if prompt.get(field) is not False:
            raise BlindBankError(f"a blind generator prompt must not satisfy {field}")


def _validate_output_schema(output_schema: object) -> None:
    if not isinstance(output_schema, Mapping) or set(output_schema) != {
        "payload_schema", "schema_path", "schema_sha256",
    }:
        raise BlindBankError("generator output schema fields differ from the closed schema")
    if output_schema.get("payload_schema") != PAYLOAD_SCHEMA:
        raise BlindBankError("generator output schema names the wrong payload schema")
    if not isinstance(output_schema.get("schema_path"), str) or not str(
        output_schema.get("schema_path")
    ).strip():
        raise BlindBankError("generator output schema path is missing")
    if not _is_sha256(output_schema.get("schema_sha256")):
        raise BlindBankError("generator output schema digest is malformed")


def _validate_sampling(sampling: object) -> None:
    expected = {
        "temperature", "top_p", "max_output_tokens", "seed", "seed_guaranteed_by_runtime",
        "decoding", "stop_sequences",
    }
    if not isinstance(sampling, Mapping) or set(sampling) != expected:
        raise BlindBankError("generator sampling fields differ from the closed schema")
    for field in ("temperature", "top_p"):
        value = sampling.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
            raise BlindBankError(f"generator sampling {field} is out of range")
    if not _is_positive_int(sampling.get("max_output_tokens")):
        raise BlindBankError("generator sampling token ceiling is malformed")
    if sampling.get("decoding") not in {"nucleus", "greedy"}:
        raise BlindBankError("generator decoding mode is malformed")
    guaranteed = sampling.get("seed_guaranteed_by_runtime")
    seed = sampling.get("seed")
    if not isinstance(guaranteed, bool):
        raise BlindBankError("seed guarantee must be a boolean")
    if guaranteed and not (isinstance(seed, int) and not isinstance(seed, bool) and seed >= 0):
        raise BlindBankError("a guaranteed seed must be a non-negative integer")
    if not guaranteed and seed is not None:
        raise BlindBankError(
            "a seed may only be recorded when the runtime guarantees it reproduces the sample"
        )
    stops = sampling.get("stop_sequences")
    if not isinstance(stops, list) or any(not isinstance(item, str) for item in stops):
        raise BlindBankError("generator stop sequences are malformed")


def _validate_normalization(normalization: object) -> None:
    if normalization != {
        "unicode_form": "NFC",
        "newline": "lf",
        "json_canonical_form": "sorted-compact-utf8",
        "strip_trailing_whitespace": True,
        "reject_non_utf8_output": True,
    }:
        raise BlindBankError("generator normalization rules drifted")


def _validate_composition(composition: object) -> Mapping[str, object]:
    if not isinstance(composition, Mapping) or set(composition) != {
        "domain_count", "pairs_per_domain", "task_count",
    }:
        raise BlindBankError("generator composition fields differ from the closed schema")
    domains = composition.get("domain_count")
    pairs = composition.get("pairs_per_domain")
    tasks = composition.get("task_count")
    if not _is_positive_int(domains) or not _is_positive_int(pairs):
        raise BlindBankError("generator composition counts are malformed")
    if tasks != int(domains) * int(pairs) * 2:  # type: ignore[arg-type]
        raise BlindBankError("generator composition task count does not reconcile")
    return composition


def _validate_assembly(assembly: object) -> None:
    if assembly != {
        "algorithm": "first-complete-domains-in-emission-order",
        "selection_depends_on_tested_system": False,
        "selection_depends_on_task_content_scoring": False,
        "reordering_permitted": False,
        "manual_curation_permitted": False,
        "opaque_domain_id_derivation": "sha256(mira-blind-bank-domain-v1||nonce||index)[:16]",
    }:
        raise BlindBankError("generator assembly rules drifted")


def _validate_structural_validation(rules: object) -> None:
    if rules != {
        "schema_conformance": True,
        "unique_task_ids": True,
        "unique_pair_ids": True,
        # The pair stores its goal, instruction, evaluator, terminal predicate, initial state,
        # permitted interfaces and required capabilities once, so the twins cannot disagree on
        # them. These three record that the representation itself carries the guarantee.
        "matched_pair_shares_one_goal_environment_and_evaluator": True,
        "matched_twins_derived_rather_than_authored": True,
        "matched_twin_delta_is_exactly_the_withheld_capability": True,
        "capability_absence_certificate_required": True,
        "absent_capability_required_by_the_shared_goal": True,
        "absent_capability_unreachable_through_any_permitted_interface": True,
        "feasible_twin_lacks_nothing_else": True,
        "terminal_evaluator_kind_allowlisted": True,
        "subjective_predicate_tokens_rejected": True,
        "forbidden_task_keys_rejected": True,
        "contamination_tokens_rejected": True,
        "tested_system_never_executed_during_validation": True,
    }:
        raise BlindBankError("structural validation rules drifted")


def _validate_oracle(oracle: object) -> None:
    if not isinstance(oracle, Mapping) or set(oracle) != {
        "enabled", "oracle_id", "distinct_from_tested_system", "distinct_from_generator",
        "may_select_among_tasks", "rejection_is_exclusion_not_reroll",
    }:
        raise BlindBankError("oracle fields differ from the closed schema")
    if not isinstance(oracle.get("enabled"), bool):
        raise BlindBankError("oracle enablement must be a boolean")
    if oracle.get("distinct_from_tested_system") is not True:
        raise BlindBankError("a class oracle may never be the system under test")
    if oracle.get("distinct_from_generator") is not True:
        raise BlindBankError("a class oracle may never be the generator that emitted the bank")
    if oracle.get("may_select_among_tasks") is not False:
        raise BlindBankError("a class oracle may confirm a class, never choose a task")
    if oracle.get("rejection_is_exclusion_not_reroll") is not True:
        raise BlindBankError("oracle rejection may never trigger a reroll")
    if oracle.get("enabled") and not _is_identifier(oracle.get("oracle_id")):
        raise BlindBankError("an enabled oracle must be identified")
    if not oracle.get("enabled") and oracle.get("oracle_id") is not None:
        raise BlindBankError("a disabled oracle must not be identified")


def _validate_failure_policy(policy: object, composition: Mapping[str, object]) -> None:
    if not isinstance(policy, Mapping) or set(policy) != {
        "minimum_domains", "minimum_pairs_per_domain",
        "structural_failure_supersedes_protocol", "partial_bank_permitted",
        "failed_materialization_is_preserved",
    }:
        raise BlindBankError("failure policy fields differ from the closed schema")
    if policy.get("partial_bank_permitted") is not False:
        raise BlindBankError("a partial bank may never be accepted")
    if policy.get("structural_failure_supersedes_protocol") is not True:
        raise BlindBankError("a structural failure must supersede the protocol, not retry it")
    if policy.get("failed_materialization_is_preserved") is not True:
        raise BlindBankError("a failed materialization must be preserved")
    if policy.get("minimum_domains") != composition.get("domain_count"):
        raise BlindBankError("failure policy domain minimum must equal the frozen domain count")
    if policy.get("minimum_pairs_per_domain") != composition.get("pairs_per_domain"):
        raise BlindBankError("failure policy pair minimum must equal the frozen pair count")


def _validate_retry_policy(policy: object) -> None:
    if policy != {
        "generation_attempts_permitted": 1,
        "reroll_permitted": False,
        "seed_change_permitted": False,
        "prompt_change_permitted": False,
        "generator_change_permitted": False,
        "second_experiment_requires_new_protocol_version": True,
    }:
        raise BlindBankError("generation retry policy drifted")


def _validate_isolation_contract(contract: object) -> None:
    if contract != {
        "runner": "container",
        "network": "none",
        "repository_mount_permitted": False,
        "secret_access_permitted": False,
        "code_forge_access_permitted": False,
        "environment_allowlisted": True,
        "single_hashed_input": True,
        "fresh_working_filesystem": True,
        "stdout_stderr_captured": True,
    }:
        raise BlindBankError("generator isolation contract drifted")


def _validate_claim_boundary(boundary: object) -> None:
    if boundary != {
        "procedural_independence_claimed": True,
        "generator_context_blindness_claimed": True,
        "training_data_independence_claimed": False,
        "human_independence_claimed": False,
        "external_reproduction_claimed": False,
        "substitutes_for_an_independent_human_maintainer": False,
        "agi": False,
        "genesis_gate_2": False,
        "genesis_gate_3": False,
    }:
        raise BlindBankError("blind-bank claim boundary drifted")



# --------------------------------------------------------------------------------------------
# payload structure
# --------------------------------------------------------------------------------------------
#
# A matched pair is stored as ONE object, not as two tasks that happen to share an identifier.
#
# The earlier draft kept two independent task objects and checked that they agreed. That can only
# ever be a check, and a check has to enumerate every field that must stay equal — miss one, and a
# pair whose instruction, initial state, evaluator or terminal predicate differs is still counted
# as evidence about an absent capability when it could equally have failed for the unrelated
# difference. External review caught exactly that gap.
#
# So the invariant half is stored once. The goal, the instruction, the evaluator, the terminal
# predicate, the initial state, the permitted interfaces and the required capabilities have a
# single copy and therefore cannot differ between twins. The only preregistered delta is whether
# the environment supplies `absent_capability.capability`, and it is derived by `materialize_twin`
# rather than written by the generator.
#
# What each twin carries of its own is its identifier and its emission provenance. Neither can
# affect whether the task can be completed.


def validate_bank_payload(
    payload: Mapping[str, object], *, spec: Mapping[str, object], development: bool = False,
) -> None:
    """Validate a materialized bank on properties that never consult the system under test.

    Every rule here is decidable from the payload and the frozen spec alone. Nothing in this
    function may run, import, call or measure the tested system: a validator that admitted tasks
    by watching how the agent handled them would be selecting a bank on the outcome it is meant
    to be evidence for.
    """

    required_schema = DEVELOPMENT_PAYLOAD_SCHEMA if development else PAYLOAD_SCHEMA
    expected = {"schema", "bank_id", "spec_commitment_sha256", "bank_nonce", "domains"}
    if development:
        expected = expected | {"status"}
    if not isinstance(payload, Mapping) or set(payload) != expected:
        raise BlindBankError("bank payload fields differ from the closed schema")
    if payload.get("schema") != required_schema:
        raise BlindBankError("bank payload schema drifted")
    if development and payload.get("status") != "DEVELOPMENT_FIXTURE_NOT_SCIENTIFIC":
        raise BlindBankError("a development payload must declare itself non-scientific")
    if not _is_identifier(payload.get("bank_id")):
        raise BlindBankError("bank identifier is malformed")
    if payload.get("spec_commitment_sha256") != spec.get("spec_commitment_sha256"):
        raise BlindBankError("bank payload does not bind the frozen generator spec")
    nonce = payload.get("bank_nonce")
    if not _is_sha256(nonce):
        raise BlindBankError("bank nonce is malformed")

    composition = spec["composition"]  # type: ignore[index]
    domain_count = int(composition["domain_count"])  # type: ignore[index]
    pairs_per_domain = int(composition["pairs_per_domain"])  # type: ignore[index]

    domains = payload.get("domains")
    if not isinstance(domains, list) or len(domains) != domain_count:
        raise BlindBankError("bank domain count does not match the frozen composition")

    for key in _keys_in(payload):
        if key in FORBIDDEN_TASK_KEYS:
            raise BlindBankError(f"bank payload carries forbidden key {key!r}")
    hits = contamination_hits(payload)
    if hits:
        raise BlindBankError(
            "bank payload mentions the tested system or this project: " + ", ".join(hits)
        )

    seen_task_ids: set[str] = set()
    seen_pair_ids: set[str] = set()
    seen_opaque: set[str] = set()
    for index, domain in enumerate(domains):
        _validate_domain(
            domain,
            domain_index=index,
            bank_nonce=str(nonce),
            pairs_per_domain=pairs_per_domain,
            seen_task_ids=seen_task_ids,
            seen_pair_ids=seen_pair_ids,
            seen_opaque=seen_opaque,
        )


def _validate_domain(
    domain: object, *, domain_index: int, bank_nonce: str, pairs_per_domain: int,
    seen_task_ids: set[str], seen_pair_ids: set[str], seen_opaque: set[str],
) -> None:
    if not isinstance(domain, Mapping) or set(domain) != {
        "domain_index", "opaque_domain_id", "pairs",
    }:
        raise BlindBankError("bank domain fields differ from the closed schema")
    if domain.get("domain_index") != domain_index:
        raise BlindBankError("bank domains are not in emission order")
    opaque = domain.get("opaque_domain_id")
    if not isinstance(opaque, str) or not _OPAQUE_DOMAIN_RE.match(opaque):
        raise BlindBankError("opaque domain identifier is malformed")
    if opaque != opaque_domain_id(bank_nonce, domain_index):
        raise BlindBankError("opaque domain identifier is not derived from the bank nonce")
    if opaque in seen_opaque:
        raise BlindBankError("opaque domain identifiers are not unique")
    seen_opaque.add(opaque)

    pairs = domain.get("pairs")
    if not isinstance(pairs, list) or len(pairs) != pairs_per_domain:
        raise BlindBankError("bank domain pair count does not match the frozen composition")
    for pair in pairs:
        _validate_pair(
            pair, opaque_domain=opaque, seen_task_ids=seen_task_ids,
            seen_pair_ids=seen_pair_ids,
        )


def _validate_pair(
    pair: object, *, opaque_domain: str, seen_task_ids: set[str], seen_pair_ids: set[str],
) -> None:
    """Validate one matched pair: one goal, one evaluation, one preregistered delta."""

    expected = {
        "pair_id", "opaque_domain_id", "instruction", "base_environment",
        "permitted_interfaces", "required_capabilities", "terminal_success_predicate",
        "absent_capability", "evaluator", "twins",
    }
    if not isinstance(pair, Mapping) or set(pair) != expected:
        raise BlindBankError("bank pair fields differ from the closed schema")
    pair_id = pair.get("pair_id")
    if not _is_identifier(pair_id):
        raise BlindBankError("bank pair identifier is malformed")
    if pair_id in seen_pair_ids:
        raise BlindBankError(f"bank pair identifier {pair_id!r} is not unique")
    seen_pair_ids.add(str(pair_id))
    if pair.get("opaque_domain_id") != opaque_domain:
        raise BlindBankError("bank pair is filed under the wrong domain")
    instruction = pair.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        raise BlindBankError("bank pair instruction is missing")

    environment = pair.get("base_environment")
    if not isinstance(environment, Mapping) or set(environment) != {
        "image_reference", "image_digest_sha256", "initial_state", "provides_capabilities",
        "network", "reproducible",
    }:
        raise BlindBankError("bank pair environment fields differ from the closed schema")
    if not _is_sha256(environment.get("image_digest_sha256")):
        raise BlindBankError("bank pair environment digest is malformed")
    if not isinstance(environment.get("image_reference"), str) or not str(
        environment.get("image_reference")
    ).strip():
        raise BlindBankError("bank pair environment image reference is missing")
    if environment.get("network") != "none":
        raise BlindBankError("bank task environments run without network access")
    if environment.get("reproducible") is not True:
        raise BlindBankError("bank task environments must be declared reproducible")
    if not isinstance(environment.get("initial_state"), Mapping):
        raise BlindBankError("bank pair initial state is malformed")

    provides = _capability_set(environment.get("provides_capabilities"), "provided capabilities")
    interfaces = _capability_set(pair.get("permitted_interfaces"), "permitted interfaces")
    required = _capability_set(pair.get("required_capabilities"), "required capabilities")
    if not required:
        raise BlindBankError("a bank pair must declare at least one required capability")

    predicate = pair.get("terminal_success_predicate")
    if not isinstance(predicate, Mapping) or set(predicate) != {"kind", "expression"}:
        raise BlindBankError("bank pair terminal predicate fields differ from the closed schema")
    if predicate.get("kind") not in PERMITTED_EVALUATOR_KINDS:
        raise BlindBankError("bank task terminal predicate kind is not allowlisted")
    if not isinstance(predicate.get("expression"), str) or not str(
        predicate.get("expression")
    ).strip():
        raise BlindBankError("bank pair terminal predicate expression is missing")
    _reject_subjective(predicate)

    evaluator = pair.get("evaluator")
    if not isinstance(evaluator, Mapping) or set(evaluator) != {
        "kind", "owner", "reads_agent_self_report", "spec",
    }:
        raise BlindBankError("bank pair evaluator fields differ from the closed schema")
    if evaluator.get("kind") not in PERMITTED_EVALUATOR_KINDS:
        raise BlindBankError("bank task evaluator kind is not allowlisted")
    if evaluator.get("owner") != "bank":
        raise BlindBankError("bank task evaluators are owned by the bank, not the runner")
    if evaluator.get("reads_agent_self_report") is not False:
        raise BlindBankError("a bank evaluator may never read the agent's own report")
    if not isinstance(evaluator.get("spec"), Mapping):
        raise BlindBankError("bank pair evaluator specification is malformed")
    _reject_subjective(evaluator)

    absent = pair.get("absent_capability")
    if not isinstance(absent, Mapping) or set(absent) != {"capability", "reason"}:
        raise BlindBankError("absent-capability certificate fields differ from the schema")
    capability = absent.get("capability")
    if not isinstance(capability, str) or not capability.strip():
        raise BlindBankError("absent-capability certificate names no capability")
    if not isinstance(absent.get("reason"), str) or not str(absent.get("reason")).strip():
        raise BlindBankError("absent-capability certificate carries no reason")

    # The three rules that make impossibility structural. The goal must genuinely need the
    # capability; the shared environment must withhold it, so the impossible twin lacks it; and
    # supplying it must be sufficient, so the feasible twin lacks nothing else. Together they
    # force the twins to differ by exactly one capability rather than merely record that they do.
    if capability not in required:
        raise BlindBankError(
            "an impossible task must require the capability its certificate declares absent"
        )
    if capability in provides:
        raise BlindBankError("the declared absent capability is present in the pair environment")
    if capability in interfaces:
        raise BlindBankError(
            "the declared absent capability is reachable through a permitted interface"
        )
    surplus = sorted(required - (provides | interfaces | {capability}))
    if surplus:
        raise BlindBankError(
            f"pair {pair_id!r} is unreachable for more than one reason: {surplus}"
        )

    twins = pair.get("twins")
    if not isinstance(twins, Mapping) or set(twins) != set(FEASIBILITY_CLASSES):
        raise BlindBankError("a pair carries exactly one feasible and one impossible twin")
    for _feasibility, twin in sorted(twins.items()):
        if not isinstance(twin, Mapping) or set(twin) != {"task_id", "provenance"}:
            raise BlindBankError("bank twin fields differ from the closed schema")
        task_id = twin.get("task_id")
        if not _is_identifier(task_id):
            raise BlindBankError("bank task identifier is malformed")
        if task_id in seen_task_ids:
            raise BlindBankError(f"bank task identifier {task_id!r} is not unique")
        seen_task_ids.add(str(task_id))
        provenance = twin.get("provenance")
        if not isinstance(provenance, Mapping) or set(provenance) != {
            "emitted_at_index", "raw_response_sha256",
        }:
            raise BlindBankError("bank twin provenance fields differ from the closed schema")
        if not isinstance(provenance.get("emitted_at_index"), int) or isinstance(
            provenance.get("emitted_at_index"), bool
        ) or int(provenance["emitted_at_index"]) < 0:
            raise BlindBankError("bank task emission index is malformed")
        if not _is_sha256(provenance.get("raw_response_sha256")):
            raise BlindBankError("bank task raw-response digest is malformed")

    # Derive both twins and state, rather than assume, that they differ in exactly the
    # preregistered way. With the shared fields stored once this cannot fail for a well-formed
    # pair, which is the point: the check is here so that a future change to the representation
    # that reintroduces a per-twin field is caught the moment it is made.
    assert_matched_pair_delta(pair)


def materialize_twin(
    pair: Mapping[str, object], feasibility_class: str,
) -> dict[str, object]:
    """Derive one runnable twin from a validated pair.

    This is the only sanctioned way to turn a pair into a task, and it is the whole causal
    argument in one function: every field is copied from the single shared source, and the sole
    difference between the two return values is whether `provides_capabilities` contains the
    certified-absent capability.
    """

    if feasibility_class not in FEASIBILITY_CLASSES:
        raise BlindBankError(f"unknown feasibility class {feasibility_class!r}")
    absent = pair["absent_capability"]
    assert isinstance(absent, Mapping)
    capability = str(absent["capability"])
    environment = dict(pair["base_environment"])  # type: ignore[arg-type]
    provided = list(environment["provides_capabilities"])
    if feasibility_class == "feasible":
        provided = sorted({*provided, capability})
    environment["provides_capabilities"] = provided
    twin = pair["twins"][feasibility_class]  # type: ignore[index]
    return {
        "task_id": twin["task_id"],
        "pair_id": pair["pair_id"],
        "opaque_domain_id": pair["opaque_domain_id"],
        "feasibility_class": feasibility_class,
        "instruction": pair["instruction"],
        "environment": environment,
        "permitted_interfaces": list(pair["permitted_interfaces"]),  # type: ignore[arg-type]
        "required_capabilities": list(pair["required_capabilities"]),  # type: ignore[arg-type]
        "terminal_success_predicate": dict(pair["terminal_success_predicate"]),  # type: ignore[arg-type]
        "absent_capability": None if feasibility_class == "feasible" else dict(absent),
        "evaluator": dict(pair["evaluator"]),  # type: ignore[arg-type]
        "provenance": dict(twin["provenance"]),
    }


# Fields of a materialized twin that must be byte-identical between the two classes. Anything not
# listed here is either the preregistered delta or an identifier with no causal role.
MATCHED_TWIN_INVARIANT_FIELDS = (
    "pair_id",
    "opaque_domain_id",
    "instruction",
    "permitted_interfaces",
    "required_capabilities",
    "terminal_success_predicate",
    "evaluator",
)

MATCHED_TWIN_PERMITTED_DELTA_FIELDS = (
    "task_id",
    "feasibility_class",
    "absent_capability",
    "provenance",
    "environment",
)


def matched_pair_delta(pair: Mapping[str, object]) -> dict[str, object]:
    """Return the difference between a pair's two materialized twins.

    Used by the validator and by the tests to state, rather than assume, that the twins differ in
    exactly the preregistered way. A pair whose twins diverge anywhere else is rejected before it
    can be counted as evidence about a capability.
    """

    feasible = materialize_twin(pair, "feasible")
    impossible = materialize_twin(pair, "capability_absent")
    feasible_environment = feasible["environment"]
    impossible_environment = impossible["environment"]
    assert isinstance(feasible_environment, Mapping)
    assert isinstance(impossible_environment, Mapping)
    return {
        "differing_task_fields": sorted(
            key for key in set(feasible) | set(impossible)
            if feasible.get(key) != impossible.get(key)
        ),
        "differing_environment_fields": sorted(
            key for key in set(feasible_environment) | set(impossible_environment)
            if feasible_environment.get(key) != impossible_environment.get(key)
        ),
        "capability_delta": sorted(
            set(feasible_environment["provides_capabilities"])
            - set(impossible_environment["provides_capabilities"])
        ),
        "reverse_capability_delta": sorted(
            set(impossible_environment["provides_capabilities"])
            - set(feasible_environment["provides_capabilities"])
        ),
    }


def assert_matched_pair_delta(pair: Mapping[str, object]) -> None:
    """Fail unless a pair's twins differ in exactly the preregistered way."""

    delta = matched_pair_delta(pair)
    absent = pair["absent_capability"]
    assert isinstance(absent, Mapping)
    capability = str(absent["capability"])
    unexpected = sorted(
        set(delta["differing_task_fields"]) - set(MATCHED_TWIN_PERMITTED_DELTA_FIELDS)
    )
    if unexpected:
        raise BlindBankError(
            f"matched twins differ outside the preregistered delta: {unexpected}"
        )
    if delta["differing_environment_fields"] != ["provides_capabilities"]:
        raise BlindBankError(
            "matched twins differ in the environment beyond the withheld capability: "
            f"{delta['differing_environment_fields']}"
        )
    if delta["capability_delta"] != [capability]:
        raise BlindBankError(
            f"the twins' capability delta is {delta['capability_delta']}, not [{capability!r}]"
        )
    if delta["reverse_capability_delta"]:
        raise BlindBankError(
            "the impossible twin provides capabilities its feasible counterpart does not: "
            f"{delta['reverse_capability_delta']}"
        )
    feasible = materialize_twin(pair, "feasible")
    impossible = materialize_twin(pair, "capability_absent")
    for field in MATCHED_TWIN_INVARIANT_FIELDS:
        if feasible[field] != impossible[field]:
            raise BlindBankError(f"matched twins disagree on the invariant field {field!r}")


def _capability_set(value: object, label: str) -> set[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise BlindBankError(f"bank task {label} are malformed")
    names = [str(item) for item in value]
    if len(set(names)) != len(names):
        raise BlindBankError(f"bank task {label} contain duplicates")
    return set(names)


def _reject_subjective(value: Mapping[str, object]) -> None:
    for text in _strings_in(value):
        folded = unicodedata.normalize("NFKC", text).casefold()
        for token in SUBJECTIVE_PREDICATE_TOKENS:
            if token in folded:
                raise BlindBankError(
                    f"terminal success may not depend on the subjective term {token!r}"
                )


# --------------------------------------------------------------------------------------------
# sealing, commitment and the generation ledger
# --------------------------------------------------------------------------------------------


def build_public_commitment(
    *,
    bank_id: str,
    milestone: str,
    spec_commitment_sha256: str,
    generator_commitment_sha256: str,
    payload_sha256: str,
    payload_bytes: int,
    ciphertext_sha256: str,
    cipher: str,
    key_custody: str,
    sealed_at: str,
    isolation_attestation_sha256: str,
    opaque_domain_ids: Sequence[str],
    domain_count: int,
    pairs_per_domain: int,
    task_count: int,
) -> dict[str, object]:
    """Assemble the only part of a sealed bank that may be published before reveal."""

    commitment: dict[str, object] = {
        "schema": COMMITMENT_SCHEMA,
        "status": "sealed_unrevealed",
        "milestone": milestone,
        "bank_id": bank_id,
        "evidence_tier": "blind_generated_sealed_bank",
        "spec_commitment_sha256": spec_commitment_sha256,
        "generator_commitment_sha256": generator_commitment_sha256,
        "isolation_attestation_sha256": isolation_attestation_sha256,
        "payload_sha256": payload_sha256,
        "payload_bytes": payload_bytes,
        "payload_canonical_form": "sorted-compact-utf8",
        "ciphertext_sha256": ciphertext_sha256,
        "cipher": cipher,
        "key_custody": key_custody,
        "sealed_at": sealed_at,
        "domain_count": domain_count,
        "pairs_per_domain": pairs_per_domain,
        "task_count": task_count,
        "opaque_domain_ids": list(opaque_domain_ids),
        "payload_present_in_repository": False,
        "revealed": False,
        "commitment_sha256": "",
    }
    commitment["commitment_sha256"] = commitment_of(commitment, omit="commitment_sha256")
    return commitment


def validate_public_commitment(
    commitment: Mapping[str, object], *, spec: Mapping[str, object] | None = None,
) -> None:
    """Validate a public commitment and confirm it discloses nothing but counts and digests."""

    expected = {
        "schema", "status", "milestone", "bank_id", "evidence_tier", "spec_commitment_sha256",
        "generator_commitment_sha256", "isolation_attestation_sha256", "payload_sha256",
        "payload_bytes", "payload_canonical_form", "ciphertext_sha256", "cipher", "key_custody",
        "sealed_at", "domain_count", "pairs_per_domain", "task_count", "opaque_domain_ids",
        "payload_present_in_repository", "revealed", "commitment_sha256",
    }
    if not isinstance(commitment, Mapping) or set(commitment) != expected:
        raise BlindBankError("public commitment fields differ from the closed schema")
    if commitment.get("schema") != COMMITMENT_SCHEMA:
        raise BlindBankError("public commitment schema drifted")
    if commitment.get("status") != "sealed_unrevealed":
        raise BlindBankError("a public commitment is only valid while the bank is sealed")
    if commitment.get("evidence_tier") != "blind_generated_sealed_bank":
        raise BlindBankError("public commitment evidence tier drifted")
    if commitment.get("payload_present_in_repository") is not False:
        raise BlindBankError("a sealed payload may never be present in this repository")
    if commitment.get("revealed") is not False:
        raise BlindBankError("a revealed bank is no longer a pre-reveal commitment")
    for field in (
        "spec_commitment_sha256", "generator_commitment_sha256", "isolation_attestation_sha256",
        "payload_sha256", "ciphertext_sha256",
    ):
        if not _is_sha256(commitment.get(field)):
            raise BlindBankError(f"public commitment {field} is malformed")
    if commitment.get("payload_canonical_form") != "sorted-compact-utf8":
        raise BlindBankError("public commitment canonical form drifted")
    if not _is_positive_int(commitment.get("payload_bytes")):
        raise BlindBankError("public commitment payload size is malformed")
    if not isinstance(commitment.get("cipher"), str) or not str(commitment.get("cipher")).strip():
        raise BlindBankError("public commitment cipher is missing")
    if commitment.get("key_custody") not in {"external-holder", "offline-project-holder"}:
        raise BlindBankError("public commitment key custody is malformed")
    if not _is_identifier(commitment.get("bank_id")):
        raise BlindBankError("public commitment bank identifier is malformed")
    if not _is_iso_date(str(commitment.get("sealed_at"))[:10]):
        raise BlindBankError("public commitment seal timestamp is malformed")
    domains = commitment.get("domain_count")
    pairs = commitment.get("pairs_per_domain")
    tasks = commitment.get("task_count")
    if not _is_positive_int(domains) or not _is_positive_int(pairs):
        raise BlindBankError("public commitment counts are malformed")
    if tasks != int(domains) * int(pairs) * 2:  # type: ignore[arg-type]
        raise BlindBankError("public commitment task count does not reconcile")
    opaque = commitment.get("opaque_domain_ids")
    if (
        not isinstance(opaque, list) or len(opaque) != domains
        or len(set(opaque)) != len(opaque)
        or any(not isinstance(item, str) or not _OPAQUE_DOMAIN_RE.match(item) for item in opaque)
    ):
        raise BlindBankError("public commitment opaque domain identifiers are malformed")
    if commitment.get("commitment_sha256") != commitment_of(
        commitment, omit="commitment_sha256"
    ):
        raise BlindBankError("public commitment digest drifted")
    hits = contamination_hits(
        {key: value for key, value in commitment.items() if key != "milestone"}
    )
    if hits:
        raise BlindBankError("public commitment leaks project context: " + ", ".join(hits))
    if spec is not None:
        if commitment.get("spec_commitment_sha256") != spec.get("spec_commitment_sha256"):
            raise BlindBankError("public commitment does not bind the frozen generator spec")
        composition = spec.get("composition")
        assert isinstance(composition, Mapping)
        if (
            commitment.get("domain_count") != composition.get("domain_count")
            or commitment.get("pairs_per_domain") != composition.get("pairs_per_domain")
            or commitment.get("task_count") != composition.get("task_count")
        ):
            raise BlindBankError("public commitment composition does not match the frozen spec")


LEDGER_OUTCOMES = ("materialized", "failed_structural_validation", "failed_isolation", "aborted")


def validate_generation_ledger(
    ledger: Mapping[str, object], *, spec_commitment_sha256: str | None = None,
) -> None:
    """Validate the append-only record of every materialization attempt.

    One frozen spec admits exactly one materialized bank. A second one is not an error to be
    corrected quietly; it is the retry this contract exists to make impossible to hide, so a
    ledger carrying two is rejected outright and every failed attempt must remain in it.

    When a frozen spec commitment is supplied, the ledger is treated as that milestone's own
    record: **every** entry must bind that commitment, and exactly one of them must be a
    materialization. External review found the earlier form accepted a ledger whose single
    materialization belonged to a different experiment, which then satisfied the generation stage
    for a spec it had nothing to do with. A single-spec ledger removes that class of mix-up
    entirely rather than filtering around it.
    """

    if not isinstance(ledger, Mapping) or set(ledger) != {"schema", "entries"}:
        raise BlindBankError("generation ledger fields differ from the closed schema")
    if ledger.get("schema") != LEDGER_SCHEMA:
        raise BlindBankError("generation ledger schema drifted")
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        raise BlindBankError("generation ledger entries are malformed")
    materialized: dict[str, int] = {}
    seen: set[tuple[str, int]] = set()
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != {
            "attempt_index", "spec_commitment_sha256", "started_at", "outcome",
            "payload_sha256", "isolation_attestation_sha256", "note",
        }:
            raise BlindBankError("generation ledger entry fields differ from the closed schema")
        attempt = entry.get("attempt_index")
        commitment = entry.get("spec_commitment_sha256")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            raise BlindBankError("generation ledger attempt index is malformed")
        if not _is_sha256(commitment):
            raise BlindBankError("generation ledger entry does not bind a frozen spec")
        key = (str(commitment), int(attempt))
        if key in seen:
            raise BlindBankError("generation ledger repeats an attempt index")
        seen.add(key)
        outcome = entry.get("outcome")
        if outcome not in LEDGER_OUTCOMES:
            raise BlindBankError("generation ledger outcome is malformed")
        if not _is_iso_date(str(entry.get("started_at"))[:10]):
            raise BlindBankError("generation ledger timestamp is malformed")
        if outcome == "materialized":
            if not _is_sha256(entry.get("payload_sha256")) or not _is_sha256(
                entry.get("isolation_attestation_sha256")
            ):
                raise BlindBankError("a materialized attempt must record both digests")
            materialized[str(commitment)] = materialized.get(str(commitment), 0) + 1
        elif entry.get("payload_sha256") is not None:
            raise BlindBankError("a non-materialized attempt may not record a payload digest")
        if not isinstance(entry.get("note"), str):
            raise BlindBankError("generation ledger note is malformed")
    for commitment, count in materialized.items():
        if count > 1:
            raise BlindBankError(
                f"spec {commitment[:12]} materialized {count} banks; one frozen spec admits one"
            )
    if spec_commitment_sha256 is None:
        return
    foreign = sorted({
        str(entry["spec_commitment_sha256"]) for entry in entries  # type: ignore[index]
        if entry["spec_commitment_sha256"] != spec_commitment_sha256  # type: ignore[index]
    })
    if foreign:
        raise BlindBankError(
            "generation ledger carries entries for another frozen spec: "
            + ", ".join(digest[:12] for digest in foreign)
        )
    count = materialized.get(spec_commitment_sha256, 0)
    if count != 1:
        raise BlindBankError(
            f"the frozen spec has materialized {count} banks; exactly one is required"
        )


# --------------------------------------------------------------------------------------------
# cross-artifact binding
# --------------------------------------------------------------------------------------------


def sealed_run_binding_problems(
    *,
    spec: Mapping[str, object],
    attestation: Mapping[str, object],
    commitment: Mapping[str, object],
    ledger: Mapping[str, object] | None = None,
) -> list[str]:
    """Return every reason the four sealed-stage artifacts do not describe one run.

    Validating each document on its own is not enough, and external review demonstrated why: an
    attestation from one generator run can be paired with a payload from another, the commitment
    made to name a third generator identity, and the ledger written to agree with whichever
    payload was chosen. Every document passes; the set describes nothing that happened.

    So each identity that must causally survive from the frozen spec, through the container run,
    into the sealed commitment and the ledger is compared here. Nothing is inferred: where two
    documents record the same fact, they must record it identically.
    """

    problems: list[str] = []
    generator = spec.get("generator")
    runtime = generator.get("runtime") if isinstance(generator, Mapping) else None

    # The payload the container emitted must be the payload that was sealed. Without this the
    # sealed bank need not be the one the isolated run produced at all.
    if attestation.get("output_sha256") != commitment.get("payload_sha256"):
        problems.append(
            "the attested generator output is not the payload recorded in the commitment"
        )
    if commitment.get("isolation_attestation_sha256") != attestation.get("attestation_sha256"):
        problems.append("bank commitment does not bind the isolation attestation")

    # The generator identity frozen before generation must be the identity the commitment claims.
    if isinstance(generator, Mapping):
        expected_generator = generator_commitment(generator)
        if commitment.get("generator_commitment_sha256") != expected_generator:
            problems.append(
                "bank commitment names a different generator from the frozen specification"
            )
    else:
        problems.append("the frozen specification carries no generator descriptor")

    # The image and runtime that actually ran must be the ones the spec pinned. A commitment can
    # name the right generator while the container ran a different image entirely.
    if isinstance(runtime, Mapping):
        for attested, declared, label in (
            ("image_digest_sha256", "image_digest_sha256", "image digest"),
            ("image_reference", "image_reference", "image reference"),
            ("runtime_name", "name", "runtime name"),
            ("runtime_version", "version", "runtime version"),
        ):
            if attestation.get(attested) != runtime.get(declared):
                problems.append(
                    f"the attested generator {label} differs from the frozen specification"
                )
    else:
        problems.append("the frozen specification carries no generator runtime")

    if commitment.get("spec_commitment_sha256") != spec.get("spec_commitment_sha256"):
        problems.append("bank commitment does not bind the frozen generator spec")

    if ledger is None:
        return problems
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        problems.append("generation ledger entries are malformed")
        return problems
    materialized = [
        entry for entry in entries
        if isinstance(entry, Mapping) and entry.get("outcome") == "materialized"
    ]
    if len(materialized) != 1:
        problems.append(
            f"generation ledger records {len(materialized)} materialized banks; "
            "exactly one is permitted"
        )
        return problems
    entry = materialized[0]
    if entry.get("spec_commitment_sha256") != spec.get("spec_commitment_sha256"):
        problems.append("the materialized ledger entry belongs to a different frozen spec")
    if entry.get("payload_sha256") != commitment.get("payload_sha256"):
        problems.append("the ledger and the commitment disagree on the sealed payload")
    if entry.get("isolation_attestation_sha256") != attestation.get("attestation_sha256"):
        problems.append("the ledger and the commitment disagree on the isolation attestation")
    return problems


# --------------------------------------------------------------------------------------------
# reveal authorization
# --------------------------------------------------------------------------------------------


def validate_reveal_authorization(
    authorization: Mapping[str, object], *, commitment: Mapping[str, object],
    protocol_commitment_sha256: str, signature_verified: bool,
) -> None:
    """Validate an explicit, signed, single-use authorization to open a sealed bank."""

    expected = {
        "schema", "milestone", "bank_id", "bank_commitment_sha256",
        "system_protocol_commitment_sha256", "authorized_by", "authorized_at",
        "signature_namespace", "authorizer_public_key_sha256", "single_execution_only",
        "result_preserved_regardless_of_outcome",
    }
    if not isinstance(authorization, Mapping) or set(authorization) != expected:
        raise BlindBankError("reveal authorization fields differ from the closed schema")
    if authorization.get("schema") != REVEAL_SCHEMA:
        raise BlindBankError("reveal authorization schema drifted")
    if authorization.get("signature_namespace") != REVEAL_SIGNATURE_NAMESPACE:
        raise BlindBankError("reveal authorization signature namespace drifted")
    if authorization.get("bank_id") != commitment.get("bank_id"):
        raise BlindBankError("reveal authorization bank identity drifted")
    if authorization.get("bank_commitment_sha256") != commitment.get("commitment_sha256"):
        raise BlindBankError("reveal authorization does not bind the sealed bank commitment")
    if authorization.get("system_protocol_commitment_sha256") != protocol_commitment_sha256:
        raise BlindBankError("reveal authorization does not bind the frozen system protocol")
    if authorization.get("single_execution_only") is not True:
        raise BlindBankError("a reveal authorizes exactly one execution")
    if authorization.get("result_preserved_regardless_of_outcome") is not True:
        raise BlindBankError("a reveal requires the result to be preserved whatever it says")
    if not isinstance(authorization.get("authorized_by"), str) or not str(
        authorization.get("authorized_by")
    ).strip():
        raise BlindBankError("reveal authorization names no authorizer")
    if not _is_iso_date(str(authorization.get("authorized_at"))[:10]):
        raise BlindBankError("reveal authorization timestamp is malformed")
    if not _is_sha256(authorization.get("authorizer_public_key_sha256")):
        raise BlindBankError("reveal authorization key digest is malformed")
    if signature_verified is not True:
        # A reveal is the one irreversible step in this contract. It is gated on a human
        # signature rather than on a file's presence, so that no automated process can open a
        # sealed bank by writing JSON.
        raise BlindBankError("reveal authorization signature is not verified")


__all__ = [
    "CONTAMINATION_TOKENS", "COMMITMENT_SCHEMA", "CONTRACT_VERSION",
    "DEVELOPMENT_PAYLOAD_SCHEMA", "EVIDENCE_TIERS", "FEASIBILITY_CLASSES",
    "FORBIDDEN_TASK_KEYS", "GENERATOR_SCHEMA", "ISOLATION_SCHEMA", "LEDGER_OUTCOMES",
    "LEDGER_SCHEMA", "MATCHED_TWIN_INVARIANT_FIELDS", "MATCHED_TWIN_PERMITTED_DELTA_FIELDS",
    "PAYLOAD_SCHEMA", "PERMITTED_EVALUATOR_KINDS", "PHASES",
    "REVEAL_SCHEMA", "REVEAL_SIGNATURE_NAMESPACE", "SPEC_SCHEMA",
    "SUBJECTIVE_PREDICATE_TOKENS", "BlindBankError", "assert_matched_pair_delta",
    "build_public_commitment",
    "canonical_bytes", "commitment_of", "contamination_hits", "generator_commitment",
    "matched_pair_delta", "materialize_twin", "sealed_run_binding_problems",
    "opaque_domain_id", "sha256_hex", "spec_commitment", "validate_bank_payload",
    "validate_generation_ledger", "validate_generator_descriptor", "validate_generator_spec",
    "validate_public_commitment", "validate_reveal_authorization",
]
