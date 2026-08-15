"""Independent finite witness certificate for Corollary M092-P.

The original theorem in ``m092_invariant`` is sound: every inherited-substrate program has an
eventual polynomial germ, and no polynomial can equal parity on an unbounded tail.  Its historical
``refute_parity`` helper, however, chose the first even/odd pair above the threshold without checking
that the pair actually disagreed with parity.  For example, the germ ``p(x)=x-2`` at threshold 0
matches parity at x=2 and x=3.  That does not invalidate M092-P, but it means those two numbers are
not, by themselves, a valid finite refutation certificate.

This pre-result module repairs only the certificate layer.  It does not change the invariant, the
runtime, the canonical search, or any target result.  For a polynomial of degree d, it examines at
most d+1 consecutive even/odd pairs above the exactness threshold.  If every pair matched parity,
then p(2n) would have d+1 distinct roots; hence p would be identically zero, which makes every odd
member disagree.  Therefore a disagreeing witness must occur within that finite bound.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from metamorphosis.m092_invariant import Germ, Poly, poly_degree, poly_evaluate
from metamorphosis.m092_runtime import canonical_bytes

REFUTATION_SCHEMA = "m092-parity-refutation-certificate/2"


class ParityRefutationError(ValueError):
    """A claimed M092-P finite refutation does not independently verify."""


@dataclass(frozen=True)
class ParityRefutationCertificate:
    polynomial: Poly
    threshold: int
    witness: int
    witness_value: int
    parity_value: int
    pairs_examined: int
    degree: int

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": REFUTATION_SCHEMA,
            "polynomial": list(self.polynomial),
            "threshold": self.threshold,
            "witness": self.witness,
            "witness_value": self.witness_value,
            "parity_value": self.parity_value,
            "pairs_examined": self.pairs_examined,
            "degree": self.degree,
            "finite_bound": "at most degree+1 consecutive even/odd pairs above threshold",
        }
        payload["certificate_digest"] = hashlib.sha256(canonical_bytes(payload)).hexdigest()
        return payload


def construct_parity_refutation(germ: Germ) -> ParityRefutationCertificate:
    """Construct a genuine finite mismatch witness for one exact eventual-polynomial germ."""

    degree = poly_degree(germ.polynomial)
    base = max(int(germ.threshold), 0)
    even = base if base % 2 == 0 else base + 1
    pair_bound = max(degree, 0) + 1

    for pair_index in range(pair_bound):
        candidate_even = even + pair_index * 2
        candidate_odd = candidate_even + 1
        for witness in (candidate_even, candidate_odd):
            value = poly_evaluate(germ.polynomial, witness)
            parity = witness % 2
            if value != parity:
                return ParityRefutationCertificate(
                    polynomial=germ.polynomial,
                    threshold=base,
                    witness=witness,
                    witness_value=value,
                    parity_value=parity,
                    pairs_examined=pair_index + 1,
                    degree=degree,
                )

    raise ParityRefutationError(
        "no finite mismatch found within degree+1 pairs; eventual-polynomial parity theorem is inconsistent"
    )


def verify_parity_refutation(
    germ: Germ,
    certificate: ParityRefutationCertificate,
) -> dict[str, object]:
    """Recompute every load-bearing field and the actual disagreement."""

    findings: list[str] = []
    expected_degree = poly_degree(germ.polynomial)
    expected_threshold = max(int(germ.threshold), 0)
    if certificate.polynomial != germ.polynomial:
        findings.append("certificate polynomial differs from the germ")
    if certificate.degree != expected_degree:
        findings.append("certificate degree differs")
    if certificate.threshold != expected_threshold:
        findings.append("certificate threshold differs")
    if certificate.witness < expected_threshold:
        findings.append("witness is below the exactness threshold")
    if certificate.pairs_examined < 1 or certificate.pairs_examined > max(expected_degree, 0) + 1:
        findings.append("pair count exceeds the finite theorem bound")

    actual = poly_evaluate(germ.polynomial, certificate.witness)
    parity = certificate.witness % 2
    if certificate.witness_value != actual:
        findings.append("stored witness value differs from recomputation")
    if certificate.parity_value != parity:
        findings.append("stored parity value differs from recomputation")
    if actual == parity:
        findings.append("witness does not refute parity")

    reconstructed = construct_parity_refutation(germ)
    if certificate != reconstructed:
        findings.append("certificate is not the deterministic first finite mismatch")

    return {
        "schema": "m092-parity-refutation-verification/1",
        "verified": not findings,
        "findings": findings,
        "witness": certificate.witness,
        "recomputed_value": actual,
        "recomputed_parity": parity,
        "degree_plus_one_pair_bound": max(expected_degree, 0) + 1,
    }


__all__ = [
    "ParityRefutationCertificate", "ParityRefutationError", "REFUTATION_SCHEMA",
    "construct_parity_refutation", "verify_parity_refutation",
]
