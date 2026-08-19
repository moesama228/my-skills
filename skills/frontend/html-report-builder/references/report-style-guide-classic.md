# Blue-White Enterprise HTML Report Style

Use this reference when creating or revising a report with `$html-report-builder`.

## Visual System

- Background: cool light gray-blue `#eef1f6`.
- Panels: white `#ffffff`.
- Text: near-black `#16202c`.
- Muted text: gray-blue `#5a6573`.
- Lines: pale blue-gray `#dde3ec`.
- Accent: strong blue `#2f6feb`.
- Accent soft: pale blue `#e7f0ff`.
- Highlight: blue bold `.hl { color: rgb(61, 110, 226); font-weight: 700; }`.
- Shadows: soft and broad, e.g. `0 12px 34px rgba(24,34,52,.10)`.
- Radius: 8px for compact controls, 12px for small cards, 14-16px for report cards/media, 22px for hero bottom corners.
- Fonts: `"Segoe UI", "Microsoft YaHei", Arial, sans-serif`; monospace only for code and file paths.

## Page Architecture

- Use one constrained `.wrap` with `max-width:1120px`, centered, `22px` side padding.
- Hero is full-width at top with a blue gradient, white text, kicker, H1, one concise paragraph, and pill tags.
- Sticky nav follows the hero. Align nav content with `.wrap` left edge.
- Use structured nav when one section has subsections:
  - primary links as white rounded pills with blue number badges;
  - grouped subsections inside a pale-blue rounded container;
  - avoid large empty nav gaps.
- Main content uses sections with `margin-top:40px` and `scroll-margin-top` for sticky nav.
- Each section starts with `.sec-head`: numbered blue badge + H2.
- Add a `.lead` paragraph only when it frames the section; avoid repeating notices or table conclusions.

## Core Components

### Cards

- `.card` uses white background, 1px border, 16px radius, 26-28px padding, and soft shadow.
- Avoid cards inside cards unless the inner card is a repeated item, media frame, table wrapper, or detail block.
- Use `.card + .card { margin-top:22px; }`.

### KPI Blocks

- Use `.kpis` as responsive grid: `repeat(auto-fit,minmax(180px,1fr))`.
- `.kpi b` is the visual anchor: 22px, dark blue, heavy weight.
- `.kpi span` is a short label, 12px muted text.

### Tables

- Wrap tables in `.table-wrap` with border, radius, and horizontal overflow.
- Header row uses pale blue background and dark blue text.
- Zebra stripe even rows with `#f7f9fc`.
- Keep first comparison column bold and dark blue.

### Flow Strips

- Use flex wrap with small gap.
- Steps are pale blue rounded rectangles with dark blue bold labels.
- Arrows are blue, heavy weight.
- Use green final steps only when representing adoption, completion, or evolution.

### Media

- Use `.shot` for screenshots or generated report images: white frame, 1px border, 14px radius, shadow.
- Add `.cap` caption below every important image.
- Images should open in a lightbox when clicked.
- Use carousels only when comparing two or three screenshots that share one narrative.

### Evidence and Raw Material

- Use `.notice` for caveats or experimental limitations: warm yellow background, orange border/text.
- Use `details.report-raw` for raw reports, logs, or long source excerpts.
- Keep raw material collapsed by default.

## Content and Copy

- Prefer "总分" structure: thesis first, then sections, then evidence or roadmap.
- Headings should be direct and short.
- Use Chinese labels naturally; avoid unnecessary English except product names, commands, and metrics.
- Avoid "AI味" phrasing such as "替代人力" unless the user explicitly wants it.
- When the report discusses AI or Agent work, frame it as expert-led collaboration, engineering capability, repeatability, or evaluation discipline.
- Highlight only decisive phrases with `.hl`; never highlight whole paragraphs.

## Layout Patterns

- Two-column visual card:
  - `.vision-layout,.arena-layout { grid-template-columns:.9fr 1.1fr; gap:26px; align-items:center; }`
  - Left side: kicker, H3, short paragraph, point list.
  - Right side: framed image.
- Feature section:
  - Use `.features` vertical grid.
  - Use `.feat` two-column layout; `.feat.rev` reverses media/text.
  - Use `.feat.big-img` when media needs more width.
- Maturity/roadmap grids:
  - `repeat(auto-fit,minmax(220px,1fr))` with small rounded boxes.
  - Use dark blue bold titles and muted descriptions.

## Responsive Rules

- Desktop is the primary target for briefing materials.
- At `max-width:820px`, collapse two-column layouts to one column and stack nav groups.
- At `max-width:560px`, make subsection nav a two-column grid.
- Text must wrap inside buttons/cards; avoid fixed-width labels that overflow.

## Image Generation Style Prompt

For generated illustrations, use this content-independent style:

```text
Generate a 16:9 enterprise technology infographic for a formal report. Blue-white palette, white-to-light-blue background, subtle grid or node texture, deep blue title in the report language, restrained 3D isometric architecture style. Use rounded cards, thin blue outlines, soft shadows, platform bases, data cubes, process modules, node networks, icon cards, arrows, and feedback lines. Professional, clean, high information density but not crowded. Use concise labels in the report language; use Chinese labels when the report is Chinese. No garbled text, no logos, no watermarks, no dark cyberpunk, no cartoon style.
```
