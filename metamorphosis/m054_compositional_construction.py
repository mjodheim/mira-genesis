"""M054: bounded endogenous construction of a composable transformation primitive.

M053 extended the transformation language by filtering a tuple of sixteen pair expressions
materialised at import. That is selection from a declared catalogue, which is the shape
decision D009 rejects and decision D016 closed one level down.

M054 removes the catalogue. Candidate primitives are built by composing formation rules, the
admissible space at the declared depth is five orders of magnitude larger than the evaluation
budget, and the number of candidates actually constructed is recorded so that a run which
merely enumerated cannot be mistaken for one which built.

The load-bearing requirement is second-order reuse: the second task is solved by composing the
acquired primitive with itself, so what the lineage acquired becomes material for the next
acquisition rather than an answer it can replay.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Iterable, Sequence

from metamorphosis.m051_variable_composition import FROZEN_CANDIDATES, M051Error


class M054Error(ValueError):
    """Raised when an M054 artifact violates the bounded protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


ATOMS = ("previous", "current")
OPERATORS = ("add", "subtract", "minimum", "maximum", "multiply")
MAX_EXPRESSION_DEPTH = 3
BEAM_WIDTH = 12
CONSTRUCTION_BUDGET = 1024
MAX_COMPOSITION_LENGTH = 2
REDUCTIONS = ("maximum", "minimum", "sum", "mean_floor")
BEHAVIOUR_DOMAIN = tuple(itertools.product(range(-4, 5), repeat=2))


def expression_space_size(depth: int) -> int:
    """Exact number of expressions of depth at most `depth` over the formation rules."""
    if depth < 0:
        raise M054Error("depth must not be negative")
    count = len(ATOMS)
    for _ in range(depth):
        count = len(ATOMS) + len(OPERATORS) * count * count
    return count


ADMISSIBLE_SPACE = expression_space_size(MAX_EXPRESSION_DEPTH)


@dataclass(frozen=True)
class Expr:
    """A formation-rule tree. Either an atom, or an operator over two subtrees."""

    atom: str | None = None
    operator: str | None = None
    left: "Expr | None" = None
    right: "Expr | None" = None

    def __post_init__(self) -> None:
        if self.atom is not None:
            if self.atom not in ATOMS:
                raise M054Error("unknown atom")
            if self.operator is not None or self.left is not None or self.right is not None:
                raise M054Error("an atom carries no operator or operands")
            return
        if self.operator not in OPERATORS:
            raise M054Error("unknown operator")
        if self.left is None or self.right is None:
            raise M054Error("an operator requires two operands")

    @property
    def depth(self) -> int:
        if self.atom is not None:
            return 0
        return 1 + max(self.left.depth, self.right.depth)

    def evaluate(self, previous: int, current: int) -> int:
        if self.atom is not None:
            return previous if self.atom == "previous" else current
        left = self.left.evaluate(previous, current)
        right = self.right.evaluate(previous, current)
        if self.operator == "add":
            return left + right
        if self.operator == "subtract":
            return left - right
        if self.operator == "minimum":
            return min(left, right)
        if self.operator == "maximum":
            return max(left, right)
        return left * right

    def body(self) -> dict[str, object]:
        if self.atom is not None:
            return {"atom": self.atom}
        return {"operator": self.operator, "left": self.left.body(), "right": self.right.body()}

    def artifact(self) -> dict[str, object]:
        body = {"schema": "m054-primitive-v1", "depth": self.depth, "expression": self.body()}
        return {**body, "digest": _digest(b"m054-primitive-v1\0", body)}

    def apply(self, values: Sequence[int]) -> tuple[int, ...]:
        """Map a sequence to the sequence of pairwise results over adjacent elements."""
        if len(values) < 2:
            raise M054Error("a pair primitive requires at least two values")
        return tuple(self.evaluate(previous, current) for previous, current in zip(values, values[1:]))

    def behaviour(self) -> tuple[int, ...]:
        """Exact behaviour on the declared finite domain.

        Two syntactically different trees can denote the same function — `maximum(a, b)` and
        `maximum(b, a)` among them. Ambiguity has to be judged on behaviour, or a search would
        refuse to commit whenever it rediscovered the same function written another way. This
        is the M052 equivalence argument applied to construction instead of to a fixed grammar.
        """
        return tuple(self.evaluate(previous, current) for previous, current in BEHAVIOUR_DOMAIN)


