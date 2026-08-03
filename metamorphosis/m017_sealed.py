"""M017 sealed evaluation specification.

Section 8.3 of the frozen protocol requires that sealed environments be generated only
from a nonce derived from the immutable head SHA, and therefore only after that head
exists. This is stricter than M012b, M013e and M014b, which draw a random runtime nonce:
a head-derived nonce is reproducible from the commit alone, and it cannot be computed
before the commit it is bound to.

Nothing here observes an environment. It derives seeds, and the laboratory turns those
seeds into environments at evaluation time.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

# Established by the development bench and unchanged at freeze:
# `scripts/run_m017_dispersion.py` uses 14 episodes and takes the late window as the
# second half, from index 7. The decisive comparison of §2 is measured on that window.
EPISODES_PER_ENVIRONMENT = 14
LATE_EPISODE_FROM = EPISODES_PER_ENVIRONMENT // 2

# The one §2 parameter the candidate protocol left unfixed. Development established the
# directional criterion on a fifty-environment sweep, after eight environments proved to
# be an optimistic sample by a factor of ten. Fifty is retained because it is the count at
# which the criterion was set, and because the criterion must hold in *every* environment:
# a larger count is strictly harder to pass, never easier. It requires a human signature
# before hashing, exactly like the thresholds it belongs to.
SEALED_ENVIRONMENTS = 50

_HEAD_SHA = re.compile(r"\A[0-9a-f]{40}\Z")


def head_nonce(head_sha: str) -> str:
    """Derive the master nonce from the immutable head SHA.

    Rejects anything that is not a full lowercase 40-hex commit id, so an abbreviated or
    mistyped head cannot silently produce a different, unreproducible environment set.
    """

    candidate = head_sha.strip().lower()
    if not _HEAD_SHA.match(candidate):
        raise ValueError(
            "M017 sealed evaluation requires a full 40-character lowercase head SHA"
        )
    return hashlib.sha256(f"m017:head:{candidate}".encode("utf-8")).hexdigest()


def derive_seed(master_nonce: str, label: str, index: int) -> int:
    raw = f"m017:{master_nonce}:{label}:{index}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


@dataclass(frozen=True)
class SealedSpec:
    head_sha: str
    master_nonce: str
    environment_seeds: tuple[int, ...]
    episode_seeds: tuple[int, ...]
    negative_seeds: tuple[int, ...]
    episodes_per_environment: int
    late_episode_from: int

    @property
    def environment_count(self) -> int:
        return len(self.environment_seeds)

    def digest(self) -> str:
        payload = ":".join(
            [
                "m017-sealed-spec/1",
                self.head_sha,
                self.master_nonce,
                ",".join(str(s) for s in self.environment_seeds),
                ",".join(str(s) for s in self.episode_seeds),
                ",".join(str(s) for s in self.negative_seeds),
                str(self.episodes_per_environment),
                str(self.late_episode_from),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sealed_spec(
    head_sha: str,
    *,
    environments: int = SEALED_ENVIRONMENTS,
) -> SealedSpec:
    """Derive the complete sealed specification from an immutable head."""

    if environments < 1:
        raise ValueError("a sealed evaluation needs at least one environment")
    master_nonce = head_nonce(head_sha)
    return SealedSpec(
        head_sha=head_sha.strip().lower(),
        master_nonce=master_nonce,
        environment_seeds=tuple(
            derive_seed(master_nonce, "environment", index)
            for index in range(environments)
        ),
        episode_seeds=tuple(
            derive_seed(master_nonce, "episode", index) for index in range(environments)
        ),
        negative_seeds=tuple(
            derive_seed(master_nonce, "negative", index) for index in range(environments)
        ),
        episodes_per_environment=EPISODES_PER_ENVIRONMENT,
        late_episode_from=LATE_EPISODE_FROM,
    )
