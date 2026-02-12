# =============================================================================
# BRKOPS-2585 LLM Service
# GPT-4 and Claude with automatic fallback
# =============================================================================

import json
from typing import Any, Dict, Optional

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

logger = structlog.get_logger()


class LLMService:
    """
    LLM service with primary (OpenAI GPT-4) and fallback (Claude) providers.
    Automatically falls back to secondary provider on failure.
    Supports demo_mode for mock responses without real API calls.
    """

    def __init__(
        self,
        demo_mode: bool = False,
        provider: str = None,
        model: str = None,
        openai_api_key: str = None,
        anthropic_api_key: str = None
    ):
        self.demo_mode = demo_mode
        self.provider_override = provider  # 'openai' or 'anthropic' (None = use default)
        self.model_override = model  # specific model name (None = use default)
        self.openai_api_key = openai_api_key  # Override from database
        self.anthropic_api_key = anthropic_api_key  # Override from database
        self.openai_client = None
        self.anthropic_client = None

        # Configurable validation/scoring defaults
        self.api_key_min_length = 20
        self.demo_intent_confidence = 85
        self.score_failed = 45
        self.score_warning = 75
        self.score_success = 95
        self.route_loss_threshold = -2
        self.fallback_score_unhealthy = 30
        self.fallback_score_healthy = 90
        self.missing_field_default_score = 50

        if not demo_mode:
            self._init_clients()

    def load_validation_config(self, config: dict):
        """Load validation scoring config from database values."""
        self.score_failed = config.get('score_failed', 45)
        self.score_warning = config.get('score_warning', 75)
        self.score_success = config.get('score_success', 95)
        self.fallback_score_unhealthy = config.get('fallback_score_unhealthy', 30)
        self.fallback_score_healthy = config.get('fallback_score_healthy', 90)
        self.route_loss_threshold = config.get('route_loss_threshold', -2)
        self.missing_field_default_score = config.get('missing_field_default_score', 50)
        self.api_key_min_length = config.get('api_key_min_length', 20)
        self.demo_intent_confidence = config.get('demo_intent_confidence', 85)

    def _init_clients(self):
        """Initialize LLM clients based on available API keys."""
        # Use provided API keys or fall back to environment variables
        openai_key = self.openai_api_key or settings.openai_api_key
        anthropic_key = self.anthropic_api_key or settings.anthropic_api_key

        # Check if API keys look valid (not placeholder values)
        openai_key_valid = (
            openai_key and
            not openai_key.startswith("sk-your-") and
            len(openai_key) > self.api_key_min_length
        )
        anthropic_key_valid = (
            anthropic_key and
            not anthropic_key.startswith("sk-ant-your-") and
            len(anthropic_key) > self.api_key_min_length
        )

        if openai_key_valid:
            try:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=openai_key)
                logger.info("OpenAI client initialized", source="database" if self.openai_api_key else "environment")
            except Exception as e:
                logger.warning("Failed to initialize OpenAI client", error=str(e))

        if anthropic_key_valid:
            try:
                from anthropic import AsyncAnthropic
                self.anthropic_client = AsyncAnthropic(api_key=anthropic_key)
                logger.info("Anthropic client initialized", source="database" if self.anthropic_api_key else "environment")
            except Exception as e:
                logger.warning("Failed to initialize Anthropic client", error=str(e))

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_response: bool = False,
    ) -> str:
        """
        Generate a completion using available LLM provider with fallback.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            json_response: If True, request JSON output

        Returns:
            Generated text response
        """
        # Check if any LLM clients are available
        if not self.openai_client and not self.anthropic_client:
            raise RuntimeError(
                "No LLM providers configured. Please set valid OPENAI_API_KEY or ANTHROPIC_API_KEY "
                "environment variables. Current keys appear to be placeholder values."
            )

        temperature = temperature or settings.llm_temperature
        max_tokens = max_tokens or settings.llm_max_tokens

        # If provider override is set, use that provider directly
        if self.provider_override == "anthropic" and self.anthropic_client:
            try:
                return await self._complete_anthropic(
                    prompt, system_prompt, temperature, max_tokens
                )
            except Exception as e:
                logger.warning("Anthropic (override) failed, trying OpenAI fallback", error=str(e))
                if self.openai_client:
                    return await self._complete_openai(
                        prompt, system_prompt, temperature, max_tokens, json_response
                    )
                raise

        if self.provider_override == "openai" and self.openai_client:
            try:
                return await self._complete_openai(
                    prompt, system_prompt, temperature, max_tokens, json_response
                )
            except Exception as e:
                logger.warning("OpenAI (override) failed, trying Anthropic fallback", error=str(e))
                if self.anthropic_client:
                    return await self._complete_anthropic(
                        prompt, system_prompt, temperature, max_tokens
                    )
                raise

        # Default behavior: try primary (OpenAI) then fallback (Anthropic)
        try:
            if self.openai_client:
                return await self._complete_openai(
                    prompt, system_prompt, temperature, max_tokens, json_response
                )
        except Exception as e:
            logger.warning("OpenAI completion failed, trying fallback", error=str(e))

        # Fallback to secondary provider
        try:
            if self.anthropic_client:
                return await self._complete_anthropic(
                    prompt, system_prompt, temperature, max_tokens
                )
        except Exception as e:
            logger.error("Anthropic completion also failed", error=str(e))
            raise

        raise RuntimeError("No LLM providers available")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _complete_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        json_response: bool,
    ) -> str:
        """Generate completion using OpenAI."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        model = self.model_override if (self.model_override and self.provider_override == "openai") else settings.openai_model
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_response:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.openai_client.chat.completions.create(**kwargs)

        return response.choices[0].message.content

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _complete_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate completion using Anthropic Claude."""
        model = self.model_override if (self.model_override and self.provider_override == "anthropic") else settings.anthropic_model
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        # Note: Anthropic doesn't have temperature in same range
        # Adjust if needed

        response = await self.anthropic_client.messages.create(**kwargs)

        return response.content[0].text

    async def parse_intent(self, transcript: str, intent_prompt: str, use_case=None) -> Dict[str, Any]:
        """
        Parse intent from voice transcript.

        Args:
            transcript: Voice command transcript
            intent_prompt: Template prompt for intent parsing
            use_case: UseCase DB model (optional, for data-driven intent)

        Returns:
            Parsed intent as dictionary
        """
        # Demo mode: return realistic mock intent
        if self.demo_mode:
            logger.info("Demo mode: returning mock intent")
            return self._generate_demo_intent(transcript, use_case=use_case)

        prompt = intent_prompt.replace("{{input_text}}", transcript)

        system_prompt = """You are a network operations intent parser.
        You analyze voice commands from network engineers and extract structured intent.
        Always respond with valid JSON."""

        response = await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            json_response=True,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON from response: {response}")

    def _extract_target_devices(self, transcript: str) -> list:
        """Extract target devices from transcript. Shared across all use case types."""
        import re
        transcript_lower = transcript.lower()

        # Detect "all routers" / "all devices" patterns
        all_pattern = re.search(
            r'\b(all\s+(routers?|devices?|of\s+them|network\s+devices?)|every\s+(router|device))\b',
            transcript_lower
        )
        if all_pattern:
            return ["all"]

        # Extract specific router names (e.g. "Router-1 and Router-3", "Router-2")
        router_matches = re.findall(r'router[-\s]?(\d+)', transcript_lower)
        if router_matches:
            seen = set()
            devices = []
            for num in router_matches:
                d = f"Router-{num}"
                if d not in seen:
                    seen.add(d)
                    devices.append(d)
            return devices

        return ["Router-1"]

    def _extract_params(self, transcript: str) -> dict:
        """Extract common parameters from transcript (area numbers, CVE IDs, etc.)."""
        import re
        transcript_lower = transcript.lower()
        params = {}

        # OSPF area number
        area_match = re.search(r'area\s*(\d+)', transcript_lower)
        if area_match:
            params["new_area"] = int(area_match.group(1))

        # CVE ID
        cve_match = re.search(r'cve[-\s]?(\d{4}[-\s]?\d+)', transcript_lower)
        if cve_match:
            params["cve_id"] = f"CVE-{cve_match.group(1).replace(' ', '-')}"

        # Credential type
        if "enable" in transcript_lower:
            params["credential_type"] = "enable_secret"
        elif "snmp" in transcript_lower:
            params["credential_type"] = "snmp"
        elif "credential" in transcript_lower or "password" in transcript_lower:
            params["credential_type"] = "enable_secret"

        return params

    def _generate_demo_intent(self, transcript: str, use_case=None) -> Dict[str, Any]:
        """Generate realistic demo intent based on transcript and use case."""
        target_devices = self._extract_target_devices(transcript)
        params = self._extract_params(transcript)

        # Determine action from use_case allowed_actions or fall back
        if use_case and getattr(use_case, 'allowed_actions', None) and len(use_case.allowed_actions) > 0:
            allowed = use_case.allowed_actions
            # Pick best matching action: prefer one whose keywords match the transcript
            transcript_lower = transcript.lower()
            action = allowed[0]  # default to first
            for a in allowed:
                # If the action name contains a word found in transcript, prefer it
                action_words = a.lower().replace("_", " ").split()
                if any(w in transcript_lower for w in action_words if len(w) > 3):
                    action = a
                    break
        elif use_case:
            # Fallback: use use_case.name as action (contains trigger keywords)
            action = use_case.name
        else:
            action = "generic_config_change"

        display_name = use_case.display_name if use_case else "generic"
        target_desc = ", ".join(target_devices) if target_devices != ["all"] else "all routers"

        return {
            "action": action,
            "target_devices": target_devices,
            "parameters": params,
            "confidence": self.demo_intent_confidence,
            "reasoning": f"Intent for {display_name} on {target_desc}",
        }

    async def generate_advice(
        self,
        intent: Dict[str, Any],
        config: Dict[str, Any],
        use_case=None,
    ) -> Dict[str, Any]:
        """
        Generate pre-deployment advice and risk assessment.

        Args:
            intent: Parsed intent dictionary
            config: Generated configuration dictionary
            use_case: UseCase DB model (optional, for DB-driven risk profile)

        Returns:
            Advice including risk assessment, recommendations, and approval suggestion
        """
        # Demo mode: return realistic mock advice
        if self.demo_mode:
            logger.info("Demo mode: returning mock advice")
            return self._generate_demo_advice(intent, config, use_case=use_case)

        prompt = f"""
        Review the following network configuration change before deployment:

        Intent: {json.dumps(intent, indent=2)}
        Configuration: {json.dumps(config, indent=2)}

        Provide a pre-deployment risk assessment in JSON format with:
        - risk_level: LOW, MEDIUM, or HIGH
        - risk_factors: List of identified risks
        - mitigation_steps: Suggested mitigations
        - impact_assessment: Expected impact description
        - rollback_ready: Boolean indicating if rollback commands are adequate
        - recommendation: APPROVE, REVIEW, or REJECT
        - recommendation_reason: Explanation for the recommendation
        - pre_checks: List of checks to verify before deployment
        """

        system_prompt = """You are a senior network engineer reviewing proposed configuration changes.
        Analyze the change for risks, impact, and provide a clear recommendation.
        Always respond with valid JSON."""

        response = await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            json_response=True,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON from response: {response}")

    def _generate_demo_advice(self, intent: Dict[str, Any], config: Dict[str, Any], use_case=None) -> Dict[str, Any]:
        """Generate advice derived from real per-device config data and DB-driven risk profile."""
        risk_level = config.get("risk_level", "medium")
        devices = intent.get("target_devices", ["Router-1"])
        per_device = config.get("per_device_configs", {})

        device_count = len(per_device) if per_device else len(devices)

        # Get risk profile, pre/post checks from use case DB fields
        db_risk_profile = getattr(use_case, 'risk_profile', None) or {
            "risk_factors": ["Configuration change"],
            "mitigation_steps": ["Review carefully before approval"],
            "affected_services": ["Network services"],
        }
        db_pre_checks = getattr(use_case, 'pre_checks', None) or ["Validate configuration syntax"]
        db_post_checks = getattr(use_case, 'post_checks', None) or ["Verify device reachability"]

        # Start with DB-defined risk factors
        risk_factors = list(db_risk_profile.get("risk_factors", []))
        mitigation_steps = list(db_risk_profile.get("mitigation_steps", []))

        if device_count > 2:
            risk_factors.append(f"High impact: {device_count} devices affected simultaneously")

        # Merge real per-device data into risk factors
        if per_device:
            for device_label, cfg in per_device.items():
                cmd_count = len(cfg.get("commands", []))
                has_rollback = len(cfg.get("rollback_commands", [])) > 0
                warnings = cfg.get("warnings", [])
                if cmd_count > 0:
                    risk_factors.append(f"{device_label}: {cmd_count} commands to apply (rollback {'ready' if has_rollback else 'NOT available'})")
                for w in warnings:
                    if "already in area" not in w and "Generated password" not in w:
                        risk_factors.append(f"{device_label}: {w}")

        # Determine risk level from device count
        if device_count > 2:
            computed_risk = "HIGH"
        elif device_count > 1:
            computed_risk = "MEDIUM"
        else:
            computed_risk = risk_level.upper() if isinstance(risk_level, str) else "MEDIUM"

        # Check all devices have rollback
        all_rollback = all(
            len(cfg.get("rollback_commands", [])) > 0
            for cfg in per_device.values()
        ) if per_device else bool(config.get("rollback_commands"))

        return {
            "risk_level": computed_risk,
            "risk_factors": risk_factors,
            "mitigation_steps": mitigation_steps,
            "impact_assessment": config.get("estimated_impact", "Expected brief service impact during change application"),
            "rollback_ready": all_rollback,
            "recommendation": "APPROVE",
            "recommendation_reason": f"Configuration built from live running configs. {device_count} device(s) targeted with {'per-device' if per_device else 'shared'} rollback commands.",
            "pre_checks": db_pre_checks,
            "post_checks": db_post_checks,
            "estimated_duration": "30-60 seconds for configuration application, 15-45 seconds for convergence",
            "affected_services": db_risk_profile.get("affected_services", ["Network services"]),
        }

    async def generate_config(
        self,
        intent: Dict[str, Any],
        config_prompt: str,
        current_config: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate network configuration from intent.

        Args:
            intent: Parsed intent dictionary
            config_prompt: Template prompt for config generation
            current_config: Current device configuration (optional)

        Returns:
            Generated configuration as dictionary
        """
        # Note: demo mode config generation is now handled by config_builder
        # in pipeline.py:process_config_generation() using real running configs.
        # This method is only called as LLM fallback when running configs are unavailable.

        prompt = config_prompt.replace("{{intent}}", json.dumps(intent, indent=2))
        if current_config:
            prompt = prompt.replace("{{current_config}}", current_config)
        else:
            prompt = prompt.replace("{{current_config}}", "Not available")

        system_prompt = """You are a Cisco network configuration expert.
        Generate precise IOS/IOS-XE commands for the given intent.
        Always respond with valid JSON containing commands array."""

        response = await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            json_response=True,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON from response: {response}")

    async def analyze_results(
        self,
        config: Dict[str, Any],
        splunk_results: Dict[str, Any],
        analysis_prompt: str,
        time_window: str = "60 seconds",
    ) -> Dict[str, Any]:
        """
        Analyze Splunk results after configuration change.

        Args:
            config: Applied configuration
            splunk_results: Results from Splunk query
            analysis_prompt: Template prompt for analysis
            time_window: Time window of analysis

        Returns:
            Analysis results as dictionary
        """
        # Demo mode: return realistic mock analysis
        if self.demo_mode:
            logger.info("Demo mode: returning mock analysis")
            return self._generate_demo_analysis(config, splunk_results)

        prompt = analysis_prompt.replace("{{config}}", json.dumps(config, indent=2))
        prompt = prompt.replace("{{splunk_results}}", json.dumps(splunk_results, indent=2))
        prompt = prompt.replace("{{time_window}}", time_window)

        system_prompt = """You are a network operations analyst.
        Analyze post-change monitoring data for issues.
        Identify problems, determine severity, and recommend actions.
        Always respond with valid JSON."""

        response = await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            json_response=True,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON from response: {response}")

    def _generate_demo_analysis(self, config: Dict[str, Any], splunk_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analysis results. No longer returns fake metrics."""
        explanation = config.get("explanation", "Configuration change")

        return {
            "status": "healthy",
            "overall_score": 95,
            "summary": f"Configuration change applied. {explanation}",
            "validation_status": "PASSED",
            "findings": [
                {
                    "category": "Deployment Status",
                    "status": "ok",
                    "message": "Configuration commands applied to target device(s)",
                    "severity": "info"
                },
            ],
            "metrics": {},
            "deployment_verified": True,
            "post_deployment_status": "Configuration applied",
            "recommendation": "Verify via monitoring stage",
            "recommendation_reason": "Analysis based on deployment result only. Real metrics come from monitoring diff.",
        }

    async def validate_deployment(
        self,
        config: Dict[str, Any],
        deployment_result: Dict[str, Any],
        splunk_results: Dict[str, Any],
        validation_prompt: str,
        time_window: str = "60 seconds",
        monitoring_diff: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validate deployment results after CML deployment.

        Args:
            config: Applied configuration
            deployment_result: Result from CML deployment stage
            splunk_results: Results from Splunk query
            validation_prompt: Template prompt for validation
            time_window: Time window of analysis
            monitoring_diff: Before/after diff from monitoring stage

        Returns:
            Validation results as dictionary
        """
        # Demo mode: return realistic mock validation
        if self.demo_mode:
            logger.info("Demo mode: returning mock validation")
            return self._generate_demo_validation(config, splunk_results, monitoring_diff)

        prompt = validation_prompt.replace("{{config}}", json.dumps(config, indent=2))
        prompt = prompt.replace("{{deployment_result}}", json.dumps(deployment_result, indent=2))
        prompt = prompt.replace("{{splunk_results}}", json.dumps(splunk_results, indent=2))
        prompt = prompt.replace("{{time_window}}", time_window)
        if monitoring_diff:
            prompt = prompt.replace("{{monitoring_diff}}", json.dumps(monitoring_diff, indent=2))

        system_prompt = """You are a senior network engineer validating deployment results.

CRITICAL TASK: Determine if this deployment was successful or requires rollback.

Analyze these inputs:
1. Monitoring Diff: Did OSPF neighbors, interfaces, or routes decrease?
2. Splunk Logs: Any ERROR messages, neighbor down events, or routing failures?
3. Expected vs Actual: Does the result match the intended change?

ROLLBACK DECISION CRITERIA:
- ROLLBACK REQUIRED: If neighbors lost, interfaces down, or critical errors in logs
- ACCEPTABLE: Minor warnings but network stable, no loss of connectivity
- SUCCESS: Change applied cleanly, network converged as expected

REQUIRED JSON STRUCTURE (you MUST include ALL fields exactly):
{
  "validation_status": "PASSED" | "WARNING" | "FAILED",
  "overall_score": <number 0-100>,
  "rollback_recommended": <boolean>,
  "rollback_reason": "<string explaining why rollback is/isn't recommended>",
  "findings": [
    {
      "category": "<string: Network State|Deployment|Logs|Configuration>",
      "status": "<string: ok|warning|critical>",
      "severity": "<string: info|warning|critical>",
      "message": "<string: description of finding>"
    }
  ],
  "summary": "<string: overall assessment>",
  "recommendation": "<string: detailed recommendation>"
}

CRITICAL RULES:
1. If OSPF neighbors decreased (change < 0): validation_status MUST be "FAILED", rollback_recommended MUST be true
2. If interfaces went down (change < 0): validation_status MUST be "FAILED", rollback_recommended MUST be true
3. If Splunk shows critical errors: validation_status MUST be "WARNING" or "FAILED"
4. overall_score: 100 = perfect, 0 = complete failure
5. Include at least 3 findings in the findings array
6. Each finding MUST have all 4 fields: category, status, severity, message

Return ONLY the JSON object, no additional text."""

        response = await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            json_response=True,
        )

        try:
            validation_dict = json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    validation_dict = json.loads(json_match.group())
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM validation response: {e}")
                    logger.error(f"Raw response: {response[:500]}")
                    # Fallback to demo-style validation
                    return self._fallback_validation(monitoring_diff)
            else:
                logger.error(f"No JSON found in LLM response: {response[:500]}")
                return self._fallback_validation(monitoring_diff)

        # VALIDATION: Ensure all required fields exist
        required_fields = {
            'validation_status': str,
            'overall_score': (int, float),
            'rollback_recommended': bool,
            'findings': list,
            'summary': str,
            'recommendation': str,
        }

        for field, expected_type in required_fields.items():
            if field not in validation_dict:
                # Set default value based on type
                if expected_type == str:
                    validation_dict[field] = f"Missing {field}"
                elif expected_type in (int, float) or expected_type == (int, float):
                    validation_dict[field] = self.missing_field_default_score
                elif expected_type == bool:
                    validation_dict[field] = False
                elif expected_type == list:
                    validation_dict[field] = []
                logger.warning(f"Missing required field '{field}' in LLM validation response, using default")
            elif not isinstance(validation_dict[field], expected_type):
                # Type mismatch - fix it
                if field == 'overall_score':
                    try:
                        validation_dict[field] = int(validation_dict[field])
                    except (ValueError, TypeError):
                        validation_dict[field] = self.missing_field_default_score
                elif field == 'rollback_recommended':
                    validation_dict[field] = bool(validation_dict[field])
                elif field == 'findings' and not isinstance(validation_dict[field], list):
                    validation_dict[field] = [{"category": "Error", "status": "warning",
                                              "message": str(validation_dict[field]),
                                              "severity": "warning"}]
                logger.warning(f"Field '{field}' has incorrect type in LLM validation response, converted")

        # Validate findings structure
        if validation_dict['findings']:
            validated_findings = []
            for finding in validation_dict['findings']:
                if isinstance(finding, dict):
                    # Ensure all required finding fields exist
                    validated_finding = {
                        'category': finding.get('category', 'General'),
                        'status': finding.get('status', 'info'),
                        'severity': finding.get('severity', 'info'),
                        'message': finding.get('message', 'No message provided')
                    }
                    validated_findings.append(validated_finding)
                else:
                    # Invalid finding format, convert to dict
                    validated_findings.append({
                        'category': 'General',
                        'status': 'warning',
                        'severity': 'warning',
                        'message': str(finding)
                    })
            validation_dict['findings'] = validated_findings
        else:
            # No findings, add a default one
            validation_dict['findings'] = [{
                'category': 'Validation',
                'status': 'ok',
                'severity': 'info',
                'message': 'No specific findings reported'
            }]

        # If no rollback_reason, generate one
        if 'rollback_reason' not in validation_dict:
            validation_dict['rollback_reason'] = (
                "Network degraded after deployment"
                if validation_dict['rollback_recommended']
                else "Deployment validated successfully"
            )

        return validation_dict

    def _fallback_validation(self, monitoring_diff: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate fallback validation when LLM response fails to parse."""
        deployment_healthy = True
        if monitoring_diff:
            deployment_healthy = monitoring_diff.get('deployment_healthy', True)

        return {
            'validation_status': 'FAILED' if not deployment_healthy else 'PASSED',
            'overall_score': self.fallback_score_unhealthy if not deployment_healthy else self.fallback_score_healthy,
            'rollback_recommended': not deployment_healthy,
            'rollback_reason': 'Network degraded - automatic assessment due to LLM parsing failure' if not deployment_healthy else 'Deployment validated successfully',
            'findings': [
                {
                    'category': 'System',
                    'status': 'critical' if not deployment_healthy else 'ok',
                    'severity': 'critical' if not deployment_healthy else 'info',
                    'message': f"LLM response parsing failed. Automatic assessment: {'Network degraded' if not deployment_healthy else 'Network healthy'}"
                }
            ],
            'summary': 'Automated validation due to LLM error',
            'recommendation': 'Rollback recommended' if not deployment_healthy else 'Deployment validated'
        }

    def _generate_demo_validation(
        self,
        config: Dict[str, Any],
        splunk_results: Dict[str, Any],
        monitoring_diff: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate realistic demo validation results including diff analysis and rollback recommendations."""
        explanation = config.get("explanation", "Configuration change")

        # Initialize rollback variables
        rollback_recommended = False
        rollback_reason = None
        validation_status = "PASSED"

        # Analyze diff to determine status and rollback need
        diff_findings = []
        if monitoring_diff:
            ospf_change = monitoring_diff.get("ospf_neighbors", {}).get("change", 0)
            interface_change = monitoring_diff.get("interfaces_up", {}).get("change", 0)
            route_change = monitoring_diff.get("routes", {}).get("change", 0)

            # CRITICAL: Rollback criteria - detect network degradation
            if ospf_change < 0 or interface_change < 0:
                rollback_recommended = True
                validation_status = "FAILED"
                rollback_reason = (
                    f"Network degradation detected: "
                    f"OSPF neighbors {ospf_change:+d}, interfaces {interface_change:+d}. "
                    f"This indicates loss of connectivity or routing instability."
                )
            elif route_change < self.route_loss_threshold:  # Lost more than threshold routes
                rollback_recommended = True
                validation_status = "FAILED"
                rollback_reason = f"Significant route loss detected: {route_change:+d} routes. This may indicate routing instability."
            elif ospf_change < 0 or interface_change < 0 or route_change < 0:
                validation_status = "WARNING"

            # Build detailed findings for each metric
            if ospf_change >= 0:
                diff_findings.append({
                    "category": "OSPF Neighbors",
                    "status": "ok",
                    "message": f"OSPF neighbor count stable ({ospf_change:+d} change)",
                    "severity": "info"
                })
            else:
                diff_findings.append({
                    "category": "OSPF Neighbors",
                    "status": "error" if rollback_recommended else "warning",
                    "message": f"CRITICAL: OSPF neighbor count decreased ({ospf_change:+d})",
                    "severity": "critical" if rollback_recommended else "warning"
                })

            if interface_change >= 0:
                diff_findings.append({
                    "category": "Interface Status",
                    "status": "ok",
                    "message": f"All interfaces stable ({interface_change:+d} change)",
                    "severity": "info"
                })
            else:
                diff_findings.append({
                    "category": "Interface Status",
                    "status": "error" if rollback_recommended else "warning",
                    "message": f"CRITICAL: Some interfaces went down ({interface_change:+d})",
                    "severity": "critical" if rollback_recommended else "warning"
                })

            if route_change >= 0:
                diff_findings.append({
                    "category": "OSPF Routes",
                    "status": "ok",
                    "message": f"Route count stable ({route_change:+d} change)",
                    "severity": "info"
                })
            else:
                diff_findings.append({
                    "category": "OSPF Routes",
                    "status": "error" if rollback_recommended else "warning",
                    "message": f"Routes lost ({route_change:+d})",
                    "severity": "critical" if route_change < self.route_loss_threshold else "warning"
                })

        base_findings = []
        if not diff_findings:
            base_findings.append({
                "category": "Deployment Status",
                "status": "ok",
                "message": "Configuration commands applied to target device(s)",
                "severity": "info"
            })

        all_findings = diff_findings + base_findings

        # Determine overall score based on validation status
        if validation_status == "FAILED":
            overall_score = self.score_failed
        elif validation_status == "WARNING":
            overall_score = self.score_warning
        else:
            overall_score = self.score_success

        # Build recommendation message
        if rollback_recommended:
            recommendation = f"ROLLBACK REQUIRED: {rollback_reason}"
        elif validation_status == "WARNING":
            recommendation = "Configuration applied with warnings. Monitor network closely for the next 10 minutes."
        else:
            recommendation = "Deployment successful. All metrics within expected parameters."

        return {
            "status": "critical" if rollback_recommended else ("degraded" if validation_status == "WARNING" else "healthy"),
            "overall_score": overall_score,
            "summary": f"Configuration change applied. {explanation}",
            "validation_status": validation_status,
            "findings": all_findings,
            "metrics": {
                "neighbor_count": monitoring_diff.get("ospf_neighbors", {}).get("after") if monitoring_diff else None,
                "routes_in_area": monitoring_diff.get("routes", {}).get("after") if monitoring_diff else None,
            },
            "deployment_verified": not rollback_recommended,
            "post_deployment_status": "CRITICAL - Rollback Required" if rollback_recommended else "Configuration applied and verified",
            "recommendation": recommendation,
            "recommendation_reason": rollback_reason if rollback_recommended else ("Some metrics changed during deployment" if validation_status == "WARNING" else "All health checks passed"),
            "rollback_recommended": rollback_recommended,
            "rollback_reason": rollback_reason,
        }

    async def generate_notification(
        self,
        template: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Generate notification message from template and context.

        Args:
            template: Message template with placeholders
            context: Context dictionary for variable substitution

        Returns:
            Generated message
        """
        # Simple variable substitution
        message = template
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            message = message.replace(placeholder, str(value))

        return message
