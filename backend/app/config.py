from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    port: int = Field(default=8080)
    log_level: str = Field(default="info")
    cors_origins: str = Field(default="*")
    model_path: str = Field(default="model/credit_model.joblib")
    features_path: str = Field(default="model/features.joblib")
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-flash-lite")
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.1-8b-instant")

    email_daily_limit: int = Field(default=100)

    # LangSmith tracing — read from .env and forwarded to os.environ in main.py
    langchain_tracing_v2: str = Field(default="")
    langsmith_api_key: str = Field(default="")
    langsmith_endpoint: str = Field(default="")
    langchain_project: str = Field(default="")

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()