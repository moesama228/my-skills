#!/usr/bin/env python3
"""Create a standalone HTML file by embedding local image assets as Base64."""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
from pathlib import Path


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif")

ATTR_IMAGE_RE = re.compile(
    r"(?P<prefix>\b(?:src|href)=)(?P<quote>[\"'])"
    r"(?P<path>(?!data:|https?://|//|#|mailto:)[^\"']+?)"
    r"(?P=quote)",
    re.IGNORECASE,
)
CSS_IMAGE_RE = re.compile(
    r"url\((?P<quote>[\"']?)"
    r"(?P<path>(?!data:|https?://|//|#|mailto:)[^)\"']+?)"
    r"(?P=quote)\)",
    re.IGNORECASE,
)


def path_without_fragment(asset_ref: str) -> str:
    return re.split(r"[?#]", asset_ref, maxsplit=1)[0]


def is_image_ref(asset_ref: str) -> bool:
    return path_without_fragment(asset_ref).lower().endswith(IMAGE_EXTENSIONS)


def guess_mime_type(path: Path) -> str:
    if path.suffix.lower() == ".svg":
        return "image/svg+xml"
    mime_type, _ = mimetypes.guess_type(path.name)
    return mime_type or "application/octet-stream"


def to_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{guess_mime_type(path)};base64,{encoded}"


def inline_assets(html: str, base_dir: Path) -> tuple[str, dict[str, int]]:
    cache: dict[str, str] = {}
    base_dir = base_dir.resolve()

    def resolve(asset_ref: str) -> str:
        if not is_image_ref(asset_ref):
            return asset_ref

        asset_path = path_without_fragment(asset_ref)
        source = (base_dir / asset_path).resolve()
        try:
            source.relative_to(base_dir)
        except ValueError as exc:
            raise ValueError(f"Refusing to inline path outside base dir: {asset_ref}") from exc

        if not source.is_file():
            raise FileNotFoundError(f"Referenced image asset not found: {asset_ref}")

        if asset_path not in cache:
            cache[asset_path] = to_data_uri(source)
        return cache[asset_path]

    def replace_attr(match: re.Match[str]) -> str:
        path = match.group("path")
        return f"{match.group('prefix')}{match.group('quote')}{resolve(path)}{match.group('quote')}"

    def replace_css(match: re.Match[str]) -> str:
        path = match.group("path")
        return f"url({match.group('quote')}{resolve(path)}{match.group('quote')})"

    html = ATTR_IMAGE_RE.sub(replace_attr, html)
    html = CSS_IMAGE_RE.sub(replace_css, html)
    return html, {
        "unique_assets": len(cache),
        "data_uri_count": len(re.findall(r"data:image/", html)),
    }


def output_default(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_standalone{input_path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Embed local image references in an HTML file as Base64 data URIs."
    )
    parser.add_argument("input", help="Input HTML file")
    parser.add_argument("-o", "--output", help="Output HTML file. Default: <input_stem>_standalone.html")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve() if args.output else output_default(input_path)

    html = input_path.read_text(encoding="utf-8")
    standalone_html, stats = inline_assets(html, input_path.parent)
    output_path.write_text(standalone_html, encoding="utf-8")

    print(f"Wrote {output_path}")
    print(f"Inlined image assets: {stats['unique_assets']}")
    print(f"Data image URIs: {stats['data_uri_count']}")
    print(f"Output size: {output_path.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
