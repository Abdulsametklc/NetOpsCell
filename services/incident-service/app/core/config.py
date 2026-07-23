from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "incident-service"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/incident_db"
    ai_service_url: str = "http://localhost:8003"
    identity_service_url: str = "http://localhost:8001"
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
