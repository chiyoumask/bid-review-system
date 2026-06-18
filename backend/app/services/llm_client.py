"""
LLM API 客户端 - 支持多渠道 OpenAI 兼容 API
"""
import json
import logging
import httpx
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Universal LLM client supporting OpenAI-compatible APIs.
    Works with DeepSeek, Qwen, OpenAI, and any compatible endpoint.
    """

    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 120):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self._client.aclose()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> str:
        """
        Send a chat completion request.

        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
            temperature: Sampling temperature
            max_tokens: Max tokens in response
            response_format: Optional {"type": "json_object"} for structured output

        Returns:
            The assistant's response text.
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            response = await self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"LLM API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            raise

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        """
        Send a chat request expecting JSON output.
        Parses the response into a dict.
        """
        # Try requesting JSON format first
        try:
            content = await self.chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return json.loads(content)
        except Exception:
            # Fallback: request without JSON format and try to parse
            content = await self.chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            # Try to extract JSON from response
            return self._extract_json(content)

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Try to extract JSON from text that might contain other content."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in markdown code fence
        import re
        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find { ... } block
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract JSON from LLM response: {text[:200]}...")
