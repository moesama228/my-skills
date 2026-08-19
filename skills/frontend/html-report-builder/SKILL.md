---
name: html-report-builder
description: Create polished static HTML report pages. Use whenever the user wants to turn source material, outlines, screenshots, metrics, research notes, or project summaries into a shareable HTML report. The skill supports two visual directions — Classic Enterprise (restrained blue-white briefing) and Modern SaaS (premium dark-hero + slate bento) — with bundled templates, style guides, and a standalone packaging script.
---

# HTML Report Builder

Build static HTML report pages that feel like a professional briefing. Choose between two bundled visual systems:

- **Classic Enterprise** — restrained blue-white enterprise style with gradient hero, sticky structured nav, white report cards, KPI blocks, tables, flow strips, and screenshot galleries.
- **Modern SaaS** — premium dark-hero opening, slate-50 body, Bento Box stitching, timelines, accordion comparison tables, role identity cards, and a strong closing CTA.

Each direction has its own template and style guide:

| Style | Template | Style Guide |
|-------|----------|-------------|
| Classic Enterprise | `assets/report-template-classic.html` | `references/report-style-guide-classic.md` |
| Modern SaaS | `assets/report-template-saas.html` | `references/report-style-guide-saas.md` |

## Required Pairing

Before designing or implementing a report, check the current session's available skills and use at least one frontend design skill when possible:

1. Prefer OpenAI `frontend-skill`. If it is available, read and follow it before using this skill.
2. If `frontend-skill` is unavailable but Anthropic `frontend-design` is available, read and follow `frontend-design`.
3. If neither skill is available, tell the user: "I did not detect `frontend-skill` or `frontend-design`. Installing one of them is recommended for higher visual quality." Ask whether they want to install one or continue without it.
4. Continue without a frontend design skill only after the user explicitly says they do not need it, do not want to install it, or wants to proceed anyway. In that fallback path, apply the built-in guardrails below.

## Workflow

### 1. Choose the visual style

Read this table and pick the direction before writing any HTML:

- **Classic Enterprise** when the audience expects a familiar corporate briefing, the material is heavy on tables/KPIs, or the user explicitly asks for the blue-white style.
- **Modern SaaS** when the audience is a product/engineering team, the story is about a new system/capability, or the user explicitly asks for the premium SaaS style.
- If the user already has an existing report file, continue in that file's existing style.

After choosing, load the matching template as the starting point and read the matching style guide for details on color, spacing, components, and copy tone.

### 2. Extract the report structure

- Identify the audience, central thesis, 2-4 major sections, supporting metrics, process diagrams, screenshots, caveats, and final takeaway.
- Prefer a "总分" narrative: start with the thesis, then expand by phases, capabilities, evidence, or roadmap.
- Remove repetition between lead text, cards, notices, and tables.
- For executive reports, keep wording professional but plain: retain necessary domain terms, and make every sentence explain a business meaning, action, or decision value.
- Avoid buzzword stacking and empty slogans; prefer concrete frames such as "input, action, output, value" or "who uses it, what problem it solves, how it is verified."

### 3. Choose reusable components

**Classic Enterprise:**
- Use `hero` for title, subtitle, and 3-6 pill tags.
- Use sticky nav for the primary structure; use grouped nav when one major section contains multiple subsections.
- Use `.sec-head` with numbered badges for sections.
- Use `.card` for major content blocks, `.kpis` for metrics, `.flow` / `.arena-flow` for process chains, `.table-wrap` for dense comparisons, `.shot` for images, and `details.report-raw` only for source material or raw reports.
- Use `.hl` for blue bold emphasis; avoid over-highlighting.

**Modern SaaS:**
- Optional global banner + scroll-aware nav (dark over hero, light over body) with grouped dropdowns.
- Dark hero with tag, large H1, subtitle, and two CTAs.
- Use `section-reveal` sections with numbered badges, H2 headlines, and short lead paragraphs.
- Use Bento components: pain-point bar, three-pillar panel, metrics grid, Mac-window video, image carousel, role identity cards, accordion comparison table, before/after split, timeline workflow, demo video block, data panel, and roadmap timeline.
- End with a single high-contrast CTA button or action block.

### 4. Apply the style system

- Load the correct `references/report-style-guide-*.md` when implementing or revising the visual format.
- Use the matching `assets/report-template-*.html` as the starting point for new reports when no existing report file is provided.
- Keep the output static and dependency-free unless the user explicitly asks for a framework.
- Store images in an `assets/` directory and reference them with relative paths by default.
- Keep paragraph-style explanatory text aligned with its content container by default. Do not give `.lead`, card descriptions, or section descriptions a narrower `max-width` than their parent unless controlling reading length is intentional.

### 5. Verify the report

- **Static checks first**: look for broken image references, text overflow, awkward nav wrapping, and duplicated copy.
- **Browser verification** (choose the method that fits the environment):
  - **Inside Codex**: start `python3 -m http.server <port> --bind 127.0.0.1` and verify in the Codex in-app browser. Use cache-busting query strings during review, e.g. `http://127.0.0.1:<port>/report.html?v=<change-id>#section`.
  - **Outside Codex or no in-app browser**: prefer using the `$ego-browser` skill to automate browser verification. Start the local server, open the report, and check image loading, anchor navigation, page scrolling, horizontal overflow, unnatural text wrapping, and interactive components. If `$ego-browser` is unavailable, fall back to the `$playwright-cli` skill for automated browser testing. As a last resort, start the local server and verify manually in any available browser.
- **What to check regardless of method**: image loading, anchor navigation, page scrolling, horizontal overflow, unnatural text wrapping, and interactive components.

## Optional Standalone HTML

When the user wants a single shareable file, run:

```bash
python3 <html-report-builder-skill-dir>/scripts/make_standalone_html.py <report.html> [-o <output.html>]
```

The script lives in this skill's `scripts/` directory; its installed path depends on the user's environment. By default, it writes `<input_stem>_standalone.html`, embedding local image references as Base64 data URIs. Use the maintainable HTML + `assets/` version as the source of truth, and regenerate the standalone file after edits.

## Guardrails

### Universal

- Do not copy business content, screenshots, titles, or domain-specific labels from any example or source report unless the user explicitly asks to reuse that material.
- Do not create a marketing landing page; create the actual report as the first screen.
- Keep all text readable on desktop and mobile; prefer wrapping and smaller headings inside compact panels.
- Keep cards purposeful: individual repeated items, framed media, tables, details, or discrete evidence blocks.

### Classic Enterprise

- Do not use one-note purple/blue gradients, dark dashboards, decorative orbs, nested cards, or card mosaics.
- Keep tables in `.table-wrap` with pale-blue headers and zebra-striped rows.
- Use `.hl` sparingly for decisive phrases only.

### Modern SaaS

- **No full-width ruled tables**: replace dense comparisons with accordion rows, `divide-x divide-y` data panels, or timelines.
- **One idea per card**: if a card carries two claims, split it.
- **Use verbs and numbers**, not adjectives and buzzwords: `60 分钟`, `0 代码`, `自动归档` rather than "赋能" or "抓手".
- **End with a CTA**: the final section must include a clear button or next-step action.
- **Grid consistency**: keep the 64px fixed grid across hero and body; opacity `0.03` in hero, `0.2` in body sections.
- **Ambient glow only in the hero**: do not add colored blurs to body sections.
- **Progressive disclosure**: headline states the judgment, paragraph explains why, card/table gives evidence, CTA names the next step.
