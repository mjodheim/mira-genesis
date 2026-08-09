"""Run Mira's qualified governed-terminal crossing and print a compact report."""
from __future__ import annotations

import json

from metamorphosis.m069_governed_terminal_repair import (
    INCOMPATIBLE_HANDLE, run_m069_development,
)


def main() -> int:
    manifest = run_m069_development()
    value = manifest.to_dict()
    print(json.dumps({
        "schema": "mira-governed-terminal-demo-v1",
        "manifest_digest": manifest.digest(),
        "compatible_tasks": {
            handle: {
                "status": result["status"],
                "selected_repair": result["selected_candidate"]["replacement"],
                "hidden_validation_passed": result["succeeded"],
            }
            for handle, result in value["task_results"].items()
            if result["selected_candidate"] is not None
        },
        "incompatible_task": {
            "status": value["task_results"][INCOMPATIBLE_HANDLE]["status"],
            "reason": value["task_results"][INCOMPATIBLE_HANDLE]["refusal_reason"],
            "writes": value["task_results"][INCOMPATIBLE_HANDLE]["write_actions"],
            "processes": (
                value["task_results"][INCOMPATIBLE_HANDLE]["public_process_actions"]
                + value["task_results"][INCOMPATIBLE_HANDLE]["hidden_process_actions"]
            ),
        },
        "all_preregistered_controls_passed": all(
            all(control.values()) if isinstance(control, dict) else control is True
            for control in value["controls"].values()
        ),
        "boundary": {
            "real_filesystem_and_processes": value["real_filesystem_process_body"],
            "operating_system_security_sandbox": value["operating_system_security_sandbox"],
            "open_ended_code_generation": value["open_ended_code_generation"],
            "general_intelligence_claimed": value["general_intelligence_claimed"],
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
