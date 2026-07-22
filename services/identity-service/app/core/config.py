from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@identity-db:5432/identity_db"
    service_port: int = 8001

    jwt_secret: str = "dev-only-secret-change-me"
    access_token_expire_minutes: int = 15
    otp_expire_minutes: int = 5

    admin_email: str = "admin@netopscell.local"
    admin_password: str = "Admin123!"

    class Config:
        env_file = ".env"


settings = Settings()
