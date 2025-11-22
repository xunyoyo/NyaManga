from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union
import json

import requests

from .config import ApiConfig


class ApiError(RuntimeError):
    """Raised when the remote API replies with a non-2xx status."""


class NyaMangaClient:
    """
    Thin wrapper around the ephone.chat-compatible API.
    Keeps surface area small so UI layers can wrap or replace pieces easily.
    """

    def __init__(self, config: ApiConfig):
        self.config = config
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {config.api_key}"})

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stream: bool = False,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Call /chat/completions for dialogue rewrite or translation."""
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model or self.config.chat_model,
            "messages": messages,
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        payload.update(extra)

        resp = self._session.post(
            url,
            json=payload,
            timeout=self.config.request_timeout,
            stream=stream,
        )
        return self._handle_response(resp)

    def edit_image(
        self,
        image_path: Union[str, Path],
        prompt: str,
        mask_path: Optional[Union[str, Path]] = None,
        model: Optional[str] = None,
        response_format: str = "b64_json",
        **extra: Any,
    ) -> Dict[str, Any]:
        """Call /images/edits with a single image and optional mask."""
        url = f"{self.config.base_url.rstrip('/')}/images/edits"
        files = {"image": open(Path(image_path), "rb")}
        if mask_path:
            files["mask"] = open(Path(mask_path), "rb")

        data: Dict[str, Any] = {
            "prompt": prompt,
            "model": model or self.config.image_model,
            "response_format": response_format,
        }
        data.update(extra)

        try:
            resp = self._session.post(
                url,
                files=files,
                data=data,
                timeout=self.config.request_timeout,
            )
        finally:
            for file in files.values():
                file.close()

        return self._handle_response(resp)

    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        response_format: str = "b64_json",
        **extra: Any,
    ) -> Dict[str, Any]:
        """Call /images/generations for pure synthesis."""
        url = f"{self.config.base_url.rstrip('/')}/images/generations"
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "model": model or self.config.image_model,
            "response_format": response_format,
        }
        payload.update(extra)

        resp = self._session.post(
            url, json=payload, timeout=self.config.request_timeout
        )
        return self._handle_response(resp)

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "NyaMangaClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _handle_response(self, resp: requests.Response) -> Dict[str, Any]:
        if resp.status_code >= 300:
            raise ApiError(f"{resp.status_code}: {resp.text}")
        if not resp.content:
            return {}
        # Try JSON first, otherwise hand back text blob.
        try:
            return resp.json()
        except json.JSONDecodeError:
            return {"data": resp.content}
