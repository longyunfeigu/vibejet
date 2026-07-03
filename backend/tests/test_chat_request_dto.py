# input: ChatRequestDTO
# output: 聊天请求 DTO 边界校验测试
# pos: 后端测试 - 聊天入参上下限（防超大文本直通 LLM/DB）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""ChatRequestDTO boundary validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from application.dto import ChatRequestDTO

_MAX_MESSAGE_CHARS = 32_000


def test_message_at_max_length_accepted() -> None:
    dto = ChatRequestDTO(message="x" * _MAX_MESSAGE_CHARS)
    assert len(dto.message) == _MAX_MESSAGE_CHARS


def test_message_over_max_length_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatRequestDTO(message="x" * (_MAX_MESSAGE_CHARS + 1))


def test_empty_message_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatRequestDTO(message="")
