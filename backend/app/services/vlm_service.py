"""
Vision-language model service using local Ollama.
"""

from __future__ import annotations

import base64
import os
from typing import List, Optional

import httpx


class VLMError(RuntimeError):
    pass


def _encode_image_bytes(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


async def label_zone_with_vlm(
    image_bytes: bytes,
    candidate_labels: List[str],
    prompt: str,
    model: Optional[str] = None,
) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # Remove /v1 suffix if present (Ollama API is at root, not /v1)
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    model_name = model or os.getenv("VLM_MODEL", "llava:latest")
    url = f"{base_url}/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "images": [_encode_image_bytes(image_bytes)],
        "stream": False,
    }
    
    # Check connection and model availability before attempting call
    try:
        import httpx
        # Remove /v1 suffix if present for tags endpoint
        tags_url = base_url if not base_url.endswith("/v1") else base_url[:-3]
        async with httpx.AsyncClient(timeout=5) as check_client:
            check_response = await check_client.get(f"{tags_url}/api/tags")
            if check_response.status_code != 200:
                raise VLMError(
                    f"Ollama server not accessible: HTTP {check_response.status_code}. "
                    f"Start Ollama with: ollama serve"
                )
            # Verify model is available (but don't fail if check has issues)
            try:
                tags_data = check_response.json()
                available_models = [m.get("name", "") for m in tags_data.get("models", [])]
                if model_name not in available_models:
                    # Try without tag (e.g., "llava:7b" vs "llava")
                    model_base = model_name.split(":")[0] if ":" in model_name else model_name
                    if not any(model_base in m for m in available_models):
                        # Log warning but don't fail - let the actual API call determine if model exists
                        import logging
                        logger = logging.getLogger("gamed_ai.services.vlm_service")
                        logger.warning(
                            f"Model '{model_name}' not found in available models: {available_models[:5]}. "
                            f"Will attempt API call anyway."
                        )
            except Exception:
                # If model check fails, continue anyway - API call will handle it
                pass
    except httpx.ConnectError:
        raise VLMError(
            f"Cannot connect to Ollama at {base_url}. "
            f"Start Ollama server with: ollama serve"
        )
    except VLMError:
        # Re-raise VLM errors
        raise
    except Exception as e:
        # Other errors, log but continue (model might still work)
        import logging
        logger = logging.getLogger("gamed_ai.services.vlm_service")
        logger.warning(f"Model check failed, attempting call anyway: {e}")
    
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(url, json=payload)
        except httpx.ConnectError:
            raise VLMError(
                f"Cannot connect to Ollama at {base_url}. "
                f"Start Ollama server with: ollama serve"
            )
        
        if response.status_code == 404:
            raise VLMError(
                f"VLM model '{model_name}' not found. "
                f"Pull model with: ollama pull {model_name}"
            )
        elif response.status_code != 200:
            error_text = response.text[:200] if response.text else "Unknown error"
            raise VLMError(
                f"Ollama VLM API error: HTTP {response.status_code}. "
                f"Response: {error_text}"
            )
        
        data = response.json()
    content = (data.get("response") or "").strip()
    if not content:
        raise VLMError("Empty VLM response from Ollama")
    # Return raw content; caller will normalize against candidate labels
    return content
