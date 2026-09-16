from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    postgres_url: str = os.getenv("POSTGRES_URL", "")
    top_k: int = int(os.getenv("TOP_K", "3"))


settings = Settings()
