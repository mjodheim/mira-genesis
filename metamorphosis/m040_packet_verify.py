"""External anchoring for M040 transport-packet rehydration."""

from __future__ import annotations

import hashlib
import re

from .m040_packet import M040PacketError, M040TransportPacket

_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")


def rehydrate_packet(raw: str, *, expected_sha256: str) -> M040TransportPacket:
    """Verify the externally committed packet digest before parsing its contents."""

    if not _SHA256.match(expected_sha256):
        raise M040PacketError("expected packet digest must be canonical SHA-256 hexadecimal")
    actual = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if actual != expected_sha256:
        raise M040PacketError("transport packet differs from the externally committed digest")
    packet = M040TransportPacket.from_json(raw)
    if packet.sha256() != expected_sha256:
        raise M040PacketError("rehydrated packet digest differs from the external anchor")
    return packet
