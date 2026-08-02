"""M025 — one transactional lifecycle for bounded portable self-rewrite.

M020 proposes a source rewrite and learns its transformation. M023 independently
re-evaluates the parent, candidate and regression evidence before adoption. M024
serialises the adopted body, rollback lineage and complete tool registry.

M025 joins those layers under one fail-closed transaction. A rejection or exception
restores both the body and the learned-tool registry to their exact pre-run state. A
successful run returns a separately rehydrated destination body and registry whose
learned tool can be replayed and whose parent can still be restored.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .m020_self_rewrite import (
    Case,
    RewriteResult,
    SelfRewriteEngine,
    ToolRegistry,
    VersionedCodeBody,
    source_digest,
)
from .m023_workspace import AdoptionDecision, CandidateWorkspace, WorkspaceAdoptionGate
from .m024_rewrite_passport import RewritePassport, export_passport, import_passport


@dataclass(frozen=True)
class LifecycleEvidence:
    parent_source_digest: str
    selected_source_digest: str
    baseline_workspace_digest: str
    candidate_workspace_digest: str
    regression_workspace_digest: str
    learned_tool_name: str | None
    passport_sha256: str | None


@dataclass(frozen=True)
class PortableRewriteLifecycle:
    adopted: bool
    reason: str
    rewrite: RewriteResult
    decision: AdoptionDecision
    evidence: LifecycleEvidence
    passport_json: str | None
    passport: RewritePassport | None
    migrated_body: VersionedCodeBody | None
    migrated_registry: ToolRegistry | None


def execute_portable_rewrite(
    body: VersionedCodeBody,
    registry: ToolRegistry,
    development_cases: Sequence[Case],
    regression_cases: Sequence[Case],
    *,
    max_edits: int = 2,
    beam_width: int = 32,
    workspace: CandidateWorkspace | None = None,
) -> PortableRewriteLifecycle:
    """Search, independently validate, adopt and migrate one bounded rewrite.

    The supplied body and registry form one transaction. M020 absorbs a selected trace
    before M023 decides whether the corresponding body may be adopted, so M025 must
    explicitly restore the registry when the independent gate rejects the candidate.
    """

    body_snapshot = (
        body.active_source,
        list(body.archive),
        list(body.adopted_digests),
    )
    learned_snapshot = list(registry.learned)
    parent_digest = source_digest(body.active_source)

    def restore() -> None:
        body.active_source = body_snapshot[0]
        body.archive[:] = body_snapshot[1]
        body.adopted_digests[:] = body_snapshot[2]
        registry.learned[:] = learned_snapshot

    try:
        rewrite = SelfRewriteEngine(
            registry,
            max_edits=max_edits,
            beam_width=beam_width,
        ).improve(
            body.active_source,
            body.function_name,
            development_cases,
        )
        decision = WorkspaceAdoptionGate(workspace).evaluate_and_adopt(
            body,
            rewrite,
            development_cases,
            regression_cases,
        )

        if not decision.adopted:
            restore()
            return PortableRewriteLifecycle(
                adopted=False,
                reason=decision.reason,
                rewrite=rewrite,
                decision=decision,
                evidence=LifecycleEvidence(
                    parent_source_digest=parent_digest,
                    selected_source_digest=rewrite.selected.digest,
                    baseline_workspace_digest=(
                        decision.baseline_development.workspace_digest
                    ),
                    candidate_workspace_digest=(
                        decision.candidate_development.workspace_digest
                    ),
                    regression_workspace_digest=(
                        decision.candidate_regression.workspace_digest
                    ),
                    learned_tool_name=None,
                    passport_sha256=None,
                ),
                passport_json=None,
                passport=None,
                migrated_body=None,
                migrated_registry=None,
            )

        raw_passport = export_passport(body, registry)
        migrated_body, migrated_registry, passport = import_passport(raw_passport)
        return PortableRewriteLifecycle(
            adopted=True,
            reason=decision.reason,
            rewrite=rewrite,
            decision=decision,
            evidence=LifecycleEvidence(
                parent_source_digest=parent_digest,
                selected_source_digest=rewrite.selected.digest,
                baseline_workspace_digest=(
                    decision.baseline_development.workspace_digest
                ),
                candidate_workspace_digest=(
                    decision.candidate_development.workspace_digest
                ),
                regression_workspace_digest=(
                    decision.candidate_regression.workspace_digest
                ),
                learned_tool_name=rewrite.learned_tool,
                passport_sha256=passport.sha256(),
            ),
            passport_json=raw_passport,
            passport=passport,
            migrated_body=migrated_body,
            migrated_registry=migrated_registry,
        )
    except Exception:
        restore()
        raise
