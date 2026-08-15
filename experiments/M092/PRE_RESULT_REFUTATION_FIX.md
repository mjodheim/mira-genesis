# M092 pre-result parity-refutation certificate correction

Status: **pre-result infrastructure correction; no H38 verdict exists on this branch.**

While the first canonical M092 criterion-search segment was still running and before any terminal
canonical artifact, selected candidate, independent reproduction result, or hidden qualification
material existed, the control-proof preparation found a defect in the historical finite helper
`metamorphosis.m092_invariant.refute_parity`.

The mathematical Corollary M092-P is unchanged: every inherited-substrate program has an eventual
polynomial germ, and no polynomial equals `x mod 2` on an unbounded tail.  The defect concerns only
the helper's claim that the first even and odd integers above the threshold necessarily form a finite
refutation witness.

Counterexample: for the exact germ `p(x) = x - 2` at threshold 0, the historical helper chooses 2
and 3.  At those points `p(2)=0` and `p(3)=1`, exactly matching parity.  The theorem is still true;
those particular two numbers simply do not certify it.

The new `m092_parity_refutation` certificate layer constructs an actual disagreement.  For a
polynomial of degree `d`, it examines at most `d+1` consecutive even/odd pairs above the exactness
threshold.  If all those pairs matched, the polynomial would have `d+1` distinct even roots and
therefore be identically zero, which immediately contradicts the odd values.  A mismatch is thus
finite and guaranteed.  The verifier independently recomputes the polynomial value, parity value,
threshold, degree bound, and deterministic first mismatch.

No runtime file, canonical-search implementation, target theorem, candidate builder, certificate
search policy, or hidden qualification generator is changed by this correction.  It cannot improve
or rescue the canonical search outcome.  Later M092 control evidence must use the corrected verified
certificate rather than trusting the historical unverified witness pair.
