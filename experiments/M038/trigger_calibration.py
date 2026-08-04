"""M038 trigger calibration. Development only, on already-consumed cases.

Run from the repository root:
    python experiments/M038/trigger_calibration.py

Selects the escalation trigger's algorithm. Deterministic counters rather than wall clock.

Wall clock is diagnostic in this repository (M017 section 9). Tractability must therefore
be argued from counted operations, not seconds.

Gap A and Gap B are defined here explicitly, because the earlier report left "Gap A = 4"
ambiguous:

  gap_a(case) = exact_bound - greedy_bound          (recoverable by a better search)
  gap_b(case) = true_minimal_states - exact_bound   (limit of the observed evidence)

Both are summed over cases and also reported per case.
"""

import hashlib
import json
import platform
import sys
from itertools import combinations
from pathlib import Path

from metamorphosis.m012b_dfa import minimize_dfa, random_minimal_dfa
from metamorphosis.m017_lab import make_out_of_language_target
from metamorphosis.structural import enumerate_words, normalize_dfa

ALGORITHM_ID = "exact-max-pairwise-distinguishable"
ALGORITHM_VERSION = "1"
# Named a development safety ceiling, not a budget: no versioned commitment fixed it
# before this calibration. The M038 budget is committed separately, in the protocol.
DEVELOPMENT_SAFETY_CEILING = 2_000_000


class Counters:
    def __init__(self):
        self.pair_tests = 0
        self.suffix_probes = 0
        self.search_nodes = 0


def evidence_from(target, words):
    return {tuple(w): target.accepts(tuple(w)) for w in words}


def prefixes_of(evidence):
    return sorted({word[:k] for word in evidence for k in range(len(word) + 1)})


def distinguishing_suffix(evidence, left, right, counters):
    """Shortest, then lexicographically smallest separating suffix. Canonical."""
    found = []
    for word, label in evidence.items():
        counters.suffix_probes += 1
        if word[: len(left)] != left:
            continue
        suffix = word[len(left):]
        other = right + suffix
        if other in evidence and evidence[other] != label:
            found.append(suffix)
    if not found:
        return None
    return min(found, key=lambda s: (len(s), s))


def build_graph(evidence, counters):
    nodes = prefixes_of(evidence)
    edges = {n: set() for n in nodes}
    witness = {}
    for a, b in combinations(nodes, 2):
        counters.pair_tests += 1
        s = distinguishing_suffix(evidence, a, b, counters)
        if s is None:
            s = distinguishing_suffix(evidence, b, a, counters)
        if s is not None:
            edges[a].add(b)
            edges[b].add(a)
            witness[(a, b)] = s
    return nodes, edges, witness


def greedy(nodes, edges):
    kept = []
    for node in nodes:
        if all(other in edges[node] for other in kept):
            kept.append(node)
    return kept


def exact_max_clique(nodes, edges, counters, ceiling):
    """Branch and bound. Canonical: lexicographically smallest among equal-size maxima."""
    incumbent = sorted(greedy(nodes, edges))
    best = [list(incumbent)]
    order = sorted(nodes, key=lambda n: (-len(edges[n]), n))
    exceeded = [False]

    def expand(clique, candidates):
        counters.search_nodes += 1
        if counters.search_nodes > ceiling:
            exceeded[0] = True
            return
        if len(clique) > len(best[0]) or (
            len(clique) == len(best[0]) and sorted(clique) < best[0]
        ):
            best[0] = sorted(clique)
        for index, node in enumerate(candidates):
            if exceeded[0]:
                return
            if len(clique) + len(candidates) - index < len(best[0]):
                return
            expand(clique + [node], [c for c in candidates[index + 1:] if c in edges[node]])

    expand([], order)
    return best[0], exceeded[0]


rows = []
for depth in (5, 6):
    words = enumerate_words(depth)
    for index in range(6):
        counters = Counters()
        base = normalize_dfa(random_minimal_dfa(50_000 + index * 7919, 4, 6))
        target = make_out_of_language_target(base, 51_000 + index * 7919)
        true_size = minimize_dfa(normalize_dfa(target)).n_states

        evidence = evidence_from(target, words)
        nodes, edges, witness = build_graph(evidence, counters)
        g = len(greedy(nodes, edges))
        clique, exceeded = exact_max_clique(nodes, edges, counters, DEVELOPMENT_SAFETY_CEILING)
        e = len(clique)

        rows.append({
            "observation_words": len(words),
            "case": index,
            "base_seed": 50_000 + index * 7919,
            "target_seed": 51_000 + index * 7919,
            "founder_states": base.n_states,
            "target_states": target.n_states,
            "true_minimal_states": true_size,
            "prefixes": len(nodes),
            "greedy_bound": g,
            "exact_bound": e,
            "gap_a_algorithmic": e - g,
            "gap_b_evidence": max(0, true_size - e),
            "pair_tests": counters.pair_tests,
            "suffix_probes": counters.suffix_probes,
            "search_nodes": counters.search_nodes,
            "ceiling_exceeded": exceeded,
        })

# The versioned artifact holds only machine-independent content, so its SHA-256 reproduces
# on any platform. The interpreter and platform are diagnostic and are printed instead.
record = {
    "algorithm_id": ALGORITHM_ID,
    "algorithm_version": ALGORITHM_VERSION,
    "development_safety_ceiling": DEVELOPMENT_SAFETY_CEILING,
    "rows": rows,
    "totals": {
        "gap_a_sum": sum(r["gap_a_algorithmic"] for r in rows),
        "gap_b_sum": sum(r["gap_b_evidence"] for r in rows),
        "cases_where_greedy_understated": sum(1 for r in rows if r["gap_a_algorithmic"] > 0),
        "cases_where_evidence_understated": sum(1 for r in rows if r["gap_b_evidence"] > 0),
        "max_search_nodes_used": max(r["search_nodes"] for r in rows),
        "max_pair_tests": max(r["pair_tests"] for r in rows),
        "any_ceiling_exceeded": any(r["ceiling_exceeded"] for r in rows),
    },
}

payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
artifact = Path(__file__).resolve().parents[2] / "results" / "artifacts" / "M038_TRIGGER_CALIBRATION.json"
artifact.parent.mkdir(parents=True, exist_ok=True)
# newline="\n" so the digest does not depend on the platform's line ending.
with open(artifact, "w", encoding="utf-8", newline="\n") as handle:
    handle.write(payload)

print(payload, end="")
print(f"artifact: {artifact}")
print(f"sha256:   {hashlib.sha256(payload.encode('utf-8')).hexdigest()}")
print(f"python:   {sys.version.split()[0]} (diagnostic)")
print(f"platform: {platform.platform()} (diagnostic)")
