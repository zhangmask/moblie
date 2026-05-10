from __future__ import annotations

from backend.cloud.registry import ProviderRegistry


_LEGACY_REGISTRY = ProviderRegistry()


def register_provider(name: str):
    def decorator(provider_cls):
        _LEGACY_REGISTRY.register(name, provider_cls())
        return provider_cls

    return decorator


def get_provider(name: str):
    return _LEGACY_REGISTRY.get(name)


def list_providers() -> list[str]:
    return _LEGACY_REGISTRY.list_names()
