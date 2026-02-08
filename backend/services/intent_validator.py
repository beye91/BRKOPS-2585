"""
Intent Validation Service

Validates that parsed intents from LLM match the defined scope of use cases.
This prevents out-of-scope requests (e.g., BGP when only OSPF is defined) from
being processed through the pipeline.
"""

from typing import Dict, Tuple, Optional
from db.models import UseCase
import structlog

logger = structlog.get_logger(__name__)


def validate_intent_scope(intent: Dict, use_case: UseCase) -> Tuple[bool, Optional[str]]:
    """
    Validate that parsed intent is within the use case scope.

    Args:
        intent: Parsed intent from LLM (contains action, target_devices, parameters)
        use_case: UseCase model with allowed_actions and scope_validation_enabled

    Returns:
        (is_valid, error_message_if_invalid)

    Example:
        intent = {"action": "configure_bgp_as_65000", "target_devices": ["Router-1"]}
        use_case = UseCase(allowed_actions=["ospf", "routing"], scope_validation_enabled=True)
        is_valid, error = validate_intent_scope(intent, use_case)
        # Returns: (False, "Request scope mismatch: 'configure_bgp' is not allowed...")
    """
    # Skip validation if disabled for this use case
    if not use_case.scope_validation_enabled:
        logger.info(
            "Scope validation disabled for use case",
            use_case=use_case.name
        )
        return True, None

    # Extract action from intent
    action = intent.get("action", "").lower()
    if not action:
        logger.warning(
            "No action found in intent",
            use_case=use_case.name,
            intent=intent
        )
        return False, "Unable to determine action from request"

    # Get allowed keywords (prefer allowed_actions, fallback to trigger_keywords)
    allowed = use_case.allowed_actions or use_case.trigger_keywords or []
    if not allowed:
        logger.warning(
            "No allowed actions or trigger keywords defined for use case",
            use_case=use_case.name
        )
        # If no scope is defined, allow all requests
        return True, None

    # Normalize allowed keywords to lowercase
    allowed_lower = [kw.lower() for kw in allowed]

    # Check if action contains at least one allowed keyword
    action_matches = any(keyword in action for keyword in allowed_lower)

    if action_matches:
        logger.info(
            "Intent validated successfully",
            use_case=use_case.name,
            action=action,
            allowed=allowed_lower
        )
        return True, None

    # Validation failed - construct user-friendly error message
    allowed_display = ', '.join(kw.upper() for kw in allowed)
    error_message = (
        f"Out of scope: Your request \"{action.replace('_', ' ')}\" doesn't match the selected use case "
        f"\"{use_case.display_name}\". "
        f"This use case only handles: {allowed_display}. "
        f"Please select a different use case or modify your request."
    )

    logger.warning(
        "Intent validation failed",
        use_case=use_case.name,
        action=action,
        allowed=allowed_lower,
        error=error_message
    )

    return False, error_message


def get_validation_status(use_case: UseCase) -> Dict[str, any]:
    """
    Get the current validation configuration for a use case.

    Args:
        use_case: UseCase model

    Returns:
        Dictionary with validation status information
    """
    return {
        "scope_validation_enabled": use_case.scope_validation_enabled,
        "allowed_actions": use_case.allowed_actions or use_case.trigger_keywords or [],
        "servicenow_enabled": use_case.servicenow_enabled,
    }
