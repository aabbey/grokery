import os
import json
import logging
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from typing import Dict, List, Any, Literal, Optional, Union

logger = logging.getLogger(__name__)

class LLMService:
    """Service for handling all LLM-related functionality."""
    
    _openai_client = None
    _anthropic_client = None
    
    # Model selection: either "gpt-4o-mini" or "claude-3.5-haiku"
    SELECTED_MODEL: Literal["gpt-4o-mini", "claude-3-5-haiku-20241022"] = "claude-3-5-haiku-20241022"
    
    @classmethod
    async def _get_openai_client(cls) -> AsyncOpenAI:
        """Get a new OpenAI client instance for each request."""
        if cls._openai_client is None:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            cls._openai_client = AsyncOpenAI(api_key=api_key)
        return cls._openai_client

    @classmethod
    async def _get_anthropic_client(cls) -> AsyncAnthropic:
        """Get a new Anthropic client instance for each request."""
        if cls._anthropic_client is None:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
            cls._anthropic_client = AsyncAnthropic(api_key=api_key)
        return cls._anthropic_client

    @classmethod
    async def get_completion(
        cls,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        tool_name: str = "process_input",
        tool_description: str = "Process the input and generate structured output.",
        system_prompt: str = "You are a helpful assistant that always responds with a valid JSON object only."
    ) -> Union[Dict[str, Any], List[Any]]:
        """
        Get completion from selected model.
        
        Args:
            prompt: The prompt to send to the model
            schema: Optional JSON schema for structured output (required for Anthropic)
            tool_name: Name of the tool for Anthropic's structured output
            tool_description: Description of the tool for Anthropic's structured output
            system_prompt: System prompt to set the model's behavior
            
        Returns:
            Parsed JSON response from the model
        """
        try:
            if cls.SELECTED_MODEL == "gpt-4o-mini":
                client = await cls._get_openai_client()
                response = await client.chat.completions.create(
                    model=cls.SELECTED_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            else:  # claude-3-5-haiku-20241022
                client = await cls._get_anthropic_client()
                if not schema:
                    raise ValueError("Schema is required for Anthropic model")

                response = await client.messages.create(
                    model=cls.SELECTED_MODEL,
                    max_tokens=2048,
                    system=system_prompt,
                    tools=[
                        {
                            "name": tool_name,
                            "description": tool_description,
                            "input_schema": schema,
                        }
                    ],
                    tool_choice={"type": "tool", "name": tool_name},
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                )
                return response.content[0].input
        except Exception as e:
            logger.error(f"Error in LLM completion: {str(e)}")
            raise

    @classmethod
    async def cleanup(cls):
        """Cleanup any resources when shutting down."""
        # Currently no cleanup needed, but method provided for future use
        pass 