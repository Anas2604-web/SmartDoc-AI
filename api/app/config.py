from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    # Groq is the preferred OpenAI-compatible provider for low-latency answers.
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    postgres_url: str = os.getenv("POSTGRES_URL", "")
    top_k: int = int(os.getenv("TOP_K", "3"))

    @property
    def answer_api_key(self) -> str:
        return self.groq_api_key or self.deepseek_api_key

    @property
    def answer_base_url(self) -> str:
        return self.groq_base_url if self.groq_api_key else self.deepseek_base_url

    @property
    def answer_model(self) -> str:
        return self.groq_model if self.groq_api_key else self.deepseek_model


settings = Settings()
