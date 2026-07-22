from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "ai-service"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5434/ai_db"
    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    llm_timeout_seconds: float = 4.0
    llm_circuit_breaker_threshold: int = 3
    llm_circuit_breaker_cooldown_seconds: float = 30.0


settings = Settings()
