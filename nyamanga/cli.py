import argparse
import base64
from pathlib import Path
import sys

from .config import ApiConfig
from .pipeline import TypesettingPipeline


def _decode_to_file(image_b64: str, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(image_b64))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manga typesetting helper using the nano-banana-2 model."
    )
    subparsers = parser.add_subparsers(dest="command")

    rewrite = subparsers.add_parser("rewrite", help="Rewrite/translate text only.")
    rewrite.add_argument("text", help="Raw dialogue to rewrite.")
    rewrite.add_argument("--target-language", default="zh", help="Target language.")
    rewrite.add_argument(
        "--tone", default="friendly manga voice", help="Tone/style hints."
    )

    embed = subparsers.add_parser("embed", help="Embed provided text into an image.")
    embed.add_argument("image", type=Path, help="Path to the panel image.")
    embed.add_argument("text", help="Text to embed.")
    embed.add_argument(
        "--bubble-hint",
        default=None,
        help="Rough placement hints (e.g. top-left balloon).",
    )
    embed.add_argument("--mask", type=Path, default=None, help="Optional PNG mask.")
    embed.add_argument(
        "--output",
        type=Path,
        default=Path("output.png"),
        help="Where to save the edited image.",
    )

    localize = subparsers.add_parser(
        "localize", help="Rewrite text and embed it into an image in one call."
    )
    localize.add_argument("image", type=Path, help="Path to the panel image.")
    localize.add_argument("text", help="Source dialogue to rewrite.")
    localize.add_argument("--target-language", default="zh", help="Target language.")
    localize.add_argument("--tone", default="friendly manga voice", help="Tone hint.")
    localize.add_argument(
        "--bubble-hint",
        default=None,
        help="Rough placement hints (e.g. top-left balloon).",
    )
    localize.add_argument("--mask", type=Path, default=None, help="Optional PNG mask.")
    localize.add_argument(
        "--output",
        type=Path,
        default=Path("output.png"),
        help="Where to save the edited image.",
    )

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    config = ApiConfig.from_env()

    with TypesettingPipeline(config) as pipeline:
        if args.command == "rewrite":
            result = pipeline.embedder.rewrite_dialogue(
                source_text=args.text,
                target_language=args.target_language,
                tone=args.tone,
            )
            print(result.text)
            return 0

        if args.command == "embed":
            result = pipeline.embedder.embed_text(
                image_path=args.image,
                text=args.text,
                bubble_hint=args.bubble_hint,
                mask_path=args.mask,
            )
            _decode_to_file(result.image_b64, args.output)
            print(f"Edited image saved to {args.output}")
            return 0

        if args.command == "localize":
            combined = pipeline.localize_panel(
                image_path=args.image,
                source_text=args.text,
                target_language=args.target_language,
                tone=args.tone,
                bubble_hint=args.bubble_hint,
                mask_path=args.mask,
            )
            _decode_to_file(combined.edited_image_b64, args.output)
            print(f"Rewritten text: {combined.rewritten_text}")
            print(f"Edited image saved to {args.output}")
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