def _expr_from_body(body: object) -> Expr:
    if not isinstance(body, dict):
        raise M054Error("malformed expression body")
    if "atom" in body:
        return Expr(atom=str(body["atom"]))
    return Expr(
        operator=str(body.get("operator")),
        left=_expr_from_body(body.get("left")),
        right=_expr_from_body(body.get("right")),
    )


def load_primitive(artifact: dict[str, object]) -> Expr:
    body = dict(artifact)
    supplied = body.pop("digest", None)
    if supplied != _digest(b"m054-primitive-v1\0", body):
        raise M054Error("primitive digest mismatch")
    expression = _expr_from_body(body.get("expression"))
    if expression.depth > MAX_EXPRESSION_DEPTH:
        raise M054Error("primitive exceeds the declared formation depth")
    if expression.depth != body.get("depth"):
        raise M054Error("primitive depth does not match its expression")
    return expression


@dataclass(frozen=True)
class Probe:
    values: tuple[int, ...]
    reduction: str
    expected: int


def _reduce(values: Sequence[int], reduction: str) -> int:
    if not values:
        raise M054Error("reduction of an empty sequence")
    if reduction == "maximum":
        return max(values)
    if reduction == "minimum":
        return min(values)
    if reduction == "sum":
        return sum(values)
    if reduction == "mean_floor":
        return sum(values) // len(values)
    raise M054Error("unknown reduction")


def run_program(chain: Sequence[Expr], reduction: str, values: Sequence[int]) -> int:
    """Apply each primitive in order, then reduce. Raises when the sequence runs out."""
    current: tuple[int, ...] = tuple(values)
    for primitive in chain:
        current = primitive.apply(current)
    return _reduce(current, reduction)


def founder_survivors(probes: Iterable[Probe]) -> tuple[str, ...]:
    """Founder candidates matching every probe. The founder language has no adjacency."""
    survivors = []
    for candidate in FROZEN_CANDIDATES:
        matched = True
        for probe in probes:
            try:
                if candidate.apply(probe.values) != probe.expected:
                    matched = False
                    break
            except M051Error:
                matched = False
                break
        if matched:
            survivors.append(str(candidate.artifact()["digest"]))
    return tuple(survivors)


def certify_founder_insufficiency(probes: Iterable[Probe]) -> dict[str, object]:
    probes = tuple(probes)
    if not probes:
        raise M054Error("public probes are required")
    survivors = founder_survivors(probes)
    evidence = [{"values": list(p.values), "reduction": p.reduction, "expected": p.expected} for p in probes]
    return {
        "founder_candidate_count": len(FROZEN_CANDIDATES),
        "survivor_count": len(survivors),
        "insufficient": not survivors,
        "evidence_digest": _digest(b"m054-founder-insufficiency-v1\0", evidence),
    }


def _program_error(chain: Sequence[Expr], reduction: str, probes: Sequence[Probe]) -> int | None:
    """Total absolute error over the probes, or None when the program does not apply."""
    total = 0
    for probe in probes:
        try:
            total += abs(run_program(chain, reduction, probe.values) - probe.expected)
        except (M054Error, ValueError):
            return None
    return total


@dataclass(frozen=True)
class ConstructionResult:
    status: str
    primitive: dict[str, object] | None
    chain_length: int
    reduction: str | None
    candidates_constructed: int
    admissible_space: int
    evidence_digest: str


def compose_from_registry(
    probes: Iterable[Probe],
    accepted: Sequence[Expr],
    max_length: int = MAX_COMPOSITION_LENGTH,
) -> tuple[tuple[Expr, ...], str] | None:
    """Search chains of already-accepted primitives. This is where acquisition compounds."""
    probes = tuple(probes)
    if not probes or not accepted:
        return None
    for length in range(1, max_length + 1):
        for chain in itertools.product(accepted, repeat=length):
            for reduction in REDUCTIONS:
                if _program_error(chain, reduction, probes) == 0:
                    return chain, reduction
    return None


