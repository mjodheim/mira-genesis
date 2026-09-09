"""Opaque handles for capabilities a lineage discovered, and a record of what it actually used.

`Substrate.discovered` returned raw Python callables. A callable is not a capability: it carries its
defining environment with it. The development substrate's `read` operation exposed
`SUBSTRATE_OPERATIONS` through `__globals__`, so a translator handed `read` could reach `list` — an
operation nobody ever probed for, and therefore one the lineage never discovered. Discovery costs
budget precisely so that knowing what a substrate can do is earned; a free reference to the whole
registry gives it away.

Two things happen here:

* the callable is rebound onto an empty global namespace, so the module registry that defined it is
  no longer reachable through the handle;
* every invocation is counted, so the migration record can say which capabilities the translation
  *used* rather than which ones it *declared*.

**What this does not do, stated rather than implied.** This is one process. A determined translator
can still walk `type(handle)` and reach whatever that class can reach, and an operation that closes
over module state will raise `NameError` here rather than run with ambient authority — which is a
loud failure and not a silent one, but it is a failure. Real isolation needs the process boundary
that candidate execution crosses and translation does not. What this closes is the accidental
aperture and the caller-authored use declaration; it is not a sandbox.
"""
from __future__ import annotations

import types
from typing import Any, Callable, Mapping, Sequence


class CapabilityError(RuntimeError):
    """Raised when something reaches for a capability the lineage never discovered."""


def _severed(operation: Callable[..., Any]) -> Callable[..., Any]:
    """The same code with its module globals removed, where the object allows that.

    Builtins are kept: without them almost nothing runs. Everything else the defining module held —
    including the registry of operations the lineage has not discovered — is gone.
    """
    code = getattr(operation, "__code__", None)
    if code is None:  # pragma: no cover - builtins and C callables
        return operation
    return types.FunctionType(
        code,
        {"__builtins__": __builtins__},
        getattr(operation, "__name__", "capability"),
        getattr(operation, "__defaults__", None),
        getattr(operation, "__closure__", None),
    )


class Capability:
    """One discovered operation, invocable and otherwise opaque."""

    __slots__ = ("_name", "_call", "_uses")

    def __init__(self, name: str, operation: Callable[..., Any]) -> None:
        object.__setattr__(self, "_name", str(name))
        object.__setattr__(self, "_call", _severed(operation))
        object.__setattr__(self, "_uses", [0])

    def __call__(self, *arguments: Any, **keywords: Any) -> Any:
        self._uses[0] += 1
        return self._call(*arguments, **keywords)

    @property
    def name(self) -> str:
        return self._name

    @property
    def uses(self) -> int:
        return self._uses[0]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<capability %r>" % self._name


class CapabilitySet(Mapping):
    """What a translation may reach: the discovered capabilities, and nothing beside them."""

    def __init__(self, operations: Mapping[str, Callable[..., Any]]) -> None:
        self._handles = {str(name): Capability(name, call) for name, call in operations.items()}

    def __getitem__(self, name: str) -> Capability:
        try:
            return self._handles[str(name)]
        except KeyError:
            raise CapabilityError(
                "this lineage never discovered a capability called %r" % (name,)
            ) from None

    def __iter__(self):
        return iter(self._handles)

    def __len__(self) -> int:
        return len(self._handles)

    def used(self) -> list[str]:
        """Which capabilities were actually invoked, derived rather than declared."""
        return sorted(name for name, handle in self._handles.items() if handle.uses)

    def use_counts(self) -> dict[str, int]:
        return {name: handle.uses for name, handle in sorted(self._handles.items())}


def undeclared_use(declared: Sequence[str], used: Sequence[str]) -> dict[str, list[str]]:
    """The difference between what a translation said it used and what it did.

    Both directions matter. Reaching a capability the declaration omits is the lineage using
    something nobody recorded; declaring one it never touched makes the record claim a dependency the
    run does not show.
    """
    declared_set, used_set = {str(name) for name in declared}, {str(name) for name in used}
    return {
        "used_but_not_declared": sorted(used_set - declared_set),
        "declared_but_not_used": sorted(declared_set - used_set),
    }
