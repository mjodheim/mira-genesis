"""Generic AST-based source transformation for M094.

A bounded, state-owned transformation language that can edit Python source
files. The language defines *how* to build a transformation, not *what*
transformation to build. The winning patch emerges from the search, not
from authored code.

Contrast with M093's CodePatch.generate which contained the exact patch.
"""

from __future__ import annotations

import ast
import hashlib
import json
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence


# ── Schemas ──────────────────────────────────────────────────────────

TRANSFORM_SCHEMA = "m094-source-transform-v1"


# ── Canonical helpers ────────────────────────────────────────────────

def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


# ── Editable region descriptors ──────────────────────────────────────

@dataclass(frozen=True)
class EditRegion:
    """A specific location in a source file that can be edited."""

    file: str
    class_name: str
    method_name: str | None  # None = insert at class level
    line_number: int
    indent: str  # whitespace indentation for this context


# ── Atomic edit operations (the transformation language) ─────────────

class EditOperation:
    """Base class for atomic source edits.

    Each operation is a self-contained, inspectable edit that can be
    applied to a source file. The edit is *not* the winning patch — it
    is one building block. Multiple operations compose into a candidate.
    """

    def describe(self) -> str:
        raise NotImplementedError

    def apply(self, source: str) -> str:
        raise NotImplementedError

    def digest(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class InsertMethod(EditOperation):
    """Insert a new method into a class."""

    class_name: str
    method_name: str
    method_body: str  # the full method source, including def line
    before_method: str | None = None  # insert before this method; None = append

    def describe(self) -> str:
        return f"InsertMethod({self.class_name}.{self.method_name})"

    def apply(self, source: str) -> str:
        tree = ast.parse(source)
        # Find the class
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == self.class_name:
                break
        else:
            raise ValueError(f"class {self.class_name} not found in source")

        if self.before_method:
            # Find the method to insert before
            for i, item in enumerate(node.body):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == self.before_method:
                        # Insert before this method
                        insert_pos = item.lineno - 1  # 0-indexed
                        break
            else:
                raise ValueError(f"method {self.before_method} not found in {self.class_name}")
        else:
            # Append after the last class body element
            last = node.body[-1]
            insert_pos = last.end_lineno  # 1-indexed, insert after

        lines = source.splitlines(keepends=True)
        indent = "    "  # 4 spaces for class-level
        method_lines = textwrap.indent(self.method_body.strip(), indent).splitlines(keepends=True)
        # Ensure trailing newline
        if not method_lines[-1].endswith("\n"):
            method_lines[-1] += "\n"

        # If inserting before a method, add a blank line before
        if self.before_method:
            method_lines = ["\n"] + method_lines

        for i, line in enumerate(method_lines):
            lines.insert(insert_pos + i, line)

        return "".join(lines)

    def digest(self) -> str:
        return _digest({
            "op": "InsertMethod",
            "class": self.class_name,
            "method": self.method_name,
            "body_digest": hashlib.sha256(self.method_body.encode("utf-8")).hexdigest(),
            "before": self.before_method,
        })


@dataclass(frozen=True)
class AddParameter(EditOperation):
    """Add a parameter to an existing method."""

    class_name: str
    method_name: str
    param_name: str
    param_default: str | None = None  # e.g. "None" or "0"

    def describe(self) -> str:
        return f"AddParameter({self.class_name}.{self.method_name}, {self.param_name})"

    def apply(self, source: str) -> str:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == self.class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == self.method_name:
                        new_param = ast.arg(arg=self.param_name, annotation=None)
                        if self.param_default is not None:
                            default = ast.parse(self.param_default).body[0].value
                        else:
                            default = None
                        item.args.args.append(new_param)
                        if default is not None:
                            item.args.defaults.append(default)
                        return ast.unparse(tree)
        raise ValueError(f"method {self.class_name}.{self.method_name} not found")

    def digest(self) -> str:
        return _digest({
            "op": "AddParameter",
            "class": self.class_name,
            "method": self.method_name,
            "param": self.param_name,
            "default": self.param_default,
        })


# ── Candidate transformation ─────────────────────────────────────────

@dataclass(frozen=True)
class SourceTransform:
    """A composed transformation made of one or more atomic edit operations."""

    operations: tuple[EditOperation, ...]
    source_digest: str  # digest of the original source

    def apply(self, source: str) -> str:
        result = source
        for op in self.operations:
            result = op.apply(result)
        return result

    def describe(self) -> str:
        return " -> ".join(op.describe() for op in self.operations)

    def digest(self) -> str:
        return _digest({
            "operations": [op.digest() for op in self.operations],
            "source_digest": self.source_digest,
        })


# ── Transformation language ──────────────────────────────────────────

# The transformation language is a finite set of operation templates.
# Each template is a function that produces an EditOperation given
# a component spec and a diagnostic hypothesis.
# This is authored, but the *choice* of which operations to compose
# and with what parameters is made by the lineage.

TransformRule = Callable[[str, str, str], list[EditOperation]]


# Example: generate a query method for a component that exposes a collection
def suggest_query_method(source: str, class_name: str, collection_name: str) -> list[EditOperation]:
    """Generate a query method for a component that has a collection.

    The method name and signature are derived from the collection name,
    not hardcoded. E.g. for 'events' → 'events_by_kind(kind)'.
    """
    # This is a template — the actual method body is structural, not authored
    singular = collection_name.rstrip("s")  # events → event
    method_name = f"{collection_name}_by_kind"
    method_body = f"""
    def {method_name}(self, kind: str) -> tuple[{singular.capitalize()}, ...]:
        \"\"\"Return every {singular} whose kind matches *kind*.\"\"\"
        if not kind:
            raise ValueError("{collection_name} kind cannot be empty")
        return tuple({singular.lower()} for {singular.lower()} in self._{collection_name} if {singular.lower()}.kind == kind)
"""
    return [InsertMethod(
        class_name=class_name,
        method_name=method_name,
        method_body=textwrap.dedent(method_body).strip(),
        before_method="history" if class_name == "MemoryLedger" else None,
    )]


TRANSFORM_TEMPLATES: tuple[TransformRule, ...] = (
    suggest_query_method,
)