def construct_primitive(
    probes: Iterable[Probe],
    budget: int = CONSTRUCTION_BUDGET,
    beam_width: int = BEAM_WIDTH,
    max_depth: int = MAX_EXPRESSION_DEPTH,
    max_chain: int = 1,
) -> ConstructionResult:
    """Build a primitive bottom-up, guided by public evidence, without enumerating the space.

    The beam keeps the expressions whose best reduction is closest to the observed answers.
    Nothing materialises the admissible space; `candidates_constructed` records how much of it
    was ever touched, so a run that enumerated in effect cannot present itself as one that
    constructed.

    `max_chain` gives the search the power to apply a candidate to its own output. The
    ablation arm that starts from an empty registry is run with the same `max_chain` the
    composing arm has, so the control is not weakened into a straw man: it may construct a
    primitive *and* compose it, and still has to do so inside the same budget.
    """
    probes = tuple(probes)
    if not probes:
        raise M054Error("public probes are required")
    if max_chain < 1:
        raise M054Error("a chain applies a primitive at least once")
    evidence = [{"values": list(p.values), "reduction": p.reduction, "expected": p.expected} for p in probes]
    evidence_digest = _digest(b"m054-public-construction-evidence-v1\0", evidence)

    def result(
        status: str, expr: Expr | None, reduction: str | None, seen: int, length: int = 0
    ) -> ConstructionResult:
        return ConstructionResult(
            status=status,
            primitive=expr.artifact() if expr is not None else None,
            chain_length=length,
            reduction=reduction,
            candidates_constructed=seen,
            admissible_space=expression_space_size(max_depth),
            evidence_digest=evidence_digest,
        )

    scored: dict[str, tuple[int, int, Expr, str, int]] = {}

    def consider(expr: Expr) -> tuple[int, int, Expr, str, int] | None:
        digest = str(expr.artifact()["digest"])
        if digest in scored:
            return None
        best: tuple[int, int, Expr, str, int] | None = None
        for length in range(1, max_chain + 1):
            for reduction in REDUCTIONS:
                error = _program_error((expr,) * length, reduction, probes)
                if error is None:
                    continue
                entry = (error, expr.depth, expr, reduction, length)
                if best is None or entry[:2] < best[:2]:
                    best = entry
        if best is None:
            best = (1 << 62, expr.depth, expr, REDUCTIONS[0], 1)
        scored[digest] = best
        return best

    def settle() -> ConstructionResult | None:
        """Commit only when every solving candidate denotes the same function.

        Two solving candidates with different behaviour mean the public evidence does not
        determine the primitive. The lineage refuses rather than picking one, and neither the
        budget nor the formation depth is widened afterwards.
        """
        solving = [entry for entry in scored.values() if entry[0] == 0]
        if not solving:
            return None
        classes: dict[tuple[int, ...], tuple[int, int, Expr, str, int]] = {}
        for entry in solving:
            signature = entry[2].behaviour()
            incumbent = classes.get(signature)
            if incumbent is None or (entry[1], str(entry[2].artifact()["digest"])) < (
                incumbent[1], str(incumbent[2].artifact()["digest"])
            ):
                classes[signature] = entry
        if len(classes) > 1:
            return result("insufficient_evidence", None, None, len(scored))
        chosen = next(iter(classes.values()))
        return result("constructed", chosen[2], chosen[3], len(scored), chosen[4])

    beam = [Expr(atom=name) for name in ATOMS]
    for expr in beam:
        consider(expr)
    settled = settle()
    if settled is not None:
        return settled

    for _ in range(max_depth):
        grown: list[tuple[int, int, Expr, str, int]] = []
        for left, right in itertools.product(beam, repeat=2):
            for operator in OPERATORS:
                if len(scored) >= budget:
                    return settle() or result("budget_exhausted", None, None, len(scored))
                candidate = Expr(operator=operator, left=left, right=right)
                if candidate.depth > max_depth:
                    continue
                found = consider(candidate)
                if found is not None:
                    grown.append(found)
        settled = settle()
        if settled is not None:
            return settled
        if not grown:
            break
        pool = grown + [scored[str(e.artifact()["digest"])] for e in beam]
        pool.sort(key=lambda item: (item[0], item[1], str(item[2].artifact()["digest"])))
        beam = [item[2] for item in pool[:beam_width]]

    return result("insufficient_evidence", None, None, len(scored))


def independently_validate(
    artifacts: Sequence[dict[str, object]], reduction: str, hidden_probes: Iterable[Probe]
) -> bool:
    """The validator owns the hidden probes and holds no adoption authority.

    It accepts a chain so the composed second-task program is validated by the same
    independent path as the single constructed primitive, not by the proposer's own report.
    """
    hidden = tuple(hidden_probes)
    if not hidden:
        raise M054Error("hidden probes are required")
    if not artifacts:
        raise M054Error("a chain of at least one primitive is required")
    chain = tuple(load_primitive(artifact) for artifact in artifacts)
    return _program_error(chain, reduction, hidden) == 0


