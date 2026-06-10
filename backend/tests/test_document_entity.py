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


def test_happy_path_pending_parsing_ready() -> None:
    doc = _make_document()
    doc.start_parsing()
    assert doc.status == "parsing"

    doc.mark_ready(content_md="# Title", parser="markitdown", metadata={"pages": 3})
    assert doc.status == "ready"
    assert doc.content_md == "# Title"
    assert doc.parser == "markitdown"
    assert doc.metadata["pages"] == 3
    assert doc.error_code is None
    assert doc.is_ready() is True


def test_failure_path_records_error_and_clears_on_retry() -> None:
    doc = _make_document()
    doc.start_parsing()
    doc.mark_failed(
        error_code="document.parse.empty_content", error_message="no text", parser="markitdown"
    )
    assert doc.status == "failed"
    assert doc.error_code == "document.parse.empty_content"

    # failed → parsing 重试时清空错误信息
    doc.start_parsing()
    assert doc.status == "parsing"
    assert doc.error_code is None
    assert doc.error_message is None


def test_start_parsing_rejected_while_parsing() -> None:
    doc = _make_document()
    doc.start_parsing()
    with pytest.raises(DocumentAlreadyProcessingException):
        doc.start_parsing()


def test_reset_for_reparse_clears_artifacts() -> None:
    doc = _make_document()
    doc.start_parsing()
    doc.mark_ready(content_md="# Title", parser="markitdown")

    doc.reset_for_reparse()
    assert doc.status == "pending"
    assert doc.content_md is None
    assert doc.error_code is None


def test_reset_for_reparse_rejected_while_parsing() -> None:
    doc = _make_document()
    doc.start_parsing()
    with pytest.raises(DocumentAlreadyProcessingException):
        doc.reset_for_reparse()


def test_reset_for_reparse_allows_stale_parsing_recovery() -> None:
    from datetime import timedelta

    from domain.common.entity import utcnow

    doc = _make_document()
    doc.start_parsing()

    # 未超时：仍拒绝
    with pytest.raises(DocumentAlreadyProcessingException):
        doc.reset_for_reparse(parsing_stale_after_seconds=900)

    # 模拟孤儿任务：上次更新远早于阈值（如进程重启丢失 BackgroundTasks）
    doc.updated_at = utcnow() - timedelta(seconds=1000)
    doc.reset_for_reparse(parsing_stale_after_seconds=900)
    assert doc.status == "pending"
