# Modern SaaS HTML Report Style

Use this reference when creating or revising a report with the **Modern SaaS** visual direction in `$html-report-builder`.

The design goal is **business-like, refined, modern, and premium**: the page should read like a top-tier B2B SaaS product briefing rather than a corporate PowerPoint. Copy is direct, specific, and outcome-oriented; visual decoration is restrained and functional.

## Visual System

### Color Palette

- **Hero background**: deep navy `#0A0E17` (near-black blue).
- **Primary accent**: blue gradient `from-blue-400 via-blue-500 to-indigo-500` for hero highlights, section emphasis, and CTAs.
- **Body background**: `slate-50` (`#f8fafc`) — never pure white; use `slate-100` (`#f1f5f9`) for subtle panel backgrounds.
- **Card background**: white `#ffffff` with `slate-200` borders (`#e2e8f0`).
- **Text hierarchy**:
  - Primary headings: `slate-900`
  - Body / secondary text: `slate-600`
  - Captions / meta: `slate-500`
- **Muted dark panels**: `slate-200/40` or `slate-800` for pain-point / contrast blocks.
- **Status colors**: prefer blue/indigo for emphasis; avoid red/green unless the data genuinely needs semantic coloring.

### Typography

- **Font stack**: `"Inter", "PingFang SC", "Microsoft YaHei", sans-serif`.
- **Hero H1**: `5xl`–`7xl`, `font-black`, `tracking-tight`, white or gradient text.
- **Section H2**: `text-3xl md:text-4xl`, `font-extrabold`, `tracking-tight`.
- **Card H3/H4**: `text-lg`–`text-2xl`, bold.
- **Body**: `text-sm`–`text-base`, `leading-relaxed`.
- **Metrics**: `text-4xl font-black text-blue-600` for numbers.
- **Text wrapping**: use `text-pretty` on descriptive paragraphs to avoid single-word last lines.

### Layout

- **Container**: `max-w-5xl mx-auto px-6` for body sections; `max-w-7xl` for nav; `max-w-4xl` for hero text.
- **Grid**: global `64px` fixed grid background (`background-attachment: fixed`) at low opacity.
- **Section spacing**: `py-16`, separated by `border-b border-slate-200`.
- **Cards**: `rounded-xl` or `rounded-2xl`, white background, `slate-200` border, soft shadow.
- **Dividers**: use `divide-x divide-y divide-slate-100` for stitched bento panels instead of full-width ruled tables.

## Page Architecture

1. **Optional global banner** — a thin, colored strip for one-line announcements.
2. **Scroll-aware nav** — starts dark over the hero, switches to light once it reaches the body. Supports grouped dropdowns for subsection anchors.
3. **Hero** — dark full-width section with tag, H1, subtitle, and two CTAs. Keeps the 64px grid at `opacity-[0.03]` and a soft ambient glow.
4. **Numbered sections** — each section has:
   - a compact badge (`01 / 章节名`)
   - H2 headline with optional blue highlight span
   - a short lead paragraph
   - one or more bento components
5. **Closing CTA** — the final section should end with a clear action (button, contact prompt, or next-step roadmap).

## Core Components

### Bento Pain-Point Bar

- A full-width tinted panel (`bg-slate-200/40`) with a left accent bar, icon, title, and one-paragraph explanation.
- Use it to frame the problem before presenting the solution.

### Three-Pillar Panel

- A white card with a subtle header and a 3-column `divide-x` grid.
- Each cell: icon in a rounded `blue-50` box, bold title, short description.

### Metrics Grid

- 3-column `divide-x` cells, each centered: big number, label, micro-explanation.
- Keep numbers specific and honest (`60 分钟`, `0 代码`, `100%`).

### Mac-Window Video

- `rounded-2xl bg-slate-900` container with a top bar (three dots + filename).
- `aspect-video` video area with poster placeholder.
- Use muted, looping, inline video for demos.

### Image Carousel

- `.media-wrapper.carousel` with `.slides`, prev/next chevron buttons (`‹` / `›`), dots, and caption.
- Use only when 2–3 screenshots share one narrative.

### Role Identity Cards

- 3 cards in a grid: light, tinted, and dark variants.
- Each shows a role title, 2–3 responsibilities, and one crossed-out task to emphasize what the role no longer does.
- Add a faint watermark SVG in the top-right corner.

