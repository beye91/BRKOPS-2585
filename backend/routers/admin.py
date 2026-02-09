# =============================================================================
# BRKOPS-2585 Admin Router
# Configuration and use case management endpoints
# =============================================================================

from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import ConfigVariable, UseCase, User
from models.admin import (
    ConfigVariableCreate,
    ConfigVariableUpdate,
    ConfigVariableResponse,
    ConfigCategory,
    UseCaseCreate,
    UseCaseUpdate,
    UseCaseResponse,
    UserResponse,
    LoginRequest,
    TokenResponse,
)

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# Configuration Variables
# =============================================================================
@router.get("/config", response_model=List[ConfigCategory])
async def get_all_config(
    db: AsyncSession = Depends(get_db),
):
    """Get all configuration variables grouped by category."""
    result = await db.execute(
        select(ConfigVariable).order_by(ConfigVariable.category, ConfigVariable.key)
    )
    variables = result.scalars().all()

    # Group by category
    categories = {}
    for var in variables:
        if var.category not in categories:
            categories[var.category] = []
        categories[var.category].append(
            ConfigVariableResponse(
                id=var.id,
                key=var.key,
                value=var.value if not var.is_secret else "***MASKED***",
                description=var.description,
                category=var.category,
                is_secret=var.is_secret,
                created_at=var.created_at,
                updated_at=var.updated_at,
            )
        )

    return [
        ConfigCategory(category=cat, variables=vars)
        for cat, vars in categories.items()
    ]


@router.get("/config/{key}", response_model=ConfigVariableResponse)
async def get_config_variable(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific configuration variable."""
    result = await db.execute(select(ConfigVariable).where(ConfigVariable.key == key))
    var = result.scalar_one_or_none()

    if not var:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration variable '{key}' not found",
        )

    return ConfigVariableResponse(
        id=var.id,
        key=var.key,
        value=var.value if not var.is_secret else "***MASKED***",
        description=var.description,
        category=var.category,
        is_secret=var.is_secret,
        created_at=var.created_at,
        updated_at=var.updated_at,
    )


@router.post("/config", response_model=ConfigVariableResponse, status_code=status.HTTP_201_CREATED)
async def create_config_variable(
    config: ConfigVariableCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new configuration variable."""
    # Check if key exists
    result = await db.execute(select(ConfigVariable).where(ConfigVariable.key == config.key))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration variable '{config.key}' already exists",
        )

    var = ConfigVariable(
        key=config.key,
        value=config.value,
        description=config.description,
        category=config.category,
        is_secret=config.is_secret,
    )

    db.add(var)
    await db.commit()
    await db.refresh(var)

    logger.info("Config variable created", key=config.key, category=config.category)

    return ConfigVariableResponse(
        id=var.id,
        key=var.key,
        value=var.value if not var.is_secret else "***MASKED***",
        description=var.description,
        category=var.category,
        is_secret=var.is_secret,
        created_at=var.created_at,
        updated_at=var.updated_at,
    )


@router.put("/config/{key}", response_model=ConfigVariableResponse)
async def update_config_variable(
    key: str,
    update: ConfigVariableUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a configuration variable."""
    result = await db.execute(select(ConfigVariable).where(ConfigVariable.key == key))
    var = result.scalar_one_or_none()

    if not var:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration variable '{key}' not found",
        )

    if update.value is not None:
        var.value = update.value
    if update.description is not None:
        var.description = update.description
    if update.is_secret is not None:
        var.is_secret = update.is_secret

    await db.commit()
    await db.refresh(var)

    logger.info("Config variable updated", key=key)

    return ConfigVariableResponse(
        id=var.id,
        key=var.key,
        value=var.value if not var.is_secret else "***MASKED***",
        description=var.description,
        category=var.category,
        is_secret=var.is_secret,
        created_at=var.created_at,
        updated_at=var.updated_at,
    )


@router.delete("/config/{key}")
async def delete_config_variable(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a configuration variable."""
    result = await db.execute(select(ConfigVariable).where(ConfigVariable.key == key))
    var = result.scalar_one_or_none()

    if not var:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration variable '{key}' not found",
        )

    await db.delete(var)
    await db.commit()

    logger.info("Config variable deleted", key=key)

    return {"success": True, "message": f"Configuration variable '{key}' deleted"}


# =============================================================================
# Use Cases
# =============================================================================
@router.get("/use-cases", response_model=List[UseCaseResponse])
async def list_use_cases(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all use cases."""
    query = select(UseCase).order_by(UseCase.sort_order, UseCase.name)

    if not include_inactive:
        query = query.where(UseCase.is_active == True)

    result = await db.execute(query)
    use_cases = result.scalars().all()

    return [UseCaseResponse.model_validate(uc) for uc in use_cases]


@router.get("/use-cases/{use_case_id}", response_model=UseCaseResponse)
async def get_use_case(
    use_case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific use case."""
    result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
    uc = result.scalar_one_or_none()

    if not uc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Use case {use_case_id} not found",
        )

    return UseCaseResponse.model_validate(uc)


