# Target-Specific Frontmatter

Read this reference when a user names one or more client targets, requests non-standard frontmatter, or an existing skill already contains a shared extension. The compatibility snapshot reflected by the bundled validator was last reviewed on 2026-08-24.

## Separate the three questions

Treat these as independent:

1. **Specification status:** whether Agent Skills defines the field.
2. **Target acceptance:** whether the selected client accepts that exact key in `SKILL.md`.
3. **Runtime semantics:** whether the client gives the field the intended effect.

A standard field can still be rejected by a client. A non-standard field can be widely implemented. Target acceptance alone does not prove that a client uses the field to enforce the intended behavior.

Run the validator once for every intended target rather than inferring compatibility from specification status:

```bash
python scripts/validate_skill.py <skill-directory> --target claude --target kimi
```

The supported target identifiers are `claude`, `codex`, `kimi`, `grok`, `cursor`, and `pi`.

`--target` adds target acceptance checks for `SKILL.md` frontmatter. Base validation also enforces the explicit-only frontmatter/OpenAI-policy pair, but it does not validate other adapter fields. Inspect those fields through their own reference and client tooling.

## Recognized extension

V1 recognizes one non-standard frontmatter extension:

```yaml
disable-model-invocation: true
```

- Use a YAML boolean, not the string `"true"` or the integer `1`.
- Add the field whenever the user requests user-only, manual, or explicit invocation; do not require a named target.
- When `true`, write `description` as a concise human-facing summary rather than a model-routing trigger list.
- Omit the field for a model-invoked skill instead of writing `false`.

Codex standalone skill loading accepts this extension, but Codex invocation behavior is controlled by its product adapter. Apply both configurations for every explicit-only skill:

```yaml
# SKILL.md frontmatter
disable-model-invocation: true

# agents/openai.yaml
policy:
  allow_implicit_invocation: false
```

The frontmatter field serves clients that implement it. The OpenAI policy prevents Codex from injecting the skill into model context while keeping explicit `$skill-name` invocation available. Pairing them avoids a target-selection question and gives the generated skill the broadest practical behavior.

Codex plugin packaging is a separate compatibility branch: its current plugin validator rejects `disable-model-invocation: true`. When a user requests a `.codex-plugin`, validate that package independently and report the conflict instead of claiming that the standalone-skill result applies to plugin ingestion.

## Deferred fields

These observed multi-client fields remain outside V1's executable schema:

| Field family | Reason to defer | Portable alternative |
|---|---|---|
| `when_to_use` / `when-to-use` / `whenToUse` | No spelling works across all implementing clients | Put activation conditions in `description` |
| `argument-hint` / `arguments` | UI hint and argument contract are not one stable semantic | Document required inputs in the instructions |
| `user-invocable` | Limited coverage and interacts with invocation policy | Express the intended invocation mode per selected target |
| `model` / `effort` | Client-specific runtime policy and value vocabularies | Preserve the caller's model and effort settings |
| `paths` | Limited coverage and client-specific discovery behavior | State the path branch in the skill instructions |

Preserve an existing unknown vendor extension during unrelated edits, but do not silently certify it. The validator continues to reject fields outside its recognized schema.

## Experimental standard field

`allowed-tools` belongs to the Agent Skills specification but remains experimental. The validator checks its shape and may report target runtime notes. Treat it as declarative guidance only: it is not a portable permission boundary and does not authorize tool use.
