from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_openai_yaml as openai_generator  # noqa: E402
import init_skill as initializer  # noqa: E402
import validate_skill as validator  # noqa: E402


def write_skill(directory: Path, name: str, frontmatter: str = "", body: str = "") -> Path:
    skill_dir = directory / name
    skill_dir.mkdir()
    extra = f"\n{frontmatter.strip()}" if frontmatter.strip() else ""
    instructions = body or "# Example\n\nPerform the requested example workflow.\n"
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\n"
        "description: Perform example workflows. Use when an example skill is requested."
        f"{extra}\n---\n\n{instructions}",
        encoding="utf-8",
    )
    return skill_dir


def write_explicit_only_policy(skill_dir: Path, value: str = "false") -> None:
    adapter = skill_dir / "agents" / "openai.yaml"
    adapter.parent.mkdir(exist_ok=True)
    adapter.write_text(
        f"policy:\n  allow_implicit_invocation: {value}\n",
        encoding="utf-8",
    )


class InitializerTests(unittest.TestCase):
    def test_default_scaffold_includes_openai_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = initializer.init_skill("Portable Skill", Path(tmp))

            self.assertEqual(skill_dir.name, "portable-skill")
            self.assertTrue((skill_dir / "SKILL.md").is_file())
            self.assertTrue((skill_dir / "agents" / "openai.yaml").is_file())
            self.assertEqual(sorted(path.name for path in skill_dir.iterdir()), ["SKILL.md", "agents"])

    def test_vendor_neutral_scaffold_can_omit_openai_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = initializer.init_skill(
                "Portable Skill",
                Path(tmp),
                include_openai=False,
            )

            self.assertFalse((skill_dir / "agents").exists())

    def test_selected_resources_and_openai_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = initializer.init_skill(
                "media-helper",
                Path(tmp),
                resources=["scripts", "assets"],
                interface_overrides=[
                    "brand_color=#336699",
                    "default_prompt=Use $media-helper to prepare media.",
                ],
            )

            self.assertTrue((skill_dir / "scripts").is_dir())
            self.assertTrue((skill_dir / "assets").is_dir())
            self.assertFalse((skill_dir / "references").exists())
            adapter = (skill_dir / "agents" / "openai.yaml").read_text(encoding="utf-8")
            self.assertIn('brand_color: "#336699"', adapter)
            self.assertIn("$media-helper", adapter)

    def test_explicit_only_scaffold_pairs_invocation_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = initializer.init_skill(
                "manual-helper",
                Path(tmp),
                explicit_only=True,
            )

            skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            adapter = (skill_dir / "agents" / "openai.yaml").read_text(encoding="utf-8")
            self.assertIn("disable-model-invocation: true", skill_md)
            self.assertIn("allow_implicit_invocation: false", adapter)
            self.assertIn("Summarize this skill for users", skill_md)

    def test_explicit_only_rejects_openai_opt_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)

            with self.assertRaises(ValueError):
                initializer.init_skill(
                    "manual-helper",
                    output,
                    include_openai=False,
                    explicit_only=True,
                )

            self.assertEqual(list(output.iterdir()), [])

    def test_invalid_name_and_long_name_fail(self) -> None:
        with self.assertRaises(ValueError):
            initializer.validate_requested_name("---")
        with self.assertRaises(ValueError):
            initializer.validate_requested_name("a" * 65)

    def test_existing_directory_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "existing"
            target.mkdir()
            marker = target / "keep.txt"
            marker.write_text("keep", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                initializer.init_skill("existing", Path(tmp))

            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_invalid_interface_leaves_no_partial_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            for override in ("unknown=value", "brand_color=blue"):
                with self.subTest(override=override):
                    with self.assertRaises(ValueError):
                        initializer.init_skill(
                            "adapter-test",
                            output,
                            include_openai=True,
                            interface_overrides=[override],
                        )
                    self.assertEqual(list(output.iterdir()), [])


class OpenAIGeneratorTests(unittest.TestCase):
    def test_generator_refuses_to_overwrite_existing_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(Path(tmp), "portable-skill")
            output = openai_generator.write_openai_yaml(skill_dir, "portable-skill", [])
            original = output.read_text(encoding="utf-8")

            with self.assertRaises(FileExistsError):
                openai_generator.write_openai_yaml(skill_dir, "portable-skill", [])

            self.assertEqual(output.read_text(encoding="utf-8"), original)

    def test_generator_can_add_explicit_only_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(Path(tmp), "manual-skill")

            output = openai_generator.write_openai_yaml(
                skill_dir,
                "manual-skill",
                [],
                explicit_only=True,
            )

            self.assertIn(
                "policy:\n  allow_implicit_invocation: false",
                output.read_text(encoding="utf-8"),
            )

    def test_generator_validates_product_fields(self) -> None:
        with self.assertRaises(ValueError):
            openai_generator.validate_interface("demo", {"brand_color": "blue"})
        with self.assertRaises(ValueError):
            openai_generator.validate_interface(
                "demo",
                {"default_prompt": "Create a demonstration."},
            )
        with self.assertRaises(ValueError):
            openai_generator.validate_interface("demo", {"icon_small": "/tmp/icon.svg"})


class ValidatorTests(unittest.TestCase):
    def test_valid_skill_passes_all_frontmatter_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(
                Path(tmp),
                "valid-skill",
                frontmatter=(
                    "license: Apache-2.0\n"
                    "compatibility: Requires Python 3.9+.\n"
                    "metadata:\n"
                    '  author: "example"\n'
                    '  version: "1.0"\n'
                    'allowed-tools: "Bash(git:*) Read"'
                ),
            )

            errors, warnings = validator.validate_skill(skill_dir)

            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_invalid_frontmatter_variants_fail(self) -> None:
        cases = {
            "unknown-field": "custom: value",
            "bad-metadata": "metadata:\n  version: 1",
            "long-compatibility": f'compatibility: "{"x" * 501}"',
            "bad-allowed-tools": "allowed-tools:\n  - Read",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, extra in cases.items():
                with self.subTest(name=name):
                    skill_dir = write_skill(root, name, frontmatter=extra)
                    errors, _ = validator.validate_skill(skill_dir)
                    self.assertTrue(errors)

    def test_extension_is_valid_without_a_target_when_policy_is_paired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(
                Path(tmp),
                "manual-skill",
                frontmatter="disable-model-invocation: true",
            )
            write_explicit_only_policy(skill_dir)

            report = validator.analyze_skill(skill_dir)
            errors, warnings = validator.validate_skill(skill_dir)

            self.assertEqual(report.errors, [])
            self.assertEqual(report.notes, [])
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_standalone_targets_accept_disable_model_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(
                Path(tmp),
                "manual-skill",
                frontmatter="disable-model-invocation: true",
            )
            write_explicit_only_policy(skill_dir)

            for target in ("claude", "codex", "kimi", "grok", "cursor", "pi"):
                with self.subTest(target=target):
                    report = validator.analyze_skill(skill_dir, targets=[target])
                    self.assertEqual(report.errors, [])
                    self.assertEqual(report.quality_warnings, [])

    def test_disable_model_invocation_requires_a_yaml_boolean(self) -> None:
        cases = {
            "quoted-boolean": 'disable-model-invocation: "true"',
            "integer-boolean": "disable-model-invocation: 1",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, frontmatter in cases.items():
                with self.subTest(name=name):
                    skill_dir = write_skill(root, name, frontmatter=frontmatter)
                    report = validator.analyze_skill(skill_dir, targets=["claude"])
                    self.assertTrue(any("YAML boolean" in error for error in report.errors))

    def test_explicit_only_extension_requires_policy_pairing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(
                Path(tmp),
                "manual-skill",
                frontmatter="disable-model-invocation: true",
            )

            missing_report = validator.analyze_skill(skill_dir)
            write_explicit_only_policy(skill_dir, value="true")
            invalid_report = validator.analyze_skill(skill_dir)
            write_explicit_only_policy(skill_dir)
            valid_report = validator.analyze_skill(skill_dir)

            self.assertTrue(
                any("INVOCATION_PAIR_MISSING" in error for error in missing_report.errors)
            )
            self.assertTrue(
                any("INVOCATION_PAIR_INVALID" in error for error in invalid_report.errors)
            )
            self.assertEqual(valid_report.errors, [])

    def test_false_extension_does_not_require_policy_pairing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(
                Path(tmp),
                "model-invoked-skill",
                frontmatter="disable-model-invocation: false",
            )

            report = validator.analyze_skill(skill_dir, targets=["codex"])

            self.assertEqual(report.errors, [])

    def test_codex_and_native_target_share_extension_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(
                Path(tmp),
                "multi-target-skill",
                frontmatter="disable-model-invocation: true",
            )
            write_explicit_only_policy(skill_dir)

            report = validator.analyze_skill(
                skill_dir,
                targets=["claude", "codex"],
            )

            self.assertEqual(report.errors, [])

    def test_target_checks_standard_field_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(
                Path(tmp),
                "codex-compatibility",
                frontmatter="compatibility: Requires Python 3.9+.",
            )

            report = validator.analyze_skill(skill_dir, targets=["codex"])

            self.assertTrue(any("compatibility" in error for error in report.errors))
            self.assertTrue(any("Codex" in error for error in report.errors))

    def test_runtime_notice_does_not_fail_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(
                Path(tmp),
                "codex-tools",
                frontmatter='allowed-tools: "Read"',
            )

            report = validator.analyze_skill(skill_dir, targets=["codex"])

            self.assertEqual(report.errors, [])
            self.assertEqual(report.quality_warnings, [])
            self.assertTrue(any("authorization" in note for note in report.notes))
            self.assertFalse(report.should_fail(strict=True))

            output = io.StringIO()
            with patch.object(
                sys,
                "argv",
                [
                    "validate_skill.py",
                    str(skill_dir),
                    "--target",
                    "codex",
                    "--strict",
                ],
            ):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(validator.main(), 0)
            self.assertIn("NOTICE:", output.getvalue())
            self.assertIn("other adapter fields were not", output.getvalue())

    def test_empty_required_fields_and_directory_mismatch_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty_dir = root / "empty"
            empty_dir.mkdir()
            (empty_dir / "SKILL.md").write_text(
                "---\nname: \"\"\ndescription: \"\"\n---\n\nBody.\n",
                encoding="utf-8",
            )
            mismatch_dir = write_skill(root, "folder-name")
            mismatch_content = (mismatch_dir / "SKILL.md").read_text(encoding="utf-8")
            (mismatch_dir / "SKILL.md").write_text(
                mismatch_content.replace("name: folder-name", "name: other-name"),
                encoding="utf-8",
            )

            empty_errors, _ = validator.validate_skill(empty_dir)
            mismatch_errors, _ = validator.validate_skill(mismatch_dir)

            self.assertGreaterEqual(len(empty_errors), 2)
            self.assertTrue(any("must match" in error for error in mismatch_errors))

    def test_description_angle_brackets_are_portable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(Path(tmp), "angle-brackets")
            skill_md = skill_dir / "SKILL.md"
            content = skill_md.read_text(encoding="utf-8")
            skill_md.write_text(
                content.replace(
                    "Perform example workflows.",
                    "Process <input> values.",
                ),
                encoding="utf-8",
            )

            errors, warnings = validator.validate_skill(skill_dir)

            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])

    def test_quality_warnings_and_strict_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = (
                "# Warning Example\n\n"
                "[TODO: Complete this workflow.]\n\n"
                "[Missing](references/missing.md)\n"
                + "\n".join(f"line {number}" for number in range(510))
                + "\n"
            )
            skill_dir = write_skill(root, "warning-skill", body=body)

            errors, warnings = validator.validate_skill(skill_dir)

            self.assertEqual(errors, [])
            self.assertTrue(any("unfinished" in warning for warning in warnings))
            self.assertTrue(any("500" in warning for warning in warnings))
            self.assertTrue(any("does not exist" in warning for warning in warnings))

            output = io.StringIO()
            with patch.object(sys, "argv", ["validate_skill.py", str(skill_dir)]):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(validator.main(), 0)
            with patch.object(
                sys,
                "argv",
                ["validate_skill.py", str(skill_dir), "--strict"],
            ):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(validator.main(), 1)

    def test_scaffold_marker_inside_code_fence_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(
                Path(tmp),
                "code-example",
                body="# Example\n\n```markdown\n[TODO: example only]\n```\n",
            )

            errors, warnings = validator.validate_skill(skill_dir)

            self.assertEqual(errors, [])
            self.assertFalse(any("unfinished" in warning for warning in warnings))

    def test_frontmatter_scaffold_marker_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = write_skill(Path(tmp), "frontmatter-marker")
            skill_md = skill_dir / "SKILL.md"
            content = skill_md.read_text(encoding="utf-8")
            skill_md.write_text(
                content.replace(
                    "description: Perform example workflows. Use when an example skill is requested.",
                    'description: "[TODO: Describe this skill.]"',
                ),
                encoding="utf-8",
            )

            errors, warnings = validator.validate_skill(skill_dir)

            self.assertEqual(errors, [])
            self.assertTrue(any("Frontmatter description" in warning for warning in warnings))

    def test_end_to_end_scaffold_edit_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = initializer.init_skill(
                "End to End",
                Path(tmp),
                resources=["references"],
            )
            (skill_dir / "references" / "guide.md").write_text("# Guide\n", encoding="utf-8")
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: end-to-end\n"
                "description: Complete end-to-end checks. Use when validating the full skill workflow.\n"
                "---\n\n"
                "# End to End\n\n"
                "Read [the guide](references/guide.md), then complete the requested check.\n",
                encoding="utf-8",
            )

            errors, warnings = validator.validate_skill(skill_dir)

            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
