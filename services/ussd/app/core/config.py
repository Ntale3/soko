from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL:             str
    INTERNAL_SECRET:          str

    # Africa's Talking — USSD
    AT_USERNAME:              str
    AT_API_KEY:               str

    PRODUCE_SERVICE_URL:      str = "http://produce-service:8003"
    ORDER_SERVICE_URL:        str = "http://order-service:8004"
    AUTH_SERVICE_URL:         str = "http://auth-service:8001"
    USER_SERVICE_URL:         str = "http://user-service:8002"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8008"

    class Config:
        env_file = ".env"


settings = Settings()