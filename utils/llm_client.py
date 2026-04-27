"""
LLM Client Wrapper
Manages the connection to OpenRouter and configures Instructor
to enforce Pydantic-based structured outputs.
"""

import os
import logging
from dotenv import load_dotenv
import instructor
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

_client = None

def get_instructor_client():
    """
    Get an Instructor-patched OpenAI client configured for OpenRouter.
    Uses singleton pattern to avoid redundant re-initialization.
    """
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("OPENROUTER_API_KEY")
    
    if not api_key or api_key == "your_openrouter_api_key_here":
        logger.warning(
            "OPENROUTER_API_KEY is not set or is using the default placeholder. "
            "LLM extractions and fact-checking will likely fail."
        )

    # OpenRouter uses the standard OpenAI SDK but with a custom base_url
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key or "invalid_key",
    )

    # Create the instructor-patched client
    _client = instructor.from_openai(client)
    return _client

# Standardize the lightweight model to use via OpenRouter
DEFAULT_LLM_MODEL = "openai/gpt-4o-mini"
