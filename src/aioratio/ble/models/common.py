"""Cross-cutting BLE response helpers.

Inspiro IPC responses share a ``result`` string field whose meaningful values
are ``"Success"`` and ``"Failed"`` (Kotlin sealed class ``IpcTransactionResult``,
``core/bluetooth/IpcTransactionResult.java`` — confirmed against the
``GenericIpcTransactionResponse$$serializer.java`` descriptor).
"""

from __future__ import annotations

from typing import Final

IPC_RESULT_SUCCESS: Final[str] = "Success"
IPC_RESULT_FAILED: Final[str] = "Failed"


def is_success(result: str) -> bool:
    return result == IPC_RESULT_SUCCESS


__all__ = ["IPC_RESULT_SUCCESS", "IPC_RESULT_FAILED", "is_success"]