@dataclass(frozen=True)
class Registry:
    accepted: tuple[dict[str, object], ...] = ()

    def primitives(self) -> tuple[Expr, ...]:
        return tuple(load_primitive(artifact) for artifact in self.accepted)

    def checkpoint(self) -> str:
        return _digest(b"m054-registry-v1\0", self.accepted)

    def snapshot(self) -> str:
        return json.dumps(self.accepted, sort_keys=True, separators=(",", ":"))

    def verify(self) -> None:
        for artifact in self.accepted:
            load_primitive(artifact)

    def adopt(self, artifact: dict[str, object], validated: bool) -> "Registry":
        if not validated:
            raise M054Error("unvalidated primitives cannot be adopted")
        load_primitive(artifact)
        return Registry(self.accepted + (artifact,))

    @classmethod
    def restore(cls, snapshot: str, expected_checkpoint: str) -> "Registry":
        restored = cls(tuple(json.loads(snapshot)))
        if restored.checkpoint() != expected_checkpoint:
            raise M054Error("restored registry does not match its checkpoint")
        restored.verify()
        return restored


def corrupt_registry(registry: Registry) -> Registry:
    """Force a post-adoption fault by tampering with the newest accepted artifact."""
    if not registry.accepted:
        raise M054Error("an empty registry cannot carry a post-adoption fault")
    tampered = dict(registry.accepted[-1])
    tampered["depth"] = int(tampered["depth"]) + 1
    return Registry(registry.accepted[:-1] + (tampered,))


def detect_fault(registry: Registry, expected_checkpoint: str) -> bool:
    if registry.checkpoint() != expected_checkpoint:
        return True
    try:
        registry.verify()
    except M054Error:
        return True
    return False


CREATION_PUBLIC = (
    Probe((2, -1, 4, 2, -9), "sum", 21),
    Probe((9, -8, 5, -1, 4), "sum", 41),
    Probe((5, 7, -1, -8, -4), "sum", 21),
)
CREATION_HIDDEN = (
    Probe((-3, 6, -2, 5), "sum", 24),
    Probe((0, 0, 4, 4), "sum", 4),
    Probe((7, 7, -2, 3, 3), "sum", 14),
)
CREATION_CONTRADICTORY_HIDDEN = (Probe((-3, 6, -2, 5), "sum", 25),)
REUSE_PUBLIC = (
    Probe((1, -4, 3, -2, 8, -6), "maximum", 5),
    Probe((-6, 0, -8, 1, -9, -1), "maximum", 2),
    Probe((4, -2, -3, -8, -4, 8), "maximum", 8),
)
REUSE_HIDDEN = (
    Probe((3, -5, 2, 6, -1, 4), "maximum", 3),
    Probe((0, 5, -5, 0, 5, -5), "maximum", 5),
)
AMBIGUOUS_PUBLIC = (Probe((3, 3), "sum", 3),)


