from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.dependencies import get_current_user, get_file_asset_service, get_idempotency_service
from api.routes.storage import router as storage_router
from application.dto import FileAssetSummaryDTO, UserDTO
from application.ports.idempotency import (
    IdempotencyRecord,
    IdempotencyStore,
    IdempotencyStoreUnavailableError,
)
from application.ports.storage import PresignedURL
from application.services.idempotency_service import IdempotencyService
from core.exceptions import register_exception_handlers
from domain.common.exceptions import UnsupportedMimeTypeException


class InMemoryIdempotencyStore(IdempotencyStore):
    def __init__(self) -> None:
        self._locks: set[tuple[str, str]] = set()
        self._results: dict[tuple[str, str], IdempotencyRecord] = {}

    async def get(self, *, scope: str, key: str):
        return self._results.get((scope, key))

    async def try_start(self, *, scope: str, key: str, request_hash: str, ttl_seconds: int) -> bool:
        _ = ttl_seconds
        lk = (scope, key)
        if lk in self._locks:
            return False
        self._locks.add(lk)
        return True

    async def set_result(
        self,
        *,
        scope: str,
        key: str,
        request_hash: str,
        payload: dict,
        ttl_seconds: int,
    ) -> None:
        _ = ttl_seconds
        self._results[(scope, key)] = IdempotencyRecord(
            scope=scope,
            key=key,
            request_hash=request_hash,
            payload=payload,
        )

    async def release(self, *, scope: str, key: str) -> None:
        self._locks.discard((scope, key))


class FakeFileAssetService:
    def __init__(self) -> None:
        self.presign_calls = 0
        self.generate_calls = 0
        self.upload_calls = 0
        self.uploaded_bytes = b""
        self.uploaded_filename = ""
        self.uploaded_content_type = None

    async def presign_upload(
        self,
        *,
        user_id,
        filename: str,
        mime_type,
        size_bytes: int,
        kind: str,
        method: str = "PUT",
        expires_in: int = 600,
    ):
        _ = (user_id, mime_type, kind, expires_in, size_bytes)
        self.presign_calls += 1
        file_summary = FileAssetSummaryDTO(
            id=self.presign_calls,
            key=f"test/{filename}",
            status="pending",
            original_filename=filename,
            content_type="text/plain",
            etag=None,
            size=0,
            url=None,
        )
        presigned = PresignedURL(
            url=f"https://example.test/upload/{self.presign_calls}", method=method, expires_in=600
        )
        return file_summary, presigned

    async def generate_upload_presign(
        self,
        *,
        asset_id: int,
        owner_id: int,
        method: str,
        expires_in: int,
    ) -> PresignedURL:
        _ = (asset_id, owner_id, expires_in)
        self.generate_calls += 1
        return PresignedURL(
            url=f"https://example.test/upload/replay/{self.generate_calls}",
            method=method,
            expires_in=600,
        )

    async def relay_upload_stream(
        self,
        *,
        user_id,
        file_stream,
        filename: str,
        kind: str,
        content_type,
    ):
        _ = (user_id, kind)
        self.upload_calls += 1
        chunks = []
        async for chunk in file_stream:
            chunks.append(chunk)
        self.uploaded_bytes = b"".join(chunks)
        self.uploaded_filename = filename
        self.uploaded_content_type = content_type
        return {
            "key": f"uploads/{filename}",
            "etag": "test-etag",
            "size": len(self.uploaded_bytes),
            "content_type": content_type,
            "url": "https://example.test/files/upload.txt",
            "file_id": 123,
            "file_status": "active",
        }


def make_test_app(fake_service: FakeFileAssetService) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(storage_router, prefix="/api/v1")

    store = InMemoryIdempotencyStore()
    idem = IdempotencyService(store=store, lock_ttl_seconds=5, result_ttl_seconds=60)

    app.dependency_overrides[get_file_asset_service] = lambda: fake_service
    app.dependency_overrides[get_idempotency_service] = lambda: idem
    # storage 路由现在要求认证；测试里直接放行一个固定用户
    app.dependency_overrides[get_current_user] = lambda: UserDTO(
        id=1, username="tester", email="tester@example.com"
    )
    return app


