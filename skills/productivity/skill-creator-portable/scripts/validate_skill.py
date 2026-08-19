#!/usr/bin/env python3
"""Validate an Agent Skill against the portable format plus quality warnings."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    import yaml
except ImportError:  # Reported cleanly by main and validate_skill.
    yaml = None


MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500
RECOMMENDED_MAX_LINES = 500
ALLOWED_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)
MARKDOWN_LINK_PATTERN = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")


def parse_skill(content: str) -> tuple[dict, str]:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required. Install scripts/requirements.txt before running validation."
        )

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        raise ValueError("SKILL.md must start with closed YAML frontmatter delimiters.")
    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML frontmatter: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ValueError("SKILL.md frontmatter must be a YAML mapping.")
    return metadata, content[match.end() :]


def validate_frontmatter(metadata: dict, skill_dir: Path) -> list[str]:
    errors: list[str] = []

    unexpected = sorted(set(metadata) - ALLOWED_FIELDS)
    if unexpected:
        errors.append(
            "Unexpected frontmatter field(s): "
            f"{', '.join(unexpected)}. Allowed fields: {', '.join(sorted(ALLOWED_FIELDS))}."
        )

    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("Field 'name' must be a non-empty string.")
    else:
        name = name.strip()
        if len(name) > MAX_SKILL_NAME_LENGTH:
            errors.append(
                f"Field 'name' exceeds {MAX_SKILL_NAME_LENGTH} characters "
                f"({len(name)} characters)."
            )
        if not NAME_PATTERN.fullmatch(name):
            errors.append(
                "Field 'name' must use lowercase ASCII letters, digits, and single hyphens, "
                "without leading or trailing hyphens."
            )
        if skill_dir.name != name:
            errors.append(
                f"Directory name '{skill_dir.name}' must match frontmatter name '{name}'."
            )

    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append("Field 'description' must be a non-empty string.")
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f"Field 'description' exceeds {MAX_DESCRIPTION_LENGTH} characters "
            f"({len(description)} characters)."
        )

    if "license" in metadata:
        license_value = metadata["license"]
        if not isinstance(license_value, str) or not license_value.strip():
            errors.append("Field 'license' must be a non-empty string when provided.")

    if "compatibility" in metadata:
        compatibility = metadata["compatibility"]
        if not isinstance(compatibility, str) or not compatibility.strip():
            errors.append("Field 'compatibility' must be a non-empty string when provided.")
        elif len(compatibility) > MAX_COMPATIBILITY_LENGTH:
            errors.append(
                f"Field 'compatibility' exceeds {MAX_COMPATIBILITY_LENGTH} characters "
                f"({len(compatibility)} characters)."
            )

    if "metadata" in metadata:
        extra_metadata = metadata["metadata"]
        if not isinstance(extra_metadata, dict):
            errors.append("Field 'metadata' must be a mapping of string keys to string values.")
        else:
            for key, value in extra_metadata.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    errors.append(
                        "Field 'metadata' must contain only string keys and string values."
                    )
                    break

    if "allowed-tools" in metadata:
        allowed_tools = metadata["allowed-tools"]
        if not isinstance(allowed_tools, str) or not allowed_tools.strip():
            errors.append("Field 'allowed-tools' must be a non-empty string when provided.")

    return errors


def find_unfinished_markers(body: str) -> bool:
    fence_character: str | None = None
    fence_length = 0

    for line in body.splitlines():
        fence = re.match(r"^[ \t]*(?:(?:[-+*]|\d+[.)])[ \t]+)?(`{3,}|~{3,})(.*)$", line)
        if fence:
            marker = fence.group(1)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif (
                marker[0] == fence_character
                and len(marker) >= fence_length
                and not fence.group(2).strip()
            ):
                fence_character = None
                fence_length = 0
            continue
        if fence_character is None and "[TODO:" in line:
            return True
    return False


def extract_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split(maxsplit=1)[0]


def find_broken_local_links(body: str, skill_dir: Path) -> list[str]:
    warnings: list[str] = []
    seen: set[str] = set()
    skill_root = skill_dir.resolve()

    for match in MARKDOWN_LINK_PATTERN.finditer(body):
        target = extract_link_target(match.group(1))
        if not target or target.startswith("#"):
            continue
        parsed = urlparse(target)
        if parsed.scheme or parsed.netloc:
            continue

        relative_target = unquote(parsed.path)
        if not relative_target:
            continue
        target_path = Path(relative_target)
        if target_path.is_absolute():
            warnings.append(f"Local Markdown link should be relative to the skill root: {target}")
            continue

        resolved = (skill_root / target_path).resolve()
        try:
            resolved.relative_to(skill_root)
        except ValueError:
            warnings.append(f"Local Markdown link escapes the skill root: {target}")
            continue

        if not resolved.exists() and target not in seen:
            warnings.append(f"Local Markdown link target does not exist: {target}")
            seen.add(target)

    return warnings


def validate_skill(skill_path: Path) -> tuple[list[str], list[str]]:
    skill_dir = Path(skill_path).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not skill_dir.exists():
        return [f"Path does not exist: {skill_dir}"], warnings
    if not skill_dir.is_dir():
        return [f"Path is not a directory: {skill_dir}"], warnings

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return ["Missing required file: SKILL.md"], warnings

    try:
        content = skill_md.read_text(encoding="utf-8")
        metadata, body = parse_skill(content)
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        return [str(exc)], warnings

    errors.extend(validate_frontmatter(metadata, skill_dir))

    description = metadata.get("description")
    if isinstance(description, str) and "[TODO:" in description:
        warnings.append("Frontmatter description contains an unfinished scaffold marker.")
    if not body.strip():
        warnings.append("SKILL.md has no instruction body.")
    if len(content.splitlines()) > RECOMMENDED_MAX_LINES:
        warnings.append(
            f"SKILL.md has {len(content.splitlines())} lines; "
            f"the portability recommendation is at most {RECOMMENDED_MAX_LINES}."
        )
    if find_unfinished_markers(body):
        warnings.append("SKILL.md contains an unfinished scaffold marker outside a code fence.")
    warnings.extend(find_broken_local_links(body, skill_dir))

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a portable Agent Skill directory.")
    parser.add_argument("skill_directory", help="Path to the skill directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero status when quality warnings are present",
    )
    args = parser.parse_args()

    errors, warnings = validate_skill(Path(args.skill_directory))
    for message in errors:
        print(f"ERROR: {message}")
    for message in warnings:
        print(f"WARNING: {message}")

    if errors or (args.strict and warnings):
        return 1
    print("Skill is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
