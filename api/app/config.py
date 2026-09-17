from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    # DeepSeek remains the primary provider for this deployment.
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # SmartDoc's app-specific Groq key is the backup provider.
    groq_api_key: str = os.getenv("SMARTDOC_GROQ_API_KEY", "")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    postgres_url: str = os.getenv("POSTGRES_URL", "")
    top_k: int = int(os.getenv("TOP_K", "3"))

    @property
    def answer_api_key(self) -> str:
        return self.deepseek_api_key or self.groq_api_key

    @property
    def answer_base_url(self) -> str:
        return self.deepseek_base_url if self.deepseek_api_key else self.groq_base_url

    @property
    def answer_model(self) -> str:
        return self.deepseek_model if self.deepseek_api_key else self.groq_model

    @property
    def answer_provider(self) -> str | None:
        if self.deepseek_api_key:
            return "deepseek"
        if self.groq_api_key:
            return "groq"
        return None

    @property
    def answer_providers(self) -> tuple[tuple[str, str, str, str], ...]:
        providers = []
        if self.deepseek_api_key:
            providers.append(("deepseek", self.deepseek_api_key, self.deepseek_base_url, self.deepseek_model))
        if self.groq_api_key:
            providers.append(("groq", self.groq_api_key, self.groq_base_url, self.groq_model))
        return tuple(providers)


settings = Settings()
