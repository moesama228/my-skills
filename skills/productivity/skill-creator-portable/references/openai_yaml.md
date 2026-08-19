# OpenAI Skill Metadata

Read this reference only when the user explicitly requests OpenAI-compatible metadata for a skill.

`agents/openai.yaml` is a product adapter read by the OpenAI skill harness rather than part of the portable Agent Skills core. Keep portable instructions in `SKILL.md`; keep display, invocation-policy, and OpenAI tool-dependency settings here.

## Interface fields

```yaml
interface:
  display_name: "User-facing skill name"
  short_description: "A 25-64 character UI description"
  icon_small: "./assets/small-icon.svg"
  icon_large: "./assets/large-icon.png"
  brand_color: "#3B82F6"
  default_prompt: "Use $skill-name to complete a representative task."
```

- Quote string values and keep keys unquoted.
- Include only fields with a concrete UI use.
- Store icons under the skill's `assets/` directory and use relative paths.
- Use a six-digit hexadecimal `brand_color`.
- A `default_prompt` should be a short representative request and explicitly mention `$skill-name`.

## Policy and dependencies

```yaml
policy:
  allow_implicit_invocation: false

dependencies:
  tools:
    - type: "mcp"
      value: "github"
      description: "GitHub MCP server"
      transport: "streamable_http"
      url: "https://example.com/mcp"
```

Add policy or dependency fields only when the user requests them or an existing adapter already relies on them. Invocation policy changes discovery behavior and is not a substitute for obtaining authorization before a mutation.

The bundled generator creates only the `interface` block and refuses to overwrite an existing file. Edit an existing adapter in place so unrelated `policy`, `dependencies`, and extension fields survive.
