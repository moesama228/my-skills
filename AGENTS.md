# Repository guidance

`AGENTS.md` is the single source of repository guidance. `CLAUDE.md` imports it with `@AGENTS.md`; keep repository rules here instead of duplicating them.

This repository is a personal monorepo of independently installable Agent Skills.

## Skill categories

Skills are organized into category folders under `skills/`:

- `engineering/` — software design, implementation, testing, debugging, code review, and delivery workflows
- `frontend/` — web interfaces, interaction, responsive layout, accessibility, and browser workflows
- `playground/` — lightweight, playful, or exploratory skills that do not yet form a stable domain
- `productivity/` — reusable cross-project productivity and meta-workflows

## Playground graduation

`playground/` is an incubation category, not a general fallback. Place a skill there only when no existing category fits and its lightweight, playful, or exploratory character is material to its purpose.

On every addition or material change to a Playground skill, review the whole category for a graduation cluster. A cluster graduates as soon as all of these conditions hold:

1. It contains at least three skills.
2. The skills share the same primary user outcome or workflow, rather than only a tone, implementation technique, or novelty.
3. The cluster admits a specific one-line category description that includes every member without catch-all wording.

When a cluster qualifies, graduate it in the same change: create the new category, move every skill in the cluster, add its category README, and update the top-level and affected category indexes. Do not add another skill to a qualifying cluster while leaving that cluster in Playground.

## Skill conventions

### Catalog and layout

Every skill must have an entry in the top-level `README.md` and in its category's `README.md`. Each entry names the skill, links directly to its `SKILL.md`, and gives a one-line description. When adding, renaming, removing, or materially changing a skill, update both indexes so their names, links, and descriptions remain accurate. The top-level `README.md` is also the canonical installation guide.

Each installable skill lives at `skills/<category>/<skill-name>/` and has `SKILL.md` as its entry point. The directory name and frontmatter `name` must match. Category README files are navigation only and are not skills.

### Resources and portability

Keep the portable behavior in `SKILL.md`. A skill may also carry resources that serve a concrete branch:

- `references/` — substantial branch-specific guidance
- `scripts/` — repeatable deterministic helpers
- `assets/` — templates or resources used in output
- `tests/` — tests for bundled helpers
- `agents/openai.yaml` — optional OpenAI interface, invocation-policy, and dependency metadata

Use paths relative to the skill root when linking resources. Keep each rule in one authoritative place and load branch-specific references from the point where that branch is reached. A short self-contained skill needs no placeholder directories, duplicated quick reference, or per-skill README.

Preserve existing metadata, policies, dependencies, licenses, and vendor extensions unless the requested behavior requires changing them.

### Validation

Before finishing a skill change, validate its frontmatter, the directory/name match, and every local Markdown link. Run tests supplied by the skill, and exercise every new or changed helper script on representative success and failure cases. Use the active coding agent's available skill-authoring and validation capabilities; no skill in this repository is the mandatory toolchain for the others.
