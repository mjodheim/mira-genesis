"""An append-only, content-addressed store for artifacts the lineage produced rather than received.

Restore has always authenticated the body it was handed: the checkpoint names an artifact digest and
refuses anything else. That is sufficient exactly while every body is an importable fixture the host
can hand back, and it stops being sufficient the moment a lineage generates one. Nobody can pass
`Genesis.restore` a body that only ever existed as bytes this lineage wrote.

So generated artifacts are written where they can be found again by the only name they have. The
store is content-addressed and append-only: a digest resolves to one set of bytes forever, and
writing the same artifact twice is not a change. There is no update, no delete and no name that
could come to mean something else — the properties a lineage's own history needs from anything
holding its bodies.

Importable fixtures are deliberately **not** stored. Their behaviour lives in a module on disk, so
storing a descriptor of them would record a pointer while implying a copy, and this file exists to
stop that particular confusion rather than to add a second version of it.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

STORE_SCHEMA = "genesis-artifact-store-v1"


class StoreError(RuntimeError):
    """Raised when an artifact cannot be stored, or comes back as something other than it went in."""


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class ArtifactStore:
    """Bytes in, the same bytes out, addressed by their own digest."""

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    # -- writing ---------------------------------------------------------------------------
    def put_bytes(self, raw: bytes) -> str:
        """Write one artifact and return its digest. Writing it again changes nothing."""
        if not isinstance(raw, (bytes, bytearray)):
            raise StoreError("an artifact is stored as bytes")
        raw = bytes(raw)
        digest = _digest(raw)
        path = self.path_for(digest)
        if path.exists():
            # Append-only means a digest keeps its bytes. If a file under this name disagrees with
            # its own name, something other than this store wrote it, and that is not a collision to
            # resolve quietly.
            if path.read_bytes() != raw:
                raise StoreError(
                    "the store already holds different bytes under %s; a content-addressed name "
                    "cannot come to mean something else" % digest[:16]
                )
            return digest
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".partial")
        temporary.write_bytes(raw)
        temporary.replace(path)
        return digest

    def put(self, artifact: Any) -> str:
        """Store an artifact that publishes exact bytes, or refuse to imply that it did."""
        if not hasattr(artifact, "exact_artifact_bytes"):
            raise StoreError(
                "only an artifact whose bytes are its behaviour can be stored; an importable "
                "symbol would be recorded as a pointer while reading as a copy"
            )
        return self.put_bytes(artifact.exact_artifact_bytes())

    # -- reading ---------------------------------------------------------------------------
    def path_for(self, digest: str) -> Path:
        clean = str(digest)
        if len(clean) != 64 or any(character not in "0123456789abcdef" for character in clean):
            raise StoreError("%r is not an artifact digest" % (digest,))
        return self.directory / clean[:2] / ("%s.json" % clean)

    def holds(self, digest: str) -> bool:
        return self.path_for(digest).exists()

    def get_bytes(self, digest: str) -> bytes:
        """Read one artifact back, and check it is the artifact that was asked for."""
        path = self.path_for(digest)
        if not path.exists():
            raise StoreError(
                "the store does not hold %s; a lineage cannot resume a body nobody kept"
                % str(digest)[:16]
            )
        raw = path.read_bytes()
        if _digest(raw) != str(digest):
            raise StoreError(
                "the bytes stored under %s are not those bytes" % str(digest)[:16]
            )
        return raw

    def get_program(self, digest: str) -> Any:
        """Rebuild a generated body from the store, or fail closed."""
        from genesis.program import ProgramArtifact, canonical_bytes
        import json

        raw = self.get_bytes(digest)
        value = json.loads(raw.decode("utf-8"))
        artifact = ProgramArtifact(value=value)
        if canonical_bytes(artifact.value) != raw:
            raise StoreError(
                "the stored program does not canonicalise to the bytes it was stored under"
            )
        return artifact

    def record(self) -> dict[str, Any]:
        return {"schema": STORE_SCHEMA, "directory": self.directory.name}
