import time
import logging
import httpx

from src.config import settings
from src.services.ai_backends.base import BaseAIBackend

logger = logging.getLogger(__name__)


class OpenRouterBackend(BaseAIBackend):
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "meta-llama/llama-3.1-8b-instruct:free"
        self.client = httpx.AsyncClient(timeout=35.0)

    async def generate(
        self,
        system_prompt: str,
        context: str,
        user_message: str,
        max_tokens: int = 1000,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if context:
            messages.append(
                {"role": "user", "content": f"Context:\n{context}"}
            )
            messages.append(
                {"role": "assistant", "content": "Understood. I have the context."}
            )

        messages.append({"role": "user", "content": user_message})

        start_time = time.monotonic()

        try:
            response = await self.client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/mentor-bot",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.45,
                },
            )
            response.raise_for_status()
            data = response.json()

            elapsed = int((time.monotonic() - start_time) * 1000)
            logger.info(f"OpenRouter response in {elapsed}ms")

            return data["choices"][0]["message"]["content"].strip()

        except httpx.TimeoutException:
            logger.error("OpenRouter API timeout")
            return "⏳ AI наставник думает слишком долго. Попробуй позже."

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code}")
            if e.response.status_code == 429:
                return "⚠️ Слишком много запросов к AI. Подожди минуту."
            return "⚠️ AI наставник временно недоступен."

        except Exception as e:
            logger.error(f"OpenRouter unexpected error: {e}")
            return "⚠️ Ошибка AI. Попробуй позже."

    async def generate_summary(self, text: str) -> str:
        return await self.generate(
            system_prompt="You are a concise summarizer. Respond in Russian. Use bullet points.",
            context="",
            user_message=f"Summarize this in 3-5 bullet points:\n{text}",
            max_tokens=300,
        )