def run_m054_compositional_construction() -> dict[str, object]:
    """One bounded lineage: construct, validate, adopt, compose, refuse, fault, restore."""
    founder_certificate = certify_founder_insufficiency(CREATION_PUBLIC)
    if not founder_certificate["insufficient"]:
        raise M054Error("the founder language is not demonstrably insufficient for task one")

    creation = construct_primitive(CREATION_PUBLIC)
    if creation.status != "constructed" or creation.primitive is None:
        raise M054Error("task one did not yield a constructed primitive")
    if creation.candidates_constructed >= creation.admissible_space:
        raise M054Error("the search enumerated its admissible space")

    validated = independently_validate((creation.primitive,), str(creation.reduction), CREATION_HIDDEN)
    if not validated:
        raise M054Error("the constructed primitive failed hidden validation")
    contradicted = independently_validate(
        (creation.primitive,), str(creation.reduction), CREATION_CONTRADICTORY_HIDDEN
    )
    if contradicted:
        raise M054Error("a contradictory hidden probe was accepted")

    founder = Registry()
    founder_checkpoint = founder.checkpoint()
    adopted = founder.adopt(creation.primitive, validated)
    adopted_checkpoint = adopted.checkpoint()
    adopted_snapshot = adopted.snapshot()

    # Second-order reuse: the second task must be reached by composing what was acquired.
    reuse_certificate = certify_founder_insufficiency(REUSE_PUBLIC)
    composed = compose_from_registry(REUSE_PUBLIC, adopted.primitives())
    if composed is None:
        raise M054Error("the acquired primitive did not compose into the second task")
    reuse_chain, reuse_reduction = composed
    if len(reuse_chain) < 2:
        raise M054Error("the second task was solved without composing the acquired primitive")
    reuse_validated = independently_validate(
        tuple(primitive.artifact() for primitive in reuse_chain), reuse_reduction, REUSE_HIDDEN
    )
    if not reuse_validated:
        raise M054Error("the composed second-task program failed hidden validation")

    # Ablation arms under the same budget. The from-scratch arm is given the same power to
    # compose that the continued lineage has, so the control is a real one.
    without_primitive = compose_from_registry(REUSE_PUBLIC, Registry().primitives())
    from_scratch = construct_primitive(REUSE_PUBLIC, max_chain=MAX_COMPOSITION_LENGTH)
    if without_primitive is not None:
        raise M054Error("the second task was solvable without the acquired primitive")
    if from_scratch.status == "constructed":
        raise M054Error("the second task was reachable from scratch within the declared budget")

    refusal = construct_primitive(AMBIGUOUS_PUBLIC)
    if refusal.status != "insufficient_evidence" or refusal.primitive is not None:
        raise M054Error("the ambiguous episode did not refuse to commit")

    faulted = corrupt_registry(adopted)
    fault_detected = detect_fault(faulted, adopted_checkpoint)
    restored = Registry.restore(adopted_snapshot, adopted_checkpoint)
    rollback_exact = (
        fault_detected
        and not detect_fault(adopted, adopted_checkpoint)
        and restored.accepted == adopted.accepted
        and restored.checkpoint() == adopted_checkpoint
        and restored.snapshot() == adopted_snapshot
        and adopted_checkpoint != founder_checkpoint
    )

    manifest = {
        "schema": "m054-manifest-v1",
        "status": "development_pending_qualification",
        "founder_candidate_count": len(FROZEN_CANDIDATES),
        "formation_atoms": list(ATOMS),
        "formation_operators": list(OPERATORS),
        "max_expression_depth": MAX_EXPRESSION_DEPTH,
        "admissible_space": ADMISSIBLE_SPACE,
        "construction_budget": CONSTRUCTION_BUDGET,
        "creation_candidates_constructed": creation.candidates_constructed,
        "creation_primitive_depth": load_primitive(creation.primitive).depth,
        "creation_reduction": creation.reduction,
        "creation_founder_certificate": founder_certificate,
        "creation_hidden_validated": validated,
        "creation_contradictory_hidden_accepted": contradicted,
        "reuse_founder_certificate": reuse_certificate,
        "reuse_chain_length": len(reuse_chain),
        "reuse_reduction": reuse_reduction,
        "reuse_hidden_validated": reuse_validated,
        "reuse_solved_without_acquired_primitive": False,
        "reuse_reachable_from_scratch_within_budget": False,
        "reuse_from_scratch_candidates_constructed": from_scratch.candidates_constructed,
        "refusal_status": refusal.status,
        "forced_fault": "adopted_primitive_artifact_tampering",
        "fault_detected": fault_detected,
        "rollback_exact": rollback_exact,
        "arbitrary_code_generation": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return {**manifest, "digest": _digest(b"m054-manifest-v1\0", manifest)}


__all__ = [
    "ADMISSIBLE_SPACE", "ATOMS", "BEAM_WIDTH", "CONSTRUCTION_BUDGET", "MAX_COMPOSITION_LENGTH",
    "MAX_EXPRESSION_DEPTH", "OPERATORS", "REDUCTIONS", "AMBIGUOUS_PUBLIC",
    "CREATION_CONTRADICTORY_HIDDEN", "CREATION_HIDDEN", "CREATION_PUBLIC", "REUSE_HIDDEN",
    "REUSE_PUBLIC", "ConstructionResult", "Expr", "M054Error", "Probe",
    "Registry", "certify_founder_insufficiency", "compose_from_registry", "construct_primitive",
    "corrupt_registry", "detect_fault", "expression_space_size", "founder_survivors",
    "independently_validate", "load_primitive", "run_m054_compositional_construction",
    "run_program",
]
