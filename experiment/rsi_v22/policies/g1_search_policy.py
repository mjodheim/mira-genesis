"""Generated Genesis DreamPolicy executable.

This source is derived deterministically from one content-addressed DreamPolicy.
The external AST/ABI guard remains authoritative.
"""

def policy_metadata():
    return (10, 6, 3, 5, 5, 4, 8, 2, 8, 1)

def select_parent_batch(view, max_parallelism):
    rows = list(view["revealed_nodes"])
    eligible = list(view["eligible_parent_ids"])
    if not eligible:
        return []

    by_id = {row["node_id"]: row for row in rows}
    root = view["root_node_id"]
    best = max(int(row["outcome"]["quality_milli"]) for row in rows)

    def features(action):
        values = set()
        family = str(action["family"])
        if family:
            values = values | {"family:" + family}
        values = values | {"target_axes:" + str(x) for x in action["target_axes"]}
        values = values | {"mechanisms:" + str(x) for x in action["mechanisms"]}
        values = values | {"changed_regions:" + str(x) for x in action["changed_regions"]}
        return values

    def score(node_id):
        parent = by_id[node_id]
        quality = int(parent["outcome"]["quality_milli"])
        generation = int(parent["outcome"]["evolver_profile_generation"])
        champion = int(bool(parent["outcome"]["ever_champion"]))
        recovery = int(quality < best)
        seen_other = set()
        for row in rows:
            if row["node_id"] != node_id:
                seen_other = seen_other | features(row["action"])
        novelty = len(features(parent["action"]) - seen_other)
        branches = {
            str(row["outcome"]["root_branch_node_id"])
            for row in rows
            if row["node_id"] != root
        }
        root_bonus = max(0, 4 - len(branches)) if node_id == root else 0
        return (
            10 * quality
            + 6 * novelty * 100
            + 3 * int(parent["lineage_depth"]) * 100
            + 5 * generation * 150
            + 5 * champion * 100
            + 4 * recovery * 100
            + 8 * root_bonus * 100
        )

    ranked = sorted([(-score(node_id), node_id) for node_id in eligible])
    limit = min(2, 4, max(1, int(max_parallelism)))
    return [row[1] for row in ranked[:limit]]
