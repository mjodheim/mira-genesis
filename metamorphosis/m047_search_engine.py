from __future__ import annotations
import time
from typing import Sequence
from metamorphosis.m047_runtime_sandbox import SoftwareSandboxError, SoftwareSandboxJob, run_bodies_in_sandbox, run_body_in_sandbox
from metamorphosis.m047_software_body import SoftwareBody, SoftwareBodyError, SoftwareCase
from metamorphosis.m047_search_memory import CausalSoftwareMemory, ModularResourceBudget, ModularSearchError, PatchSearchStatus, _canonical_json
from metamorphosis.m047_search_patch import PatchSearchResult, SoftwarePatch
from metamorphosis.m047_search_diagnosis import diagnose_limiting_module
from metamorphosis.m047_search_templates import _candidate_sources, _regression_cases

def heuristic_software_patch_search(parent: SoftwareBody, task_id: str, public_cases: Sequence[SoftwareCase], memory: CausalSoftwareMemory, budget: ModularResourceBudget) -> PatchSearchResult:
    if len(public_cases) > budget.max_public_cases:
        raise ModularSearchError('public diagnostic case budget exceeded')
    started = time.monotonic()
    incumbent = run_body_in_sandbox(parent, public_cases, timeout_seconds=budget.sandbox_timeout_seconds)
    if not incumbent.disposable_process:
        raise ModularSearchError('diagnostic execution was not disposable')
    diagnosis = diagnose_limiting_module(incumbent.cases)
    incumbent_mapping = tuple((case.to_dict() for case in incumbent.cases))
    if not diagnosis.sufficient:
        elapsed = time.monotonic() - started
        return PatchSearchResult(status=PatchSearchStatus.INSUFFICIENT_DIAGNOSIS, diagnosis=diagnosis, incumbent_case_results=incumbent_mapping, proposals=(), generated_patches=0, invalid_patches=0, program_space_lower_bound=max(4096, len(parent.modules) * 1024), exploration_fraction_ppm=0, reused_causal_memory=False, sandbox_runs=1, working_memory_bytes=len(_canonical_json(incumbent_mapping)), time_budget_respected=elapsed <= budget.max_search_seconds)
    generated_cases = _regression_cases(task_id, public_cases)
    parent_names = set(parent.module_names())
    prepared: list[tuple[str, SoftwareBody, tuple[str, ...], tuple[str, ...], int, int]] = []
    invalid = 0
    for template_id, replacements in _candidate_sources(parent, diagnosis):
        if len(prepared) >= budget.max_generated_patches:
            break
        try:
            candidate = parent.replace_modules(replacements, added_regression_cases=generated_cases)
            if candidate.total_source_bytes > budget.max_total_source_bytes:
                raise SoftwareBodyError('candidate source budget exceeded')
            changed = tuple(sorted((name for name in set(candidate.module_names()) | parent_names if name not in parent_names or candidate.source(name) != parent.source(name))))
            added = tuple(sorted(set(candidate.module_names()) - parent_names))
            prepared.append((template_id, candidate, changed, added, memory.template_bias(template_id), candidate.total_source_bytes - parent.total_source_bytes))
        except (SoftwareBodyError, ModularSearchError):
            invalid += 1
    proposals: list[SoftwarePatch] = []
    sandbox_runs = 1
    if prepared:
        jobs = tuple((SoftwareSandboxJob(f'candidate_{index}', candidate, tuple(public_cases)) for index, (_, candidate, _, _, _, _) in enumerate(prepared)))
        try:
            results = run_bodies_in_sandbox(jobs, timeout_seconds=budget.sandbox_timeout_seconds)
            sandbox_runs += 1
        except SoftwareSandboxError:
            results = {}
            invalid += len(prepared)
        for index, (template_id, candidate, changed, added, memory_bias, source_delta) in enumerate(prepared):
            candidate_result = results.get(f'candidate_{index}')
            if candidate_result is None or not candidate_result.disposable_process:
                invalid += 1
                continue
            public_passes = candidate_result.passed_cases if candidate_result.generated_tests_passed else 0
            proposals.append(SoftwarePatch(template_id=template_id, diagnosed_module=diagnosis.module, changed_modules=changed, added_modules=added, parent_body_digest=parent.digest(), candidate_body=candidate, generated_case_ids=tuple((case.case_id for case in generated_cases)), public_passes=public_passes, public_total=len(public_cases), memory_bias=memory_bias, evidence_case_ids=diagnosis.evidence_case_ids, source_delta_bytes=source_delta))
    proposals.sort(key=lambda proposal: (-proposal.ranking_score, proposal.template_id, proposal.digest()))
    elapsed = time.monotonic() - started
    lower_bound = max(4096, len(parent.modules) * 1024)
    generated = len(proposals)
    fraction = generated * 1000000 // lower_bound
    reused = bool(memory.episodes) and any((proposal.memory_bias != 0 for proposal in proposals))
    preliminary = {'diagnosis': diagnosis.to_dict(), 'incumbent': list(incumbent_mapping), 'proposal_digests': [proposal.digest() for proposal in proposals], 'invalid': invalid, 'sandbox_runs': sandbox_runs}
    working_bytes = len(_canonical_json(preliminary))
    status = PatchSearchStatus.READY if proposals else PatchSearchStatus.INSUFFICIENT_DIAGNOSIS
    if generated > budget.max_generated_patches or working_bytes > budget.max_working_memory_bytes or elapsed > budget.max_search_seconds:
        status = PatchSearchStatus.RESOURCE_BUDGET_EXHAUSTED
    return PatchSearchResult(status=status, diagnosis=diagnosis, incumbent_case_results=incumbent_mapping, proposals=tuple(proposals), generated_patches=generated, invalid_patches=invalid, program_space_lower_bound=lower_bound, exploration_fraction_ppm=fraction, reused_causal_memory=reused, sandbox_runs=sandbox_runs, working_memory_bytes=working_bytes, time_budget_respected=elapsed <= budget.max_search_seconds, complete_program_space_enumerated=False)
