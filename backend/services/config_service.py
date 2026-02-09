# =============================================================================
# BRKOPS-2585 Config Service
# Read configuration from database config_variables table
# =============================================================================

import json
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ConfigVariable

logger = structlog.get_logger()


class ConfigService:
    """Service for reading configuration from database."""

    @staticmethod
    async def get_config(db: AsyncSession, key: str, default: Any = None) -> Any:
        """
        Get a configuration value from the database.

        Args:
            db: Database session
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value (parsed from JSON) or default
        """
        try:
            result = await db.execute(
                select(ConfigVariable).where(ConfigVariable.key == key)
            )
            config_var = result.scalar_one_or_none()

            if not config_var:
                return default

            # Value is stored as JSONB, so it's already parsed
            value = config_var.value

            # Handle quoted strings (JSON strings need to be unquoted)
            if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                return value[1:-1]  # Remove quotes

            return value

        except Exception as e:
            logger.warning(
                "Failed to read config from database",
                key=key,
                error=str(e)
            )
            return default

    @staticmethod
    async def get_llm_config(db: AsyncSession) -> dict:
        """
        Get all LLM configuration from database.

        Args:
            db: Database session

        Returns:
            Dictionary with LLM configuration
        """
        try:
            result = await db.execute(
                select(ConfigVariable).where(ConfigVariable.category == 'llm')
            )
            config_vars = result.scalars().all()

            config = {}
            for var in config_vars:
                # Remove category prefix from key (llm.temperature -> temperature)
                key = var.key
                if '.' in key:
                    key = key.split('.', 1)[1]

                # Unwrap JSON string values
                value = var.value
                if isinstance(value, str) and value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]

                config[key] = value

            logger.info("LLM configuration loaded from database", keys=list(config.keys()))
            return config

        except Exception as e:
            logger.error("Failed to load LLM config from database", error=str(e))
            return {}
