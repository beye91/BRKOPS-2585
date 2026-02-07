# =============================================================================
# BRKOPS-2585 Backend Configuration
# Environment-based configuration with Pydantic Settings
# =============================================================================

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ==========================================================================
    # Application
    # ==========================================================================
    app_name: str = "BRKOPS-2585"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = "changeme-generate-secure-key"

    # ==========================================================================
    # Server
    # ==========================================================================
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ==========================================================================
    # Database
    # ==========================================================================
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "brkops2585"
    postgres_user: str = "brkops"
    postgres_password: str = "changeme"

    @property
    def database_url(self) -> str:
        """Construct async database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Construct sync database URL for migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ==========================================================================
    # Redis
    # ==========================================================================
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: Optional[str] = None

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"

    # ==========================================================================
    # LLM Providers
    # ==========================================================================
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    llm_timeout: int = 30

    # ==========================================================================
    # MCP Servers
    # ==========================================================================
    cml_mcp_url: Optional[str] = None
    cml_host: Optional[str] = None
    cml_username: Optional[str] = None
    cml_password: Optional[str] = None

    splunk_mcp_url: Optional[str] = None
    splunk_host: Optional[str] = None
    splunk_token: Optional[str] = None

    # ==========================================================================
    # Notifications
    # ==========================================================================
    webex_webhook_url: Optional[str] = None
    webex_bot_token: Optional[str] = None
    webex_room_id: Optional[str] = None
    servicenow_instance: Optional[str] = None
    servicenow_username: Optional[str] = None
    servicenow_password: Optional[str] = None

    # ==========================================================================
    # Pipeline Defaults
    # ==========================================================================
    pipeline_convergence_wait: int = 45
    pipeline_mcp_timeout: int = 60
    pipeline_max_retries: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export singleton
settings = get_settings()
