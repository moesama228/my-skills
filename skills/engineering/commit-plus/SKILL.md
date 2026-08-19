---
name: commit-plus
description: Commit Git changes safely and atomically. Use when the user asks to create a commit, stage a coherent change, or split changes into separate commits.
---

# Commit Plus

Make surgical commits: change only the selected index scope, preserve all other local work, and leave remotes untouched.

## Options and modes

- `--style=auto|simple|full`: Use `auto` by default. Force a subject-only message with `simple` or a body with optional footers with `full`, unless repository policy requires otherwise.
- `--type=feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert`: Override type inference.
- `--confirm`: Show the final scope, validation, and message, then wait for explicit confirmation before each `git commit`.
- `--no-verify`: Skip workflow checks and bypass pre-commit and commit-msg verification hooks. Report the bypass before a confirmed commit and after an autonomous commit.

Default to autonomous mode: select, stage, validate, and commit without confirmation. Pause only for unsafe or materially ambiguous state, a likely secret in scope, or failed validation that needs a user decision.

Reject unsupported option values. Preserve all noncandidate state. Limit mutations to the surgical index adjustment and resulting commit; treat any other worktree, history, or remote mutation as a separate request.

For likely credentials, private keys, `.env` files, dumps, and similar artifacts, inspect only paths and metadata until the user approves the exact file. Keep secret values out of all output.

## Steps

### 1. Inventory the repository

1. Resolve the root and inspect `git status --short --branch`.
2. Inventory staged, unstaged, and untracked changes; inspect candidate diffs deeply enough to account for every hunk.
3. Read applicable repository instructions, contribution guidance, commitlint configuration, and recent subjects.
4. Identify conflicts, merge/rebase state, submodules, and secret-bearing or generated artifacts. Pause when an ordinary commit is ambiguous or unsafe.

**Complete when:** repository state, policy, message convention, every current change, and every blocker are accounted for.

### 2. Plan atomic candidates

Use the staged diff as the starting candidate while preserving staged and unstaged boundaries. Assign every current change to an ordered candidate or explicitly exclude it.

Apply the one-subject test: every hunk in a candidate must support one imperative subject. Keep direct implementation, tests, and documentation together; split independent features, fixes, refactors, dependencies, and formatting churn. For multiple candidates, record their order and process them one at a time.

**Complete when:** every candidate has an exact path or hunk scope and one-line intent, and every current change is assigned or excluded.

### 3. Stage the candidate

Stage each candidate path as a separately quoted literal argument after `git add --`; use hunk staging for mixed files. Keep broad pathspecs and repository-wide staging outside the surgical scope.

When the index contains out-of-scope changes, record its original boundaries and adjust only the entries or hunks needed for the candidate, leaving worktree content intact. Carry deferred staged hunks forward; if the workflow stops before committing them, restore their staged status before reporting. Re-read `git diff --cached` after staging.

**Complete when:** the cached diff exactly matches the selected candidate and original index boundaries are recorded.

### 4. Validate the candidate

Without `--no-verify`:

1. Run `git diff --cached --check`.
2. Run every check required by repository policy for this candidate.
3. For each relevant category not already covered, run the narrowest documented test, lint, type-check, build, or documentation check; omit broader duplicates.
4. Report when no repository-defined check exists. Leave dependency installation and unrelated fixes for a separate request.

On failure, ask whether to fix it, revise the candidate, or proceed with the failure acknowledged. When a check changes tracked files, show the state and return to candidate planning before including them. With `--no-verify`, record workflow checks and verification hooks as skipped.

**Complete when:** every selected check is passed or explicitly waived, outcomes are recorded, and the cached diff remains unchanged.

### 5. Compose the message

Select the style first. Follow enforced repository policy, then an explicit `--style=simple|full`. For `auto`, read [references/style-selection.md](references/style-selection.md) completely and apply its subject-sufficiency test.

Choose syntax by precedence: enforced repository policy, then a clear recent-history convention, then the migrated default of emoji-prefixed Conventional Commits.

Use `[<emoji> ]<type>[optional scope]: <description>`. Include emoji when policy permits and history commonly uses them; omit them when strict parsing or history expects the type first. With no repository signal, include the default emoji.

Map types: `feat` ✨ · `fix` 🐛 · `docs` 📝 · `style` 🎨 · `refactor` ♻️ · `perf` ⚡️ · `test` ✅ · `chore` 🔧 · `ci` 👷 · `build` 📦 · `revert` ⏪.

Infer one type unless `--type` overrides it. Derive a brief noun scope from history or the component; omit an unclear scope. Write an imperative subject with no period, follow repository capitalization, target 50 characters, and stay within 72 unless policy differs.

When the selected style is `full`, read [references/full-style.md](references/full-style.md) completely before composing.

**Complete when:** the style follows the selection precedence, the exact message follows repository convention, and every claim is supported by every staged hunk.

### 6. Commit

Build the commit record from staged paths, the one-subject assessment, validation outcomes, exact message, and any `--no-verify` warning. With `--confirm`, show that record and wait; otherwise continue immediately. If the cached diff changes, rebuild the record and, with `--confirm`, wait again.

Commit without a shell editor. Preserve verification hooks unless `--no-verify` was explicit. On hook failure or generated changes, report state and pause without automatic retry, restaging, amendment, or bypass.

For multiple candidates, re-inventory after each successful commit and repeat all steps for the next one.

**Complete when:** `HEAD` contains the candidate represented by the final commit record. Pause rather than advance whenever the selected mode or a blocker requires input.

### 7. Report completion

Restore the original staged status of any deferred hunks, then report the hash and subject, committed files, validation outcomes, and remaining staged, unstaged, and untracked changes. Account for every planned candidate as committed or explicitly deferred.

**Complete when:** the reported hash resolves to the created commit, deferred index state is restored, and every planned candidate has a recorded outcome.
