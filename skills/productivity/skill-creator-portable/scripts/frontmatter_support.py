"""Validate frontmatter against Agent Skills and a 2026-08-24 target snapshot.

Target acceptance describes standalone skills. Product adapters and plugin-package
ingestion have separate schemas and must be validated independently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

HOST_NAMES = {
    "claude": "Claude Code",
    "codex": "Codex",
    "kimi": "Kimi Code",
    "grok": "Grok Build",
    "cursor": "Cursor",
    "pi": "Pi Agent",
}
SUPPORTED_TARGETS = tuple(HOST_NAMES)

NATIVE = "native"
ACCEPTED = "accepted"
REJECTED = "rejected"
UNCONFIRMED = "unconfirmed"


@dataclass(frozen=True)
class FieldRule:
    host_acceptance: Mapping[str, str]


@dataclass
class FrontmatterAnalysis:
    errors: list[str]
    notes: list[str]


ALL_NATIVE = {target: NATIVE for target in SUPPORTED_TARGETS}

FIELD_RULES = {
    "name": FieldRule(ALL_NATIVE),
    "description": FieldRule(ALL_NATIVE),
    "license": FieldRule(
        {
            "claude": ACCEPTED,
            "codex": ACCEPTED,
            "kimi": UNCONFIRMED,
            "grok": ACCEPTED,
            "cursor": UNCONFIRMED,
            "pi": ACCEPTED,
        },
    ),
    "compatibility": FieldRule(
        {
            "claude": ACCEPTED,
            "codex": REJECTED,
            "kimi": UNCONFIRMED,
            "grok": ACCEPTED,
            "cursor": UNCONFIRMED,
            "pi": ACCEPTED,
        },
    ),
    "metadata": FieldRule(
        {
            "claude": ACCEPTED,
            "codex": ACCEPTED,
            "kimi": UNCONFIRMED,
            "grok": ACCEPTED,
            "cursor": ACCEPTED,
            "pi": ACCEPTED,
        },
    ),
    "allowed-tools": FieldRule(
        {
            "claude": NATIVE,
            "codex": ACCEPTED,
            "kimi": UNCONFIRMED,
            "grok": NATIVE,
            "cursor": UNCONFIRMED,
            "pi": ACCEPTED,
        },
    ),
    "disable-model-invocation": FieldRule(
        {
            "claude": NATIVE,
            "codex": ACCEPTED,
            "kimi": NATIVE,
            "grok": NATIVE,
            "cursor": NATIVE,
            "pi": NATIVE,
        },
    ),
}


def _display_targets(targets: Sequence[str]) -> str:
    return ", ".join(HOST_NAMES.get(target, target) for target in targets)


def _validate_known_fields(metadata: Mapping[object, object], skill_dir: Path) -> list[str]:
    errors: list[str] = []

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

    if "disable-model-invocation" in metadata:
        value = metadata["disable-model-invocation"]
        if not isinstance(value, bool):
            errors.append("Field 'disable-model-invocation' must be a YAML boolean.")

    return errors


def analyze_frontmatter(
    metadata: Mapping[object, object],
    skill_dir: Path,
    targets: Sequence[str] = (),
) -> FrontmatterAnalysis:
    """Return frontmatter errors and non-failing compatibility notes."""

    errors: list[str] = []
    notes: list[str] = []
    normalized_targets = tuple(dict.fromkeys(targets))

    unknown_targets = [target for target in normalized_targets if target not in HOST_NAMES]
    if unknown_targets:
        errors.append(
            "[HC_UNKNOWN_TARGET] Unknown target(s): "
            f"{', '.join(unknown_targets)}. Supported targets: "
            f"{', '.join(SUPPORTED_TARGETS)}."
        )

    non_string_keys = [key for key in metadata if not isinstance(key, str)]
    if non_string_keys:
        errors.append("Frontmatter field names must be strings.")

    string_keys = {key for key in metadata if isinstance(key, str)}
    unexpected = sorted(string_keys - set(FIELD_RULES))
    if unexpected:
        errors.append(
            "Unexpected frontmatter field(s): "
            f"{', '.join(unexpected)}. Recognized fields: "
            f"{', '.join(sorted(FIELD_RULES))}."
        )

    errors.extend(_validate_known_fields(metadata, skill_dir))

    if "allowed-tools" in metadata:
        notes.append(
            "[TOOLS_RUNTIME] 'allowed-tools' is experimental and does not establish "
            "portable authorization; client enforcement varies."
        )

    if normalized_targets and not unknown_targets:
        for key in sorted(string_keys & set(FIELD_RULES)):
            rule = FIELD_RULES[key]
            accepted_targets = [
                target
                for target in normalized_targets
                if rule.host_acceptance[target] in {NATIVE, ACCEPTED}
            ]
            rejected_targets = [
                target
                for target in normalized_targets
                if rule.host_acceptance[target] == REJECTED
            ]
            unconfirmed_targets = [
                target
                for target in normalized_targets
                if rule.host_acceptance[target] == UNCONFIRMED
            ]

            if rejected_targets and accepted_targets:
                errors.append(
                    f"[HC_TARGET_SET_UNRENDERABLE] Frontmatter field '{key}' cannot be "
                    f"shared by targets {_display_targets(normalized_targets)} because "
                    f"{_display_targets(rejected_targets)} rejects it. Use target-specific "
                    "artifacts."
                )
            elif rejected_targets:
                errors.append(
                    f"[HC_SCHEMA_REJECTS_FIELD] {_display_targets(rejected_targets)} "
                    f"rejects frontmatter field '{key}'."
                )

            if unconfirmed_targets:
                errors.append(
                    f"[HC_COVERAGE_UNCONFIRMED] Current compatibility data does not confirm "
                    f"frontmatter field '{key}' for {_display_targets(unconfirmed_targets)}."
                )

    return FrontmatterAnalysis(errors=errors, notes=notes)
