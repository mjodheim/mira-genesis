"""The integrated Genesis runtime.

Separate from `metamorphosis/`, which holds frozen experiment modules. This package reuses their
validated invariants by construction and edits none of their sources.

The architecture splits in two and the split does not bend:

* `genesis.trust_root` is immutable. It holds isolation, budget, provenance and the final
  accept/reject, imports nothing from the rest of this package, and re-derives every number it
  decides on. Genesis must never be able to become better by modifying the measure that decides it
  is better.
* everything else is mutable Genesis, which may evolve.
"""
