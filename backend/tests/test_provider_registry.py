from __future__ import annotations

import pytest

from backend.cloud.contracts.file_transfer import FileTransferPort
from backend.cloud.demo_provider import DemoCloudProvider
from backend.cloud.registry import ProviderRegistry


def test_registry_registers_provider_by_name() -> None:
    registry = ProviderRegistry()
    provider = DemoCloudProvider()
    registry.register("demo", provider)
    assert registry.get("demo") is provider


def test_registry_raises_clear_error_for_missing_capability() -> None:
    registry = ProviderRegistry()
    registry.register("fake", object())
    with pytest.raises(TypeError, match="FileTransferPort"):
        registry.require_capability("fake", FileTransferPort)
