import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration settings for LLM model provider."""

    api_key: Optional[str] = Field(default=None)
    base_url: str = Field(default="https://api.openai.com/v1")
    model: str = Field(default="gpt-4o-mini")
    timeout: float = Field(default=30.0)
    max_steps: int = Field(default=5)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load configuration from environment variables or local .env file."""
        cls._load_dotenv_if_exists()

        api_key = os.getenv("SPECPILOT_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("SPECPILOT_LLM_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("SPECPILOT_LLM_MODEL", "gpt-4o-mini")


        timeout_raw = os.getenv("SPECPILOT_LLM_TIMEOUT", "30.0")
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 30.0

        max_steps_raw = os.getenv("SPECPILOT_LLM_MAX_STEPS", "5")
        try:
            max_steps = int(max_steps_raw)
        except ValueError:
            max_steps = 5

        return cls(
            api_key=api_key if api_key and api_key.strip() else None,
            base_url=base_url.rstrip("/"),
            model=model,
            timeout=timeout,
            max_steps=max_steps,
        )

    def is_configured(self) -> bool:
        """Return True if an API key is configured."""
        return self.api_key is not None and len(self.api_key.strip()) > 0

    @classmethod
    def _load_dotenv_if_exists(cls) -> None:
        """Parse local .env file if environment variables are not already populated."""
        if os.getenv("SPECPILOT_DISABLE_DOTENV"):
            return
        dotenv_path = Path(".env")
        if dotenv_path.is_file():
            try:
                with open(dotenv_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass


