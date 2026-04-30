"""Pluggable token persistence interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TokenStore(ABC):
    """Abstract base for token persistence backends."""

    @abstractmethod
    async def load(self) -> dict[str, Any] | None:
        """Return the persisted token bundle, or ``None`` if absent."""

    @abstractmethod
    async def save(self, tokens: dict[str, Any]) -> None:
        """Persist the given token bundle."""
