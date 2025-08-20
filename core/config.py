from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, field_validator
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    app_name: str = "Smartelia API"
    environment: Literal["dev", "staging", "prod"] = "dev"
    secret_key: SecretStr
    access_token_expires_minutes: int = 30
    cors_origins: list[str] = Field(default_factory=list)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    enable_docs: bool = True
    database_url: str | None = None
    database_pool_size: int = 5
    database_pool_overflow: int = 10
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # Paths
    static_dir: str = "static"
    templates_dir: str = "templates"
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if len(v.get_secret_value()) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

settings = Settings()
