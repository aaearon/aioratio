"""Token persistence for aioratio."""
from __future__ import annotations

import abc
import asyncio
import json
import os
import time
from dataclasses import dataclass, fields
from typing import Any

from .exceptions import RatioError

__all__ = [
    "TokenBundle",
    "TokenStore",
    "MemoryTokenStore",
    "JsonFileTokenStore",
]


@dataclass(slots=True)
class TokenBundle:
    """All persisted Cognito auth state for a Ratio user session."""

    access_token: str
    id_token: str
    refresh_token: str
    expires_at: float
    token_type: str = "Bearer"
    device_key: str | None = None
    device_group_key: str | None = None
    device_password: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "id_token": self.id_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
            "device_key": self.device_key,
            "device_group_key": self.device_group_key,
            "device_password": self.device_password,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenBundle":
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at - 30


class TokenStore(abc.ABC):
    """Abstract async token persistence interface."""

    @abc.abstractmethod
    async def load(self) -> TokenBundle | None: ...

    @abc.abstractmethod
    async def save(self, bundle: TokenBundle) -> None: ...

    @abc.abstractmethod
    async def clear(self) -> None: ...


class MemoryTokenStore(TokenStore):
    """In-memory token store. Useful for tests and ephemeral CLI use."""

    def __init__(self) -> None:
        self._bundle: TokenBundle | None = None

    async def load(self) -> TokenBundle | None:
        return self._bundle

    async def save(self, bundle: TokenBundle) -> None:
        self._bundle = bundle

    async def clear(self) -> None:
        self._bundle = None


class JsonFileTokenStore(TokenStore):
    """Atomic JSON file token store with 0600 permissions."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = os.fspath(path)
        self._tmp = self._path + ".tmp"
        self._lock = asyncio.Lock()

    def _read(self) -> dict[str, Any]:
        with open(self._path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict[str, Any]) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(self._tmp, flags, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            try:
                os.unlink(self._tmp)
            except FileNotFoundError:
                pass
            raise
        os.chmod(self._tmp, 0o600)
        os.replace(self._tmp, self._path)

    def _unlink(self) -> None:
        try:
            os.unlink(self._path)
        except FileNotFoundError:
            pass

    async def load(self) -> TokenBundle | None:
        async with self._lock:
            if not os.path.exists(self._path):
                return None
            try:
                data = await asyncio.to_thread(self._read)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                raise RatioError(f"Failed to load token file {self._path}") from exc
            try:
                return TokenBundle.from_dict(data)
            except (TypeError, KeyError) as exc:
                raise RatioError(f"Malformed token data in {self._path}") from exc

    async def save(self, bundle: TokenBundle) -> None:
        async with self._lock:
            await asyncio.to_thread(self._write, bundle.to_dict())

    async def clear(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._unlink)
