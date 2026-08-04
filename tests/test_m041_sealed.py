from __future__ import annotations

import pytest

from metamorphosis.m041_sealed import derive_seed, head_nonce, sealed_spec

HEAD = "1" * 40
PARENT = "2" * 40
PROTOCOL = "3" * 64


def test_sealed_spec_is_deterministic_and_head_bound():
    first = sealed_spec(HEAD, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)
    second = sealed_spec(HEAD, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)
    changed = sealed_spec("4" * 40, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)

    assert first == second
    assert first.digest() == second.digest()
    assert first.completion_seed == derive_seed(first.master_nonce, "completion", 0)
    assert first.master_nonce == head_nonce(HEAD, PROTOCOL)
    assert first.completion_seed != changed.completion_seed


def test_protocol_identity_changes_the_completion_seed():
    first = sealed_spec(HEAD, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)
    changed = sealed_spec(HEAD, frozen_parent_sha=PARENT, protocol_sha256="5" * 64)

    assert first.master_nonce != changed.master_nonce
    assert first.completion_seed != changed.completion_seed


@pytest.mark.parametrize(
    "head,parent,protocol",
    [
        ("1" * 39, PARENT, PROTOCOL),
        (HEAD.upper(), PARENT, PROTOCOL),
        (HEAD, "2" * 39, PROTOCOL),
        (HEAD, PARENT, "3" * 63),
        (HEAD, PARENT, PROTOCOL.upper()),
        (HEAD, HEAD, PROTOCOL),
    ],
)
def test_sealed_spec_rejects_noncanonical_identities(head, parent, protocol):
    with pytest.raises(ValueError):
        sealed_spec(head, frozen_parent_sha=parent, protocol_sha256=protocol)


def test_seed_labels_and_indexes_are_closed():
    nonce = head_nonce(HEAD, PROTOCOL)

    with pytest.raises(ValueError):
        derive_seed(nonce, "", 0)
    with pytest.raises(ValueError):
        derive_seed(nonce, "bad:label", 0)
    with pytest.raises(ValueError):
        derive_seed(nonce, "completion", -1)
