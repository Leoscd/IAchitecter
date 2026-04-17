from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str
    supabase_service_key: str
    minimax_api_key: str
    minimax_group_id: str
    secret_key: str
    environment: str = "development"
    allowed_origins: list[str] = ["http://localhost:3000"]
    log_level: str = "INFO"


settings = Settings()
