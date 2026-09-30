from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import httpx
from app.core.config import get_settings

settings = get_settings()


class BaseAIProvider(ABC):
    name: str
    models: List[str]
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def health_check(self, api_key: Optional[str] = None) -> bool:
        pass


class OpenAIProvider(BaseAIProvider):
    name = "openai"
    models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    base_url = "https://api.openai.com/v1"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        key = api_key or settings.OPENAI_API_KEY
        if not key:
            raise ValueError("OpenAI API key not configured")
        
        model = model or "gpt-4o-mini"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if resp.status_code == 429:
                raise RuntimeError("RATE_LIMIT")
            if resp.status_code >= 500:
                raise RuntimeError("PROVIDER_UNAVAILABLE")
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            return {
                "content": choice["message"]["content"],
                "model": data.get("model", model),
                "provider": self.name,
                "usage": data.get("usage", {}),
            }
    
    async def health_check(self, api_key: Optional[str] = None) -> bool:
        key = api_key or settings.OPENAI_API_KEY
        if not key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False


class XAIProvider(BaseAIProvider):
    name = "xai"
    models = ["grok-2", "grok-2-mini", "grok-beta"]
    base_url = "https://api.x.ai/v1"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        key = api_key or settings.XAI_API_KEY
        if not key:
            raise ValueError("xAI API key not configured")
        
        model = model or "grok-2-mini"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if resp.status_code == 429:
                raise RuntimeError("RATE_LIMIT")
            if resp.status_code >= 500:
                raise RuntimeError("PROVIDER_UNAVAILABLE")
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            return {
                "content": choice["message"]["content"],
                "model": data.get("model", model),
                "provider": self.name,
                "usage": data.get("usage", {}),
            }
    
    async def health_check(self, api_key: Optional[str] = None) -> bool:
        key = api_key or settings.XAI_API_KEY
        if not key:
            return False
        try:
            # Simple models list or a lightweight call
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                return resp.status_code in (200, 404)  # some endpoints may differ
        except Exception:
            return False


class GeminiProvider(BaseAIProvider):
    name = "gemini"
    models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"]
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        key = api_key or settings.GOOGLE_API_KEY
        if not key:
            raise ValueError("Google API key not configured")
        
        model = model or "gemini-1.5-flash"
        
        # Convert OpenAI-style messages to Gemini format
        contents = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/models/{model}:generateContent?key={key}",
                headers={"Content-Type": "application/json"},
                json=body,
            )
            if resp.status_code == 429:
                raise RuntimeError("RATE_LIMIT")
            if resp.status_code >= 500:
                raise RuntimeError("PROVIDER_UNAVAILABLE")
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("No response from Gemini")
            text = candidates[0]["content"]["parts"][0]["text"]
            return {
                "content": text,
                "model": model,
                "provider": self.name,
                "usage": data.get("usageMetadata", {}),
            }
    
    async def health_check(self, api_key: Optional[str] = None) -> bool:
        key = api_key or settings.GOOGLE_API_KEY
        if not key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models?key={key}",
                )
                return resp.status_code == 200
        except Exception:
            return False
