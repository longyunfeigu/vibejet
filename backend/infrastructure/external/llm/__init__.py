# input: core.config.settings.llm（provider/api_key/base_url）, OpenAI/Anthropic SDK
# output: init_llm_client, shutdown_llm_client, get_llm_client 生命周期函数（provider 路由）
# owner: unknown
# pos: 基础设施层 - LLM 客户端生命周期管理与 provider 选择（openai/openrouter/litellm/anthropic，每个 provider 外套熔断）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""LLM client lifecycle management with provider routing.

Supported ``LLM__PROVIDER`` values:

- ``openai``      OpenAI / Azure / vLLM 及任何 OpenAI 兼容端点（配 ``LLM__BASE_URL``）
- ``openrouter``  OpenRouter（OpenAI 兼容；base_url 默认 https://openrouter.ai/api/v1）
- ``litellm``     LiteLLM proxy（OpenAI 兼容；``LLM__BASE_URL`` 必填，指向 proxy 地址，
                  api_key 为 LiteLLM master/virtual key，模型名按 LiteLLM 路由配置）
- ``anthropic``   Anthropic 原生 SDK（需要安装 extra：``uv sync --extra anthropic``）

OpenAI 兼容的三个 provider 共用 OpenAIProvider，只是默认 base_url 不同。
每个 provider 外套 CircuitBreakingLLM（见 circuit_breaking.py），上游持续故障时本地快速失败。
"""

from __future__ import annotations

from typing import Optional

from application.ports.llm import LLMPort
from core.config import settings
from core.logging_config import get_logger
from infrastructure.external.circuit_breaker import SREBreaker

from .circuit_breaking import CircuitBreakingLLM

logger = get_logger(__name__)

_llm_client: Optional[LLMPort] = None

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENAI_COMPATIBLE_PROVIDERS = {"openai", "openrouter", "litellm"}


def _build_client(llm_cfg) -> LLMPort:
    provider = (llm_cfg.provider or "openai").lower()

    if provider in _OPENAI_COMPATIBLE_PROVIDERS:
        base_url = llm_cfg.base_url
        if provider == "openrouter" and not base_url:
            base_url = _OPENROUTER_BASE_URL
        if provider == "litellm" and not base_url:
            raise ValueError(
                "LLM__PROVIDER=litellm requires LLM__BASE_URL pointing to the LiteLLM proxy "
                "(e.g. http://localhost:4000)"
            )
        from .openai_provider import OpenAIProvider, is_upstream_failure

        return CircuitBreakingLLM(
            OpenAIProvider(
                api_key=llm_cfg.api_key,
                base_url=base_url,
                default_model=llm_cfg.default_model,
                default_temperature=llm_cfg.temperature,
                default_max_tokens=llm_cfg.max_tokens,
                timeout=llm_cfg.timeout,
                max_retries=llm_cfg.max_retries,
            ),
            SREBreaker(f"llm:{provider}"),
            is_upstream_failure,
        )

    if provider == "anthropic":
        try:
            from .anthropic_provider import AnthropicProvider, is_upstream_failure
        except ImportError as exc:
            raise ImportError(
                "anthropic SDK not installed. Run `uv sync --extra anthropic` "
                "(or `pip install vibejet[anthropic]`)."
            ) from exc

        return CircuitBreakingLLM(
            AnthropicProvider(
                api_key=llm_cfg.api_key,
                base_url=llm_cfg.base_url,
                default_model=llm_cfg.default_model,
                default_temperature=llm_cfg.temperature,
                default_max_tokens=llm_cfg.max_tokens,
                timeout=llm_cfg.timeout,
                max_retries=llm_cfg.max_retries,
            ),
            SREBreaker(f"llm:{provider}"),
            is_upstream_failure,
        )

    raise ValueError(
        f"Unsupported LLM__PROVIDER: {provider!r}. "
        f"Expected one of: openai, openrouter, litellm, anthropic"
    )


async def init_llm_client() -> None:
    """Initialize the LLM client based on configuration."""
    global _llm_client

    if _llm_client is not None:
        logger.warning("LLM client already initialized")
        return

    llm_cfg = settings.llm
    if not llm_cfg.api_key:
        logger.warning(
            "llm_client_skipped",
            reason="LLM__API_KEY not configured; LLM features will be unavailable",
        )
        return

    try:
        _llm_client = _build_client(llm_cfg)
        logger.info(
            "llm_client_initialized",
            provider=llm_cfg.provider,
            model=llm_cfg.default_model,
            base_url=llm_cfg.base_url,
        )
    except Exception as exc:
        logger.error("llm_client_init_failed", error=str(exc))
        raise


def get_llm_client() -> Optional[LLMPort]:
    """Get the LLM client instance (may be None if not configured)."""
    return _llm_client


async def shutdown_llm_client() -> None:
    """Shutdown the LLM client."""
    global _llm_client

    if _llm_client is None:
        return

    try:
        # OpenAI/Anthropic SDK 内部都是 httpx client；存在 close 则关闭（先剥掉熔断外壳）
        provider_client = getattr(_llm_client, "inner", _llm_client)
        client = getattr(provider_client, "_client", None)
        if client is not None and hasattr(client, "close"):
            await client.close()
        logger.info("llm_client_shutdown")
    except Exception as exc:
        logger.error("llm_client_shutdown_failed", error=str(exc))
    finally:
        _llm_client = None


__all__ = [
    "init_llm_client",
    "get_llm_client",
    "shutdown_llm_client",
]