### Accordion Comparison Table

- Replace traditional full-width tables with a `.compare.saas-table` where each row is clickable.
- Row: dimension, before-state, after-state; expanded detail reveals the explanation.

### Before & After Split

- Two-column card with a vertical divider: left side tinted `slate-100/80` for the old way, right side white for the new way.
- Each side has a small header icon and 2 concise bullet points.

### Timeline Workflow

- A bento card split 1/3 – 2/3: left timeline with numbered steps and right deliverables panel.
- Use a vertical left border with blue active dot and gray inactive dots.

### Demo Video Block

- Dark rounded container (`bg-slate-900`) with a single large video and 1× / 1.5× / 2× speed buttons.

### Roadmap Timeline

- Vertical numbered timeline with `bg-white` cards connected by a faint center line.
- Each step: number circle, title, short description.

### CTA Button

- End the report with one high-contrast button (`bg-slate-900 text-white` or `bg-blue-600`).
- Copy should name the next action, e.g. “获取完整方案 →”.

## Texture & Contrast

- **Global grid**: 64px fixed grid (`background-size: 64px 64px; background-attachment: fixed`) using `slate-300` lines. Hero opacity `0.03`; body sections `0.2`.
- **Ambient glow**: large blurred circles (`blur-[120px]`) in blue/indigo at low opacity behind the hero. Do not add glow to body sections.
- **Dark contrast modules**: use `bg-slate-900` for video wrappers and `bg-slate-800` for the third role card or emphasis panels.
- **Shadows**: soft layered shadows (`shadow-sm`, `shadow-md`, `shadow-2xl`) rather than heavy drop shadows.

## Motion

- **Section reveal**: sections start with `opacity: 0; transform: translateY(28px)` and animate to visible when entering the viewport.
- **Direction-aware re-trigger**: after leaving the viewport, sections reset; they re-animate only when re-entering from above. Re-entry from below shows instantly to avoid backwards motion.
- **Reduced motion**: wrap transitions in `@media (prefers-reduced-motion: reduce)` to disable animations.

## Tone of Voice

- **No buzzwords**: avoid “赋能”、“抓手”、“闭环”、“生态” unless the user explicitly supplies them.
- **Verbs first**: use concrete actions — “自动归档”、“调用知识库”、“生成报告”、“压缩周期”。
- **Outcome-oriented data**: pair every claim with a measurable result — `60 分钟`, `0 代码`, `从天级到小时级`.
- **Progressive disclosure**: the headline makes the judgment; the paragraph explains why; the card/table gives evidence; the CTA names the next step.
- **One idea per card**: if a card contains two claims, split it.

## Responsive Rules

- Desktop is primary; mobile must not overflow horizontally.
- Collapse multi-column bento grids to single column on small screens (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`).
- Keep nav usable: grouped nav can stack or hide behind a simple inline list on very small screens.
- Avoid fixed widths on text containers unless intentionally limiting reading measure.

## Image Generation Style Prompt

```text
Generate a 16:9 premium B2B SaaS infographic. Deep navy hero area (#0A0E17) transitioning to a soft slate-50 body. Subtle 64px grid texture, restrained blue-to-indigo gradient accents, soft ambient glow. Use rounded-2xl white cards, thin slate-200 borders, clean iconography, timeline dots, and data panels. Isometric or flat 3D modules, node networks, and process strips. Professional, high information density, no cartoon style, no dark cyberpunk, no garbled text, no logos, no watermarks. Labels in the report language; use Chinese labels when the report is Chinese.
```

## Design Maxims

1. **“每一屏只回答一个问题，每张卡片只给一个新信息。”** 避免在同一块 Bento 里堆叠多个论点；信息去重比信息堆砌更有说服力。
2. **“用具体数字代替形容词，用动词代替名词。”** 不说“大幅提升”，说“60 分钟跑通”；不说“智能化赋能”，说“自动归档结论”。
3. **“表格不是版面，Bento 才是。”** 把全屏横线表格拆成可点击的 Accordion 行、Timeline 或 divide-x 数据面板，消灭视觉死角。
4. **“报告的最后 10% 决定报告的去向。”** 永远以明确的 CTA 收尾——按钮、联系方式或下一步动作，不要让读者滑到底后“就这么结束了”。
