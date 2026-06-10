# input: shared.codes.BusinessCode, domain.common.exceptions.BusinessException
# output: 文档领域异常类（NotFound/NotReady/AlreadyProcessing）
# pos: 领域层 - 文档聚合异常定义；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Domain exceptions for the document aggregate."""

from __future__ import annotations

from typing import Optional

from domain.common.exceptions import BusinessException
from shared.codes import BusinessCode


class DocumentNotFoundException(BusinessException):
    def __init__(self, document_id: Optional[int] = None):
        details = {"document_id": document_id} if document_id is not None else None
        super().__init__(
            code=BusinessCode.DOCUMENT_NOT_FOUND,
            message="Document not found",
            error_type="DocumentNotFound",
            details=details,
            message_key="document.not_found",
        )


class DocumentNotReadyException(BusinessException):
    """请求解析产物但文档尚未 ready（pending/parsing/failed）。"""

    def __init__(self, document_id: Optional[int] = None, *, status: Optional[str] = None):
        details: dict = {}
        if document_id is not None:
            details["document_id"] = document_id
        if status is not None:
            details["status"] = status
        super().__init__(
            code=BusinessCode.DOCUMENT_NOT_READY,
            message="Document is not ready",
            error_type="DocumentNotReady",
            details=details or None,
            message_key="document.not_ready",
        )


class DocumentAlreadyProcessingException(BusinessException):
    """文档正在解析中，拒绝并发进入 parsing 或重解析。"""

    def __init__(self, document_id: Optional[int] = None):
        details = {"document_id": document_id} if document_id is not None else None
        super().__init__(
            code=BusinessCode.DOCUMENT_ALREADY_PROCESSING,
            message="Document is already being processed",
            error_type="DocumentAlreadyProcessing",
            details=details,
            message_key="document.already_processing",
        )
