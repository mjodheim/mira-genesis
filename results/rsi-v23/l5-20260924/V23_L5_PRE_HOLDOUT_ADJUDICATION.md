# V23 / L5 pre-holdout adjudication — negative causal attribution

Date: 2026-09-24

Status: **NEGATIVE BEFORE FRESH HOLDOUT — HOLDOUT NOT CONSUMED**

The prospectively frozen V23 meta-search produced a development successor that is strictly better than G2 and that preserves the complete L4 stopping behavior at zero tolerance.

However, the preregistered causal ablation predicate failed:

- G2-meta selected successor: `fda0bef4…`
- G2-ablation selected successor: `fda0bef4…`
- G2-meta meta-process utility: `(8, 12, 11240, -32, -32, -4, -4)`
- G2-ablation meta-process utility: `(8, 12, 11240, -32, -32, -4, -4)`

The two arms are exactly equal. Removing only G2's L4-validated `best >= 780 -> stop` block neither changes the selected successor nor the cost of discovering it.

G1-meta also selected the same successor, and did so with fewer represented meta-search requests/rounds: `3 / 2` versus G2-meta `4 / 4`.

Therefore the acquired L4 mechanism is **not causally established as improving recursive successor discovery in this V23 protocol**. Per preregistration, the fresh four-task BrewTrack/Brewstead holdout is not executed.

The holdout remains fresh and may be reused only by a new prospectively frozen successor protocol that does not tune itself on these unrevealed outcomes.

Evidence:
- freeze: `db258c2912ea6ceed745548ad67919437c834aea`
- canonical L5 apparatus merge: `9acff7900e057629f61217c1b481993ea8726449`
- meta-search run: `36012396710`
- artifact: `10813257837`
- G3 L4 retention: **PASS**
- fresh holdout consumed: **NO**
