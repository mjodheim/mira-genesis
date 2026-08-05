from __future__ import annotations
from typing import Sequence
from metamorphosis.m047_runtime_sandbox import SoftwareSandboxError, SoftwareSandboxJob, SoftwareSandboxResult, run_bodies_in_sandbox, run_body_in_sandbox
from metamorphosis.m047_search import ModularResourceBudget, PatchSearchResult, PatchSearchStatus, SoftwarePatch
from metamorphosis.m047_software_body import BASELINE_CASES, SoftwareBody, SoftwareBodyError, SoftwareCase
from metamorphosis.m047_task_definition import HiddenSoftwareTask, ModularTaskError, StopAction
from metamorphosis.m047_validation_records import IndependentSoftwareSelection, SoftwareValidationReport, ValidationAttempt

def _case_groups(parent: SoftwareBody, task: HiddenSoftwareTask, protected_cases: Sequence[SoftwareCase]=()) -> tuple[tuple[SoftwareCase, ...], tuple[SoftwareCase, ...], tuple[SoftwareCase, ...]]:
    regressions = BASELINE_CASES + parent.regression_cases + tuple(protected_cases)
    task_cases = task.public.public_cases + task.hidden_cases
    complete = regressions + task_cases
    return (regressions, task_cases, complete)

def _expected_module_change(patch: SoftwarePatch, task: HiddenSoftwareTask) -> bool:
    return set(patch.changed_modules) == set(task.public.expected_changed_modules)

def _attempt(patch: SoftwarePatch, candidate_result: SoftwareSandboxResult | None, *, reason: str, accepted: bool, public_ids: set[str], hidden_ids: set[str], regression_ids: set[str]) -> ValidationAttempt:
    if candidate_result is None:
        public_passes = hidden_passes = regression_passes = 0
        regression_total = len(regression_ids)
        generated_tests_passed = False
        disposable = False
    else:
        public_passes = sum((candidate_result.case(case_id).passed for case_id in public_ids))
        hidden_passes = sum((candidate_result.case(case_id).passed for case_id in hidden_ids))
        regression_passes = sum((candidate_result.case(case_id).passed for case_id in regression_ids))
        regression_total = len(regression_ids)
        generated_tests_passed = candidate_result.generated_tests_passed
        disposable = candidate_result.disposable_process
    return ValidationAttempt(proposal_digest=patch.digest(), template_id=patch.template_id, accepted=accepted, reason=reason, candidate_body_digest=patch.candidate_body.digest(), public_passes=public_passes, hidden_passes=hidden_passes, regression_passes=regression_passes, regression_total=regression_total, generated_tests_passed=generated_tests_passed, worker_disposable=disposable)

