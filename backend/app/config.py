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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
