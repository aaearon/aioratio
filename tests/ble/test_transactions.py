"""Transaction registry + ID generator."""

from __future__ import annotations

import asyncio

import pytest

from aioratio.ble.transactions import TransactionRegistry, new_transaction_id


def test_new_transaction_id_is_16_alphanumeric() -> None:
    for _ in range(50):
        txn = new_transaction_id()
        assert len(txn) == 16
        assert txn.isalnum()


def test_new_transaction_ids_are_unique() -> None:
    ids = {new_transaction_id() for _ in range(1000)}
    assert len(ids) >= 998  # birthday-paradox slack but still very high


async def test_register_then_resolve_with_exact_match() -> None:
    reg = TransactionRegistry()
    fut = reg.register("abc123")
    matched = reg.resolve("X", {"transaction": "abc123", "result": "success"})
    assert matched is True
    cls, body = await fut
    assert cls == "X"
    assert body["result"] == "success"


async def test_resolve_with_substring_match() -> None:
    """APK ``BluetoothService$write$3$1$2`` matches ``contains`` semantics."""
    reg = TransactionRegistry()
    fut = reg.register("abc")
    matched = reg.resolve("X", {"transaction": "prefix-abc-suffix"})
    assert matched is True
    cls, body = await fut
    assert cls == "X"


async def test_resolve_with_no_match_returns_false() -> None:
    reg = TransactionRegistry()
    reg.register("abc")
    assert reg.resolve("X", {"transaction": "xyz"}) is False


async def test_resolve_without_transaction_field() -> None:
    reg = TransactionRegistry()
    reg.register("abc")
    assert reg.resolve("X", {}) is False
    assert reg.resolve("X", {"transaction": 42}) is False


async def test_cancel_clears_pending() -> None:
    reg = TransactionRegistry()
    reg.register("abc")
    assert reg.pending_count == 1
    reg.cancel("abc")
    assert reg.pending_count == 0


async def test_fail_all_sets_exception_on_pending() -> None:
    reg = TransactionRegistry()
    fut1 = reg.register("a")
    fut2 = reg.register("b")
    reg.fail_all(RuntimeError("bye"))
    with pytest.raises(RuntimeError):
        await fut1
    with pytest.raises(RuntimeError):
        await fut2
    assert reg.pending_count == 0


async def test_resolve_does_not_double_complete() -> None:
    reg = TransactionRegistry()
    fut = reg.register("abc")
    assert reg.resolve("X", {"transaction": "abc"}) is True
    # Second response with the same id is ignored — the txn is gone.
    assert reg.resolve("X", {"transaction": "abc"}) is False
    cls, body = await asyncio.wait_for(fut, timeout=0.1)
    assert cls == "X"
