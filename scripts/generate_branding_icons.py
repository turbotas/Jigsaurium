#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageColor


ICON_SPECS: tuple[tuple[str, int], ...] = (
    ("favicon-16.png", 16),
    ("favicon-32.png", 32),
    ("apple-touch-icon.png", 180),
    ("icon-192.png", 192),
    ("icon-512.png", 512),
)


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    default_source = repo_root / "app" / "static" / "branding" / "JigsauriumLogoMaster.png"
    default_output_dir = repo_root / "app" / "static" / "branding" / "icons"
    default_manifest = repo_root / "app" / "static" / "branding" / "site.webmanifest"

    parser = argparse.ArgumentParser(
        description="Generate favicon and mobile app icons from a single master image."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=default_source,
        help=f"Input master logo image (default: {default_source})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help=f"Directory for generated icon files (default: {default_output_dir})",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.08,
        help="Padding around the logo inside each square icon, as a fraction (default: 0.08)",
    )
    parser.add_argument(
        "--background",
        default="#00000000",
        help="Background color behind logo (default: transparent). Examples: '#ffffff', '#ffffffff'.",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=default_manifest,
        help=f"Path for generated web manifest (default: {default_manifest})",
    )
    parser.add_argument(
        "--app-name",
        default="Jigsaurium",
        help="Application name for the web manifest (default: Jigsaurium)",
    )
    parser.add_argument(
        "--short-name",
        default="Jigsaurium",
        help="Short application name for the web manifest (default: Jigsaurium)",
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help="Skip generating site.webmanifest",
    )

    args = parser.parse_args()
    if args.padding < 0 or args.padding >= 0.5:
        raise SystemExit("--padding must be >= 0 and < 0.5")
    return args


def build_square_icon(source: Image.Image, size: int, padding: float, background: tuple[int, ...]) -> Image.Image:
    source = source.convert("RGBA")
    target = Image.new("RGBA", (size, size), background)

    max_dimension = max(1, round(size * (1 - (padding * 2))))
    scale = min(max_dimension / source.width, max_dimension / source.height)
    resized = source.resize(
        (
            max(1, round(source.width * scale)),
            max(1, round(source.height * scale)),
        ),
        Image.Resampling.LANCZOS,
    )

    x_offset = (size - resized.width) // 2
    y_offset = (size - resized.height) // 2
    target.paste(resized, (x_offset, y_offset), resized)
    return target


def write_manifest(path: Path, app_name: str, short_name: str) -> None:
    payload = {
        "name": app_name,
        "short_name": short_name,
        "icons": [
            {
                "src": "/static/branding/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": "/static/branding/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
        "theme_color": "#1d70b8",
        "background_color": "#ffffff",
        "display": "standalone",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    source_path = args.source
    output_dir = args.output_dir

    if not source_path.exists():
        raise SystemExit(f"Source file not found: {source_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    background = ImageColor.getcolor(args.background, "RGBA")

    with Image.open(source_path) as source_image:
        generated_paths: list[Path] = []

        for file_name, size in ICON_SPECS:
            icon = build_square_icon(source_image, size=size, padding=args.padding, background=background)
            output_path = output_dir / file_name
            icon.save(output_path, format="PNG")
            generated_paths.append(output_path)

        ico_source = build_square_icon(source_image, size=64, padding=args.padding, background=background)
        favicon_ico = output_dir / "favicon.ico"
        ico_source.save(favicon_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
        generated_paths.append(favicon_ico)

    if not args.no_manifest:
        write_manifest(args.manifest_path, app_name=args.app_name, short_name=args.short_name)
        generated_paths.append(args.manifest_path)

    print("Generated branding assets:")
    for path in generated_paths:
        print(f"- {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
