---
name: skill-creator-portable
description: Create, update, and review Agent Skills against the Agent Skills specification and selected client targets. Use when designing or scaffolding a skill, improving an existing SKILL.md, choosing its invocation mode, validating a skill folder, checking target-specific frontmatter, or maintaining its OpenAI adapter.
license: Apache-2.0
compatibility: Portable across Agent Skills-compatible agents. Bundled helper scripts require Python 3.9+ and PyYAML 6.x.
---

# Skill Creator Portable

Create skills that supply useful, non-obvious guidance while preserving the user's product choices, scope, and authority.

## Principles

**Assume the agent is capable.** Include information that changes decisions or improves execution. Remove generic advice, repeated rules, speculative edge cases, and examples that do not clarify a real branch.

**Preserve intent and authority.** A skill supports the requested task. It does not expand the assignment, replace a chosen product, modify unrelated configuration, or imply permission for external actions. Define stopping conditions for retries and mutations in proportion to risk.

**Match specificity to risk.** Describe outcomes and decision criteria for open-ended work. Use fixed sequences, deterministic scripts, and absolute language only for safety, correctness, permissions, or fragile operations.

**Keep discovery precise.** For a model-invoked skill, the frontmatter description is a routing pointer: state what the skill does and the distinct situations that should activate it. For an explicit-only skill, make it a concise human-facing summary. Avoid catchalls and redundant trigger synonyms.

**Disclose progressively.** Keep shared workflow and constraints in `SKILL.md`. Put branch-specific procedures in `references/`, repeatable mechanics in `scripts/`, and output resources in `assets/`. Link each supporting file from the place where its branch becomes relevant.

## Workflow

### 1. Ground the request

Determine whether the user wants to create, update, or review a skill. Establish the intended tasks, users, compatible agent clients, output location, constraints, and observable success criteria.

Treat a request for user-only, manual, or explicit invocation as a complete cross-client invocation choice. Apply the paired configuration in the Invocation Mode section without asking the user to name Codex or another target.

Respect a supplied destination. Otherwise, use an existing `skills/` directory in the current project. If neither provides a clear location, ask rather than inventing a vendor-specific install path.

Write generated instructions in the language of the current conversation unless the user requests another language. Keep specification field names, filenames, commands, and code identifiers unchanged.

Completion criterion: the target behavior, destination, and compatibility requirements are known well enough that implementation requires no product guesswork.

### 2. Design the smallest useful skill

Choose a short, action-oriented name and a discriminating description. Identify realistic requests the skill should handle and nearby requests it should not attract.

Add optional resources only when they have a concrete job:

- `scripts/` for repeated deterministic operations.
- `references/` for substantial information needed only on particular branches.
- `assets/` for templates, images, data, or boilerplate copied into outputs.

Keep concepts co-located and each rule in one authoritative place. A short self-contained skill needs no router, placeholders, or empty ancillary documentation.

Completion criterion: every proposed file either affects agent decisions or directly supports generated output.

### 3. Create or update

For a new skill, the bundled initializer can create a portable scaffold:

```bash
python scripts/init_skill.py <skill-name> --path <output-directory> [--resources scripts,references,assets] [--explicit-only] [--no-openai]
```

The portable instructions remain in `SKILL.md`, while the initializer generates `agents/openai.yaml` by default. Pass `--no-openai` only when the user explicitly requests a vendor-neutral artifact. An explicit-only skill always keeps the default adapter, so `--explicit-only` and `--no-openai` are incompatible.

Customize default OpenAI interface metadata when requested:

```bash
python scripts/init_skill.py <skill-name> --path <output-directory> [--interface key=value]
```

For an existing skill, read its complete `SKILL.md` and inspect the purpose and callers of any resource before changing or removing it. Make the narrowest coherent edit. Preserve unknown vendor extensions, metadata, policies, dependencies, and unrelated user configuration.

Completion criterion: the skill implements the requested behavior without unrelated files or overwritten extensions.

