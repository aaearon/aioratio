"""Tests for aioratio.token_store."""
from __future__ import annotations

import asyncio
import json
import os
import time

import pytest

from aioratio.exceptions import RatioError
from aioratio.token_store import (
    JsonFileTokenStore,
    MemoryTokenStore,
    TokenBundle,
)

pytestmark = pytest.mark.asyncio


def _full_bundle(**overrides: object) -> TokenBundle:
    base = dict(
        access_token="acc",
        id_token="idt",
        refresh_token="rft",
        expires_at=time.time() + 3600,
        token_type="Bearer",
        device_key="dk",
        device_group_key="dgk",
        device_password="dpw",
    )
    base.update(overrides)
    return TokenBundle(**base)  # type: ignore[arg-type]


async def test_token_bundle_roundtrip() -> None:
    full = _full_bundle()
    assert TokenBundle.from_dict(full.to_dict()) == full

    no_dev = TokenBundle(
        access_token="a",
        id_token="i",
        refresh_token="r",
        expires_at=123.0,
    )
    assert TokenBundle.from_dict(no_dev.to_dict()) == no_dev


async def test_token_bundle_unknown_fields_dropped() -> None:
    data = {
        "access_token": "a",
        "id_token": "i",
        "refresh_token": "r",
        "expires_at": 1.0,
        "extra": 1,
        "another": "x",
    }
    b = TokenBundle.from_dict(data)
    assert b.access_token == "a"
    assert b.expires_at == 1.0


async def test_token_bundle_missing_optional_device_fields() -> None:
    data = {
        "access_token": "a",
        "id_token": "i",
        "refresh_token": "r",
        "expires_at": 1.0,
    }
    b = TokenBundle.from_dict(data)
    assert b.device_key is None
    assert b.device_group_key is None
    assert b.device_password is None
    assert b.token_type == "Bearer"


async def test_is_expired() -> None:
    now = time.time()
    not_expired = TokenBundle(
        access_token="a", id_token="i", refresh_token="r", expires_at=now + 60
    )
    assert not not_expired.is_expired

    within_skew = TokenBundle(
        access_token="a", id_token="i", refresh_token="r", expires_at=now + 10
    )
    assert within_skew.is_expired

    past = TokenBundle(
        access_token="a", id_token="i", refresh_token="r", expires_at=now - 10
    )
    assert past.is_expired


async def test_memory_store_lifecycle() -> None:
    store = MemoryTokenStore()
    assert await store.load() is None
    b = _full_bundle()
    await store.save(b)
    assert await store.load() == b
    await store.clear()
    assert await store.load() is None


async def test_json_file_store_lifecycle(tmp_path) -> None:
    path = tmp_path / "tokens.json"
    store = JsonFileTokenStore(path)
    assert await store.load() is None

    b = _full_bundle()
    await store.save(b)
    loaded = await store.load()
    assert loaded == b

    await store.clear()
    assert not path.exists()
    assert await store.load() is None


async def test_json_file_store_atomic_write_no_tmp_left(tmp_path) -> None:
    path = tmp_path / "tokens.json"
    store = JsonFileTokenStore(path)
    await store.save(_full_bundle())
    leftovers = [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


async def test_json_file_store_file_mode_0600(tmp_path) -> None:
    path = tmp_path / "tokens.json"
    store = JsonFileTokenStore(path)
    await store.save(_full_bundle())
    mode = os.stat(path).st_mode & 0o777
    assert mode == 0o600


async def test_json_file_store_unparseable_raises_ratio_error(tmp_path) -> None:
    path = tmp_path / "tokens.json"
    path.write_text("not json {{{")
    store = JsonFileTokenStore(path)
    with pytest.raises(RatioError):
        await store.load()


async def test_json_file_store_concurrent_saves(tmp_path) -> None:
    path = tmp_path / "tokens.json"
    store = JsonFileTokenStore(path)
    bundles = [
        _full_bundle(access_token=f"acc{i}", id_token=f"id{i}", refresh_token=f"rt{i}")
        for i in range(10)
    ]
    await asyncio.gather(*(store.save(b) for b in bundles))

    # File parses cleanly.
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    loaded = TokenBundle.from_dict(data)
    assert loaded in bundles
