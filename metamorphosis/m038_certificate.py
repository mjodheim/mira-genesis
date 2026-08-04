"""M038 exact structural-incapacity certificate.

The historical M035 lower bound is greedy and remains untouched so its recorded
behaviour stays reproducible. M038 uses an exact maximum pairwise-distinguishable
set under a committed deterministic budget.

The proposer sees only the organism's body size and oracle evidence. It never
receives the hidden target. A certificate proves a lower bound when present; an
unavailable certificate proves nothing and never falls back to the greedy result.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import combinations
from typing import Mapping, Sequence

from .m012b_dfa import DFA
from .m038_journal import encode

Word = tuple[int, ...]

ALGORITHM_ID = "exact-max-pairwise-distinguishable"
ALGORITHM_VERSION = "m038-certificate/1"
MAXIMUM_SEARCH_NODES = 2_000_000
MAXIMUM_PREFIX_COUNT = 512
STATUS_AVAILABLE = "available"
STATUS_UNAVAILABLE = "unavailable_within_committed_budget"
_EVIDENCE_DOMAIN = b"m038-structural-incapacity-evidence-v1"


@dataclass
class CertificateCounters:
    pair_tests: int = 0
    suffix_probes: int = 0
    search_nodes: int = 0

    def to_mapping(self) -> dict[str, int]:
        return {
            "pair_tests": self.pair_tests,
            "suffix_probes": self.suffix_probes,
            "search_nodes": self.search_nodes,
        }


@dataclass(frozen=True)
class StructuralIncapacityCertificate:
    body_state_count: int
    certified_lower_bound: int
    witness_prefixes: tuple[Word, ...]
    distinguishing_suffixes: tuple[tuple[Word, Word, Word], ...]
    evidence_digest: bytes
    algorithm_id: str
    algorithm_version: str
    maximum_search_nodes: int
    maximum_prefix_count: int
    search_nodes_used: int
    pair_tests: int
    suffix_probes: int
    certificate_status: str

    def proves_incapacity(self) -> bool:
        return (
            self.certificate_status == STATUS_AVAILABLE
            and self.certified_lower_bound > self.body_state_count
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "body_state_count": self.body_state_count,
            "certified_lower_bound": self.certified_lower_bound,
            "witness_prefixes": [list(prefix) for prefix in self.witness_prefixes],
            "distinguishing_suffixes": [
                {
                    "left": list(left),
                    "right": list(right),
                    "suffix": list(suffix),
                }
                for left, right, suffix in self.distinguishing_suffixes
            ],
            "evidence_digest": self.evidence_digest,
            "algorithm_id": self.algorithm_id,
            "algorithm_version": self.algorithm_version,
            "maximum_search_nodes": self.maximum_search_nodes,
            "maximum_prefix_count": self.maximum_prefix_count,
            "search_nodes_used": self.search_nodes_used,
            "pair_tests": self.pair_tests,
            "suffix_probes": self.suffix_probes,
            "certificate_status": self.certificate_status,
        }

    @staticmethod
    def from_mapping(data: Mapping[str, object]) -> "StructuralIncapacityCertificate":
        return StructuralIncapacityCertificate(
            body_state_count=int(data["body_state_count"]),
            certified_lower_bound=int(data["certified_lower_bound"]),
            witness_prefixes=tuple(
                tuple(int(symbol) for symbol in prefix)
                for prefix in data["witness_prefixes"]  # type: ignore[index]
            ),
            distinguishing_suffixes=tuple(
                (
                    tuple(int(symbol) for symbol in row["left"]),
                    tuple(int(symbol) for symbol in row["right"]),
                    tuple(int(symbol) for symbol in row["suffix"]),
                )
                for row in data["distinguishing_suffixes"]  # type: ignore[index]
            ),
            evidence_digest=bytes(data["evidence_digest"]),
            algorithm_id=str(data["algorithm_id"]),
            algorithm_version=str(data["algorithm_version"]),
            maximum_search_nodes=int(data["maximum_search_nodes"]),
            maximum_prefix_count=int(data["maximum_prefix_count"]),
            search_nodes_used=int(data["search_nodes_used"]),
            pair_tests=int(data["pair_tests"]),
            suffix_probes=int(data["suffix_probes"]),
            certificate_status=str(data["certificate_status"]),
        )


class CertificateVerificationError(ValueError):
    """The certificate is malformed, non-canonical, or unsupported by the evidence."""


class _BudgetExceeded(RuntimeError):
    pass


def canonical_evidence(evidence: Mapping[Word, bool]) -> tuple[tuple[Word, bool], ...]:
    return tuple(
        (tuple(int(symbol) for symbol in word), bool(label))
        for word, label in sorted(evidence.items())
    )


def evidence_digest(evidence: Mapping[Word, bool]) -> bytes:
    payload = [
        {"word": list(word), "label": label}
        for word, label in canonical_evidence(evidence)
    ]
    return hashlib.sha256(_EVIDENCE_DOMAIN + encode(payload)).digest()


def _prefixes(evidence: Mapping[Word, bool]) -> tuple[Word, ...]:
    return tuple(
        sorted({word[:length] for word in evidence for length in range(len(word) + 1)})
    )


def _distinguishing_suffix(
    evidence: Mapping[Word, bool],
    left: Word,
    right: Word,
    counters: CertificateCounters,
) -> Word | None:
    candidates: set[Word] = set()
    for word in sorted(evidence):
        counters.suffix_probes += 1
        if word[: len(left)] == left:
            suffix = word[len(left) :]
            other = right + suffix
            if other in evidence and evidence[other] != evidence[word]:
                candidates.add(suffix)
        if word[: len(right)] == right:
            suffix = word[len(right) :]
            other = left + suffix
            if other in evidence and evidence[other] != evidence[word]:
                candidates.add(suffix)
    if not candidates:
        return None
    return min(candidates, key=lambda suffix: (len(suffix), suffix))


def _graph(
    evidence: Mapping[Word, bool],
    counters: CertificateCounters,
) -> tuple[
    tuple[Word, ...],
    dict[Word, set[Word]],
    dict[tuple[Word, Word], Word],
]:
    nodes = _prefixes(evidence)
    edges = {node: set() for node in nodes}
    witnesses: dict[tuple[Word, Word], Word] = {}
    for left, right in combinations(nodes, 2):
        counters.pair_tests += 1
        suffix = _distinguishing_suffix(evidence, left, right, counters)
        if suffix is None:
            continue
        edges[left].add(right)
        edges[right].add(left)
        witnesses[(left, right)] = suffix
    return nodes, edges, witnesses


def _greedy_clique(nodes: Sequence[Word], edges: Mapping[Word, set[Word]]) -> tuple[Word, ...]:
    kept: list[Word] = []
    for node in sorted(nodes):
        if all(other in edges[node] for other in kept):
            kept.append(node)
    return tuple(kept)


def _exact_maximum_clique(
    nodes: Sequence[Word],
    edges: Mapping[Word, set[Word]],
    *,
    maximum_search_nodes: int,
    counters: CertificateCounters,
) -> tuple[Word, ...]:
    if maximum_search_nodes < 1:
        raise _BudgetExceeded

    best = list(_greedy_clique(nodes, edges))
    order = sorted(nodes, key=lambda node: (-len(edges[node]), node))

    def consider(clique: Sequence[Word]) -> None:
        nonlocal best
        canonical = sorted(clique)
        if len(canonical) > len(best) or (
            len(canonical) == len(best) and canonical < best
        ):
            best = canonical

    def expand(clique: list[Word], candidates: list[Word]) -> None:
        counters.search_nodes += 1
        if counters.search_nodes > maximum_search_nodes:
            raise _BudgetExceeded
        consider(clique)
        for index, node in enumerate(candidates):
            if len(clique) + len(candidates) - index < len(best):
                return
            next_candidates = [
                candidate
                for candidate in candidates[index + 1 :]
                if candidate in edges[node]
            ]
            expand(clique + [node], next_candidates)

    expand([], order)
    return tuple(best)


def compute_structural_incapacity_certificate(
    body: DFA,
    evidence: Mapping[Word, bool],
    *,
    maximum_search_nodes: int = MAXIMUM_SEARCH_NODES,
    maximum_prefix_count: int = MAXIMUM_PREFIX_COUNT,
) -> StructuralIncapacityCertificate:
    """Compute the exact certificate or an explicit unavailable result."""

    if maximum_search_nodes < 1 or maximum_prefix_count < 1:
        raise ValueError("certificate budgets must be positive")
    frozen = dict(canonical_evidence(evidence))
    counters = CertificateCounters()
    nodes, edges, witnesses = _graph(frozen, counters)

    if len(nodes) > maximum_prefix_count:
        return StructuralIncapacityCertificate(
            body_state_count=body.n_states,
            certified_lower_bound=0,
            witness_prefixes=(),
            distinguishing_suffixes=(),
            evidence_digest=evidence_digest(frozen),
            algorithm_id=ALGORITHM_ID,
            algorithm_version=ALGORITHM_VERSION,
            maximum_search_nodes=maximum_search_nodes,
            maximum_prefix_count=maximum_prefix_count,
            search_nodes_used=0,
            pair_tests=counters.pair_tests,
            suffix_probes=counters.suffix_probes,
            certificate_status=STATUS_UNAVAILABLE,
        )

    try:
        clique = _exact_maximum_clique(
            nodes,
            edges,
            maximum_search_nodes=maximum_search_nodes,
            counters=counters,
        )
    except _BudgetExceeded:
        return StructuralIncapacityCertificate(
            body_state_count=body.n_states,
            certified_lower_bound=0,
            witness_prefixes=(),
            distinguishing_suffixes=(),
            evidence_digest=evidence_digest(frozen),
            algorithm_id=ALGORITHM_ID,
            algorithm_version=ALGORITHM_VERSION,
            maximum_search_nodes=maximum_search_nodes,
            maximum_prefix_count=maximum_prefix_count,
            search_nodes_used=counters.search_nodes,
            pair_tests=counters.pair_tests,
            suffix_probes=counters.suffix_probes,
            certificate_status=STATUS_UNAVAILABLE,
        )

    pair_witnesses = tuple(
        (left, right, witnesses[(left, right)])
        for left, right in combinations(clique, 2)
    )
    return StructuralIncapacityCertificate(
        body_state_count=body.n_states,
        certified_lower_bound=max(1, len(clique)),
        witness_prefixes=clique,
        distinguishing_suffixes=pair_witnesses,
        evidence_digest=evidence_digest(frozen),
        algorithm_id=ALGORITHM_ID,
        algorithm_version=ALGORITHM_VERSION,
        maximum_search_nodes=maximum_search_nodes,
        maximum_prefix_count=maximum_prefix_count,
        search_nodes_used=counters.search_nodes,
        pair_tests=counters.pair_tests,
        suffix_probes=counters.suffix_probes,
        certificate_status=STATUS_AVAILABLE,
    )


def _validate_witnesses(
    evidence: Mapping[Word, bool],
    certificate: StructuralIncapacityCertificate,
) -> None:
    if certificate.witness_prefixes != tuple(sorted(certificate.witness_prefixes)):
        raise CertificateVerificationError("witness prefixes are not canonical")
    if len(set(certificate.witness_prefixes)) != len(certificate.witness_prefixes):
        raise CertificateVerificationError("witness prefixes contain duplicates")
    if certificate.certified_lower_bound != max(1, len(certificate.witness_prefixes)):
        raise CertificateVerificationError("certified lower bound does not match witnesses")

    expected_pairs = tuple(combinations(certificate.witness_prefixes, 2))
    actual_pairs = tuple(
        (left, right)
        for left, right, _ in certificate.distinguishing_suffixes
    )
    if actual_pairs != expected_pairs:
        raise CertificateVerificationError("pair witnesses are incomplete or non-canonical")

    for left, right, suffix in certificate.distinguishing_suffixes:
        if left + suffix not in evidence or right + suffix not in evidence:
            raise CertificateVerificationError("a distinguishing suffix is absent from evidence")
        if evidence[left + suffix] == evidence[right + suffix]:
            raise CertificateVerificationError("a recorded suffix does not distinguish its pair")
        counters = CertificateCounters()
        canonical = _distinguishing_suffix(evidence, left, right, counters)
        if suffix != canonical:
            raise CertificateVerificationError("a distinguishing suffix is not canonical")


def verify_structural_incapacity_certificate(
    body: DFA,
    evidence: Mapping[Word, bool],
    certificate: StructuralIncapacityCertificate | Mapping[str, object],
    *,
    recompute: bool = True,
) -> StructuralIncapacityCertificate:
    """Verify witnesses and, by default, recompute the committed exact result."""

    parsed = (
        certificate
        if isinstance(certificate, StructuralIncapacityCertificate)
        else StructuralIncapacityCertificate.from_mapping(certificate)
    )
    frozen = dict(canonical_evidence(evidence))

    if parsed.algorithm_id != ALGORITHM_ID or parsed.algorithm_version != ALGORITHM_VERSION:
        raise CertificateVerificationError("unknown certificate algorithm")
    if parsed.body_state_count != body.n_states:
        raise CertificateVerificationError("certificate body size does not match the body")
    if parsed.evidence_digest != evidence_digest(frozen):
        raise CertificateVerificationError("certificate evidence digest does not match")
    if parsed.maximum_search_nodes < 1 or parsed.maximum_prefix_count < 1:
        raise CertificateVerificationError("certificate budgets are invalid")
    if parsed.certificate_status not in (STATUS_AVAILABLE, STATUS_UNAVAILABLE):
        raise CertificateVerificationError("unknown certificate status")

    if parsed.certificate_status == STATUS_AVAILABLE:
        _validate_witnesses(frozen, parsed)
    else:
        if parsed.certified_lower_bound or parsed.witness_prefixes or parsed.distinguishing_suffixes:
            raise CertificateVerificationError("an unavailable certificate must carry no claim")

    if recompute:
        expected = compute_structural_incapacity_certificate(
            body,
            frozen,
            maximum_search_nodes=parsed.maximum_search_nodes,
            maximum_prefix_count=parsed.maximum_prefix_count,
        )
        if parsed.to_mapping() != expected.to_mapping():
            raise CertificateVerificationError("certificate does not match exact recomputation")
    return parsed


def proved_structural_incapacity(
    body: DFA,
    evidence: Mapping[Word, bool],
    *,
    maximum_search_nodes: int = MAXIMUM_SEARCH_NODES,
    maximum_prefix_count: int = MAXIMUM_PREFIX_COUNT,
) -> StructuralIncapacityCertificate:
    """Return the committed diagnosis; callers escalate only when it proves incapacity."""

    return compute_structural_incapacity_certificate(
        body,
        evidence,
        maximum_search_nodes=maximum_search_nodes,
        maximum_prefix_count=maximum_prefix_count,
    )
