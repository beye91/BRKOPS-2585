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
    """

    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
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
