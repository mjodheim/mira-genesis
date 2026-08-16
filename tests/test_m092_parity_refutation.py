from __future__ import annotations

from metamorphosis.m092_invariant import Germ
from metamorphosis.m092_parity_refutation import (
    construct_parity_refutation,
    verify_parity_refutation,
)


def test_regression_historical_first_pair_can_match_parity() -> None:
    # p(x)=x-2 at threshold 0: historical helper's pair (2,3) is exactly (0,1), so neither number
    # refutes parity.  The new constructor must keep looking and return a real mismatch.
    germ = Germ((-2, 1), threshold=0)
    assert germ.at(2) == 0
    assert germ.at(3) == 1
    certificate = construct_parity_refutation(germ)
    assert certificate.witness not in (2, 3)
    assert certificate.witness_value != certificate.parity_value
    report = verify_parity_refutation(germ, certificate)
    assert report["verified"] is True
    assert report["findings"] == []


def test_constant_zero_uses_odd_mismatch() -> None:
    germ = Germ((), threshold=7)
    certificate = construct_parity_refutation(germ)
    assert certificate.witness >= 7
    assert certificate.witness % 2 == 1
    assert certificate.witness_value == 0
    assert certificate.parity_value == 1
    assert verify_parity_refutation(germ, certificate)["verified"] is True


def test_constant_one_uses_even_mismatch() -> None:
    germ = Germ((1,), threshold=5)
    certificate = construct_parity_refutation(germ)
    assert certificate.witness >= 5
    assert certificate.witness % 2 == 0
    assert certificate.witness_value == 1
    assert certificate.parity_value == 0
    assert verify_parity_refutation(germ, certificate)["verified"] is True


def test_nonconstant_certificate_stays_within_degree_plus_one_pair_bound() -> None:
    for polynomial in ((0, 1), (1, -3, 2), (7, 0, 0, -1)):
        germ = Germ(polynomial, threshold=11)
        certificate = construct_parity_refutation(germ)
        assert certificate.pairs_examined <= max(certificate.degree, 0) + 1
        assert verify_parity_refutation(germ, certificate)["verified"] is True


def test_tampered_witness_fails_independent_recomputation() -> None:
    germ = Germ((-2, 1), threshold=0)
    certificate = construct_parity_refutation(germ)
    tampered = type(certificate)(
        polynomial=certificate.polynomial,
        threshold=certificate.threshold,
        witness=2,
        witness_value=0,
        parity_value=0,
        pairs_examined=1,
        degree=certificate.degree,
    )
    report = verify_parity_refutation(germ, tampered)
    assert report["verified"] is False
    assert "witness does not refute parity" in report["findings"]
