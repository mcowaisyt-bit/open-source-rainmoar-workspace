from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.database.models import User, AICredential, UserSettings
from app.core.security import decrypt_credential
from app.ai.providers import OpenAIProvider, XAIProvider, GeminiProvider, BaseAIProvider
import logging

logger = logging.getLogger(__name__)


class AIRouter:
    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {
            "openai": OpenAIProvider(),
            "xai": XAIProvider(),
            "gemini": GeminiProvider(),
        }
        self.task_preferences = {
            "reasoning": ["openai", "xai", "gemini"],
            "coding": ["openai", "xai", "gemini"],
            "writing": ["openai", "xai", "gemini"],
            "classification": ["gemini", "openai", "xai"],
            "fast": ["gemini", "xai", "openai"],
            "default": ["openai", "xai", "gemini"],
        }
        self.default_models = {
            "openai": "gpt-4o-mini",
            "xai": "grok-2-mini",
            "gemini": "gemini-1.5-flash",
        }

    def _get_user_credentials(self, user: User, db: Session) -> Dict[str, str]:
        creds = {}
        for c in db.query(AICredential).filter(
            AICredential.user_id == user.id,
            AICredential.is_active == True,
        ).all():
            try:
                creds[c.provider] = decrypt_credential(c.encrypted_api_key)
            except Exception:
                logger.warning(f"Failed to decrypt credential for {c.provider}")
        return creds

    def _infer_task_type(self, messages: List[Dict[str, str]]) -> str:
        text = " ".join(m.get("content", "") for m in messages).lower()
        if any(k in text for k in ["code", "function", "bug", "python", "javascript", "implement"]):
            return "coding"
        if any(k in text for k in ["reason", "analyze", "explain why", "complex", "deep"]):
            return "reasoning"
        if any(k in text for k in ["write", "draft", "email", "letter", "summarize"]):
            return "writing"
        if any(k in text for k in ["classify", "categorize", "label", "is this important"]):
            return "classification"
        if len(text) < 200:
            return "fast"
        return "default"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        user: User,
        db: Session,
        model: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        task_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        creds = self._get_user_credentials(user, db)
        settings = user.settings or UserSettings(auto_routing=True, auto_fallback=True)

        if not creds:
            raise ValueError("No AI providers connected. Please add an API key in Integrations.")

        if model and model != "auto" and model in self.providers:
            chain = [model]
        elif model and model not in ("auto",) and any(
            model.startswith(p) or (p == "openai" and model.startswith("gpt")) for p in self.providers
        ):
            chain = []
            for p in self.providers:
                if model.startswith(p) or (p == "openai" and model.startswith("gpt")):
                    chain = [p]
                    break
            if not chain:
                chain = list(creds.keys())
        else:
            task = task_hint or self._infer_task_type(messages)
            preferred = self.task_preferences.get(task, self.task_preferences["default"])
            chain = [p for p in preferred if p in creds]
            if not chain:
                chain = list(creds.keys())

        if not getattr(settings, "auto_fallback", True):
            chain = chain[:1]

        last_error = None
        fallback_log: List[Dict[str, str]] = []
        max_retries = 3

        for provider_name in chain[:max_retries]:
            if provider_name not in creds:
                continue
            provider = self.providers[provider_name]
            api_key = creds[provider_name]
            selected_model = self.default_models.get(provider_name)

            if model and model not in ("auto",) and model not in self.providers:
                selected_model = model

            try:
                result = await provider.chat(
                    messages=messages,
                    model=selected_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=api_key,
                )
                result["fallback_log"] = fallback_log
                result["was_fallback"] = len(fallback_log) > 0
                if fallback_log:
                    result["routing_note"] = (
                        f"AUTO: {fallback_log[0].get('provider')} unavailable → using {provider_name}"
                    )
                else:
                    result["routing_note"] = f"AUTO → {provider_name}" if model == "auto" or not model else f"{provider_name}"
                return result
            except RuntimeError as e:
                err = str(e)
                last_error = err
                fallback_log.append({"provider": provider_name, "error": err})
                logger.warning(f"Provider {provider_name} failed: {err}")
                if err not in ("RATE_LIMIT", "PROVIDER_UNAVAILABLE"):
                    # Still try next on unexpected errors if fallback enabled
                    continue
                continue
            except Exception as e:
                last_error = str(e)
                fallback_log.append({"provider": provider_name, "error": str(e)})
                logger.warning(f"Provider {provider_name} error: {e}")
                continue

        raise RuntimeError(
            f"No available AI provider could complete this task. Last error: {last_error}"
        )


_router: Optional[AIRouter] = None


def get_ai_router() -> AIRouter:
    global _router
    if _router is None:
        _router = AIRouter()
    return _router