async def test_presign_upload_idempotent_replay() -> None:
    fake = FakeFileAssetService()
    app = make_test_app(fake)

    payload = {
        "filename": "a.txt",
        "mime_type": None,
        "size_bytes": 1,
        "kind": "uploads",
        "method": "PUT",
        "expires_in": 600,
    }
    headers = {"Idempotency-Key": "aaaaaaaa"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post("/api/v1/storage/presign-upload", json=payload, headers=headers)
        r2 = await client.post("/api/v1/storage/presign-upload", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["data"]["file"]["id"] == r2.json()["data"]["file"]["id"]
    assert fake.presign_calls == 1
    assert fake.generate_calls == 1


async def test_presign_upload_idempotency_key_reused_with_different_payload() -> None:
    fake = FakeFileAssetService()
    app = make_test_app(fake)

    payload1 = {
        "filename": "a.txt",
        "mime_type": None,
        "size_bytes": 1,
        "kind": "uploads",
        "method": "PUT",
        "expires_in": 600,
    }
    payload2 = {
        "filename": "b.txt",
        "mime_type": None,
        "size_bytes": 1,
        "kind": "uploads",
        "method": "PUT",
        "expires_in": 600,
    }
    headers = {"Idempotency-Key": "bbbbbbbb"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post("/api/v1/storage/presign-upload", json=payload1, headers=headers)
        r2 = await client.post("/api/v1/storage/presign-upload", json=payload2, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 422
    assert r2.json()["code"] == 10003


async def test_relay_upload_accepts_multipart_file() -> None:
    fake = FakeFileAssetService()
    app = make_test_app(fake)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/storage/upload",
            params={"kind": "uploads"},
            files={"file": ("upload.txt", b"hello multipart", "text/plain")},
        )

    assert response.status_code == 200
    assert response.json()["data"]["size"] == len(b"hello multipart")
    assert fake.upload_calls == 1
    assert fake.uploaded_bytes == b"hello multipart"
    assert fake.uploaded_filename == "upload.txt"
    assert fake.uploaded_content_type == "text/plain"


class UnavailableIdempotencyStore(InMemoryIdempotencyStore):
    """模拟 Redis 不可用：try_start 抛 store 不可用（非业务异常）。"""

    async def try_start(self, *, scope: str, key: str, request_hash: str, ttl_seconds: int) -> bool:
        raise IdempotencyStoreUnavailableError("redis unavailable")


async def test_presign_upload_fails_open_when_store_unavailable() -> None:
    """Store 后端不可用必须 fail-open（照常执行、不去重），
    而不是把基础设施故障误报成 in_progress 4xx。"""
    fake = FakeFileAssetService()
    app = make_test_app(fake)
    idem = IdempotencyService(
        store=UnavailableIdempotencyStore(), lock_ttl_seconds=5, result_ttl_seconds=60
    )
    app.dependency_overrides[get_idempotency_service] = lambda: idem

    payload = {
        "filename": "a.txt",
        "mime_type": None,
        "size_bytes": 1,
        "kind": "uploads",
        "method": "PUT",
        "expires_in": 600,
    }
    headers = {"Idempotency-Key": "cccccccc"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/storage/presign-upload", json=payload, headers=headers)

    assert resp.status_code == 200
    assert fake.presign_calls == 1


class _FailOnceFileAssetService(FakeFileAssetService):
    """第一次 presign 抛业务异常（如不支持的 MIME），之后正常。"""

    def __init__(self) -> None:
        super().__init__()
        self.failures_left = 1

    async def presign_upload(self, **kwargs):
        if self.failures_left:
            self.failures_left -= 1
            raise UnsupportedMimeTypeException("application/x-msdownload")
        return await super().presign_upload(**kwargs)


_PRESIGN_PAYLOAD = {
    "filename": "a.txt",
    "mime_type": None,
    "size_bytes": 1,
    "kind": "uploads",
    "method": "PUT",
    "expires_in": 600,
}


async def test_presign_failure_releases_lock_so_retry_reexecutes() -> None:
    """被保护操作失败必须释放锁：同 key 重试重新执行，而不是在 lock_ttl 内报 in_progress。"""
    fake = _FailOnceFileAssetService()
    app = make_test_app(fake)
    headers = {"Idempotency-Key": "dddddddd"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post(
            "/api/v1/storage/presign-upload", json=_PRESIGN_PAYLOAD, headers=headers
        )
        r2 = await client.post(
            "/api/v1/storage/presign-upload", json=_PRESIGN_PAYLOAD, headers=headers
        )

    assert r1.status_code == 422
    assert r1.json()["code"] == 10003
    assert r2.status_code == 200, r2.json()
    assert fake.presign_calls == 1


def _set_user(app: FastAPI, user_id: int) -> None:
    app.dependency_overrides[get_current_user] = lambda: UserDTO(
        id=user_id, username=f"u{user_id}", email=f"u{user_id}@example.com"
    )


async def test_idempotency_subject_survives_token_refresh() -> None:
    """subject 是用户 id 而非 Authorization 头：换 token 重试仍命中缓存，不报 key reused。"""
    fake = FakeFileAssetService()
    app = make_test_app(fake)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post(
            "/api/v1/storage/presign-upload",
            json=_PRESIGN_PAYLOAD,
            headers={"Idempotency-Key": "eeeeeeee", "Authorization": "Bearer old-token"},
        )
        r2 = await client.post(
            "/api/v1/storage/presign-upload",
            json=_PRESIGN_PAYLOAD,
            headers={"Idempotency-Key": "eeeeeeee", "Authorization": "Bearer refreshed-token"},
        )

    assert r1.status_code == 200
    assert r2.status_code == 200, r2.json()
    assert r1.json()["data"]["file"]["id"] == r2.json()["data"]["file"]["id"]
    assert fake.presign_calls == 1


async def test_idempotency_key_is_namespaced_per_user() -> None:
    """不同用户用同一个 Idempotency-Key 互不影响：各自执行，不串结果、不报 key reused。"""
    fake = FakeFileAssetService()
    app = make_test_app(fake)
    headers = {"Idempotency-Key": "ffffffff"}
    other_payload = {**_PRESIGN_PAYLOAD, "filename": "b.txt"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        _set_user(app, 1)
        r1 = await client.post(
            "/api/v1/storage/presign-upload", json=_PRESIGN_PAYLOAD, headers=headers
        )
        _set_user(app, 2)
        r2 = await client.post(
            "/api/v1/storage/presign-upload", json=other_payload, headers=headers
        )

    assert r1.status_code == 200
    assert r2.status_code == 200, r2.json()
    assert r1.json()["data"]["file"]["id"] != r2.json()["data"]["file"]["id"]
    assert fake.presign_calls == 2
