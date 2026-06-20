from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "local"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    database_url: str = "sqlite:////data/beater.db"
    session_secret: str = "change-me"
    google_client_id: str = ""
    google_client_secret: str = ""
    gemini_api_key: str = ""
    sentry_dsn: str = ""
    sentry_environment: str = ""
    sentry_release: str = ""
    sentry_traces_sample_rate: float = 0.0
    sentry_send_default_pii: bool = False
    bogus_request_sentry_enabled: bool = True
    bogus_request_webhook_url: str = ""
    bogus_request_webhook_token: str = ""
    bogus_request_webhook_timeout_seconds: float = 3.0
    bogus_request_min_status_code: int = 400

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
