# =============================================================================
# BRKOPS-2585 Device Resolver
# Resolves "all routers", "all devices", specific device names to actual
# CML lab nodes. Used during intent parsing to expand target_devices.
# =============================================================================

import re
from typing import Any, Dict, List, Optional, Tuple

import structlog

from services.cml_client import CMLClient

logger = structlog.get_logger()

# Router node definitions recognized by CML
ROUTER_NODE_DEFINITIONS = {
    "cat8000v",
    "iosv",
    "csr1000v",
    "iosxrv9000",
    "iosxrv",
    "iosvl2",  # L2 switch but sometimes used as router
}

# Node states considered "alive" and targetable
ACTIVE_NODE_STATES = {"BOOTED", "STARTED"}

# Patterns that mean "target all routers"
ALL_KEYWORDS = {
    "all",
    "all routers",
    "all devices",
    "every router",
    "every device",
    "all network devices",
    "all of them",
    "all the routers",
}


def is_all_keyword(targets: List[str]) -> bool:
    """
    Check if target_devices list contains an "all" keyword.

    Examples:
        ["all"] -> True
        ["all routers"] -> True
        ["Router-1"] -> False
        ["Router-1", "Router-2"] -> False
    """
    if not targets or len(targets) != 1:
        return False

    target = targets[0].strip().lower()
    return target in ALL_KEYWORDS


async def get_available_routers(
    client: CMLClient,
    lab_id: str,
) -> List[Dict[str, Any]]:
    """
    Query CML for all active router nodes in a lab.

    Returns list of node dicts with at least: id, label, node_definition, state
    """
    nodes = await client.get_nodes(lab_id)

    routers = []
    for node in nodes:
        node_def = (node.get("node_definition") or "").lower()
        state = (node.get("state") or "").upper()
        label = node.get("label", "")

        # Filter to routers by node_definition AND active state
        if node_def in ROUTER_NODE_DEFINITIONS and state in ACTIVE_NODE_STATES:
            routers.append(node)
            logger.debug(
                "Found active router",
                label=label,
                node_definition=node_def,
                state=state,
            )

    # Sort by label for consistent ordering
    routers.sort(key=lambda n: n.get("label", ""))

    logger.info(
        "Available routers resolved",
        count=len(routers),
        labels=[r.get("label") for r in routers],
    )

    return routers


async def resolve_target_devices(
    raw_targets: List[str],
    client: CMLClient,
    lab_id: str,
) -> Tuple[List[str], List[str]]:
    """
    Resolve raw target_devices from intent to actual CML node labels.

    If raw_targets contains an "all" keyword, resolves to all active routers.
    If raw_targets contains specific names, validates each exists in CML.

    Args:
        raw_targets: Target device list from intent (e.g. ["all"], ["Router-1", "Router-3"])
        client: CML client instance
        lab_id: CML lab ID

    Returns:
        (resolved_labels, errors) tuple.
        resolved_labels: list of valid device labels
        errors: list of error messages (e.g. device not found)
    """
    if not raw_targets:
        return [], ["No target devices specified"]

    available = await get_available_routers(client, lab_id)
    available_labels = [r.get("label", "") for r in available]

    # Case 1: "all" keyword -> return all available routers
    if is_all_keyword(raw_targets):
        if not available_labels:
            return [], [
                "No active routers found in CML lab. "
                "Ensure routers are in BOOTED/STARTED state."
            ]

        logger.info(
            "Resolved 'all' to available routers",
            count=len(available_labels),
            devices=available_labels,
        )
        return available_labels, []

    # Case 2: Specific device names -> validate each
    resolved = []
    errors = []

    for target in raw_targets:
        target_clean = target.strip()

        # Case-insensitive label match
        matched = None
        for label in available_labels:
            if label.lower() == target_clean.lower():
                matched = label
                break

        if matched:
            if matched not in resolved:  # avoid duplicates
                resolved.append(matched)
        else:
            errors.append(
                f"Device '{target_clean}' not found or not active. "
                f"Available devices: {', '.join(available_labels)}"
            )

    if not resolved and errors:
        logger.warning(
            "No target devices could be resolved",
            raw_targets=raw_targets,
            available=available_labels,
            errors=errors,
        )
    elif errors:
        logger.warning(
            "Some target devices not found",
            resolved=resolved,
            errors=errors,
        )
    else:
        logger.info(
            "All target devices resolved",
            resolved=resolved,
        )

    return resolved, errors
