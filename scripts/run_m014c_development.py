from __future__ import annotations

import json
from pathlib import Path
import statistics

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m013e_lab import make_development_positive_machine
from metamorphosis.m013e_runtime import opaque_body_to_dfa
from metamorphosis.m014b_lab import make_state_adding_target
from metamorphosis.m014b_scratch import learn_dfa_from_scratch_lstar
from metamorphosis.m014c_engine import DistributionGeneralPlasticityEngine
from metamorphosis.m014c_lab import (
    PROGRAM_LIBRARY, BehavioralOracle, development_demonstrations,
    generate_environment_sequence, generated_profile, make_out_of_library_target,
)
from metamorphosis.m014c_meta import (
    MetaPlasticitySession, train_meta_passport, uniform_meta_passport,
)

ROOT = Path(__file__).resolve().parents[1]


def med(values: list[int]) -> float:
    return float(statistics.median(values)) if values else 0.0


def main() -> None:
    passport = train_meta_passport(PROGRAM_LIBRARY, development_demonstrations())
    uniform = uniform_meta_passport(passport)
    totals = {name: [] for name in ("active", "static", "random", "uniform", "scratch")}
    wins = {name: 0 for name in ("static", "random", "uniform")}
    environments: list[dict[str, object]] = []

    for env in range(12):
        profile = generated_profile(80_000 + env)
        sequence = generate_environment_sequence(profile, 81_000 + env, episodes=16, min_states=7, max_states=10)
        active = MetaPlasticitySession(passport, adaptive=True)
        static = MetaPlasticitySession(passport, adaptive=False)
        random_session = MetaPlasticitySession(passport, adaptive=False)
        uniform_session = MetaPlasticitySession(uniform, adaptive=False)
        local = {name: [] for name in totals}
        for episode, (base, target, _) in enumerate(sequence):
            seed = 82_000 + env * 100 + episode
            rows = {
                "active": active.identify(base, BehavioralOracle(target), search_seed=seed),
                "static": static.identify(base, BehavioralOracle(target), search_seed=seed),
                "random": random_session.identify(base, BehavioralOracle(target), search_seed=seed, policy="random"),
                "uniform": uniform_session.identify(base, BehavioralOracle(target), search_seed=seed),
            }
            scratch = learn_dfa_from_scratch_lstar(target, BehavioralOracle(target))
            assert all(row.status == "success" for row in rows.values())
            assert scratch.status == "success" and scratch.hypothesis is not None
            assert exact_equivalence(scratch.hypothesis, target)[0]
            if episode >= 4:
                for name, row in rows.items():
                    local[name].append(row.identification_calls)
                local["scratch"].append(scratch.unique_membership_queries)
        for name, values in local.items():
            totals[name].extend(values)
        for name in wins:
            wins[name] += int(sum(local["active"]) < sum(local[name]))
        environments.append({
            "environment": env,
            "profile": profile,
            **{f"{name}_calls": sum(values) for name, values in local.items()},
        })

    embodiment: list[dict[str, object]] = []
    for family in range(3):
        machine = make_development_positive_machine(family)
        engine = DistributionGeneralPlasticityEngine(machine, passport.to_json())
        sequence = generate_environment_sequence(generated_profile(83_000 + family), 84_000 + family, episodes=4, min_states=6, max_states=8)
        for episode, (base, target, _) in enumerate(sequence):
            certificate = engine.adapt_episode(base, BehavioralOracle(target), 85_000 + family * 100 + episode)
            assert certificate.status == "success", certificate.reason
            assert certificate.old_body is not None and certificate.new_body is not None
            embodiment.append({
                "family": family,
                "episode": episode,
                "old_exact": exact_equivalence(base, opaque_body_to_dfa(certificate.old_body, machine))[0],
                "new_exact": exact_equivalence(target, opaque_body_to_dfa(certificate.new_body, machine))[0],
                "archive_exact": certificate.old_body_bit_exact,
            })

    negative: list[dict[str, object]] = []
    for index in range(12):
        base, _, _ = generate_environment_sequence(generated_profile(86_000 + index), 87_000 + index, episodes=1, min_states=7, max_states=10)[0]
        kind = index % 3
        if kind == 0:
            oracle = BehavioralOracle(make_out_of_library_target(base, 88_000 + index))
            label = "outside_library"
        elif kind == 1:
            oracle = BehavioralOracle(make_state_adding_target(base, 88_000 + index))
            label = "state_adding"
        else:
            oracle = BehavioralOracle(make_out_of_library_target(base, 88_000 + index), mode="alternating")
            label = "unstable"
        result = MetaPlasticitySession(passport).identify(base, oracle, search_seed=89_000 + index)
        negative.append({"kind": label, "status": result.status, "reason": result.reason})

    summary = {
        "development_only": True,
        "scored_episodes": len(totals["active"]),
        **{f"{name}_calls": sum(values) for name, values in totals.items()},
        **{f"median_{name}": med(values) for name, values in totals.items()},
        "active_to_static_ratio": sum(totals["active"]) / sum(totals["static"]),
        "active_to_random_ratio": sum(totals["active"]) / sum(totals["random"]),
        "active_to_uniform_ratio": sum(totals["active"]) / sum(totals["uniform"]),
        "active_to_scratch_ratio": sum(totals["active"]) / sum(totals["scratch"]),
        "environment_wins": wins,
        "embodiment_exact": sum(row["old_exact"] and row["new_exact"] and row["archive_exact"] for row in embodiment),
        "embodiment_total": len(embodiment),
        "negative_abstentions": sum(row["status"] == "abstained" for row in negative),
        "negative_total": len(negative),
        "passport_sha256": passport.sha256(),
        "passport_bytes": len(passport.to_json().encode("utf-8")),
        "trace_format": "integers_only",
    }
    output = {"summary": summary, "environments": environments, "embodiment": embodiment, "negative_controls": negative}
    path = ROOT / "results" / "M014c_development.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
