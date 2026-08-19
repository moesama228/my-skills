#!/usr/bin/env python3
"""Atomically initialize a portable Agent Skill."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

from generate_openai_yaml import parse_interface_overrides, write_openai_yaml


MAX_SKILL_NAME_LENGTH = 64
ALLOWED_RESOURCES = {"scripts", "references", "assets"}

SKILL_TEMPLATE = """---
name: {skill_name}
description: "[TODO: Describe what this skill does and when an agent should use it.]"
---

# {skill_title}

[TODO: Add the task-specific guidance an agent needs. Keep only resources that support real workflow branches.]
"""


def normalize_skill_name(raw_name: str) -> str:
    normalized = raw_name.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized


def validate_requested_name(raw_name: str) -> str:
    normalized = normalize_skill_name(raw_name)
    if not normalized:
        raise ValueError("Skill name must contain at least one ASCII letter or digit.")
    if len(normalized) > MAX_SKILL_NAME_LENGTH:
        raise ValueError(
            f"Normalized skill name is {len(normalized)} characters; "
            f"the maximum is {MAX_SKILL_NAME_LENGTH}."
        )
    return normalized


def title_case_skill_name(skill_name: str) -> str:
    return " ".join(word.capitalize() for word in skill_name.split("-"))


def parse_resources(raw_resources: str) -> list[str]:
    if not raw_resources:
        return []
    resources = [item.strip() for item in raw_resources.split(",") if item.strip()]
    invalid = sorted(set(resources) - ALLOWED_RESOURCES)
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_RESOURCES))
        raise ValueError(f"Unknown resource type(s): {', '.join(invalid)}. Allowed: {allowed}.")
    return list(dict.fromkeys(resources))


def init_skill(
    raw_name: str,
    output_directory: Path,
    resources: list[str] | None = None,
    include_openai: bool = False,
    interface_overrides: list[str] | None = None,
) -> Path:
    skill_name = validate_requested_name(raw_name)
    resources = resources or []
    interface_overrides = interface_overrides or []

    invalid = sorted(set(resources) - ALLOWED_RESOURCES)
    if invalid:
        raise ValueError(f"Unknown resource type(s): {', '.join(invalid)}.")
    if interface_overrides and not include_openai:
        raise ValueError("--interface requires --openai.")
    if include_openai:
        parse_interface_overrides(interface_overrides)

    output_directory = Path(output_directory).expanduser().resolve()
    skill_dir = output_directory / skill_name
    if skill_dir.exists():
        raise FileExistsError(f"Skill directory already exists: {skill_dir}")

    output_directory.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{skill_name}.", dir=output_directory))

    try:
        title = title_case_skill_name(skill_name)
        (staging / "SKILL.md").write_text(
            SKILL_TEMPLATE.format(skill_name=skill_name, skill_title=title),
            encoding="utf-8",
        )
        for resource in resources:
            (staging / resource).mkdir()
        if include_openai:
            write_openai_yaml(staging, skill_name, interface_overrides)
        staging.rename(skill_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return skill_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a portable Agent Skill scaffold.")
    parser.add_argument("skill_name", help="Skill name; normalized to lowercase hyphen-case")
    parser.add_argument("--path", required=True, help="Directory that will contain the skill")
    parser.add_argument(
        "--resources",
        default="",
        help="Comma-separated optional directories: scripts,references,assets",
    )
    parser.add_argument(
        "--openai",
        action="store_true",
        help="Add the optional agents/openai.yaml product adapter",
    )
    parser.add_argument(
        "--interface",
        action="append",
        default=[],
        help="OpenAI interface field in key=value form; requires --openai",
    )
    args = parser.parse_args()

    try:
        resources = parse_resources(args.resources)
        skill_dir = init_skill(
            args.skill_name,
            Path(args.path),
            resources=resources,
            include_openai=args.openai,
            interface_overrides=args.interface,
        )
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    normalized = skill_dir.name
    if normalized != args.skill_name:
        print(f"[NOTE] Normalized '{args.skill_name}' to '{normalized}'.")
    print(f"[OK] Created portable skill scaffold: {skill_dir}")
    print("Next: replace scaffold markers, add only needed resources, then run validate_skill.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
