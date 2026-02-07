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

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.openai_client = None
        self.anthropic_client = None
        if not demo_mode:
            self._init_clients()

    def _init_clients(self):
        """Initialize LLM clients based on available API keys."""
        if settings.openai_api_key:
            try:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.warning("Failed to initialize OpenAI client", error=str(e))

        if settings.anthropic_api_key:
            try:
                from anthropic import AsyncAnthropic
                self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
                logger.info("Anthropic client initialized")
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
        temperature = temperature or settings.llm_temperature
        max_tokens = max_tokens or settings.llm_max_tokens

        # Try primary provider first
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

        kwargs = {
            "model": settings.openai_model,
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
        kwargs = {
            "model": settings.anthropic_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        # Note: Anthropic doesn't have temperature in same range
        # Adjust if needed

        response = await self.anthropic_client.messages.create(**kwargs)

        return response.content[0].text

    async def parse_intent(self, transcript: str, intent_prompt: str) -> Dict[str, Any]:
        """
        Parse intent from voice transcript.

        Args:
            transcript: Voice command transcript
            intent_prompt: Template prompt for intent parsing

        Returns:
            Parsed intent as dictionary
        """
        # Demo mode: return realistic mock intent
        if self.demo_mode:
            logger.info("Demo mode: returning mock intent")
            return self._generate_demo_intent(transcript)

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

    def _generate_demo_intent(self, transcript: str) -> Dict[str, Any]:
        """Generate realistic demo intent based on transcript."""
        transcript_lower = transcript.lower()

        if "ospf" in transcript_lower and "area" in transcript_lower:
            # Extract router and area from transcript
            router = "Router-1"
            area = "10"
            if "router-2" in transcript_lower:
                router = "Router-2"
            if "router-3" in transcript_lower:
                router = "Router-3"
            if "router-4" in transcript_lower:
                router = "Router-4"

            import re
            area_match = re.search(r'area\s*(\d+)', transcript_lower)
            if area_match:
                area = area_match.group(1)

            return {
                "action": "modify_ospf_area",
                "target_devices": [router],
                "parameters": {
                    "ospf_process_id": 1,
                    "new_area": int(area),
                    "interfaces": ["GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"]
                },
                "confidence": 95,
                "reasoning": f"User wants to change OSPF configuration on {router} to use area {area}"
            }

        elif "credential" in transcript_lower or "password" in transcript_lower:
            return {
                "action": "rotate_credentials",
                "target_devices": ["Router-1", "Router-2", "Router-3", "Router-4"],
                "parameters": {
                    "credential_type": "enable_secret",
                    "scope": "datacenter"
                },
                "confidence": 90,
                "reasoning": "User wants to rotate credentials across datacenter devices"
            }

        elif "security" in transcript_lower or "cve" in transcript_lower:
            return {
                "action": "apply_security_patch",
                "target_devices": ["Router-1", "Router-2"],
                "parameters": {
                    "cve_id": "CVE-2024-1234",
                    "patch_type": "access_list"
                },
                "confidence": 88,
                "reasoning": "User wants to apply security remediation for CVE"
            }

        else:
            return {
                "action": "generic_config_change",
                "target_devices": ["Router-1"],
                "parameters": {},
                "confidence": 70,
                "reasoning": "Generic configuration change request"
            }

    async def generate_advice(
        self,
        intent: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate pre-deployment advice and risk assessment.

        Args:
            intent: Parsed intent dictionary
            config: Generated configuration dictionary

        Returns:
            Advice including risk assessment, recommendations, and approval suggestion
        """
        # Demo mode: return realistic mock advice
        if self.demo_mode:
            logger.info("Demo mode: returning mock advice")
            return self._generate_demo_advice(intent, config)

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

    def _generate_demo_advice(self, intent: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic demo advice based on intent and config."""
        action = intent.get("action", "")
        risk_level = config.get("risk_level", "medium")
        devices = intent.get("target_devices", ["Router-1"])

        risk_factors = []
        mitigation_steps = []
        pre_checks = []

        if action == "modify_ospf_area":
            risk_factors = [
                "OSPF area change will cause temporary neighbor adjacency reset",
                f"Affects {len(devices)} device(s) in the network",
                "May cause brief traffic rerouting during convergence"
            ]
            mitigation_steps = [
                "Ensure backup paths exist before applying changes",
                "Apply during maintenance window if possible",
                "Have rollback commands ready"
            ]
            pre_checks = [
                "Verify current OSPF neighbor state",
                "Confirm no active maintenance on affected devices",
                "Check that rollback commands are correct"
            ]
        elif action == "rotate_credentials":
            risk_factors = [
                "Credential change affects device access",
                "Concurrent sessions may be impacted"
            ]
            mitigation_steps = [
                "Ensure new credentials are documented securely",
                "Test access with new credentials immediately after change"
            ]
            pre_checks = [
                "Verify current access to affected devices",
                "Confirm new password meets complexity requirements"
            ]
        elif action == "apply_security_patch":
            risk_factors = [
                "ACL changes may impact legitimate traffic",
                "Blocking rules are permanent until removed"
            ]
            mitigation_steps = [
                "Monitor traffic after applying ACL",
                "Have NOC on standby for any user reports"
            ]
            pre_checks = [
                "Review ACL entries for correctness",
                "Verify interface attachment points"
            ]
        else:
            risk_factors = ["Generic configuration change with unknown impact"]
            mitigation_steps = ["Review carefully before approval"]
            pre_checks = ["Validate configuration syntax"]

        return {
            "risk_level": risk_level.upper() if isinstance(risk_level, str) else "MEDIUM",
            "risk_factors": risk_factors,
            "mitigation_steps": mitigation_steps,
            "impact_assessment": config.get("estimated_impact", "Expected brief service impact during change application"),
            "rollback_ready": bool(config.get("rollback_commands")),
            "recommendation": "APPROVE",
            "recommendation_reason": f"Configuration is syntactically correct and follows best practices. {len(devices)} device(s) targeted with adequate rollback commands provided.",
            "pre_checks": pre_checks,
            "estimated_duration": "30-60 seconds for configuration application, 15-45 seconds for convergence",
            "affected_services": ["OSPF routing", "Inter-area traffic"] if "ospf" in action else ["Device access"]
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
        # Demo mode: return realistic mock config
        if self.demo_mode:
            logger.info("Demo mode: returning mock config")
            return self._generate_demo_config(intent)

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

    def _generate_demo_config(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic demo config based on intent."""
        action = intent.get("action", "")
        params = intent.get("parameters", {})
        devices = intent.get("target_devices", ["Router-1"])

        if action == "modify_ospf_area":
            new_area = params.get("new_area", 10)
            interfaces = params.get("interfaces", ["GigabitEthernet2"])
            process_id = params.get("ospf_process_id", 1)

            commands = [
                f"router ospf {process_id}",
            ]
            rollback_commands = [
                f"router ospf {process_id}",
            ]

            for iface in interfaces:
                commands.append(f"  interface {iface}")
                commands.append(f"    ip ospf {process_id} area {new_area}")
                rollback_commands.append(f"  interface {iface}")
                rollback_commands.append(f"    ip ospf {process_id} area 0")

            return {
                "commands": commands,
                "rollback_commands": rollback_commands,
                "target_devices": devices,
                "explanation": f"Configure OSPF area {new_area} on interfaces {', '.join(interfaces)}",
                "risk_level": "medium",
                "estimated_impact": "Brief OSPF neighbor flap during area transition"
            }

        elif action == "rotate_credentials":
            return {
                "commands": [
                    "enable algorithm-type sha256 secret NewSecureP@ss2024!",
                    "username admin privilege 15 algorithm-type sha256 secret NewSecureP@ss2024!"
                ],
                "rollback_commands": [
                    "enable algorithm-type sha256 secret OldP@ssword123",
                    "username admin privilege 15 algorithm-type sha256 secret OldP@ssword123"
                ],
                "target_devices": devices,
                "explanation": "Rotate enable secret and admin credentials with SHA-256 hashing",
                "risk_level": "low",
                "estimated_impact": "No service impact expected"
            }

        elif action == "apply_security_patch":
            cve = params.get("cve_id", "CVE-2024-1234")
            return {
                "commands": [
                    "ip access-list extended CVE-2024-1234-BLOCK",
                    "  deny tcp any any eq 445 log",
                    "  deny udp any any eq 445 log",
                    "  permit ip any any",
                    "interface GigabitEthernet1",
                    "  ip access-group CVE-2024-1234-BLOCK in"
                ],
                "rollback_commands": [
                    "no ip access-list extended CVE-2024-1234-BLOCK",
                    "interface GigabitEthernet1",
                    "  no ip access-group CVE-2024-1234-BLOCK in"
                ],
                "target_devices": devices,
                "explanation": f"Apply security ACL to block exploit traffic for {cve}",
                "risk_level": "low",
                "estimated_impact": "Potential minor latency increase from ACL processing"
            }

        else:
            return {
                "commands": ["! No specific commands generated"],
                "rollback_commands": ["! No rollback needed"],
                "target_devices": devices,
                "explanation": "Generic configuration placeholder",
                "risk_level": "unknown",
                "estimated_impact": "Unknown"
            }

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
        """Generate realistic demo analysis/validation results."""
        explanation = config.get("explanation", "Configuration change")

        return {
            "status": "healthy",
            "overall_score": 95,
            "summary": f"Configuration change applied successfully. {explanation}",
            "validation_status": "PASSED",
            "findings": [
                {
                    "category": "OSPF Convergence",
                    "status": "ok",
                    "message": "OSPF neighbors re-established within 5 seconds",
                    "severity": "info"
                },
                {
                    "category": "Interface Status",
                    "status": "ok",
                    "message": "All configured interfaces are up/up",
                    "severity": "info"
                },
                {
                    "category": "CPU Utilization",
                    "status": "ok",
                    "message": "CPU utilization within normal range (12%)",
                    "severity": "info"
                },
                {
                    "category": "Memory Usage",
                    "status": "ok",
                    "message": "Memory usage stable at 45%",
                    "severity": "info"
                }
            ],
            "metrics": {
                "ospf_convergence_time_ms": 4850,
                "neighbor_count": 3,
                "routes_in_area": 12,
                "cpu_utilization_percent": 12,
                "memory_utilization_percent": 45
            },
            "deployment_verified": True,
            "post_deployment_status": "Configuration applied and verified successfully",
            "recommendation": "No action required",
            "recommendation_reason": "All health checks passed. OSPF converged successfully with no anomalies detected.",
            "risk_assessment": {
                "level": "low",
                "factors": [
                    "Single area configuration change",
                    "No traffic disruption observed",
                    "All neighbors stable"
                ]
            }
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

You MUST provide a clear recommendation: "ROLLBACK REQUIRED", "ACCEPTABLE", or "SUCCESS".

Always respond with valid JSON including:
- validation_status: "PASSED|WARNING|FAILED"
- rollback_recommended: boolean
- rollback_reason: string explaining why rollback is needed (if applicable)
- findings: array of specific issues found
- recommendation: clear action for operator"""

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
            elif route_change < -2:  # Lost more than 2 routes
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
                    "severity": "critical" if route_change < -2 else "warning"
                })

        base_findings = [
            {
                "category": "OSPF Convergence",
                "status": "ok",
                "message": "OSPF neighbors re-established within expected timeframe",
                "severity": "info"
            },
            {
                "category": "CPU Utilization",
                "status": "ok",
                "message": "CPU utilization within normal range (12%)",
                "severity": "info"
            },
        ]

        all_findings = diff_findings + base_findings

        # Determine overall score based on validation status
        if validation_status == "FAILED":
            overall_score = 45
        elif validation_status == "WARNING":
            overall_score = 75
        else:
            overall_score = 95

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
                "ospf_convergence_time_ms": 4850,
                "neighbor_count": monitoring_diff.get("ospf_neighbors", {}).get("after", 3) if monitoring_diff else 3,
                "routes_in_area": monitoring_diff.get("routes", {}).get("after", 12) if monitoring_diff else 12,
                "cpu_utilization_percent": 12,
                "memory_utilization_percent": 45
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
