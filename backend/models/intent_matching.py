# =============================================================================
# BRKOPS-2585 Intent Matching Models
# Data structures for LLM-based intent matching
# =============================================================================

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExtractedIntent(BaseModel):
    """Extracted intent details from LLM parsing."""

    action: str = Field(..., description="The specific action requested (must be from allowed_actions)")
    devices: List[str] = Field(default_factory=list, description="Target devices (router names, device IDs)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters (area, ASN, VLAN, etc.)")


class IntentMatchResult(BaseModel):
    """Result of LLM-based intent matching."""

    matched_use_case: Optional[str] = Field(None, description="Matched use case name or None if no match")
    confidence: float = Field(..., description="Confidence score 0-100")
    reasoning: str = Field(..., description="Explanation of why this use case was selected or not selected")
    extracted_intent: Optional[ExtractedIntent] = Field(None, description="Parsed intent details if matched")

    class Config:
        json_schema_extra = {
            "example": {
                "matched_use_case": "ospf_configuration_change",
                "confidence": 85.0,
                "reasoning": "Input clearly mentions OSPF protocol and area configuration",
                "extracted_intent": {
                    "action": "modify_ospf_area",
                    "devices": ["Router-1"],
                    "parameters": {"area": "10"}
                }
            }
        }
