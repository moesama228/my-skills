#!/usr/bin/env python3
"""Generate the optional agents/openai.yaml adapter for an Agent Skill."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ACRONYMS = {"AI", "API", "CI", "CLI", "GH", "LLM", "MCP", "PDF", "PR", "SQL", "UI", "URL"}
BRANDS = {
    "fastapi": "FastAPI",
    "github": "GitHub",
    "openai": "OpenAI",
    "openapi": "OpenAPI",
    "sqlite": "SQLite",
}
SMALL_WORDS = {"and", "or", "to", "up", "with"}
ALLOWED_INTERFACE_KEYS = {
    "display_name",
    "short_description",
    "icon_small",
    "icon_large",
    "brand_color",
    "default_prompt",
}


def yaml_quote(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def format_display_name(skill_name: str) -> str:
    words = [word for word in skill_name.split("-") if word]
    formatted: list[str] = []
    for index, word in enumerate(words):
        lower = word.lower()
        upper = word.upper()
        if upper in ACRONYMS:
            formatted.append(upper)
        elif lower in BRANDS:
            formatted.append(BRANDS[lower])
        elif index > 0 and lower in SMALL_WORDS:
            formatted.append(lower)
        else:
            formatted.append(word.capitalize())
    return " ".join(formatted)


def generate_short_description(display_name: str) -> str:
    candidates = [
        f"Create and update {display_name}",
        f"Help with {display_name} tasks",
        f"Help with {display_name} workflows",
        f"{display_name} tools and guidance",
    ]
    for candidate in candidates:
        if 25 <= len(candidate) <= 64:
            return candidate

    suffix = " skill helper"
    trimmed = display_name[: 64 - len(suffix)].rstrip()
    description = f"{trimmed}{suffix}"
    if len(description) < 25:
        description = f"{description} and workflows"
    return description[:64].rstrip()


def parse_interface_overrides(raw_overrides: list[str]) -> tuple[dict[str, str], list[str]]:
    overrides: dict[str, str] = {}
    optional_order: list[str] = []

    for item in raw_overrides:
        if "=" not in item:
            raise ValueError(f"Invalid interface override '{item}'; expected key=value.")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key not in ALLOWED_INTERFACE_KEYS:
            allowed = ", ".join(sorted(ALLOWED_INTERFACE_KEYS))
            raise ValueError(f"Unknown interface field '{key}'. Allowed: {allowed}.")
        if not value:
            raise ValueError(f"Interface field '{key}' cannot be empty.")
        overrides[key] = value
        if key not in {"display_name", "short_description"} and key not in optional_order:
            optional_order.append(key)

    return overrides, optional_order


def validate_interface(skill_name: str, overrides: dict[str, str]) -> tuple[str, str]:
    display_name = overrides.get("display_name") or format_display_name(skill_name)
    short_description = overrides.get("short_description") or generate_short_description(display_name)

    if not display_name:
        raise ValueError("display_name cannot be empty.")
    if not 25 <= len(short_description) <= 64:
        raise ValueError(
            "short_description must be 25-64 characters "
            f"(got {len(short_description)})."
        )

    for key in ("icon_small", "icon_large"):
        value = overrides.get(key)
        if value and (Path(value).is_absolute() or not value.startswith("./assets/")):
            raise ValueError(f"{key} must be a relative path under ./assets/.")

    brand_color = overrides.get("brand_color")
    if brand_color and not re.fullmatch(r"#[0-9A-Fa-f]{6}", brand_color):
        raise ValueError("brand_color must be a six-digit hexadecimal color such as #3B82F6.")

    default_prompt = overrides.get("default_prompt")
    if default_prompt and f"${skill_name}" not in default_prompt:
        raise ValueError(f"default_prompt must explicitly mention ${skill_name}.")

    return display_name, short_description


def read_frontmatter_name(skill_dir: Path) -> str:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise ValueError(f"SKILL.md not found in {skill_dir}.")

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required. Install scripts/requirements.txt before running this command."
        ) from exc

    content = skill_md.read_text(encoding="utf-8")
    match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", content, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md has invalid YAML frontmatter delimiters.")
    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML frontmatter: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise ValueError("SKILL.md frontmatter must be a mapping.")
    name = frontmatter.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("SKILL.md frontmatter requires a non-empty string 'name'.")
    return name.strip()


def write_openai_yaml(
    skill_dir: Path,
    skill_name: str,
    raw_overrides: list[str],
) -> Path:
    overrides, optional_order = parse_interface_overrides(raw_overrides)
    display_name, short_description = validate_interface(skill_name, overrides)

    output_path = skill_dir / "agents" / "openai.yaml"
    if output_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing adapter: {output_path}. Edit it in place."
        )

    lines = [
        "interface:",
        f"  display_name: {yaml_quote(display_name)}",
        f"  short_description: {yaml_quote(short_description)}",
    ]
    for key in optional_order:
        lines.append(f"  {key}: {yaml_quote(overrides[key])}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create the optional agents/openai.yaml adapter for an Agent Skill."
    )
    parser.add_argument("skill_dir", help="Path to the skill directory")
    parser.add_argument("--name", help="Skill name override; defaults to SKILL.md frontmatter")
    parser.add_argument(
        "--interface",
        action="append",
        default=[],
        help="OpenAI interface field in key=value form; repeat as needed",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).expanduser().resolve()
    if not skill_dir.is_dir():
        print(f"[ERROR] Skill directory not found: {skill_dir}", file=sys.stderr)
        return 1

    try:
        skill_name = args.name or read_frontmatter_name(skill_dir)
        output_path = write_openai_yaml(skill_dir, skill_name, args.interface)
    except (FileExistsError, RuntimeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"[OK] Created {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