@router.post("/use-cases", response_model=UseCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_use_case(
    use_case: UseCaseCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new use case."""
    # Check if name exists
    result = await db.execute(select(UseCase).where(UseCase.name == use_case.name))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Use case '{use_case.name}' already exists",
        )

    uc = UseCase(
        name=use_case.name,
        display_name=use_case.display_name,
        description=use_case.description,
        trigger_keywords=use_case.trigger_keywords,
        intent_prompt=use_case.intent_prompt,
        config_prompt=use_case.config_prompt,
        analysis_prompt=use_case.analysis_prompt,
        notification_template=use_case.notification_template,
        cml_target_lab=use_case.cml_target_lab,
        splunk_index=use_case.splunk_index,
        convergence_wait_seconds=use_case.convergence_wait_seconds,
        servicenow_enabled=use_case.servicenow_enabled,
        allowed_actions=use_case.allowed_actions,
        scope_validation_enabled=use_case.scope_validation_enabled,
        llm_provider=use_case.llm_provider,
        llm_model=use_case.llm_model,
        explanation_template=use_case.explanation_template,
        impact_description=use_case.impact_description,
        splunk_query_config=use_case.splunk_query_config,
        pre_checks=use_case.pre_checks,
        post_checks=use_case.post_checks,
        risk_profile=use_case.risk_profile,
        is_active=use_case.is_active,
        sort_order=use_case.sort_order,
    )

    db.add(uc)
    await db.commit()
    await db.refresh(uc)

    logger.info("Use case created", name=use_case.name)

    return UseCaseResponse.model_validate(uc)


@router.put("/use-cases/{use_case_id}", response_model=UseCaseResponse)
async def update_use_case(
    use_case_id: int,
    update: UseCaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a use case."""
    result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
    uc = result.scalar_one_or_none()

    if not uc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Use case {use_case_id} not found",
        )

    if update.display_name is not None:
        uc.display_name = update.display_name
    if update.description is not None:
        uc.description = update.description
    if update.trigger_keywords is not None:
        uc.trigger_keywords = update.trigger_keywords
    if update.intent_prompt is not None:
        uc.intent_prompt = update.intent_prompt
    if update.config_prompt is not None:
        uc.config_prompt = update.config_prompt
    if update.analysis_prompt is not None:
        uc.analysis_prompt = update.analysis_prompt
    if update.notification_template is not None:
        uc.notification_template = update.notification_template
    if update.cml_target_lab is not None:
        uc.cml_target_lab = update.cml_target_lab
    if update.splunk_index is not None:
        uc.splunk_index = update.splunk_index
    if update.convergence_wait_seconds is not None:
        uc.convergence_wait_seconds = update.convergence_wait_seconds
    if update.servicenow_enabled is not None:
        uc.servicenow_enabled = update.servicenow_enabled
    if update.explanation_template is not None:
        uc.explanation_template = update.explanation_template
    if update.impact_description is not None:
        uc.impact_description = update.impact_description
    if update.splunk_query_config is not None:
        uc.splunk_query_config = update.splunk_query_config
    if update.pre_checks is not None:
        uc.pre_checks = update.pre_checks
    if update.post_checks is not None:
        uc.post_checks = update.post_checks
    if update.risk_profile is not None:
        uc.risk_profile = update.risk_profile
    if update.is_active is not None:
        uc.is_active = update.is_active
    if update.sort_order is not None:
        uc.sort_order = update.sort_order

    await db.commit()
    await db.refresh(uc)

    logger.info("Use case updated", id=use_case_id)

    return UseCaseResponse.model_validate(uc)


@router.delete("/use-cases/{use_case_id}")
async def delete_use_case(
    use_case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a use case."""
    result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
    uc = result.scalar_one_or_none()

    if not uc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Use case {use_case_id} not found",
        )

    await db.delete(uc)
    await db.commit()

    logger.info("Use case deleted", id=use_case_id)

    return {"success": True, "message": f"Use case {use_case_id} deleted"}


# =============================================================================
# Users (Basic - for admin authentication)
# =============================================================================
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
):
    """List all users."""
    result = await db.execute(select(User).order_by(User.username))
    users = result.scalars().all()

    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role if isinstance(user.role, str) else user.role.value,
            is_active=user.is_active,
            last_login=user.last_login,
            created_at=user.created_at,
        )
        for user in users
    ]


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT token."""
    from passlib.hash import bcrypt
    from jose import jwt
    from datetime import datetime, timedelta

    result = await db.execute(
        select(User).where(User.username == request.username, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not bcrypt.verify(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Generate JWT
    from config import settings

    expires = datetime.utcnow() + timedelta(hours=24)
    token_data = {
        "sub": user.username,
        "role": user.role.value,
        "exp": expires,
    }
    token = jwt.encode(token_data, settings.secret_key, algorithm="HS256")

    logger.info("User logged in", username=user.username)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=86400,  # 24 hours
    )
