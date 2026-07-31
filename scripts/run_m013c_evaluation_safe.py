from __future__ import annotations

import argparse
from pathlib import Path

import run_m013c_evaluation as base
from metamorphosis.core import exact_equivalence
from metamorphosis.unknown_substrate import OpaqueNativeBody, opaque_body_to_dfa


def safe_evaluate_certificate(cert, passport, machine, suite):
    record = {
        "status": cert.status,
        "reason": cert.reason,
        "probe_calls": cert.probe_calls,
        "candidate_evaluations": cert.candidate_evaluations,
        "native_components": cert.native_components,
        "serialized_bytes": cert.serialized_bytes,
        "elapsed_seconds": cert.elapsed_seconds,
        "used_opcodes": list(cert.used_opcodes),
        "trace": dict(cert.trace),
        "exact": False,
        "hidden_accuracy": 0.0,
        "serialization_round_trip": False,
        "semantic_exact_used": False,
        "semantic_audit": {},
        "body_sha256": None,
    }
    if cert.body is None:
        return record
    raw = cert.body.to_json()
    record["body_sha256"] = base.sha256_bytes(raw.encode("utf-8"))
    try:
        restored = OpaqueNativeBody.from_json(raw)
        candidate = opaque_body_to_dfa(restored, machine)
    except (ValueError, RecursionError) as exc:
        record["evaluation_error"] = f"{type(exc).__name__}:{exc}"
        return record
    record["exact"] = exact_equivalence(passport, candidate)[0]
    record["hidden_accuracy"] = suite.accuracy(candidate) if suite is not None else float(record["exact"])
    record["serialization_round_trip"] = restored == cert.body
    semantic_exact, audit = base.semantic_audit(cert, machine)
    record["semantic_exact_used"] = semantic_exact
    record["semantic_audit"] = audit
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--output", default=str(base.ROOT / "results" / "M013c.json"))
    args = parser.parse_args()
    base.evaluate_certificate = safe_evaluate_certificate
    result = base.run(args.git_commit, Path(args.output))
    print(base.report(result))


if __name__ == "__main__":
    main()