### 4. Write the instructions

Write the desired outcome, non-obvious context, real constraints, and completion criteria another agent needs. Prefer positive target behavior over long prohibition lists. Keep detailed examples only when they distinguish otherwise ambiguous cases.

The body should stay comfortably below the specification's recommendations of 500 lines and roughly 5,000 tokens. These are context-efficiency recommendations, not conformance errors.

## Agent Skills Conformance

A skill directory must contain `SKILL.md` with YAML frontmatter followed by Markdown instructions. The directory name and frontmatter `name` must match.

Frontmatter fields:

- `name` is required, 1-64 characters, and uses lowercase ASCII letters, digits, and single hyphens. It cannot start or end with a hyphen.
- `description` is required, non-empty, and at most 1,024 characters. Include activation conditions for model-invoked skills; use a concise human-facing summary for explicit-only skills.
- `license` is optional and contains a license name or a bundled license-file reference.
- `compatibility` is optional, non-empty when present, at most 500 characters, and describes genuine environment requirements.
- `metadata` is optional and maps string keys to string values.
- `allowed-tools` is an optional, experimental, space-separated string. Client support varies, so do not rely on it for portable authorization.

Additional files and directories are allowed. Use paths relative to the skill root when linking files. Prefer references one level deep from `SKILL.md`; this is a portability recommendation rather than a hard format requirement.

## Invocation Mode

Keep automatic model invocation enabled by default. When the user declares the skill user-only, manual, or explicit-only, silently apply both settings:

- Add `disable-model-invocation: true` to `SKILL.md` frontmatter.
- Set `agents/openai.yaml` `policy.allow_implicit_invocation` to `false`.

Use YAML booleans and write the description as a concise human-facing summary. Do this regardless of whether the user names client targets. For target acceptance, other frontmatter extensions, or Codex plugin packaging, read [references/frontmatter_extensions.md](references/frontmatter_extensions.md).

## Vendor Adapters

Keep product-specific configuration outside the portable core. The initializer creates the OpenAI adapter automatically; read [references/openai_yaml.md](references/openai_yaml.md) when editing its interface, invocation policy, dependencies, or existing fields. Do not load that reference when `--no-openai` was explicitly selected.

## Validate

Run the bundled validator after edits:

```bash
python scripts/validate_skill.py <skill-directory>
python scripts/validate_skill.py <skill-directory> --strict
python scripts/validate_skill.py <skill-directory> --target claude --target kimi
```

Without a target, validation checks the specification, recognized extensions, and the explicit-only configuration pair. Repeat `--target` to add standalone `SKILL.md` frontmatter acceptance checks for multiple clients. Other product-adapter fields and plugin-package ingestion remain separate validation branches. Errors always fail; quality warnings such as unfinished scaffold markers, a body over 500 lines, or broken local Markdown links fail only in strict mode. Compatibility notices never change the exit status.

Run every new or changed helper script on representative success and failure cases. If the official `skills-ref` tool is already available, use it as an additional conformance check; do not make it a runtime dependency.

Structural validation does not prove that instructions produce good behavior.

### Independent forward-testing

For a new or substantially revised skill whose behavior is complex or high-risk, run an independent subagent on a realistic user request. Give the evaluator the completed skill and only the raw inputs needed for the task. Withhold the intended answer, suspected defect, proposed fix, and authoring conclusions unless the evaluation genuinely requires them.

Use an isolated workspace and keep permissions, side effects, time, and cost within the available authority. Review the actual output and artifacts against the skill's success criteria, then make only narrow revisions supported by observed failures. Ordinary creation and small edits do not require this pass.

Completion criterion: the skill passes structural validation, its scripts pass meaningful tests, all references resolve, and the resulting behavior matches the user's success criteria.

## Avoid Unnecessary Files

Do not add a README, changelog, installation guide, duplicated quick reference, example asset, or placeholder directory unless the requested workflow or packaging format gives it a concrete purpose.
