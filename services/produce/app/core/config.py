from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    REDIS_URL: str = "redis://redis:6379/1"
    SECRET_KEY: str = "supersecretkey_change_in_prod"
    ALGORITHM: str = "HS256"
    FARMER_SERVICE_URL: str = "http://farmer_service:8002"
    INTERNAL_API_KEY: str = "soko-internal-dev-key"

    class Config:
        env_file = ".env"


settings = Settings()
