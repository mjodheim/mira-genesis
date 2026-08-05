from __future__ import annotations
from dataclasses import dataclass
from metamorphosis.m047_runtime_sandbox import SoftwareSandboxResult
from metamorphosis.m047_search import SoftwarePatch
from metamorphosis.m047_software_body import SoftwareBody
from metamorphosis.m047_task_definition import StopAction, _domain_digest

@dataclass(frozen=True)
class ValidationAttempt:
    proposal_digest: str
    template_id: str
    accepted: bool
    reason: str
    candidate_body_digest: str
    public_passes: int
    hidden_passes: int
    regression_passes: int
    regression_total: int
    generated_tests_passed: bool
    worker_disposable: bool

    def to_dict(self) -> dict[str, object]:
        return {'proposal_digest': self.proposal_digest, 'template_id': self.template_id, 'accepted': self.accepted, 'reason': self.reason, 'candidate_body_digest': self.candidate_body_digest, 'public_passes': self.public_passes, 'hidden_passes': self.hidden_passes, 'regression_passes': self.regression_passes, 'regression_total': self.regression_total, 'generated_tests_passed': self.generated_tests_passed, 'worker_disposable': self.worker_disposable}

@dataclass(frozen=True)
class SoftwareValidationReport:
    action: StopAction
    reason: str
    task_digest: str
    public_task_digest: str
    parent_body_digest: str
    search_digest: str
    selected_patch_digest: str | None
    candidate_body_digest: str | None
    attempts: tuple[ValidationAttempt, ...]
    incumbent_task_passes: int
    incumbent_task_total: int
    candidate_task_passes: int
    candidate_task_total: int
    regression_preserved: bool
    generated_tests_meaningful: bool
    independent_hidden_suite_used: bool
    disposable_runtime_used: bool
    resource_limits_respected: bool

    @property
    def accepted(self) -> bool:
        return self.action is StopAction.ADOPT

    def to_dict(self) -> dict[str, object]:
        return {'action': self.action.value, 'reason': self.reason, 'task_digest': self.task_digest, 'public_task_digest': self.public_task_digest, 'parent_body_digest': self.parent_body_digest, 'search_digest': self.search_digest, 'selected_patch_digest': self.selected_patch_digest, 'candidate_body_digest': self.candidate_body_digest, 'attempts': [attempt.to_dict() for attempt in self.attempts], 'incumbent_task_passes': self.incumbent_task_passes, 'incumbent_task_total': self.incumbent_task_total, 'candidate_task_passes': self.candidate_task_passes, 'candidate_task_total': self.candidate_task_total, 'regression_preserved': self.regression_preserved, 'generated_tests_meaningful': self.generated_tests_meaningful, 'independent_hidden_suite_used': self.independent_hidden_suite_used, 'disposable_runtime_used': self.disposable_runtime_used, 'resource_limits_respected': self.resource_limits_respected}

    def digest(self) -> str:
        return _domain_digest(b'm047-software-validation-report-v1\x00', self.to_dict())

@dataclass(frozen=True)
class IndependentSoftwareSelection:
    report: SoftwareValidationReport
    selected_patch: SoftwarePatch | None
    candidate_body: SoftwareBody | None

    @property
    def accepted(self) -> bool:
        return self.report.accepted

    @property
    def rejected_templates(self) -> tuple[str, ...]:
        return tuple((attempt.template_id for attempt in self.report.attempts if not attempt.accepted))

    def digest(self) -> str:
        return _domain_digest(b'm047-independent-software-selection-v1\x00', {'report_digest': self.report.digest(), 'selected_patch_digest': None if self.selected_patch is None else self.selected_patch.digest(), 'candidate_body_digest': None if self.candidate_body is None else self.candidate_body.digest()})
