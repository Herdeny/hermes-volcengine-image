"""Volcengine Ark Seedream image generation backend for Hermes Agent."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    resolve_aspect_ratio,
    save_b64_image,
    save_url_image,
    success_response,
)
from agent.secret_scope import get_secret

logger = logging.getLogger(__name__)


API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
DEFAULT_MODEL = "doubao-seedream-5-0-260128"

_MODELS: Dict[str, Dict[str, str]] = {
    "doubao-seedream-5-0-260128": {
        "display": "Doubao Seedream 5.0 Pro",
        "price": "¥0.30/image",
        "strengths": "Highest fidelity and strong Chinese small-text rendering",
    },
    "doubao-seedream-4-5-251128": {
        "display": "Doubao Seedream 4.5",
        "price": "¥0.25/image",
        "strengths": "Balanced image quality, prompt adherence, and cost",
    },
    "doubao-seedream-4-0-250828": {
        "display": "Doubao Seedream 4.0",
        "price": "¥0.22/image",
        "strengths": "Cost-effective general-purpose image generation",
    },
}

_SIZES = {
    "landscape": "2848x1600",
    "square": "2048x2048",
    "portrait": "1600x2848",
}


def _error_message(response: requests.Response, result: Any = None) -> str:
    """Extract a concise Ark error message from an HTTP response."""
    if result is None:
        try:
            result = response.json()
        except Exception:
            result = None

    if isinstance(result, dict):
        error = result.get("error")
        if isinstance(error, dict):
            for key in ("message", "code", "type"):
                value = error.get(key)
                if value:
                    return str(value)
        elif error:
            return str(error)
        for key in ("message", "code"):
            value = result.get(key)
            if value:
                return str(value)

    text = getattr(response, "text", "")
    return str(text)[:300] if text else "Unknown API error"


class VolcengineImageGenProvider(ImageGenProvider):
    """Text-to-image provider backed by Volcengine Ark Seedream."""

    @property
    def name(self) -> str:
        return "volcengine"

    @property
    def display_name(self) -> str:
        return "Volcengine Seedream"

    def is_available(self) -> bool:
        try:
            return bool((get_secret("ARK_API_KEY") or "").strip())
        except Exception:
            return False

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": model_id,
                "display": metadata["display"],
                "price": metadata["price"],
                "strengths": metadata["strengths"],
            }
            for model_id, metadata in _MODELS.items()
        ]

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Volcengine Seedream",
            "badge": "paid",
            "tag": "Seedream 5.0/4.5/4.0 via Volcengine Ark",
            "env_vars": [
                {
                    "key": "ARK_API_KEY",
                    "prompt": "Volcengine Ark API key",
                    "url": "https://console.volcengine.com/ark",
                },
            ],
        }

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def capabilities(self) -> Dict[str, Any]:
        return {"modalities": ["text"], "max_reference_images": 0}

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate a Seedream image and cache the returned image locally."""
        aspect = DEFAULT_ASPECT_RATIO
        model = DEFAULT_MODEL
        clean_prompt = ""

        try:
            aspect = resolve_aspect_ratio(aspect_ratio)
            clean_prompt = prompt.strip() if isinstance(prompt, str) else ""
            model_value = kwargs.get("model")
            if isinstance(model_value, str) and model_value in _MODELS:
                model = model_value
            api_key = (get_secret("ARK_API_KEY") or "").strip()
            if not api_key:
                return error_response(
                    error="ARK_API_KEY 未配置",
                    error_type="auth_required",
                    provider="volcengine",
                    model=model,
                    prompt=clean_prompt,
                    aspect_ratio=aspect,
                )

            payload: Dict[str, Any] = {
                "model": model,
                "prompt": clean_prompt,
                "size": _SIZES[aspect],
                "watermark": kwargs.get("watermark", False),
            }
            for optional_key in ("guidance_scale", "seed"):
                if optional_key in kwargs:
                    payload[optional_key] = kwargs[optional_key]

            response = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )

            if response.status_code == 401:
                return error_response(
                    error="无效的 ARK_API_KEY",
                    error_type="auth_error",
                    provider="volcengine",
                    model=model,
                    prompt=clean_prompt,
                    aspect_ratio=aspect,
                )

            try:
                result = response.json()
            except Exception:
                result = None

            api_error = _error_message(response, result)
            model_not_open = "ModelNotOpen" in api_error or (
                isinstance(result, dict) and "ModelNotOpen" in str(result)
            )
            if response.status_code == 404 or model_not_open:
                return error_response(
                    error=(
                        "Seedream 模型未开通，请前往火山方舟控制台开通模型："
                        "https://console.volcengine.com/ark"
                    ),
                    error_type="model_not_open",
                    provider="volcengine",
                    model=model,
                    prompt=clean_prompt,
                    aspect_ratio=aspect,
                )

            if not 200 <= response.status_code < 300:
                return error_response(
                    error=f"火山方舟生图失败 ({response.status_code}): {api_error}",
                    error_type="api_error",
                    provider="volcengine",
                    model=model,
                    prompt=clean_prompt,
                    aspect_ratio=aspect,
                )

            if not isinstance(result, dict):
                return error_response(
                    error="火山方舟返回了无效的 JSON 响应",
                    error_type="invalid_response",
                    provider="volcengine",
                    model=model,
                    prompt=clean_prompt,
                    aspect_ratio=aspect,
                )

            data = result.get("data")
            first = data[0] if isinstance(data, list) and data else None
            if not isinstance(first, dict):
                return error_response(
                    error="火山方舟返回的响应中没有图片数据",
                    error_type="empty_response",
                    provider="volcengine",
                    model=model,
                    prompt=clean_prompt,
                    aspect_ratio=aspect,
                )

            url = first.get("url")
            b64_json = first.get("b64_json")
            if isinstance(url, str) and url:
                image = str(save_url_image(url, prefix=f"volcengine_{model}"))
            elif isinstance(b64_json, str) and b64_json:
                image = str(save_b64_image(b64_json, prefix=f"volcengine_{model}"))
            else:
                return error_response(
                    error="火山方舟响应中既没有图片 URL，也没有 base64 数据",
                    error_type="empty_response",
                    provider="volcengine",
                    model=model,
                    prompt=clean_prompt,
                    aspect_ratio=aspect,
                )

            return success_response(
                image=image,
                model=model,
                prompt=clean_prompt,
                aspect_ratio=aspect,
                provider="volcengine",
                modality="text",
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            logger.warning("Volcengine image generation network error: %s", exc)
            return error_response(
                error=f"火山方舟网络请求失败: {exc}",
                error_type="network_error",
                provider="volcengine",
                model=model,
                prompt=clean_prompt,
                aspect_ratio=aspect,
            )
        except requests.RequestException as exc:
            logger.warning("Volcengine image generation request failed: %s", exc)
            return error_response(
                error=f"火山方舟网络请求失败: {exc}",
                error_type="network_error",
                provider="volcengine",
                model=model,
                prompt=clean_prompt,
                aspect_ratio=aspect,
            )
        except Exception as exc:
            logger.exception("Unexpected Volcengine image generation error")
            return error_response(
                error=f"火山方舟生图失败: {exc}",
                error_type="provider_error",
                provider="volcengine",
                model=model,
                prompt=clean_prompt,
                aspect_ratio=aspect,
            )


def register(ctx) -> None:
    """Register the Volcengine Seedream provider with Hermes."""
    ctx.register_image_gen_provider(VolcengineImageGenProvider())
