# input: domain.document 实体与异常
# output: Document 状态机单元测试
# pos: 后端测试 - 文档聚合状态机行为验证；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Unit tests for the Document aggregate state machine."""

from __future__ import annotations

import pytest

from domain.common.exceptions import DomainValidationException
from domain.document import Document, DocumentAlreadyProcessingException


def _make_document(**overrides) -> Document:
    defaults = {"id": 1, "file_asset_id": 10, "source_filename": "report.pdf"}
    defaults.update(overrides)
    return Document(**defaults)


def test_document_defaults_to_pending() -> None:
    doc = _make_document()
    assert doc.status == "pending"
    assert doc.metadata == {}


def test_document_rejects_invalid_status() -> None:
    with pytest.raises(DomainValidationException):
        _make_document(status="bogus")


def test_document_requires_file_asset() -> None:
    with pytest.raises(DomainValidationException):
        Document(id=1, file_asset_id=0)


# 注：进入 parsing 没有实体方法——认领走仓储原子条件 UPDATE（try_mark_parsing，
# 见 test_document_repository.py）。以下测试用构造参数直接进入 parsing 态。


def test_happy_path_parsing_to_ready() -> None:
    doc = _make_document(status="parsing")

    doc.mark_ready(content_md="# Title", parser="markitdown", metadata={"pages": 3})
    assert doc.status == "ready"
    assert doc.content_md == "# Title"
    assert doc.parser == "markitdown"
    assert doc.metadata["pages"] == 3
    assert doc.error_code is None
    assert doc.is_ready() is True


def test_failure_path_records_error() -> None:
    doc = _make_document(status="parsing")
    doc.mark_failed(
        error_code="document.parse.empty_content", error_message="no text", parser="markitdown"
    )
    assert doc.status == "failed"
    assert doc.error_code == "document.parse.empty_content"
    assert doc.error_message == "no text"


def test_reset_for_reparse_clears_artifacts() -> None:
    doc = _make_document(status="parsing")
    doc.mark_ready(content_md="# Title", parser="markitdown")

    doc.reset_for_reparse()
    assert doc.status == "pending"
    assert doc.content_md is None
    assert doc.error_code is None


def test_reset_for_reparse_rejected_while_parsing() -> None:
    doc = _make_document(status="parsing")
    with pytest.raises(DocumentAlreadyProcessingException):
        doc.reset_for_reparse()


def test_reset_for_reparse_allows_stale_parsing_recovery() -> None:
    from datetime import timedelta

    from domain.common.entity import utcnow

    # updated_at 即认领时间（try_mark_parsing 落库时写入）；None 视为 stale
    doc = _make_document(status="parsing", updated_at=utcnow())

    # 未超时：仍拒绝
    with pytest.raises(DocumentAlreadyProcessingException):
        doc.reset_for_reparse(parsing_stale_after_seconds=900)

    # 模拟孤儿任务：上次更新远早于阈值（如进程重启丢失 BackgroundTasks）
    doc.updated_at = utcnow() - timedelta(seconds=1000)
    doc.reset_for_reparse(parsing_stale_after_seconds=900)
    assert doc.status == "pending"
