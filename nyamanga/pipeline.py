from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .client import NyaMangaClient
from .config import ApiConfig
from .embedder import DialogueRewriteResult, EmbedResult, MangaEmbedder


@dataclass
class PanelResult:
    rewritten_text: str
    edited_image_b64: str
    dialogue_response: dict
    image_response: dict


class TypesettingPipeline:
    """
    Minimal end-to-end pipeline. UI code can call `localize_panel` and then
    decide how to display or post-process the base64 image and rewritten text.
    """

    def __init__(self, config: Optional[ApiConfig] = None, client: Optional[NyaMangaClient] = None):
        self.config = config or ApiConfig.from_env()
        self.client = client or NyaMangaClient(self.config)
        self.embedder = MangaEmbedder(self.client)

    def localize_panel(
        self,
        image_path: Path,
        source_text: str,
        target_language: str = "zh",
        tone: str = "friendly manga voice",
        bubble_hint: Optional[str] = None,
        mask_path: Optional[Path] = None,
        style_hint: Optional[str] = None,
    ) -> PanelResult:
        """
        Translate/rewrite dialogue and send a single edit request to place it.

        Returns base64 image data so callers can render it on any platform.
        """
        dialogue: DialogueRewriteResult = self.embedder.rewrite_dialogue(
            source_text=source_text,
            target_language=target_language,
            tone=tone,
        )
        embed: EmbedResult = self.embedder.embed_text(
            image_path=image_path,
            text=dialogue.text,
            bubble_hint=bubble_hint,
            mask_path=mask_path,
            style_hint=style_hint,
        )
        return PanelResult(
            rewritten_text=dialogue.text,
            edited_image_b64=embed.image_b64,
            dialogue_response=dialogue.raw_response,
            image_response=embed.raw_response,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "TypesettingPipeline":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
