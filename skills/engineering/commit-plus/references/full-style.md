# Full-style commit messages

Read this reference when the main workflow selects `full`. Use its chosen subject syntax.

## Format

```text
[<emoji> ]<type>[optional scope]: <description>

<body>

<footer>
```

## Body

- Explain what changed and why; leave implementation narration to the diff.
- State the motivation or previous behavior when it helps review.
- Use bullets for multiple related effects.
- Wrap prose at 72 characters unless repository policy differs.

## Footer

Include only footers supported by the staged diff or user-provided context:

- `BREAKING CHANGE: <description>` for an actual breaking change.
- `Closes:`, `Fixes:`, or `Refs:` with known issue identifiers.
- `Co-authored-by:`, `Reviewed-by:`, or `Approved-by:` with verified attribution.

Separate the subject, body, and footer with blank lines. Keep every body and footer claim grounded in the staged change or explicit user context.
