"""Constructive hidden-task qualification for M043 gate Q3.

The evaluator keeps target bodies and witness traces private. Search proposals are generated
only from the current Mealy body, the declared alphabets and a causal capability surface.
A task is admitted only after an exact structural-incapacity proof and an independently
replayed Q2 rewrite trace establish that it is both necessary and reachable.
"""
from metamorphosis.m043_task_model import (
    AdmittedConstructiveTask,
    CatalogueResult,
    CatalogueStatus,
    ControlArm,
    HiddenTargetEvaluator,
    OperationKind,
    PublicTaskView,
    SearchBudget,
    SearchCapabilities,
    SearchOutcome,
    SearchStatus,
    StructuralIncapacityCertificate,
    TaskQualificationError,
    control_capabilities,
    prove_structural_incapacity,
    validate_control_surfaces,
)
from metamorphosis.m043_task_search import (
    Q3_DEVELOPMENT_BUDGET,
    Q3_DEVELOPMENT_MAXIMUM_CANDIDATES,
    Q3_DEVELOPMENT_MINIMUM_ENTRIES,
    Q3_DEVELOPMENT_OBSERVATION_LIMIT,
    ProposedPath,
    blind_constructive_search,
    build_development_catalogue,
    propose_operation_paths,
    q3_development_parent,
    run_q3_development_catalogue,
)

__all__ = [
    "AdmittedConstructiveTask",
    "CatalogueResult",
    "CatalogueStatus",
    "ControlArm",
    "HiddenTargetEvaluator",
    "OperationKind",
    "ProposedPath",
    "PublicTaskView",
    "Q3_DEVELOPMENT_BUDGET",
    "Q3_DEVELOPMENT_MAXIMUM_CANDIDATES",
    "Q3_DEVELOPMENT_MINIMUM_ENTRIES",
    "Q3_DEVELOPMENT_OBSERVATION_LIMIT",
    "SearchBudget",
    "SearchCapabilities",
    "SearchOutcome",
    "SearchStatus",
    "StructuralIncapacityCertificate",
    "TaskQualificationError",
    "blind_constructive_search",
    "build_development_catalogue",
    "control_capabilities",
    "propose_operation_paths",
    "prove_structural_incapacity",
    "q3_development_parent",
    "run_q3_development_catalogue",
    "validate_control_surfaces",
]
