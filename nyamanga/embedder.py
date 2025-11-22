"""
Higher-level helpers for manga typesetting flows.
UI layers can call these functions directly or wrap them inside their own state.
"""
import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from .client import NyaMangaClient


@dataclass
class DialogueRewriteResult:
    text: str
    raw_response: Dict


@dataclass
class EmbedResult:
    image_b64: str
    raw_response: Dict

    def save(self, path: Path) -> Path:
        data = base64.b64decode(self.image_b64)
        path.write_bytes(data)
        return path


class MangaEmbedder:
    """Couples chat + image calls into manga-friendly utilities."""

    def __init__(self, client: NyaMangaClient):
        self.client = client

    def rewrite_dialogue(
        self,
        source_text: str,
        target_language: str = "zh",
        tone: str = "friendly manga voice",
    ) -> DialogueRewriteResult:
        """Rewrite or translate dialogue via the chat endpoint."""
        system_prompt = (
            "You are a manga typesetting assistant. Translate or rewrite speech "
            f"into {target_language} while keeping natural pacing and concise bubbles. "
            "Return plain text only."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": source_text},
        ]
        resp = self.client.chat_completion(
            messages,
            temperature=0.7,
            model=self.client.config.chat_model,
        )
        choice = _first_message_content(resp)
        return DialogueRewriteResult(text=choice, raw_response=resp)

    def embed_text(
        self,
        image_path: Path,
        text: str,
        bubble_hint: Optional[str] = None,
        mask_path: Optional[Path] = None,
        style_hint: Optional[str] = None,
    ) -> EmbedResult:
        """Send an image edit request that places text into the given panel."""
        prompt = self._build_prompt(
            text,
            bubble_hint,
            style_hint or "clean manga typesetting, legible, keep art intact",
        )
        resp = self.client.edit_image(
            image_path=image_path,
            prompt=prompt,
            mask_path=mask_path,
            response_format="b64_json",
        )
        image_b64 = _first_b64_image(resp)
        return EmbedResult(image_b64=image_b64, raw_response=resp)

    def auto_localize(
        self,
        image_path: Path,
        target_language: str = "zh",
        bubble_hint: Optional[str] = None,
        mask_path: Optional[Path] = None,
        style_hint: Optional[str] = None,
    ) -> EmbedResult:
        """
        Ask the image model to read existing dialogue and replace it with a
        translation/typeset version directly (no separate text input).
        """
        placement = (
            f"Focus on balloons: {bubble_hint}. " if bubble_hint else "Use existing speech balloons. "
        )
        prompt = (
            f"{placement}"
            f"Read all speech/text in the image, translate to {target_language}, "
            "and replace with natural, concise manga typesetting. "
            "Preserve art, faces, and backgrounds; avoid redraw artifacts. "
            f"{style_hint or 'Clean, legible, balanced layout.'}"
        )
        resp = self.client.edit_image(
            image_path=image_path,
            prompt=prompt,
            mask_path=mask_path,
            response_format="b64_json",
        )
        image_b64 = _first_b64_image(resp)
        return EmbedResult(image_b64=image_b64, raw_response=resp)

    def _build_prompt(self, text: str, bubble_hint: Optional[str], style_hint: str) -> str:
        placement = (
            f"Place the text inside speech balloons: {bubble_hint}. "
            if bubble_hint
            else "Place the text into existing speech balloons while preserving line art. "
        )
        return (
            f"{placement}"
            f"Text to typeset: {text}. "
            f"Styling: {style_hint}. "
            "Use natural spacing and avoid altering faces or backgrounds."
        )


def _first_message_content(resp: Dict) -> str:
    """Extract first message content from a chat completion response."""
    choices = resp.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return message.get("content", "").strip()


def _first_b64_image(resp: Dict) -> str:
    """Extract base64 image string from an image response."""
    data_list = resp.get("data") or []
    if not data_list:
        return ""
    item = data_list[0]
    if isinstance(item, dict):
        return item.get("b64_json") or item.get("base64") or ""
    if isinstance(item, str):
        return item
    return ""
