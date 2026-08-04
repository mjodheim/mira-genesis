from dataclasses import replace

import pytest

from metamorphosis.m012b_dfa import DFA
from metamorphosis.m035_evolution import required_states_lower_bound
from metamorphosis.m038_certificate import (
    ALGORITHM_ID,
    STATUS_AVAILABLE,
    STATUS_UNAVAILABLE,
    CertificateVerificationError,
    StructuralIncapacityCertificate,
    compute_structural_incapacity_certificate,
    evidence_digest,
    verify_structural_incapacity_certificate,
)
from metamorphosis.structural import enumerate_words, normalize_dfa


def target_three_states() -> DFA:
    return normalize_dfa(
        DFA(
            (0, 1),
            (
                (1, 0),
                (2, 1),
                (0, 2),
            ),
            (False, False, True),
            0,
        )
    )


def body_two_states() -> DFA:
    return normalize_dfa(
        DFA(
            (0, 1),
            (
                (1, 0),
                (1, 0),
            ),
            (False, True),
            0,
        )
    )


def observed(target: DFA, depth: int = 5):
    return {word: target.accepts(word) for word in enumerate_words(depth)}


def test_the_exact_certificate_proves_a_real_structural_incapacity():
    target = target_three_states()
    body = body_two_states()
    evidence = observed(target)

    certificate = compute_structural_incapacity_certificate(body, evidence)

    assert target.n_states == 3
    assert body.n_states == 2
    assert certificate.certificate_status == STATUS_AVAILABLE
    assert certificate.certified_lower_bound == target.n_states
    assert certificate.proves_incapacity()
    assert len(certificate.witness_prefixes) == 3
    verify_structural_incapacity_certificate(body, evidence, certificate)


def test_the_certificate_uses_only_body_and_evidence():
    target = target_three_states()
    body = body_two_states()
    evidence = observed(target)

    first = compute_structural_incapacity_certificate(body, evidence)
    second = compute_structural_incapacity_certificate(body, dict(reversed(list(evidence.items()))))

    assert first == second
    assert first.algorithm_id == ALGORITHM_ID


def test_the_evidence_digest_is_insertion_order_independent():
    evidence = observed(target_three_states())
    assert evidence_digest(evidence) == evidence_digest(dict(reversed(list(evidence.items()))))


def test_the_historical_greedy_function_is_left_untouched_and_is_only_a_lower_bound():
    evidence = observed(target_three_states())
    body = body_two_states()
    exact = compute_structural_incapacity_certificate(body, evidence)

    assert required_states_lower_bound(evidence) <= exact.certified_lower_bound


def test_a_search_budget_exhaustion_returns_no_partial_claim_and_no_greedy_fallback():
    certificate = compute_structural_incapacity_certificate(
        body_two_states(),
        observed(target_three_states()),
        maximum_search_nodes=1,
    )

    assert certificate.certificate_status == STATUS_UNAVAILABLE
    assert certificate.certified_lower_bound == 0
    assert certificate.witness_prefixes == ()
    assert certificate.distinguishing_suffixes == ()
    assert not certificate.proves_incapacity()
    verify_structural_incapacity_certificate(
        body_two_states(),
        observed(target_three_states()),
        certificate,
    )


def test_a_prefix_budget_exhaustion_returns_no_partial_claim():
    certificate = compute_structural_incapacity_certificate(
        body_two_states(),
        observed(target_three_states()),
        maximum_prefix_count=1,
    )

    assert certificate.certificate_status == STATUS_UNAVAILABLE
    assert certificate.certified_lower_bound == 0
    assert certificate.search_nodes_used == 0


def test_a_tampered_bound_is_detected_even_when_the_witnesses_are_unchanged():
    body = body_two_states()
    evidence = observed(target_three_states())
    certificate = compute_structural_incapacity_certificate(body, evidence)
    forged = replace(certificate, certified_lower_bound=certificate.certified_lower_bound + 1)

    with pytest.raises(CertificateVerificationError, match="lower bound"):
        verify_structural_incapacity_certificate(body, evidence, forged, recompute=False)


def test_a_missing_pair_witness_is_detected():
    body = body_two_states()
    evidence = observed(target_three_states())
    certificate = compute_structural_incapacity_certificate(body, evidence)
    forged = replace(
        certificate,
        distinguishing_suffixes=certificate.distinguishing_suffixes[:-1],
    )

    with pytest.raises(CertificateVerificationError, match="incomplete"):
        verify_structural_incapacity_certificate(body, evidence, forged, recompute=False)


def test_a_non_separating_suffix_is_detected():
    body = body_two_states()
    evidence = observed(target_three_states())
    certificate = compute_structural_incapacity_certificate(body, evidence)
    left, right, _ = certificate.distinguishing_suffixes[0]
    forged_rows = list(certificate.distinguishing_suffixes)
    forged_rows[0] = (left, right, ())
    forged = replace(certificate, distinguishing_suffixes=tuple(forged_rows))

    with pytest.raises(CertificateVerificationError, match="does not distinguish|absent"):
        verify_structural_incapacity_certificate(body, evidence, forged, recompute=False)


def test_an_evidence_change_invalidates_the_certificate():
    body = body_two_states()
    evidence = observed(target_three_states())
    certificate = compute_structural_incapacity_certificate(body, evidence)
    changed = dict(evidence)
    changed[()] = not changed[()]

    with pytest.raises(CertificateVerificationError, match="evidence digest"):
        verify_structural_incapacity_certificate(body, changed, certificate, recompute=False)


def test_a_mapping_round_trip_preserves_the_certificate():
    body = body_two_states()
    evidence = observed(target_three_states())
    certificate = compute_structural_incapacity_certificate(body, evidence)

    restored = StructuralIncapacityCertificate.from_mapping(certificate.to_mapping())

    assert restored == certificate
    verify_structural_incapacity_certificate(body, evidence, restored)


def test_invalid_budgets_are_rejected_before_any_claim():
    with pytest.raises(ValueError, match="positive"):
        compute_structural_incapacity_certificate(
            body_two_states(),
            observed(target_three_states()),
            maximum_search_nodes=0,
        )
