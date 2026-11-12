"""Storage port boundary: provider not-found must surface as the port-level error.

应用层不认识 infrastructure 的 NotFoundError（不是 BusinessException），曾导致
/storage/complete 在对象未上传时 500；adapter 负责翻译成 StorageObjectNotFoundError。
"""

from __future__ import annotations

import pytest

from application.ports.storage import StorageObjectNotFoundError
from infrastructure.adapters.storage_port import StorageProviderPortAdapter
from infrastructure.external.storage import NotFoundError, StorageError


class _Provider:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def get_metadata(self, key: str):
        raise self._exc


async def test_get_metadata_maps_provider_not_found_to_port_error() -> None:
    adapter = StorageProviderPortAdapter(_Provider(NotFoundError("Object not found")))

    with pytest.raises(StorageObjectNotFoundError) as exc_info:
        await adapter.get_metadata("uploads/missing.bin")

    assert exc_info.value.key == "uploads/missing.bin"
    assert isinstance(exc_info.value.__cause__, NotFoundError)


async def test_get_metadata_keeps_other_storage_errors() -> None:
    adapter = StorageProviderPortAdapter(_Provider(StorageError("boom")))

    with pytest.raises(StorageError):
        await adapter.get_metadata("uploads/x.bin")
