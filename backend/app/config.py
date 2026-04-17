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

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()