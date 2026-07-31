from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "bundle"
MANIFEST = BUNDLE / "manifest.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if target != destination and destination not in target.parents:
            raise RuntimeError(f"Unsafe archive member: {member.name}")
    archive.extractall(destination)


def main() -> None:
    if not MANIFEST.exists():
        print("No bundle manifest; nothing to unpack.")
        return

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    parts = [BUNDLE / name for name in manifest["parts"]]
    missing = [str(path) for path in parts if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing bundle parts: {missing}")

    encoded = b"".join(path.read_bytes() for path in parts)
    if sha256(encoded) != manifest["base64_sha256"]:
        raise RuntimeError("Base64 bundle checksum mismatch")

    compressed = base64.b64decode(encoded, validate=True)
    if sha256(compressed) != manifest["tar_gz_sha256"]:
        raise RuntimeError("Tar archive checksum mismatch")

    with tempfile.NamedTemporaryFile(suffix=".tar.gz") as handle:
        handle.write(compressed)
        handle.flush()
        with tarfile.open(handle.name, "r:gz") as archive:
            safe_extract(archive, ROOT)

    shutil.rmtree(BUNDLE)
    print("Canonical Mira Genesis repository expanded successfully.")


if __name__ == "__main__":
    main()
