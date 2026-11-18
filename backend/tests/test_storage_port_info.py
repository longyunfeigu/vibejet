"""Storage port info(): the storage type must survive the middleware wrapper.

启动时 provider 总会被 apply_middleware 包一层（LoggingMiddleware 恒在），包装器
没有 config，adapter.info() 曾因此拿到空串 storage_type，违反 file_assets 的
storage_type 检查约束——默认配置下每一次上传都失败（还被误报成 FileAssetKeyConflict）。
"""

from __future__ import annotations

import pytest

from infrastructure.adapters.storage_port import StorageProviderPortAdapter
from infrastructure.external.storage.config import StorageConfig, StorageType
from infrastructure.external.storage.providers.local import LocalProvider
from infrastructure.external.storage.utils import LoggingMiddleware, apply_middleware


def _local_provider(tmp_path) -> LocalProvider:
    return LocalProvider(StorageConfig(type=StorageType.LOCAL, local_base_path=str(tmp_path)))


def test_info_reads_type_through_middleware_wrapper(tmp_path) -> None:
    wrapped = apply_middleware(_local_provider(tmp_path), [LoggingMiddleware()])

    info = StorageProviderPortAdapter(wrapped).info()

    assert info.type == "local"


def test_info_reads_type_from_bare_provider(tmp_path) -> None:
    info = StorageProviderPortAdapter(_local_provider(tmp_path)).info()

    assert info.type == "local"


def test_info_fails_loudly_when_type_unknown() -> None:
    # 拿不到类型时宁可报错，也不写一个必然违反检查约束的空串
    with pytest.raises(RuntimeError):
        StorageProviderPortAdapter(object()).info()
