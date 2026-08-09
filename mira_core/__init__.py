"""Reusable governed agent runtime for Mira Genesis.

The historical `metamorphosis` package preserves experiment-specific mechanisms.  `mira_core`
starts the operational platform: typed body interactions, least-privilege action admission,
tamper-evident memory and a bounded agent loop.  Its contracts remain provider-neutral, while an
explicit optional Codex CLI adapter makes the external model dependency visible.  It grants no
external authority by default.
"""

from mira_core.agent import AgentResult, MiraAgent
from mira_core.calibration import (
    CalibrationError, CalibrationReport, CapabilityCertificate, CapabilityProbe, EpisodeOutcome,
    EpisodeRecord, ProbeVerdict, Solvability, TaskLabel, calibration_digest, certify,
    measure_calibration,
)
from mira_core.container import (
    ContainerBodyError, ContainerExecResult, ContainerLimits, ContainerSpec, DockerCliEngine,
    IsolatedContainerBody,
)
from mira_core.contracts import Action, AuthorityAwareBody, Body, Goal, Observation, Policy
from mira_core.memory import MemoryEvent, MemoryLedger
from mira_core.model import (
    CodexExecBackend, ModelBackendError, ModelPolicyLimits, ModelRequest, StructuredModelBackend,
    StructuredModelPolicy, find_codex_executable,
)
from mira_core.probing import (
    ProbeExecutionError, harbor_probe_executor, label_task, probe_environment,
    probe_environment_async,
)
from mira_core.safety import Authority, SafetyDecision, SafetyPolicy
from mira_core.terminal import CommandSpec, GovernedTerminalBody, TerminalBodyError, TerminalLimits

__all__ = [
    "Action", "AgentResult", "Authority", "AuthorityAwareBody", "Body", "CalibrationError",
    "CalibrationReport", "CapabilityCertificate", "CapabilityProbe", "CodexExecBackend",
    "CommandSpec", "ContainerBodyError", "ContainerExecResult", "ContainerLimits", "ContainerSpec",
    "DockerCliEngine", "EpisodeOutcome", "EpisodeRecord", "Goal", "GovernedTerminalBody",
    "IsolatedContainerBody", "MemoryEvent", "MemoryLedger", "MiraAgent", "ModelBackendError",
    "ModelPolicyLimits", "ModelRequest", "Observation", "Policy", "ProbeExecutionError",
    "ProbeVerdict", "SafetyDecision", "SafetyPolicy", "Solvability", "StructuredModelBackend",
    "StructuredModelPolicy", "TaskLabel", "TerminalBodyError", "TerminalLimits",
    "calibration_digest", "certify", "find_codex_executable", "harbor_probe_executor",
    "label_task", "measure_calibration", "probe_environment", "probe_environment_async",
]
