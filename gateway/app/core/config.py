from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_port: int = 8000

    identity_service_url: str = "http://identity-service:8001"
    incident_service_url: str = "http://incident-service:8002"
    ai_service_url: str = "http://ai-service:8003"
    gamification_service_url: str = "http://gamification-service:8004"

    redis_url: str = "redis://redis:6379/0"

    frontend_origins: str = "http://localhost:5173,http://localhost:3000"

    rate_limit_login_per_minute: int = 10
    rate_limit_general_per_minute: int = 100

    @property
    def frontend_origin_list(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


settings = Settings()
