# M097 — endogenous operation acquisition on real Python source

M096 proved that the fixed inherited operation set can compose safely when mapping outputs use
closed exact contracts. It did not change that operation set. M097 attacks that next ceiling.

## The gap

Every inherited mapping item reads exactly one `self` field, possibly under a unary `list`/`tuple`
wrapper or a zero-argument renderer call. Naming a method and selecting a return shape introduce no
value expression, and composing more independent items never combines them. Therefore the inherited
language cannot emit `ast.BinOp` at any depth.

The development caller demands one exact mapping value computed as `upper - lower`. This is not a
search-budget failure: the required AST constructor lies outside the inherited constructive image.

## Acquisition rather than delivery

The extension substrate contains seven stack micro-instructions and a length-four bound. It contains
no completed “include a difference” operation and no class, field, key or qualification identifier.
The lineage exhausts all 2,800 programs, and a separate validator tests well-formed candidates on
public behavior. It adopts the shortest accepted construction, breaking semantic ties by content
digest, and registers only the resulting symbolic definition.

A fixed generic interpreter later parameterizes that definition with field and key roles recovered
from each observed demand. Until registration, the definition is not offered to repair search.

## Qualification and controls

Four new real-Python value-object worlds vary names, field order, arity, scalar type and narrative.
Before freeze, the apparatus may only construct and parse them and recover their unambiguous binary
demands. It may not acquire, register, run an extended search or execute a candidate.

Qualification requires 0/4 for the inherited language and 4/4 for the restored extended registry.
The same-language more-budget control is closed by the structural invariant, and the
built-but-unregistered control must remain unreachable. The inherited operation digest must be
conserved through serialization.

## Boundary

Only the extension definition and inherited digest are serialized lineage state; the generic AST
interpreter remains authored host code. This is not full language self-hosting. Serialization is
tested in-process here; complete process death, absence of acquisition/development modules and
faulted restart are M098's separate claim.
