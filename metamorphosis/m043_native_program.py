"""Table-free native Mealy synthesis over an experimentally discovered field basis."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

from metamorphosis.m043_mealy import (
    MealyMachine,
    exact_mealy_equivalence,
    mealy_digest,
)
from metamorphosis.m043_rewrite import exact_body_bytes, exact_body_digest
from metamorphosis.m043_opaque_substrate import (
    DiscoveredFieldSubstrate,
    OpaqueFieldMachine,
    SubstrateError,
)


class NativeProgramError(ValueError):
    """Raised when a native program or synthesis certificate is malformed."""


PROGRAM_SCHEMA = "m043-q5-native-program-v1"
SYNTHESIS_METHOD = "finite-field-lagrange-dag-v1"
FORBIDDEN_TABLE_KEYS = frozenset(
    {"transitions", "outputs", "transition_table", "output_table", "truth_table", "table"}
)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


def _require_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise NativeProgramError(f"{field} must be an object")
    return value


def _require_sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise NativeProgramError(f"{field} must be a sequence")
    return value


def _require_int(value: object, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise NativeProgramError(f"{field} must be an integer >= {minimum}")
    return value


def _require_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeProgramError(f"{field} must be a nonempty string")
    return value


def _require_digest(value: object, field: str) -> str:
    raw = _require_string(value, field)
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise NativeProgramError(f"{field} must be a lowercase SHA-256 digest")
    return raw


def _exact_fields(raw: Mapping[str, object], required: set[str], field: str) -> None:
    if set(raw) != required:
        missing = sorted(required - set(raw))
        extra = sorted(set(raw) - required)
        raise NativeProgramError(
            f"invalid {field} fields: missing={missing}, extra={extra}"
        )


@dataclass(frozen=True)
class NativeNode:
    kind: str
    value: int | None = None
    opcode: str | None = None
    args: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.kind in {"state", "symbol"}:
            if self.value is not None or self.opcode is not None or self.args:
                raise NativeProgramError(f"{self.kind} nodes carry no payload")
        elif self.kind == "constant":
            if self.value is None or self.opcode is not None or self.args:
                raise NativeProgramError("constant nodes require only a value")
            _require_int(self.value, "constant value")
        elif self.kind == "call":
            if self.value is not None or not self.opcode or not self.args:
                raise NativeProgramError("call nodes require an opcode and arguments")
            if len(self.args) > 2:
                raise NativeProgramError("native calls are limited to arity two")
            for argument in self.args:
                _require_int(argument, "call argument")
        else:
            raise NativeProgramError(f"unknown native node kind: {self.kind!r}")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "value": self.value,
            "opcode": self.opcode,
            "args": list(self.args),
        }

    @staticmethod
    def from_dict(value: object) -> "NativeNode":
        raw = _require_mapping(value, "native node")
        _exact_fields(raw, {"kind", "value", "opcode", "args"}, "native node")
        kind = _require_string(raw["kind"], "native node kind")
        raw_value = raw["value"]
        raw_opcode = raw["opcode"]
        return NativeNode(
            kind=kind,
            value=(
                None
                if raw_value is None
                else _require_int(raw_value, "native node value")
            ),
            opcode=(
                None
                if raw_opcode is None
                else _require_string(raw_opcode, "native node opcode")
            ),
            args=tuple(
                _require_int(item, "native node argument")
                for item in _require_sequence(raw["args"], "native node args")
            ),
        )


@dataclass(frozen=True)
class NativeMealyProgram:
    machine_id: str
    modulus: int
    discovery_digest: str
    declared_state_count: int
    input_alphabet: tuple[int, ...]
    output_alphabet: tuple[int, ...]
    initial_state: int
    nodes: tuple[NativeNode, ...]
    next_state_root: int
    output_root: int
    synthesis_method: str = SYNTHESIS_METHOD
    schema: str = PROGRAM_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PROGRAM_SCHEMA:
            raise NativeProgramError("unsupported native program schema")
        if self.synthesis_method != SYNTHESIS_METHOD:
            raise NativeProgramError("unsupported native synthesis method")
        _require_string(self.machine_id, "machine_id")
        _require_digest(self.discovery_digest, "discovery_digest")
        if self.modulus != 5:
            raise NativeProgramError("Q5 native programs require modulus 5")
        if not 1 <= self.declared_state_count <= self.modulus:
            raise NativeProgramError("invalid declared state count")
        if not self.input_alphabet or not self.output_alphabet:
            raise NativeProgramError("native alphabets must be nonempty")
        for name, alphabet in (
            ("input", self.input_alphabet),
            ("output", self.output_alphabet),
        ):
            if len(set(alphabet)) != len(alphabet):
                raise NativeProgramError(f"{name} alphabet symbols must be unique")
            if any(
                isinstance(symbol, bool)
                or not isinstance(symbol, int)
                or not 0 <= symbol < self.modulus
                for symbol in alphabet
            ):
                raise NativeProgramError(f"{name} alphabet exceeds the field")
        if not 0 <= self.initial_state < self.declared_state_count:
            raise NativeProgramError("invalid native initial state")
        if not self.nodes:
            raise NativeProgramError("native program must contain nodes")
        for index, node in enumerate(self.nodes):
            if node.kind == "constant" and (
                node.value is None or not 0 <= node.value < self.modulus
            ):
                raise NativeProgramError("constant lies outside the field")
            if node.kind == "call" and any(argument >= index for argument in node.args):
                raise NativeProgramError("native DAG contains a forward reference")
        for root_name, root in (
            ("next_state_root", self.next_state_root),
            ("output_root", self.output_root),
        ):
            if isinstance(root, bool) or not isinstance(root, int) or not 0 <= root < len(
                self.nodes
            ):
                raise NativeProgramError(f"invalid {root_name}")
        if self.reachable_node_indices() != frozenset(range(len(self.nodes))):
            raise NativeProgramError("native program contains unreachable payload nodes")

    def reachable_node_indices(self) -> frozenset[int]:
        found: set[int] = set()
        pending = [self.next_state_root, self.output_root]
        while pending:
            index = pending.pop()
            if index in found:
                continue
            found.add(index)
            pending.extend(self.nodes[index].args)
        return frozenset(found)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "synthesis_method": self.synthesis_method,
            "machine_id": self.machine_id,
            "modulus": self.modulus,
            "discovery_digest": self.discovery_digest,
            "declared_state_count": self.declared_state_count,
            "input_alphabet": list(self.input_alphabet),
            "output_alphabet": list(self.output_alphabet),
            "initial_state": self.initial_state,
            "nodes": [node.to_dict() for node in self.nodes],
            "next_state_root": self.next_state_root,
            "output_root": self.output_root,
        }

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def digest(self) -> str:
        return hashlib.sha256(b"m043-q5-native-program-v1\x00" + self.to_bytes()).hexdigest()

    @staticmethod
    def from_bytes(payload: bytes | str) -> "NativeMealyProgram":
        try:
            raw = _require_mapping(json.loads(payload), "native program")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise NativeProgramError("native program is not valid JSON") from exc
        required = {
            "schema",
            "synthesis_method",
            "machine_id",
            "modulus",
            "discovery_digest",
            "declared_state_count",
            "input_alphabet",
            "output_alphabet",
            "initial_state",
            "nodes",
            "next_state_root",
            "output_root",
        }
        _exact_fields(raw, required, "native program")
        return NativeMealyProgram(
            schema=_require_string(raw["schema"], "schema"),
            synthesis_method=_require_string(
                raw["synthesis_method"], "synthesis_method"
            ),
            machine_id=_require_string(raw["machine_id"], "machine_id"),
            modulus=_require_int(raw["modulus"], "modulus", minimum=2),
            discovery_digest=_require_digest(
                raw["discovery_digest"], "discovery_digest"
            ),
            declared_state_count=_require_int(
                raw["declared_state_count"], "declared_state_count", minimum=1
            ),
            input_alphabet=tuple(
                _require_int(item, "input symbol")
                for item in _require_sequence(raw["input_alphabet"], "input_alphabet")
            ),
            output_alphabet=tuple(
                _require_int(item, "output symbol")
                for item in _require_sequence(raw["output_alphabet"], "output_alphabet")
            ),
            initial_state=_require_int(raw["initial_state"], "initial_state"),
            nodes=tuple(
                NativeNode.from_dict(item)
                for item in _require_sequence(raw["nodes"], "nodes")
            ),
            next_state_root=_require_int(
                raw["next_state_root"], "next_state_root"
            ),
            output_root=_require_int(raw["output_root"], "output_root"),
        )

    def used_opcodes(self) -> frozenset[str]:
        return frozenset(
            node.opcode
            for node in self.nodes
            if node.kind == "call" and node.opcode is not None
        )

    def _evaluate(
        self,
        machine: OpaqueFieldMachine,
        state: int,
        symbol: int,
    ) -> tuple[int, ...]:
        if machine.machine_id != self.machine_id or machine.modulus != self.modulus:
            raise NativeProgramError("native program targets another substrate")
        if not 0 <= state < self.modulus or not 0 <= symbol < self.modulus:
            raise NativeProgramError("native runtime input lies outside the field")
        values: list[int] = []
        for node in self.nodes:
            if node.kind == "state":
                values.append(state)
            elif node.kind == "symbol":
                values.append(symbol)
            elif node.kind == "constant":
                assert node.value is not None
                values.append(node.value)
            else:
                assert node.kind == "call" and node.opcode is not None
                values.append(
                    machine.execute(node.opcode, tuple(values[index] for index in node.args))
                )
        return tuple(values)

    def step(
        self,
        machine: OpaqueFieldMachine,
        state: int,
        symbol: int,
    ) -> tuple[int, int]:
        values = self._evaluate(machine, state, symbol)
        return values[self.next_state_root], values[self.output_root]

    def transduce(
        self,
        machine: OpaqueFieldMachine,
        word: Sequence[int],
    ) -> tuple[int, ...]:
        state = self.initial_state
        emitted: list[int] = []
        for symbol in word:
            state, output = self.step(machine, state, symbol)
            if not 0 <= state < self.declared_state_count:
                raise NativeProgramError("native execution escaped the declared state set")
            if output not in self.output_alphabet:
                raise NativeProgramError("native execution emitted an invalid symbol")
            emitted.append(output)
        return tuple(emitted)


class _DagBuilder:
    def __init__(self, discovery: DiscoveredFieldSubstrate) -> None:
        self.discovery = discovery
        self.nodes: list[NativeNode] = []
        self.memo: dict[tuple[object, ...], int] = {}
        self.state = self._node(("state",), NativeNode("state"))
        self.symbol = self._node(("symbol",), NativeNode("symbol"))
        self.zero = self.constant(0)
        self.one = self.constant(1)

    def _node(self, key: tuple[object, ...], node: NativeNode) -> int:
        if key in self.memo:
            return self.memo[key]
        index = len(self.nodes)
        self.nodes.append(node)
        self.memo[key] = index
        return index

    def constant(self, value: int) -> int:
        value %= self.discovery.modulus
        return self._node(("constant", value), NativeNode("constant", value=value))

    def call(self, role: str, *args: int) -> int:
        opcode = self.discovery.opcode_for(role)
        if role in {"add", "mul"} and len(args) == 2 and args[1] < args[0]:
            args = (args[1], args[0])
        return self._node(
            ("call", opcode, args), NativeNode("call", opcode=opcode, args=tuple(args))
        )

    def neg(self, value: int) -> int:
        if value == self.zero:
            return self.zero
        return self.call("neg", value)

    def add(self, left: int, right: int) -> int:
        if left == self.zero:
            return right
        if right == self.zero:
            return left
        return self.call("add", left, right)

    def mul(self, left: int, right: int) -> int:
        if left == self.zero or right == self.zero:
            return self.zero
        if left == self.one:
            return right
        if right == self.one:
            return left
        return self.call("mul", left, right)

    def sub_constant(self, value: int, constant: int) -> int:
        if constant % self.discovery.modulus == 0:
            return value
        return self.add(value, self.neg(self.constant(constant)))

    def power(self, value: int, exponent: int) -> int:
        if exponent == 0:
            return self.one
        result = self.one
        base = value
        remaining = exponent
        while remaining:
            if remaining & 1:
                result = self.mul(result, base)
            remaining >>= 1
            if remaining:
                base = self.mul(base, base)
        return result

    def indicator(self, value: int, expected: int) -> int:
        difference = self.sub_constant(value, expected)
        nonzero = self.power(difference, self.discovery.modulus - 1)
        return self.add(self.one, self.neg(nonzero))

    def interpolate(self, values: Sequence[tuple[int, int, int]]) -> int:
        total = self.zero
        state_basis = {
            state: self.indicator(self.state, state)
            for state in sorted({state for state, _, _ in values})
        }
        symbol_basis = {
            symbol: self.indicator(self.symbol, symbol)
            for symbol in sorted({symbol for _, symbol, _ in values})
        }
        for state, symbol, output in values:
            coefficient = self.constant(output)
            term = self.mul(
                coefficient,
                self.mul(state_basis[state], symbol_basis[symbol]),
            )
            total = self.add(total, term)
        return total


@dataclass(frozen=True)
class NativeSynthesisCertificate:
    source_body_digest: str
    source_behaviour_digest: str
    native_program_digest: str
    discovery_digest: str
    exact_pair_count: int
    pairwise_exact: bool
    behavioural_equivalence: bool
    distinguishing_word: tuple[int, ...] | None
    forbidden_table_keys_absent: bool
    source_body_bytes_embedded: bool
    all_nodes_reachable: bool
    maximum_call_arity: int
    synthesis_method: str = SYNTHESIS_METHOD

    def __post_init__(self) -> None:
        for field_name, value in (
            ("source_body_digest", self.source_body_digest),
            ("source_behaviour_digest", self.source_behaviour_digest),
            ("native_program_digest", self.native_program_digest),
            ("discovery_digest", self.discovery_digest),
        ):
            _require_digest(value, field_name)
        _require_int(self.exact_pair_count, "exact_pair_count", minimum=1)
        _require_int(self.maximum_call_arity, "maximum_call_arity")
        if self.synthesis_method != SYNTHESIS_METHOD:
            raise NativeProgramError("unsupported certificate synthesis method")
        if self.distinguishing_word is not None:
            for symbol in self.distinguishing_word:
                _require_int(symbol, "distinguishing word symbol")

    def to_dict(self) -> dict[str, object]:
        return {
            "source_body_digest": self.source_body_digest,
            "source_behaviour_digest": self.source_behaviour_digest,
            "native_program_digest": self.native_program_digest,
            "discovery_digest": self.discovery_digest,
            "exact_pair_count": self.exact_pair_count,
            "pairwise_exact": self.pairwise_exact,
            "behavioural_equivalence": self.behavioural_equivalence,
            "distinguishing_word": (
                None if self.distinguishing_word is None else list(self.distinguishing_word)
            ),
            "forbidden_table_keys_absent": self.forbidden_table_keys_absent,
            "source_body_bytes_embedded": self.source_body_bytes_embedded,
            "all_nodes_reachable": self.all_nodes_reachable,
            "maximum_call_arity": self.maximum_call_arity,
            "synthesis_method": self.synthesis_method,
        }

    def digest(self) -> str:
        return _digest(b"m043-q5-native-certificate-v1\x00", self.to_dict())

    @staticmethod
    def from_dict(value: object) -> "NativeSynthesisCertificate":
        raw = _require_mapping(value, "native synthesis certificate")
        required = {
            "source_body_digest",
            "source_behaviour_digest",
            "native_program_digest",
            "discovery_digest",
            "exact_pair_count",
            "pairwise_exact",
            "behavioural_equivalence",
            "distinguishing_word",
            "forbidden_table_keys_absent",
            "source_body_bytes_embedded",
            "all_nodes_reachable",
            "maximum_call_arity",
            "synthesis_method",
        }
        _exact_fields(raw, required, "native synthesis certificate")
        raw_word = raw["distinguishing_word"]
        word = (
            None
            if raw_word is None
            else tuple(
                _require_int(item, "distinguishing word symbol")
                for item in _require_sequence(raw_word, "distinguishing_word")
            )
        )
        booleans = {}
        for field in (
            "pairwise_exact",
            "behavioural_equivalence",
            "forbidden_table_keys_absent",
            "source_body_bytes_embedded",
            "all_nodes_reachable",
        ):
            if not isinstance(raw[field], bool):
                raise NativeProgramError(f"{field} must be a boolean")
            booleans[field] = raw[field]
        return NativeSynthesisCertificate(
            source_body_digest=_require_digest(
                raw["source_body_digest"], "source_body_digest"
            ),
            source_behaviour_digest=_require_digest(
                raw["source_behaviour_digest"], "source_behaviour_digest"
            ),
            native_program_digest=_require_digest(
                raw["native_program_digest"], "native_program_digest"
            ),
            discovery_digest=_require_digest(
                raw["discovery_digest"], "discovery_digest"
            ),
            exact_pair_count=_require_int(
                raw["exact_pair_count"], "exact_pair_count", minimum=1
            ),
            pairwise_exact=booleans["pairwise_exact"],
            behavioural_equivalence=booleans["behavioural_equivalence"],
            distinguishing_word=word,
            forbidden_table_keys_absent=booleans[
                "forbidden_table_keys_absent"
            ],
            source_body_bytes_embedded=booleans[
                "source_body_bytes_embedded"
            ],
            all_nodes_reachable=booleans["all_nodes_reachable"],
            maximum_call_arity=_require_int(
                raw["maximum_call_arity"], "maximum_call_arity"
            ),
            synthesis_method=_require_string(
                raw["synthesis_method"], "synthesis_method"
            ),
        )

    @property
    def exact(self) -> bool:
        return (
            self.pairwise_exact
            and self.behavioural_equivalence
            and self.distinguishing_word is None
            and self.forbidden_table_keys_absent
            and not self.source_body_bytes_embedded
            and self.all_nodes_reachable
            and self.maximum_call_arity <= 2
        )


def audit_program_against_discovery(
    program: NativeMealyProgram,
    discovery: DiscoveredFieldSubstrate,
) -> None:
    if program.machine_id != discovery.machine_id:
        raise NativeProgramError("program and discovery machine identities differ")
    if program.modulus != discovery.modulus:
        raise NativeProgramError("program and discovery moduli differ")
    if program.discovery_digest != discovery.digest():
        raise NativeProgramError("program is bound to another discovery record")
    descriptors = {item.opcode: item for item in discovery.opcodes if item.stable}
    core = {discovery.opcode_for(role) for role in ("add", "mul", "neg")}
    if not program.used_opcodes() <= core:
        raise NativeProgramError("program uses non-core or undiscovered opcodes")
    for node in program.nodes:
        if node.kind != "call":
            continue
        assert node.opcode is not None
        if node.opcode not in descriptors:
            raise NativeProgramError("program uses an unknown opcode")
        if descriptors[node.opcode].arity != len(node.args):
            raise NativeProgramError("program call arity differs from discovery")


def native_program_to_mealy(
    program: NativeMealyProgram,
    machine: OpaqueFieldMachine,
) -> MealyMachine:
    transitions: list[tuple[int, ...]] = []
    outputs: list[tuple[int, ...]] = []
    for state in range(program.declared_state_count):
        transition_row: list[int] = []
        output_row: list[int] = []
        for symbol in program.input_alphabet:
            target, emitted = program.step(machine, state, symbol)
            if not 0 <= target < program.declared_state_count:
                raise NativeProgramError("native program leaves the declared state set")
            if emitted not in program.output_alphabet:
                raise NativeProgramError("native program emits outside its alphabet")
            transition_row.append(target)
            output_row.append(emitted)
        transitions.append(tuple(transition_row))
        outputs.append(tuple(output_row))
    return MealyMachine(
        input_alphabet=program.input_alphabet,
        output_alphabet=program.output_alphabet,
        transitions=tuple(transitions),
        outputs=tuple(outputs),
        initial=program.initial_state,
    )


def _contains_forbidden_table_key(value: object) -> bool:
    if isinstance(value, Mapping):
        if any(key in FORBIDDEN_TABLE_KEYS for key in value):
            return True
        return any(_contains_forbidden_table_key(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_forbidden_table_key(item) for item in value)
    return False


def _prune_nodes(
    nodes: Sequence[NativeNode],
    roots: tuple[int, int],
) -> tuple[tuple[NativeNode, ...], tuple[int, int]]:
    reachable: set[int] = set()
    pending = list(roots)
    while pending:
        index = pending.pop()
        if index in reachable:
            continue
        reachable.add(index)
        pending.extend(nodes[index].args)
    order = sorted(reachable)
    remap = {old: new for new, old in enumerate(order)}
    pruned = tuple(
        NativeNode(
            kind=nodes[old].kind,
            value=nodes[old].value,
            opcode=nodes[old].opcode,
            args=tuple(remap[arg] for arg in nodes[old].args),
        )
        for old in order
    )
    return pruned, (remap[roots[0]], remap[roots[1]])


def synthesize_native_mealy(
    source: MealyMachine,
    discovery: DiscoveredFieldSubstrate,
    machine: OpaqueFieldMachine,
) -> tuple[NativeMealyProgram, NativeSynthesisCertificate]:
    if source.n_states > discovery.modulus:
        raise NativeProgramError("source state count exceeds the discovered field")
    if any(symbol >= discovery.modulus or symbol < 0 for symbol in source.input_alphabet):
        raise NativeProgramError("source input alphabet exceeds the discovered field")
    if any(symbol >= discovery.modulus or symbol < 0 for symbol in source.output_alphabet):
        raise NativeProgramError("source output alphabet exceeds the discovered field")
    if machine.machine_id != discovery.machine_id:
        raise NativeProgramError("synthesis machine differs from discovery")

    builder = _DagBuilder(discovery)
    transition_values = [
        (state, symbol, source.transitions[state][symbol_index])
        for state in range(source.n_states)
        for symbol_index, symbol in enumerate(source.input_alphabet)
    ]
    output_values = [
        (state, symbol, source.outputs[state][symbol_index])
        for state in range(source.n_states)
        for symbol_index, symbol in enumerate(source.input_alphabet)
    ]
    next_state_root = builder.interpolate(transition_values)
    output_root = builder.interpolate(output_values)
    nodes, roots = _prune_nodes(
        builder.nodes, (next_state_root, output_root)
    )
    next_state_root, output_root = roots
    program = NativeMealyProgram(
        machine_id=discovery.machine_id,
        modulus=discovery.modulus,
        discovery_digest=discovery.digest(),
        declared_state_count=source.n_states,
        input_alphabet=source.input_alphabet,
        output_alphabet=source.output_alphabet,
        initial_state=source.initial,
        nodes=nodes,
        next_state_root=next_state_root,
        output_root=output_root,
    )
    audit_program_against_discovery(program, discovery)
    reconstructed = native_program_to_mealy(program, machine)
    equivalent, witness = exact_mealy_equivalence(source, reconstructed)
    pairwise = source == reconstructed
    mapping = program.to_dict()
    maximum_arity = max(
        (len(node.args) for node in program.nodes if node.kind == "call"),
        default=0,
    )
    certificate = NativeSynthesisCertificate(
        source_body_digest=exact_body_digest(source),
        source_behaviour_digest=mealy_digest(source, minimise=True),
        native_program_digest=program.digest(),
        discovery_digest=discovery.digest(),
        exact_pair_count=source.n_states * len(source.input_alphabet),
        pairwise_exact=pairwise,
        behavioural_equivalence=equivalent,
        distinguishing_word=witness,
        forbidden_table_keys_absent=not _contains_forbidden_table_key(mapping),
        source_body_bytes_embedded=exact_body_bytes(source) in program.to_bytes(),
        all_nodes_reachable=(
            program.reachable_node_indices() == frozenset(range(len(program.nodes)))
        ),
        maximum_call_arity=maximum_arity,
    )
    if not certificate.exact:
        raise NativeProgramError("native synthesis failed its exact certificate")
    return program, certificate