def validate_ranked_software_patches_independently(parent: SoftwareBody, task: HiddenSoftwareTask, search: PatchSearchResult, budget: ModularResourceBudget, *, protected_cases: Sequence[SoftwareCase]=()) -> IndependentSoftwareSelection:
    if task.public.parent_body_digest != parent.digest():
        raise ModularTaskError('software task is stale for the parent body')
    regressions, task_cases, complete_cases = _case_groups(parent, task, protected_cases)
    incumbent = run_body_in_sandbox(parent, complete_cases, timeout_seconds=budget.sandbox_timeout_seconds)
    if not incumbent.disposable_process:
        raise ModularTaskError('incumbent validation runtime was not disposable')
    regression_ids = {case.case_id for case in regressions}
    public_ids = {case.case_id for case in task.public.public_cases}
    hidden_ids = {case.case_id for case in task.hidden_cases}
    task_ids = public_ids | hidden_ids
    incumbent_task_passes = sum((incumbent.case(case_id).passed for case_id in task_ids))
    attempts: list[ValidationAttempt] = []
    if search.status is not PatchSearchStatus.READY:
        report = SoftwareValidationReport(action=StopAction.TERMINATE_INSUFFICIENT_EVIDENCE, reason=f'patch search terminated as {search.status.value}', task_digest=task.digest(), public_task_digest=task.public.digest(), parent_body_digest=parent.digest(), search_digest=search.digest(), selected_patch_digest=None, candidate_body_digest=None, attempts=(), incumbent_task_passes=incumbent_task_passes, incumbent_task_total=len(task_ids), candidate_task_passes=0, candidate_task_total=len(task_ids), regression_preserved=True, generated_tests_meaningful=False, independent_hidden_suite_used=True, disposable_runtime_used=True, resource_limits_respected=search.time_budget_respected)
        return IndependentSoftwareSelection(report, None, None)
    ranked = tuple(search.proposals[:budget.max_validation_attempts])
    precheck_errors: dict[int, str] = {}
    jobs: list[SoftwareSandboxJob] = []
    for index, patch in enumerate(ranked):
        try:
            if patch.parent_body_digest != parent.digest():
                raise ModularTaskError('patch parent identity mismatch')
            if patch.candidate_body.total_source_bytes > budget.max_total_source_bytes:
                raise ModularTaskError('candidate source budget exceeded')
            if not _expected_module_change(patch, task):
                raise ModularTaskError('patch changed modules outside the diagnosed boundary')
            if len(patch.candidate_body.regression_cases) <= len(parent.regression_cases):
                raise ModularTaskError('patch did not add executable regression tests')
            jobs.append(SoftwareSandboxJob(f'candidate_{index}', patch.candidate_body, tuple(complete_cases)))
        except (SoftwareBodyError, ModularTaskError) as exc:
            precheck_errors[index] = str(exc)
    batch_results: dict[str, SoftwareSandboxResult] = {}
    if jobs:
        try:
            batch_results = run_bodies_in_sandbox(tuple(jobs), timeout_seconds=budget.sandbox_timeout_seconds)
        except SoftwareSandboxError as exc:
            for index, _ in enumerate(ranked):
                if index not in precheck_errors:
                    precheck_errors[index] = str(exc)
    for index, patch in enumerate(ranked):
        candidate_result = batch_results.get(f'candidate_{index}')
        if index in precheck_errors:
            attempts.append(_attempt(patch, None, reason=precheck_errors[index], accepted=False, public_ids=public_ids, hidden_ids=hidden_ids, regression_ids=regression_ids))
            continue
        if candidate_result is None:
            attempts.append(_attempt(patch, None, reason='candidate runtime result missing', accepted=False, public_ids=public_ids, hidden_ids=hidden_ids, regression_ids=regression_ids))
            continue
        reason = 'rejected'
        try:
            if not candidate_result.disposable_process:
                raise ModularTaskError('candidate validation runtime was not disposable')
            regression_preserved = all((candidate_result.case(case_id).passed for case_id in regression_ids))
            task_exact = all((candidate_result.case(case_id).passed for case_id in task_ids))
            candidate_public_passes = sum((candidate_result.case(case_id).passed for case_id in public_ids))
            generated_tests_meaningful = candidate_result.generated_tests_passed and incumbent_task_passes < len(task_ids) and (candidate_public_passes == len(public_ids))
            if not regression_preserved:
                raise ModularTaskError('candidate regressed an accepted capability')
            if not generated_tests_meaningful:
                raise ModularTaskError('candidate-generated tests were not meaningful')
            if not task_exact:
                raise ModularTaskError('candidate failed the independent hidden suite')
            attempts.append(_attempt(patch, candidate_result, reason='accepted', accepted=True, public_ids=public_ids, hidden_ids=hidden_ids, regression_ids=regression_ids))
            report = SoftwareValidationReport(action=StopAction.ADOPT, reason='candidate passed regression, generated and hidden suites in a disposable runtime', task_digest=task.digest(), public_task_digest=task.public.digest(), parent_body_digest=parent.digest(), search_digest=search.digest(), selected_patch_digest=patch.digest(), candidate_body_digest=patch.candidate_body.digest(), attempts=tuple(attempts), incumbent_task_passes=incumbent_task_passes, incumbent_task_total=len(task_ids), candidate_task_passes=len(task_ids), candidate_task_total=len(task_ids), regression_preserved=True, generated_tests_meaningful=True, independent_hidden_suite_used=True, disposable_runtime_used=True, resource_limits_respected=len(attempts) <= budget.max_validation_attempts and patch.candidate_body.total_source_bytes <= budget.max_total_source_bytes)
            return IndependentSoftwareSelection(report, patch, patch.candidate_body)
        except (SoftwareBodyError, ModularTaskError) as exc:
            reason = str(exc)
        attempts.append(_attempt(patch, candidate_result, reason=reason, accepted=False, public_ids=public_ids, hidden_ids=hidden_ids, regression_ids=regression_ids))
    report = SoftwareValidationReport(action=StopAction.TERMINATE_INSUFFICIENT_EVIDENCE, reason='no ranked patch earned independent release authority', task_digest=task.digest(), public_task_digest=task.public.digest(), parent_body_digest=parent.digest(), search_digest=search.digest(), selected_patch_digest=None, candidate_body_digest=None, attempts=tuple(attempts), incumbent_task_passes=incumbent_task_passes, incumbent_task_total=len(task_ids), candidate_task_passes=0, candidate_task_total=len(task_ids), regression_preserved=True, generated_tests_meaningful=False, independent_hidden_suite_used=True, disposable_runtime_used=True, resource_limits_respected=len(attempts) <= budget.max_validation_attempts)
    return IndependentSoftwareSelection(report, None, None)
