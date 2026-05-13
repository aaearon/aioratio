"""IPC transaction registry.

Each request carries a 16-char alphanumeric ``transaction`` field; matching
responses include the same identifier. ``BluetoothService.java`` matches by
substring (``contains``), so the registry uses substring matching too: when
a response arrives, any pending transaction ID found anywhere in the response
body's ``transaction`` field counts as a match.
"""

from __future__ import annotations

import asyncio
import random
import string
from typing import Any

from ..exceptions import RatioBleProtocolError

_TXN_ALPHABET = string.ascii_letters + string.digits
_TXN_LEN = 16


def new_transaction_id() -> str:
    """16-char alphanumeric, matches ``TransactionIdGenerator`` semantics."""
    return "".join(random.choices(_TXN_ALPHABET, k=_TXN_LEN))


class TransactionRegistry:
    """Couples outgoing transactions to their incoming response futures."""

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[tuple[str, dict[str, Any]]]] = {}

    def register(self, txn: str) -> asyncio.Future[tuple[str, dict[str, Any]]]:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[tuple[str, dict[str, Any]]] = loop.create_future()
        self._pending[txn] = fut
        return fut

    def cancel(self, txn: str) -> None:
        self._pending.pop(txn, None)

    def resolve(self, classname: str, body: dict[str, Any]) -> bool:
        """Try to match an incoming frame to a pending transaction.

        Returns ``True`` if a pending future was completed; ``False`` if no
        matching transaction was found (caller may choose to drop or log).
        """
        observed = body.get("transaction")
        if not isinstance(observed, str) or not observed:
            return False
        for txn, fut in list(self._pending.items()):
            # APK uses substring match (BluetoothService$write$3$1$2 calls
            # response.transaction.contains(request.transaction)).
            if txn in observed and not fut.done():
                fut.set_result((classname, body))
                self._pending.pop(txn, None)
                return True
        return False

    def fail_all(self, exc: BaseException) -> None:
        """Reject every pending transaction (e.g. on disconnect)."""
        for txn, fut in list(self._pending.items()):
            if not fut.done():
                fut.set_exception(exc)
            self._pending.pop(txn, None)

    @property
    def pending_count(self) -> int:
        return len(self._pending)


def extract_result(body: dict[str, Any]) -> str:
    """Return the ``result`` field of a response, raising on missing/bad."""
    result = body.get("result")
    if not isinstance(result, str):
        raise RatioBleProtocolError("response missing string 'result' field")
    return result


__all__ = [
    "TransactionRegistry",
    "new_transaction_id",
    "extract_result",
]
