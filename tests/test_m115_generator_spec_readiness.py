from metamorphosis import m115_carrier_bank as bank
from metamorphosis import m115_route_selection as route_selection


def test_generator_spec_candidate_builds_from_preserved_blob_provenance():
    spec = bank.build_generator_spec_candidate()

    assert spec["schema"] == bank.GENERATOR_SPEC_SCHEMA
    assert spec["milestone"] == "M115"
    assert spec["provider_selection"]["selected"] == "Alibaba"
    assert spec["provider_selection"]["matrix_git_blob"] == route_selection.PRESERVED_MATRIX_BLOB
    assert spec["provider_selection"]["matrix_commit"] is None
    assert spec["runtime_identity_attestation"]["requested_alias"] == route_selection.REQUESTED_MODEL
    assert (
        spec["runtime_identity_attestation"]["required_checkpoint"]
        == route_selection.CANONICAL_CHECKPOINT
    )
    assert spec["canonical_request_body"]["provider"] == {
        "allow_fallbacks": False,
        "only": ["Alibaba"],
        "require_parameters": True,
    }
