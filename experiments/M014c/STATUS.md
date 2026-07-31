# M014c — Status

- Protocol: **DEVELOPMENT DRAFT**
- Canonical results allowed: **NO**
- Structural meta-passport: **implemented**
- Persistent opaque-substrate engine: **implemented**
- Development tests: **7 passing**, within a repository suite of **26**
- Sealed evaluation seeds: **none**
- Scientific status: `DEVELOPMENT — QUERY AND EMBODIMENT BENCHMARKING`

The next gate is a reproducible development benchmark across generated held-out
environment profiles, followed by negative-control integration and protocol freezing.
No canonical PR may be opened before those gates pass.

## Open risk that blocks the freeze

The development benchmark reports `active_to_scratch_ratio = 0.083`. That number must
not be read as a fifteen-fold improvement in meta-learning. It is dominated by a
parameter choice: held-out DFAs carry 7 to 10 states, so scratch L\* pays a cost that
grows with the automaton while Genesis pays a cost that grows with its library of
twelve programs. Enlarging the held-out automata would inflate the same ratio without
any change to what the passport learned.

The comparison that actually carries the M014c hypothesis is the adaptive session
against its own non-adaptive twin: `active_to_static_ratio = 0.88`. Twelve percent, on
a task where the theoretical optimum sits near four queries and random selection sits
at eight — a measurable window barely four queries wide.

M014b failed on exactly this geometry: a pre-registered 25% margin, measured on a scale
too coarse to separate signal from sampling noise. Freezing M014c against the L\*
baseline would pass trivially and would repeat the error in the opposite direction.

Before the protocol may be frozen:

1. state which single comparison decides the experiment, and justify why the others
   are reported but not decisive;
2. justify the held-out state range from the hypothesis, not from the margin it yields;
3. establish that the chosen margin exceeds the dispersion across environment profiles,
   rather than assuming it does.
