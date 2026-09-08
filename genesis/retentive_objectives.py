"""Retention-preserving wrapper around objective-scoped policy evolution.

Per-cycle retention is not enough for continued evolution. The trust root correctly refuses a
candidate that forgets tasks its parent solved *in the current comparison*, but a later driver could
present a disjoint task family and thereby remove old work from the comparison entirely. A lineage
would then be able to improve on the new objective while forgetting capabilities acquired earlier.

This module persists a content-addressed multiset of question digests for the most recent successfully
adopted objective. Before any later policy search or machinery expansion, the new objective must
contain that multiset with multiplicity. Task labels do not matter; question/target contents do.
Because later objectives are measured on a superset of the retained corpus, the ordinary trust-root
retention rule now mechanically covers earlier solved work as well as new work.

The corpus stores hashes, not task plaintext. It is tied to the objective/evaluation contract and to
the acquisition verdict that caused it to become the retained frontier, and it survives process
death as lineage state.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from genesis import objective_policy_controller as opc
from genesis import policy_controller
from genesis import state as lineage_state
from genesis.loop import evaluation_snapshot, question_digest
from genesis.trust_root import digest_of, provenance

RETENTION_SCHEMA = "genesis-retention-corpus-v1"
RETENTION_TOOL_NAME = "retained_objective_corpus"
RETENTION_ROLE = "cross_objective_retention"


class RetentionObjectiveError(RuntimeError):
    """Raised when a new objective would remove previously retained evaluated work."""


def _question_multiset(tasks: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    snapshot = evaluation_snapshot(tasks)
    return tuple(sorted(question_digest(task) for task in snapshot))


def _tool(genesis) -> Mapping[str, Any] | None:
    matches = [
        tool
        for tool in genesis.state.get("tools", [])
        if tool.get("name") == RETENTION_TOOL_NAME and tool.get("role") == RETENTION_ROLE
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise RetentionObjectiveError("lineage carries more than one retention corpus")
    return matches[0]


def bound_corpus(genesis) -> dict[str, Any] | None:
    """Validate and return the persisted cross-objective retention frontier."""
    tool = _tool(genesis)
    if tool is None:
        return None
    record = tool.get("artifact")
    if not isinstance(record, Mapping) or record.get("schema") != RETENTION_SCHEMA:
        raise RetentionObjectiveError("retention tool carries no recognised corpus artifact")
    objective = opc.validate_objective(record.get("objective") or {})
    if objective["evaluation_contract_digest"] != genesis.evaluation_contract["contract_digest"]:
        raise RetentionObjectiveError(
            "retention corpus was established under a different evaluation contract"
        )
    questions = record.get("question_digests")
    if not isinstance(questions, list) or any(not isinstance(value, str) or not value for value in questions):
        raise RetentionObjectiveError("retention corpus carries malformed question identities")
    canonical_questions = sorted(questions)
    if canonical_questions != questions:
        raise RetentionObjectiveError("retention corpus question identities are not canonical")
    if objective["task_set_digest"] != digest_of(canonical_questions):
        raise RetentionObjectiveError(
            "retention corpus question multiset does not reproduce its objective task-set digest"
        )
    source_name = str(record.get("source_candidate") or "")
    source_verdict = str(record.get("source_verdict_digest") or "")
    if not source_name or not source_verdict:
        raise RetentionObjectiveError("retention corpus names no acquisition verdict")
    if not any(
        item.get("name") == source_name and item.get("verdict_digest") == source_verdict
        for item in genesis.state.get("acquisitions", [])
    ):
        raise RetentionObjectiveError(
            "retention corpus does not point to an acquisition the lineage actually carries"
        )
    payload = {
        "schema": RETENTION_SCHEMA,
        "objective": objective,
        "question_digests": canonical_questions,
        "source_candidate": source_name,
        "source_verdict_digest": source_verdict,
        "generation": int(record.get("generation", -1)),
    }
    if record.get("corpus_digest") != digest_of(payload):
        raise RetentionObjectiveError("retention corpus does not reproduce its own digest")
    return {**payload, "corpus_digest": record["corpus_digest"]}


def assert_retains_prior_work(genesis, here) -> None:
    """Refuse a new objective that omits any retained question/target, including duplicates."""
    retained = bound_corpus(genesis)
    if retained is None:
        return
    available = Counter(_question_multiset(here.tasks))
    required = Counter(retained["question_digests"])
    missing = required - available
    if missing:
        raise RetentionObjectiveError(
            "new objective removes %d retained evaluated question occurrence(s); later evolution "
            "must include prior work so the trust root can measure forgetting"
            % sum(missing.values())
        )


def _install_corpus(genesis, here, candidate_name: str) -> dict[str, Any]:
    acquisition = next(
        (
            item
            for item in reversed(genesis.state.get("acquisitions", []))
            if item.get("name") == candidate_name
        ),
        None,
    )
    if not isinstance(acquisition, Mapping):
        raise RetentionObjectiveError(
            "an accepted policy-generated body has no matching lineage acquisition record"
        )
    verdict = str(acquisition.get("verdict_digest") or "")
    if not verdict:
        raise RetentionObjectiveError("accepted acquisition names no verdict")
    objective = opc.objective_record(genesis, here)
    payload = {
        "schema": RETENTION_SCHEMA,
        "objective": objective,
        "question_digests": list(_question_multiset(here.tasks)),
        "source_candidate": candidate_name,
        "source_verdict_digest": verdict,
        "generation": int(genesis.state["generation"]),
    }
    corpus = {**payload, "corpus_digest": digest_of(payload)}
    tools = []
    replaced = False
    for tool in genesis.state.get("tools", []):
        if tool.get("name") == RETENTION_TOOL_NAME and tool.get("role") == RETENTION_ROLE:
            if replaced:
                raise RetentionObjectiveError("lineage carries duplicate retention corpus tools")
            tools.append(
                {
                    "name": RETENTION_TOOL_NAME,
                    "role": RETENTION_ROLE,
                    "artifact": corpus,
                    "provenance": provenance(
                        "lineage_owned",
                        produced_by="retentive objective controller",
                        detail=verdict,
                    ),
                }
            )
            replaced = True
        else:
            tools.append(tool)
    if not replaced:
        tools.append(
            {
                "name": RETENTION_TOOL_NAME,
                "role": RETENTION_ROLE,
                "artifact": corpus,
                "provenance": provenance(
                    "lineage_owned",
                    produced_by="retentive objective controller",
                    detail=verdict,
                ),
            }
        )

    observation = {
        "kind": "retention_corpus_advanced",
        "objective_digest": objective["objective_digest"],
        "corpus_digest": corpus["corpus_digest"],
        "source_candidate": candidate_name,
        "source_verdict_digest": verdict,
        "question_count": len(corpus["question_digests"]),
    }
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=tools,
        acquisitions=genesis.state["acquisitions"],
        observations=genesis.state["observations"] + [observation],
        generation=genesis.state["generation"],
    )
    genesis.journal.append(
        "observation",
        genesis.state["generation"],
        {
            "arm": "cross_objective_retention",
            **observation,
            "new_state_digest": genesis.state["state_digest"],
        },
    )
    return corpus


def run_policy(
    genesis,
    here,
    *,
    seed_policy: Mapping[str, Any] | None = None,
    max_steps: int = 32,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Run objective-scoped policy evolution while making old evaluated work non-optional."""
    assert_retains_prior_work(genesis, here)
    record = opc.run_policy(
        genesis,
        here,
        seed_policy=seed_policy,
        max_steps=max_steps,
        checkpoint_directory=checkpoint_directory,
    )
    accepted = [step for step in record["steps"] if step.get("accepted")]
    if len(accepted) > 1:
        raise RetentionObjectiveError("one policy run adopted more than one body")
    if accepted:
        corpus = _install_corpus(genesis, here, str(accepted[0]["name"]))
        record["retention_corpus"] = corpus
        if checkpoint_directory is not None:
            record["retention_checkpoint_digest"] = genesis.persist(
                Path(checkpoint_directory)
            )["checkpoint"]
    else:
        record["retention_corpus"] = bound_corpus(genesis)
        record["retention_checkpoint_digest"] = ""
    record["final_state_digest"] = genesis.state["state_digest"]
    record["run_digest"] = digest_of({k: v for k, v in record.items() if k != "run_digest"})
    return record


def expand_policy(genesis, here, *, checkpoint_directory: Path | None = None) -> dict[str, Any]:
    """A machinery update may not make previously retained work disappear from its objective."""
    assert_retains_prior_work(genesis, here)
    return opc.expand_policy(
        genesis,
        here,
        checkpoint_directory=checkpoint_directory,
    )


def exhausted(genesis, here, policy: Mapping[str, Any] | None = None) -> bool:
    assert_retains_prior_work(genesis, here)
    return opc.exhausted(genesis, here, policy)
