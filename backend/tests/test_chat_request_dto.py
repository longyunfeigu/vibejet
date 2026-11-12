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
