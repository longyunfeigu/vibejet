from __future__ import annotations

import gettext
from contextvars import ContextVar
from pathlib import Path

from core.logging_config import get_logger

_current_locale: ContextVar[str] = ContextVar("current_locale", default="en")
_translators: dict[str, gettext.NullTranslations] = {}
# structlog：支持 kwargs 结构化字段（stdlib logging.warning 传 kwargs 会 TypeError）
_logger = get_logger(__name__)


def set_locale(locale: str) -> None:
    """Set current request locale (fallback to 'en')."""
    _current_locale.set(locale or "en")


def get_locale() -> str:
    """Get current request locale (default 'en')."""
    return _current_locale.get()


def _get_translator(locale: str) -> gettext.NullTranslations:
    tr = _translators.get(locale)
    if tr is not None:
        return tr
    localedir = Path(__file__).resolve().parent.parent / "locales"
    try:
        tr = gettext.translation(
            domain="messages",
            localedir=str(localedir),
            languages=[locale],
            fallback=True,
        )
    except Exception as exc:
        # 翻译目录损坏/不可读等：降级为原文，但要留痕，不能静默
        _logger.warning("i18n_translation_load_failed", locale=locale, error=str(exc))
        tr = gettext.NullTranslations()
    _translators[locale] = tr
    return tr


def t(msgid: str, **params) -> str:
    """Translate msgid using current locale and format with params.

    If translation file is missing or key not found, returns msgid itself.
    """
    text = _get_translator(get_locale()).gettext(msgid)
    if not params:
        return text
    try:
        return text.format(**params)
    except Exception as exc:
        # Log and fallback to untranslated text to avoid breaking UX
        _logger.warning(
            "i18n_format_failed", msgid=msgid, params=list(params.keys()), error=str(exc)
        )
        return text
