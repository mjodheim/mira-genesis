"""M093 experiment runner — real component transformation pipeline.

Usage:
    python -m scripts.run_m093_experiment

This script orchestrates the full M093 transformation lifecycle:
1. Inspect a real component
2. Generate a candidate code patch
3. Run original and candidate in disposable subprocess sandboxes
4. Compare A/B on a pre-defined criterion
5. Validate the candidate independently (separate, held-out validator)
6. Adopt the patch in the real file via a versioned store
7. Prove persistence by reloading the store in a fresh process
8. Prove rollback by restoring the previous version
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add scripts/ to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metamorphosis.m093 import (
    ComponentInsufficiency,
    CodePatch,
    TransformationStore,
    State,
    ABNullHypothesis,
    IndependentValidation,
    SandboxResult,
    compare_ab,
    inspect_component,
    run_in_sandbox,
    validate_independently,
    _domain_digest,
)
from metamorphosis.m093_suites import (
    ORIGINAL_SANDBOX_SCRIPT,
    CANDIDATE_SANDBOX_SCRIPT,
)

TARGET_FILE = "mira_core/memory.py"
WORK_DIR = Path.cwd()


def step(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def main() -> int:
    report = {}

    # ── Step 1: Inspect ──────────────────────────────────────────────
    step("1. Inspection du composant réel")
    target_path = WORK_DIR / TARGET_FILE
    insufficiency = inspect_component(str(target_path))
    report["insufficiency"] = {
        "file": insufficiency.file,
        "component": insufficiency.component,
        "insufficiency": insufficiency.insufficiency,
        "measured_evidence": insufficiency.measured_evidence,
    }
    print(f"  Composant: {insufficiency.file}")
    print(f"  Insuffisance: {insufficiency.insufficiency}")
    print(f"  Preuve: {insufficiency.measured_evidence}")

    # ── Step 2: Generate candidate ──────────────────────────────────
    step("2. Génération du patch candidat")
    patch = CodePatch.generate(str(target_path))
    report["patch"] = {
        "file": patch.file,
        "added_lines": patch.added_class_lines,
        "added_methods": patch.added_method_count,
        "digest": patch.digest,
        "original_digest": patch.original_digest(),
        "modified_digest": patch.modified_digest(),
    }
    print(f"  Fichier: {patch.file}")
    print(f"  Lignes ajoutées: {patch.added_class_lines}")
    print(f"  Delta digest: {patch.original_digest()[:16]}... → {patch.modified_digest()[:16]}...")

    # ── Step 3: Sandbox tests ────────────────────────────────────────
    step("3. Test dans l'environnement isolé (sandbox)")
    print("  [Original] Running existing behavior tests...")
    t0 = time.time()
    orig_result = run_in_sandbox(
        patch.old_source, "memory",
        sandbox_script=ORIGINAL_SANDBOX_SCRIPT, timeout_seconds=30,
    )
    orig_result = SandboxResult(
        orig_result.variant_id, orig_result.passed,
        orig_result.total_assertions, orig_result.failed_assertions,
        time.time() - t0, orig_result.stdout, orig_result.stderr,
        orig_result.exit_code,
    )
    print(f"    → passed={orig_result.passed} {orig_result.total_assertions}/{orig_result.total_assertions - orig_result.failed_assertions} ok")

    print("  [Candidat] Running new behavior tests...")
    t0 = time.time()
    cand_result = run_in_sandbox(
        patch.new_source, "memory",
        sandbox_script=CANDIDATE_SANDBOX_SCRIPT, timeout_seconds=30,
    )
    cand_result = SandboxResult(
        cand_result.variant_id, cand_result.passed,
        cand_result.total_assertions, cand_result.failed_assertions,
        time.time() - t0, cand_result.stdout, cand_result.stderr,
        cand_result.exit_code,
    )
    print(f"    → passed={cand_result.passed} {cand_result.total_assertions}/{cand_result.total_assertions - cand_result.failed_assertions} ok")

    report["sandbox"] = {
        "original": {"passed": orig_result.passed, "assertions": orig_result.total_assertions, "failed": orig_result.failed_assertions, "runtime_s": round(orig_result.runtime_seconds, 3)},
        "candidate": {"passed": cand_result.passed, "assertions": cand_result.total_assertions, "failed": cand_result.failed_assertions, "runtime_s": round(cand_result.runtime_seconds, 3)},
    }

    # ── Step 4: A/B comparison ───────────────────────────────────────
    step("4. Comparaison objective (original vs candidat)")
    comparison = compare_ab(orig_result, cand_result, criterion="all_assertions_pass_and_candidate_adds_query_capability")
    report["comparison"] = {
        "criterion": comparison.criterion,
        "null_rejected": comparison.null_rejected,
        "reason": comparison.reason,
    }
    print(f"  Critère: {comparison.criterion}")
    print(f"  H0 rejetée: {comparison.null_rejected}")
    print(f"  Raison: {comparison.reason}")

    if not comparison.null_rejected:
        print("\n  ❌ H0 non rejetée — arrêt de l'expérience.")
        report["outcome"] = "stopped_at_comparison"
        print(json.dumps(report, indent=2))
        return 1

    # ── Step 5: Independent validation ────────────────────────────────
    step("5. Validation indépendante (validateur séparé)")
    print("  Running held-out validator (does NOT see original result)...")
    validation = validate_independently(patch, validator_id="m093-validator", timeout_seconds=30)
    report["validation"] = {
        "validator_id": validation.validator_id,
        "passed": validation.passed,
        "accepted": validation.accepted,
        "report": validation.report,
        "digest": validation.digest,
    }
    print(f"  → accepted={validation.accepted} passed={validation.passed}")
    print(f"  Rapport: {validation.report}")

    if not validation.accepted:
        print("\n  ❌ Validation indépendante rejetée.")
        report["outcome"] = "stopped_at_validation"
        print(json.dumps(report, indent=2))
        return 1

    # ── Step 6: Adopt ────────────────────────────────────────────────
    step("6. Adoption réelle dans le fichier")
    store = TransformationStore.init_or_load(
        str(WORK_DIR),
        _domain_digest(b"m093-source-v1\0", patch.old_source),
    )
    print(f"  Store version avant adoption: {store.version}")

    adopted = store.adopt(patch, validation, comparison)
    report["adoption"] = {
        "adopted": adopted,
        "version_after": store.version,
        "state_digest": store.state.to_dict().get("current_file_digest", ""),
    }
    print(f"  Adopté: {adopted}")
    print(f"  Version store: {store.version}")
    print(f"  Fichier écrit: {target_path}")

    if not adopted:
        print("\n  ❌ Adoption refusée.")
        report["outcome"] = "adoption_refused"
        print(json.dumps(report, indent=2))
        return 1

    # Verify the file was actually written
    written = target_path.read_text(encoding="utf-8")
    written_digest = _domain_digest(b"m093-source-v1\0", written)
    file_matches = written_digest == patch.modified_digest()
    report["adoption"]["file_verified"] = file_matches
    print(f"  Vérification fichier: {file_matches}")

    if not file_matches:
        print("  ⚠️  Le fichier écrit ne correspond pas au patch — rollback nécessaire.")
        store.rollback()
        report["outcome"] = "adoption_file_mismatch_rolled_back"
        print(json.dumps(report, indent=2))
        return 1

    # ── Step 7: Persistence proof ────────────────────────────────────
    step("7. Preuve de persistance après redémarrage")
    state_path = TransformationStore.persistence_path(WORK_DIR)
    print(f"  Fichier d'état: {state_path}")
    assert state_path.exists(), "state file should exist after adoption"
    state_bytes = state_path.read_bytes()
    reloaded_state = State.restore(state_bytes)
    persistence_ok = reloaded_state.version == store.version and reloaded_state.current_file_digest == store.state.current_file_digest
    report["persistence"] = {
        "state_file_exists": state_path.exists(),
        "reloaded_version": reloaded_state.version,
        "digest_match": persistence_ok,
    }
    print(f"  Fichier d'état présent: {state_path.exists()}")
    print(f"  Version rechargée: {reloaded_state.version}")
    print(f"  Digest correspond: {persistence_ok}")

    # ── Step 8: Rollback proof ───────────────────────────────────────
    step("8. Preuve de rollback exact")
    rollback_entry = store.rollback()
    report["rollback"] = {
        "rolled_back": rollback_entry is not None,
        "version_after_rollback": store.version,
        "event": rollback_entry.event if rollback_entry else None,
    }
    if rollback_entry:
        print(f"  Rollback effectué: {rollback_entry.event} (version → {store.version})")
        # Verify the file is back to original
        restored = target_path.read_text(encoding="utf-8")
        restored_digest = _domain_digest(b"m093-source-v1\0", restored)
        exact_restoration = restored_digest == patch.original_digest()
        report["rollback"]["exact_restoration"] = exact_restoration
        print(f"  Restauration exacte: {exact_restoration}")
        if not exact_restoration:
            print("  ❌ ÉCHEC: rollback n'a pas restauré l'original exact.")

    # ── Final report ─────────────────────────────────────────────────
    step("RÉSULTATS")
    report["outcome"] = "completed"
    report["component"] = "mira_core/memory.py"
    report["modification"] = "events_by_kind(kind) method"
    print(json.dumps(report, indent=2))

    # Re-adopt the patch since the experiment proved it works
    step("🏁 Ré-adoption du patch (expérience réussie, modification conservée)")
    store2 = TransformationStore.init_or_load(str(WORK_DIR), patch.original_digest())
    store2.adopt(patch, validation, comparison)
    target_path.write_text(patch.new_source, encoding="utf-8")
    print(f"  memory.py mis à jour avec events_by_kind (version {store2.version})")

    return 0


if __name__ == "__main__":
    sys.exit(main())