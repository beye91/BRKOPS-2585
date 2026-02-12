# =============================================================================
# BRKOPS-2585 Intent Matcher Service
# Fully dynamic LLM-based intent matching and parsing
# =============================================================================

import json
from typing import List, Optional

import structlog

from db.models import UseCase
from models.intent_matching import IntentMatchResult, ExtractedIntent
from services.llm_service import LLMService

logger = structlog.get_logger()


class IntentMatcherService:
    """Fully dynamic LLM-based intent matching and parsing."""

    def __init__(self, llm_service: LLMService, temperature: float = 0.3):
        self.llm = llm_service
        self.temperature = temperature

    async def match_and_parse_intent(
        self,
        user_input: str,
        use_cases: List[UseCase],
        force_use_case: Optional[str] = None
    ) -> IntentMatchResult:
        """
        Single-pass LLM intent matching + parsing.

        Args:
            user_input: Raw user input
            use_cases: All available use cases from database
            force_use_case: Optional forced use case (for advanced mode)

        Returns:
            IntentMatchResult with matched use case + parsed intent
        """
        if force_use_case:
            # Advanced mode: skip matching, use specified use case
            selected_case = next((uc for uc in use_cases if uc.name == force_use_case), None)
            if not selected_case:
                raise ValueError(f"Use case not found: {force_use_case}")

            # Still parse intent with LLM
            logger.info(
                "Force mode enabled - using specified use case",
                use_case=force_use_case,
                user_input=user_input
            )
            intent = await self._parse_intent(user_input, selected_case)
            return IntentMatchResult(
                matched_use_case=selected_case.name,
                confidence=100.0,
                reasoning="User-specified use case (force mode)",
                extracted_intent=intent
            )

        # Build prompt with all use cases
        prompt = self._build_matching_prompt(user_input, use_cases)

        logger.info(
            "Matching intent with LLM",
            user_input=user_input,
            available_use_cases=[uc.name for uc in use_cases]
        )

        # Call LLM
        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt="You are an expert network automation intent classifier. Be strict - better to return no match than guess wrong.",
                json_response=True,
                temperature=self.temperature
            )

            # Parse JSON response
            result = json.loads(response)

            if result["matched_use_case"] == "no_match":
                logger.info(
                    "No use case matched",
                    reasoning=result["reasoning"],
                    confidence=result["confidence"]
                )
                return IntentMatchResult(
                    matched_use_case=None,
                    confidence=result["confidence"],
                    reasoning=result["reasoning"],
                    extracted_intent=None
                )

            # Extract intent from result
            extracted_intent = ExtractedIntent(
                action=result["extracted_intent"]["action"],
                devices=result["extracted_intent"].get("devices", []),
                parameters=result["extracted_intent"].get("parameters", {})
            )

            logger.info(
                "Intent matched successfully",
                use_case=result["matched_use_case"],
                confidence=result["confidence"],
                action=extracted_intent.action,
                devices=extracted_intent.devices
            )

            return IntentMatchResult(
                matched_use_case=result["matched_use_case"],
                confidence=result["confidence"],
                reasoning=result["reasoning"],
                extracted_intent=extracted_intent
            )

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON", error=str(e), response=response)
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")
        except KeyError as e:
            logger.error("LLM response missing required fields", error=str(e), response=response)
            raise ValueError(f"LLM response missing field: {str(e)}")
        except Exception as e:
            logger.error("Intent matching failed", error=str(e))
            raise

    async def _parse_intent(self, user_input: str, use_case: UseCase) -> ExtractedIntent:
        """
        Parse intent using use case-specific prompt.

        Args:
            user_input: Raw user input
            use_case: Selected use case

        Returns:
            ExtractedIntent with parsed details
        """
        # Use the use case's intent_prompt if available
        intent_prompt = use_case.intent_prompt if use_case.intent_prompt else """
        Analyze the following voice command and extract structured intent:

        Voice Command: {input_text}

        Respond in JSON format with:
        - action: The type of action requested
        - devices: List of target devices
        - parameters: Dictionary of parameters
        """

        # Replace placeholder with actual input
        formatted_prompt = intent_prompt.replace("{input_text}", user_input).replace("{{input_text}}", user_input)

        response = await self.llm.complete(
            prompt=formatted_prompt,
            system_prompt="You are a network automation intent parser. Extract structured data from voice commands.",
            json_response=True,
            temperature=self.temperature
        )

        result = json.loads(response)

        return ExtractedIntent(
            action=result.get("action", "unknown"),
            devices=result.get("devices", result.get("target_devices", [])),
            parameters=result.get("parameters", {})
        )

    def _build_matching_prompt(self, user_input: str, use_cases: List[UseCase]) -> str:
        """Build prompt with all available use cases."""
        use_case_descriptions = []
        for uc in use_cases:
            # Only show first 5 trigger keywords as examples
            example_triggers = ", ".join(uc.trigger_keywords[:5]) if uc.trigger_keywords else "N/A"

            use_case_descriptions.append(f"""
USE CASE: {uc.name}
DISPLAY NAME: {uc.display_name}
DESCRIPTION: {uc.description}
ALLOWED ACTIONS: {', '.join(uc.allowed_actions) if uc.allowed_actions else 'N/A'}
EXAMPLE TRIGGERS: {example_triggers}
""")

        return f"""You are an expert network automation intent classifier.

USER INPUT: {user_input}

AVAILABLE USE CASES:
{''.join(use_case_descriptions)}

TASK:
1. Determine which use case (if any) matches the user's intent
2. If no use case matches, return "no_match"
3. If a use case matches, extract:
   - action: The specific action requested (must be from allowed_actions)
   - devices: Target devices (router names, device IDs, or ["all"] if all devices)
   - parameters: Configuration parameters (area, ASN, VLAN, etc.)

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
  "matched_use_case": "use_case_name" or "no_match",
  "confidence": 0-100,
  "reasoning": "why this use case was selected or not selected",
  "extracted_intent": {{
    "action": "...",
    "devices": [...],
    "parameters": {{}}
  }}
}}

Rules:
- Match based on SEMANTIC meaning, not keywords
- If user mentions BGP, don't match OSPF use cases
- If user mentions credentials/passwords, match credential_rotation
- If user mentions security/advisory, match security_advisory
- If confidence < 70%, return "no_match"
- Be strict - better to ask than guess wrong
- Extract action must be from the use case's allowed_actions list
- If no use case matches, set extracted_intent to null

IMPORTANT: Return ONLY the JSON object. Do not wrap in markdown code blocks or add any other text.
"""
