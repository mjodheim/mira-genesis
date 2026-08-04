"""Independent exhaustive audit of M040 post-migration proposal search."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Mapping, Sequence

from .m012b_dfa import DFA, exact_equivalence
from .m038_journal import encode
from .m039_lineage import LineageTool, ORIGIN_LINEAGE_CONSTRUCTED
from .structural import Atom, apply_atom, normalize_dfa

AUDIT_SCHEMA = "m040-post-search-audit/1"
TRANSCRIPT_DOMAIN = b"m040-post-search-transcript-v1"
RAW_BODY_DOMAIN = b"m040-post-search-raw-body-v1"


class M040SearchAuditError(ValueError):
    pass


def _raw_body_digest(body: DFA) -> str:
    return hashlib.sha256(RAW_BODY_DOMAIN + encode(body.to_dict())).hexdigest()


@dataclass(frozen=True)
class M040SearchAudit:
    arm: str
    registry_tool_ids: tuple[str, ...]
    preferred_programs: tuple[tuple[str, ...], ...]
    maximum_depth: int
    node_budget: int
    exact: bool
    reason: str
    quality_numerator: int
    quality_denominator: int
    symbolic_search_nodes: int
    primitive_expansion_operations: int
    candidates_constructed: int
    candidates_evaluated: int
    evidence_checks: int
    tool_symbols_used: int
    accepted_candidate_id: str | None
    accepted_tool_ids: tuple[str, ...]
    transcript_digest: str
    transcript_entries: int
    schema: str = AUDIT_SCHEMA

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "arm": self.arm,
            "registry_tool_ids": list(self.registry_tool_ids),
            "preferred_programs": [list(program) for program in self.preferred_programs],
            "maximum_depth": self.maximum_depth,
            "node_budget": self.node_budget,
            "exact": self.exact,
            "reason": self.reason,
            "quality_numerator": self.quality_numerator,
            "quality_denominator": self.quality_denominator,
            "symbolic_search_nodes": self.symbolic_search_nodes,
            "primitive_expansion_operations": self.primitive_expansion_operations,
            "candidates_constructed": self.candidates_constructed,
            "candidates_evaluated": self.candidates_evaluated,
            "evidence_checks": self.evidence_checks,
            "tool_symbols_used": self.tool_symbols_used,
            "accepted_candidate_id": self.accepted_candidate_id,
            "accepted_tool_ids": list(self.accepted_tool_ids),
            "transcript_digest": self.transcript_digest,
            "transcript_entries": self.transcript_entries,
        }


def audit_post_search(
    *,
    arm: str,
    founder: DFA | None,
    output_quality_body: DFA | None,
    target: DFA,
    observations: Mapping[tuple[int, ...], bool],
    registry: Sequence[LineageTool],
    preferred_tool_ids: Sequence[str],
    preferred_programs: Sequence[Sequence[str]],
    maximum_depth: int,
    node_budget: int,
    expected_result: object,
) -> M040SearchAudit:
    """Re-enumerate every post-migration expansion and compare with the engine result."""

    # Local import avoids a module-initialisation cycle while retaining separately written
    # enumeration logic in this verifier.
    from .m040_engine import _candidate_id, _quality, _registry_by_memory, _tool_atoms, dfa_digest

    expected_mapping = expected_result.mapping()
    transcript: list[Mapping[str, object]] = []
    ordered_observations = tuple(sorted(observations.items()))
    symbolic_nodes = 0
    primitive_operations = 0
    candidates_constructed = 0
    candidates_evaluated = 0
    evidence_checks = 0
    tool_symbols_used = 0
    best_quality = 0
    accepted_candidate_id: str | None = None
    accepted_tool_ids: tuple[str, ...] = ()
    exact = False
    reason = "no_exact_candidate_within_committed_language"

    if founder is None:
        quality = 0 if output_quality_body is None else _quality(output_quality_body, observations)
        transcript.append(
            {
                "kind": "no_portable_rewrite_state",
                "arm": arm,
                "output_body_digest": (
                    None if output_quality_body is None else dfa_digest(output_quality_body)
                ),
                "quality": quality,
                "observations": len(observations),
            }
        )
        best_quality = quality
        reason = "output_only_has_no_portable_rewrite_state"
    else:
        ordered_registry = _registry_by_memory(registry, preferred_tool_ids)
        registry_by_id = {tool.tool_id: tool for tool in registry}
        best_quality = _quality(founder, observations)
        stop = False

        def evaluate_completed(
            *,
            selected: Sequence[LineageTool],
            expanded: Sequence[Atom],
            body: DFA,
            source: str,
            requested_depth: int,
        ) -> bool:
            nonlocal candidates_constructed
            nonlocal candidates_evaluated
            nonlocal evidence_checks
            nonlocal best_quality
            nonlocal accepted_candidate_id
            nonlocal accepted_tool_ids
            nonlocal exact
            nonlocal reason
            candidates_constructed += 1
            normalized = normalize_dfa(body)
            first_mismatch: tuple[int, ...] | None = None
            first_expected: bool | None = None
            first_actual: bool | None = None
            quality = 0
            for word, expected in ordered_observations:
                evidence_checks += 1
                actual = normalized.accepts(word)
                quality += int(actual == expected)
                if first_mismatch is None and actual != expected:
                    first_mismatch = word
                    first_expected = expected
                    first_actual = actual
            best_quality = max(best_quality, quality)
            ids = tuple(tool.tool_id for tool in selected)
            candidate_id = _candidate_id(
                arm=arm,
                tool_ids=ids,
                program=tuple(expanded),
                body=normalized,
            )
            transcript.append(
                {
                    "kind": "completed_candidate",
                    "arm": arm,
                    "source": source,
                    "requested_depth": requested_depth,
                    "tool_ids": list(ids),
                    "expanded_program": [atom.to_list() for atom in expanded],
                    "candidate_id": candidate_id,
                    "body_digest": dfa_digest(normalized),
                    "quality": quality,
                    "first_mismatch_word": (
                        None if first_mismatch is None else list(first_mismatch)
                    ),
                    "first_mismatch_expected": first_expected,
                    "first_mismatch_actual": first_actual,
                }
            )
            if quality != len(observations):
                return False
            candidates_evaluated += 1
            is_exact, witness = exact_equivalence(normalized, target)
            transcript.append(
                {
                    "kind": "exact_evaluation",
                    "arm": arm,
                    "candidate_id": candidate_id,
                    "exact": is_exact,
                    "witness": None if witness is None else list(witness),
                }
            )
            if not is_exact:
                return False
            accepted_candidate_id = candidate_id
            accepted_tool_ids = ids
            exact = True
            reason = (
                "transported_continuation_adopted"
                if source == "transported_continuation"
                else "exact_candidate_adopted"
            )
            return True

        for program_index, program_ids in enumerate(preferred_programs):
            selected: list[LineageTool] = []
            expanded: list[Atom] = []
            current: DFA | None = founder
            program_valid = True
            for position, tool_id in enumerate(program_ids):
                tool = registry_by_id.get(str(tool_id))
                if tool is None:
                    transcript.append(
                        {
                            "kind": "preferred_program_missing_tool",
                            "arm": arm,
                            "program_index": program_index,
                            "position": position,
                            "tool_id": str(tool_id),
                        }
                    )
                    program_valid = False
                    break
                symbolic_nodes += 1
                if symbolic_nodes > node_budget:
                    reason = "symbolic_node_budget_exhausted"
                    stop = True
                    break
                atoms = _tool_atoms(tool)
                applied = 0
                for atom in atoms:
                    primitive_operations += 1
                    applied += 1
                    current = apply_atom(current, atom)  # type: ignore[arg-type]
                    if current is None:
                        break
                    expanded.append(atom)
                transcript.append(
                    {
                        "kind": "preferred_symbolic_expansion",
                        "arm": arm,
                        "program_index": program_index,
                        "position": position,
                        "tool_id": tool.tool_id,
                        "primitive_operations_applied": applied,
                        "success": current is not None,
                        "raw_result_digest": (
                            None if current is None else _raw_body_digest(current)
                        ),
                    }
                )
                if current is None:
                    program_valid = False
                    break
                if tool.provenance.origin == ORIGIN_LINEAGE_CONSTRUCTED:
                    tool_symbols_used += 1
                selected.append(tool)
            if stop:
                break
            if program_valid and current is not None and evaluate_completed(
                selected=selected,
                expanded=expanded,
                body=current,
                source="transported_continuation",
                requested_depth=len(program_ids),
            ):
                stop = True
                break

        def descend(
            current: DFA,
            selected: tuple[LineageTool, ...],
            expanded: tuple[Atom, ...],
            remaining: int,
            requested_depth: int,
        ) -> bool:
            nonlocal symbolic_nodes
            nonlocal primitive_operations
            nonlocal tool_symbols_used
            nonlocal reason
            if remaining == 0:
                return evaluate_completed(
                    selected=selected,
                    expanded=expanded,
                    body=current,
                    source="generic_enumeration",
                    requested_depth=requested_depth,
                )
            for index, tool in enumerate(ordered_registry):
                symbolic_nodes += 1
                if symbolic_nodes > node_budget:
                    reason = "symbolic_node_budget_exhausted"
                    return True
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
                        "kind": "generic_symbolic_expansion",
                        "arm": arm,
                        "requested_depth": requested_depth,
                        "remaining_before": remaining,
                        "selected_tool_index": index,
                        "selected_tool_id": tool.tool_id,
                        "prefix_tool_ids": [value.tool_id for value in selected],
                        "primitive_operations_applied": applied,
                        "success": body is not None,
                        "raw_result_digest": None if body is None else _raw_body_digest(body),
                    }
                )
                if body is None:
                    continue
                if tool.provenance.origin == ORIGIN_LINEAGE_CONSTRUCTED:
                    tool_symbols_used += 1
                if descend(
                    body,
                    selected + (tool,),
                    expanded + atoms,
                    remaining - 1,
                    requested_depth,
                ):
                    return True
            return False

        if not stop:
            for depth in range(1, maximum_depth + 1):
                if descend(founder, (), (), depth, depth):
                    break

    counters = {
        "symbolic_search_nodes": symbolic_nodes,
        "primitive_expansion_operations": primitive_operations,
        "candidates_constructed": candidates_constructed,
        "candidates_evaluated": candidates_evaluated,
        "evidence_checks": evidence_checks,
        "tool_symbols_used": tool_symbols_used,
    }
    if counters != dict(expected_mapping["counters"]):
        raise M040SearchAuditError(
            f"{arm} audit counters differ: {counters} != {expected_mapping['counters']}"
        )
    expected_fields = {
        "exact": exact,
        "reason": reason,
        "quality_numerator": best_quality,
        "quality_denominator": len(observations),
        "accepted_candidate_id": accepted_candidate_id,
        "accepted_tool_ids": list(accepted_tool_ids),
    }
    for field, actual in expected_fields.items():
        if expected_mapping[field] != actual:
            raise M040SearchAuditError(
                f"{arm} audit {field}={actual!r}, engine={expected_mapping[field]!r}"
            )
    digest = hashlib.sha256(TRANSCRIPT_DOMAIN + encode(transcript)).hexdigest()
    return M040SearchAudit(
        arm=arm,
        registry_tool_ids=tuple(tool.tool_id for tool in registry),
        preferred_programs=tuple(tuple(str(value) for value in program) for program in preferred_programs),
        maximum_depth=maximum_depth,
        node_budget=node_budget,
        exact=exact,
        reason=reason,
        quality_numerator=best_quality,
        quality_denominator=len(observations),
        symbolic_search_nodes=symbolic_nodes,
        primitive_expansion_operations=primitive_operations,
        candidates_constructed=candidates_constructed,
        candidates_evaluated=candidates_evaluated,
        evidence_checks=evidence_checks,
        tool_symbols_used=tool_symbols_used,
        accepted_candidate_id=accepted_candidate_id,
        accepted_tool_ids=accepted_tool_ids,
        transcript_digest=digest,
        transcript_entries=len(transcript),
    )
