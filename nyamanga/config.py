from dataclasses import dataclass
import os
from typing import Optional


DEFAULT_BASE_URL = "https://api.ephone.chat/v1"


@dataclass
class ApiConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    chat_model: str = "nano-banana-2"
    image_model: str = "nano-banana-2"
    request_timeout: float = 120.0

    @classmethod
    def from_env(cls) -> "ApiConfig":
        """
        Load configuration from environment variables.

        Supported keys:
        - NYAMANGA_API_KEY or EPHONE_API_KEY (required)
        - NYAMANGA_BASE_URL (optional)
        - NYAMANGA_CHAT_MODEL (optional)
        - NYAMANGA_IMAGE_MODEL (optional)
        - NYAMANGA_TIMEOUT (optional, seconds)
        """
        api_key = (
            os.environ.get("NYAMANGA_API_KEY")
            or os.environ.get("EPHONE_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )
        if not api_key:
            raise ValueError("Set NYAMANGA_API_KEY/EPHONE_API_KEY/OPENAI_API_KEY")

        base_url = os.environ.get("NYAMANGA_BASE_URL", DEFAULT_BASE_URL)
        chat_model = os.environ.get("NYAMANGA_CHAT_MODEL", "nano-banana-2")
        image_model = os.environ.get("NYAMANGA_IMAGE_MODEL", "gpt-image-1")
        timeout_raw: Optional[str] = os.environ.get("NYAMANGA_TIMEOUT")
        timeout = float(timeout_raw) if timeout_raw else 30.0
        return cls(
            api_key=api_key,
            base_url=base_url,
            chat_model=chat_model,
            image_model=image_model,
            request_timeout=timeout,
        )
