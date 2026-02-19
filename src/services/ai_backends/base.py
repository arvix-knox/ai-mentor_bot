from abc import ABC, abstractmethod


class BaseAIBackend(ABC):
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        context: str,
        user_message: str,
        max_tokens: int = 1000,
    ) -> str:
        pass

    @abstractmethod
    async def generate_summary(self, text: str) -> str:
        pass