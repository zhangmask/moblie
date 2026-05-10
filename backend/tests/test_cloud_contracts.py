from __future__ import annotations

from backend.cloud.contracts.instance import InstanceSpec
from backend.models.schemas import InstanceCreateRequest


def test_instance_spec_uses_generic_fields() -> None:
    spec = InstanceSpec(
        image_ref="img-demo",
        instance_type="standard.small",
        network_ref="private-a",
        security_groups=["default"],
    )
    assert spec.image_ref == "img-demo"
    assert spec.network_ref == "private-a"


def test_instance_request_accepts_legacy_aliases() -> None:
    payload = InstanceCreateRequest(
        job_pubkey="job-1",
        provider="demo",
        image_id="img-legacy",
        owner_wallet="wallet-a",
        agent_wallet="wallet-b",
        security_group_ids=["sg-default"],
        subnet_id="subnet-legacy",
    )
    assert payload.provider_name == "demo"
    assert payload.image_ref == "img-legacy"
    assert payload.network_ref == "subnet-legacy"
    assert payload.security_groups == ["sg-default"]
