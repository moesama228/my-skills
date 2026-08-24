#!/usr/bin/env python3
"""Validate an Agent Skill against the portable format plus quality warnings."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import unquote, urlparse

from frontmatter_support import SUPPORTED_TARGETS, analyze_frontmatter

try:
    import yaml
except ImportError:  # Reported cleanly by main and validate_skill.
    yaml = None


RECOMMENDED_MAX_LINES = 500
FRONTMATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)
MARKDOWN_LINK_PATTERN = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")


@dataclass
class ValidationReport:
    errors: list[str]
    quality_warnings: list[str]
    notes: list[str]

    def should_fail(self, strict: bool = False) -> bool:
        return bool(self.errors or (strict and self.quality_warnings))


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


def validate_explicit_only_pair(metadata: dict, skill_dir: Path) -> list[str]:
    """Require the OpenAI invocation policy when portable frontmatter is explicit-only."""

    if metadata.get("disable-model-invocation") is not True:
        return []

    adapter_path = skill_dir / "agents" / "openai.yaml"
    if not adapter_path.is_file():
        return [
            "[INVOCATION_PAIR_MISSING] An explicit-only skill also requires "
            "agents/openai.yaml with policy.allow_implicit_invocation set to false."
        ]

    try:
        adapter = yaml.safe_load(adapter_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return [f"Invalid agents/openai.yaml for explicit-only invocation: {exc}"]

    policy = adapter.get("policy") if isinstance(adapter, dict) else None
    if not isinstance(policy, dict) or policy.get("allow_implicit_invocation") is not False:
        return [
            "[INVOCATION_PAIR_INVALID] An explicit-only skill requires "
            "agents/openai.yaml policy.allow_implicit_invocation to be the YAML boolean false."
        ]
    return []


def analyze_skill(
    skill_path: Path,
    *,
    targets: Sequence[str] = (),
) -> ValidationReport:
    skill_dir = Path(skill_path).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    if not skill_dir.exists():
        return ValidationReport([f"Path does not exist: {skill_dir}"], warnings, notes)
    if not skill_dir.is_dir():
        return ValidationReport([f"Path is not a directory: {skill_dir}"], warnings, notes)

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return ValidationReport(["Missing required file: SKILL.md"], warnings, notes)

    try:
        content = skill_md.read_text(encoding="utf-8")
        metadata, body = parse_skill(content)
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        return ValidationReport([str(exc)], warnings, notes)

    frontmatter = analyze_frontmatter(metadata, skill_dir, targets)
    errors.extend(frontmatter.errors)
    notes.extend(frontmatter.notes)
    errors.extend(validate_explicit_only_pair(metadata, skill_dir))

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

    return ValidationReport(errors, warnings, notes)


def validate_skill(skill_path: Path) -> tuple[list[str], list[str]]:
    """Compatibility wrapper for validation without target-specific checks."""

    report = analyze_skill(skill_path)
    return report.errors, report.quality_warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a portable Agent Skill directory.")
    parser.add_argument("skill_directory", help="Path to the skill directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero status when quality warnings are present",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        choices=SUPPORTED_TARGETS,
        help="Check SKILL.md frontmatter for a client target; repeat for multiple targets",
    )
    args = parser.parse_args()

    report = analyze_skill(Path(args.skill_directory), targets=args.target)
    for message in report.errors:
        print(f"ERROR: {message}")
    for message in report.quality_warnings:
        print(f"WARNING: {message}")
    for message in report.notes:
        print(f"NOTICE: {message}")

    if report.should_fail(strict=args.strict):
        return 1
    if args.target:
        targets = ", ".join(dict.fromkeys(args.target))
        print(
            "SKILL.md is valid and its frontmatter is accepted by target(s): "
            f"{targets}. Explicit-only pairing was checked; other adapter fields were not."
        )
    else:
        print("Skill is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
