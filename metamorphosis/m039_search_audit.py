"""Independent exhaustive audit of M039's deterministic proposal search.

The operational engine records counters and causally journals evidence-admitted candidates.
For full replay, counters are not enough: two different rejected search histories can have
the same totals.  This module independently enumerates every symbolic expansion and every
completed body up to the adopted candidate, recording success, evidence rejection, exact
evaluation and ordering in one canonical transcript digest.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Mapping, Sequence

from .m012b_dfa import DFA, exact_equivalence
from .m038_journal import encode
from .m039_engine import Candidate, M039Task, _candidate_id, _tool_atoms, dfa_digest
from .m039_lineage import CycleManifest, LineageTool
from .structural import Atom, apply_atom, normalize_dfa

SEARCH_AUDIT_SCHEMA = "m039-search-audit/1"
SEARCH_TRANSCRIPT_DOMAIN = b"m039-complete-search-transcript-v1"
RAW_BODY_DOMAIN = b"m039-raw-search-body-v1"


class M039SearchAuditError(ValueError):
    pass


def _raw_body_digest(body: DFA) -> str:
    return hashlib.sha256(RAW_BODY_DOMAIN + encode(body.to_dict())).hexdigest()


@dataclass(frozen=True)
class SearchAudit:
    cycle: int
    maximum_depth: int
    registry_tool_ids: tuple[str, ...]
    symbolic_search_nodes: int
    primitive_expansion_operations: int
    completed_candidates: int
    evidence_rejections: int
    evidence_admitted_candidates: int
    exact_evaluations: int
    accepted_candidate_id: str
    transcript_digest: str
    transcript_entries: int
    schema: str = SEARCH_AUDIT_SCHEMA

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "cycle": self.cycle,
            "maximum_depth": self.maximum_depth,
            "registry_tool_ids": list(self.registry_tool_ids),
            "symbolic_search_nodes": self.symbolic_search_nodes,
            "primitive_expansion_operations": self.primitive_expansion_operations,
            "completed_candidates": self.completed_candidates,
            "evidence_rejections": self.evidence_rejections,
            "evidence_admitted_candidates": self.evidence_admitted_candidates,
            "exact_evaluations": self.exact_evaluations,
            "accepted_candidate_id": self.accepted_candidate_id,
            "transcript_digest": self.transcript_digest,
            "transcript_entries": self.transcript_entries,
        }


def audit_search(
    *,
    cycle: int,
    founder: DFA,
    target: DFA,
    registry: Sequence[LineageTool],
    maximum_depth: int,
    expected_accepted_candidate_id: str,
    observation_words: Sequence[tuple[int, ...]],
) -> SearchAudit:
    """Re-enumerate the whole ordered search prefix ending at the adopted candidate."""

    if maximum_depth < 1:
        raise ValueError("maximum depth must be positive")
    evidence = {word: target.accepts(word) for word in observation_words}
    ordered_evidence = tuple(sorted(evidence.items()))
    transcript: list[Mapping[str, object]] = []
    symbolic_nodes = 0
    primitive_operations = 0
    completed = 0
    evidence_rejections = 0
    evidence_admitted = 0
    exact_evaluations = 0
    accepted: str | None = None

    def descend(
        current: DFA,
        indices: tuple[int, ...],
        selected_tools: tuple[LineageTool, ...],
        expanded: tuple[Atom, ...],
        remaining: int,
        requested_depth: int,
    ) -> bool:
        nonlocal symbolic_nodes
        nonlocal primitive_operations
        nonlocal completed
        nonlocal evidence_rejections
        nonlocal evidence_admitted
        nonlocal exact_evaluations
        nonlocal accepted

        if remaining == 0:
            completed += 1
            normalized = normalize_dfa(current)
            candidate_id = _candidate_id(cycle, indices, selected_tools, normalized)
            mismatch_word: tuple[int, ...] | None = None
            mismatch_expected: bool | None = None
            mismatch_actual: bool | None = None
            for word, expected in ordered_evidence:
                actual = normalized.accepts(word)
                if actual != expected:
                    mismatch_word = word
                    mismatch_expected = expected
                    mismatch_actual = actual
                    break
            evidence_match = mismatch_word is None
            transcript.append(
                {
                    "kind": "completed_candidate",
                    "cycle": cycle,
                    "requested_depth": requested_depth,
                    "tool_indices": list(indices),
                    "tool_ids": [tool.tool_id for tool in selected_tools],
                    "expanded_program": [atom.to_list() for atom in expanded],
                    "candidate_id": candidate_id,
                    "normalized_body_digest": dfa_digest(normalized),
                    "evidence_match": evidence_match,
                    "first_mismatch_word": list(mismatch_word) if mismatch_word is not None else None,
                    "first_mismatch_expected": mismatch_expected,
                    "first_mismatch_actual": mismatch_actual,
                }
            )
            if not evidence_match:
                evidence_rejections += 1
                return False

            evidence_admitted += 1
            exact_evaluations += 1
            exact, separating_word = exact_equivalence(normalized, target)
            transcript.append(
                {
                    "kind": "exact_evaluation",
                    "cycle": cycle,
                    "candidate_id": candidate_id,
                    "exact": exact,
                    "separating_word": list(separating_word) if separating_word is not None else None,
                }
            )
            if exact:
                accepted = candidate_id
                return True
            return False

        for index, tool in enumerate(registry):
            symbolic_nodes += 1
            body: DFA | None = current
            atoms = _tool_atoms(tool)
            applied = 0
            for atom in atoms:
                primitive_operations += 1
                applied += 1
                body = apply_atom(body, atom)  # type: ignore[arg-type]
                if body is None:
                    break
            transcript.append(
                {
                    "kind": "symbolic_expansion",
                    "cycle": cycle,
                    "requested_depth": requested_depth,
                    "remaining_before": remaining,
                    "prefix_tool_indices": list(indices),
                    "selected_tool_index": index,
                    "selected_tool_id": tool.tool_id,
                    "primitive_operations_applied": applied,
                    "success": body is not None,
                    "raw_result_digest": _raw_body_digest(body) if body is not None else None,
                }
            )
            if body is None:
                continue
            if descend(
                body,
                indices + (index,),
                selected_tools + (tool,),
                expanded + atoms,
                remaining - 1,
                requested_depth,
            ):
                return True
        return False

    for depth in range(1, maximum_depth + 1):
        if descend(founder, (), (), (), depth, depth):
            break

    if accepted is None:
        raise M039SearchAuditError("independent search audit found no exact candidate")
    if accepted != expected_accepted_candidate_id:
        raise M039SearchAuditError(
            "independent search audit adopted a different candidate: "
            f"{accepted} != {expected_accepted_candidate_id}"
        )
    digest = hashlib.sha256(
        SEARCH_TRANSCRIPT_DOMAIN + encode(transcript)
    ).hexdigest()
    return SearchAudit(
        cycle=cycle,
        maximum_depth=maximum_depth,
        registry_tool_ids=tuple(tool.tool_id for tool in registry),
        symbolic_search_nodes=symbolic_nodes,
        primitive_expansion_operations=primitive_operations,
        completed_candidates=completed,
        evidence_rejections=evidence_rejections,
        evidence_admitted_candidates=evidence_admitted,
        exact_evaluations=exact_evaluations,
        accepted_candidate_id=accepted,
        transcript_digest=digest,
        transcript_entries=len(transcript),
    )


def verify_cycle_search_audit(
    audit: SearchAudit,
    cycle: CycleManifest,
) -> None:
    """Bind the independent transcript back to the engine's committed counters."""

    expected = cycle.functional_counters
    comparisons = {
        "symbolic_search_nodes": audit.symbolic_search_nodes,
        "primitive_expansion_operations": audit.primitive_expansion_operations,
        "candidates_constructed": audit.completed_candidates,
    }
    for field, actual in comparisons.items():
        if expected.get(field) != actual:
            raise M039SearchAuditError(
                f"search audit {field}={actual}, engine committed {expected.get(field)}"
            )
    if cycle.accepted_candidate_id != audit.accepted_candidate_id:
        raise M039SearchAuditError("search audit accepted candidate differs from the manifest")


def audit_result_searches(
    *,
    tasks: Sequence[M039Task],
    cycles: Sequence[CycleManifest],
    final_registry: Sequence[LineageTool],
    cycle_one_depth: int,
    later_depth: int,
    observation_words: Sequence[tuple[int, ...]],
) -> tuple[SearchAudit, ...]:
    if len(tasks) != 3 or len(cycles) != 3:
        raise M039SearchAuditError("M039 search audit requires exactly three cycles")
    audits: list[SearchAudit] = []
    for task, cycle in zip(tasks, cycles):
        available = tuple(
            tool for tool in final_registry if tool.introduced_cycle < task.cycle
        )
        maximum_depth = cycle_one_depth if task.cycle == 1 else later_depth
        audit = audit_search(
            cycle=task.cycle,
            founder=task.founder,
            target=task.target,
            registry=available,
            maximum_depth=maximum_depth,
            expected_accepted_candidate_id=cycle.accepted_candidate_id,
            observation_words=observation_words,
        )
        verify_cycle_search_audit(audit, cycle)
        audits.append(audit)
    return tuple(audits)
