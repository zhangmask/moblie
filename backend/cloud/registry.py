from __future__ import annotations

from typing import Any


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, object] = {}

    def register(self, name: str, provider: object) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> object:
        provider = self._providers.get(name)
        if provider is None:
            raise ValueError(f"未注册的 provider: {name}，可用: {sorted(self._providers)}")
        return provider

    def has(self, name: str) -> bool:
        return name in self._providers

    def supports(self, name: str, capability: type[Any]) -> bool:
        provider = self.get(name)
        return isinstance(provider, capability)

    def require_capability(self, name: str, capability: type[Any]) -> object:
        provider = self.get(name)
        if not isinstance(provider, capability):
            raise TypeError(
                f"provider `{name}` 不支持能力 `{capability.__name__}`"
            )
        return provider

    def list_names(self) -> list[str]:
        return sorted(self._providers)
