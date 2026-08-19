---
name: markdown-document-export
description: Convert Markdown files into polished document exports, defaulting to PDF and optionally producing Word (.docx). Use this whenever the user wants to export, print, render, package, deliver, or generate a final document from Markdown, especially for proposals, reports, plans, specs, handoff docs, shareable materials, or files that need to be sent, printed, archived, or reviewed. Also use it when the user asks to turn Markdown into PDF, Word, docx, printable documents, formal documents, or presentation-ready output, even if they do not explicitly mention this skill. Common Chinese triggers include 把 Markdown 导出成 PDF, 导出文档, 生成 PDF, 转成 Word, 转 docx, 输出正式文档, 打印出来, 排版后导出, 做成可分享版本, 生成汇报材料, 生成方案文档, 生成可交付文件, 导出为附件, 保留 Mermaid 图和本地图片.
---

# Markdown Document Export

Use this skill when the user wants a Markdown document exported as a final document, especially when the Markdown contains:

- fenced `mermaid` blocks
- Mermaid labels that use `fa:fa-*` Font Awesome icons
- relative local image references in Markdown or HTML

## Trigger cues

This skill should trigger aggressively when the user is asking for document output rather than Markdown editing.

Typical English cues:

- export this Markdown to PDF
- convert this `.md` file to Word or `.docx`
- print this Markdown as a document
- generate a polished report from this Markdown
- create a shareable final document from this note
- package this proposal/spec/plan as a document attachment

Typical Chinese cues:

- 把这个 Markdown 导出成 PDF
- 把这个 md 转成 Word / docx
- 帮我导出文档
- 生成正式文档 / 最终文档 / 可交付文档
- 把这份笔记排版后导出
- 输出一个可打印版本
- 做成可以发给别人/发领导/发客户的版本
- 生成汇报材料 / 方案文档 / 立项文档 / 报告
- 导出附件 / 导出文件 / 生成成品
- 保留 Mermaid 图、流程图、本地图片、表格样式

Do not use this skill for ordinary Markdown rewriting, summarization, translation, or note cleanup when the user is not asking for a final exported document.

## Requirements

- `pandoc` must be installed and available in `PATH`
- `mmdc` (`@mermaid-js/mermaid-cli`) must be installed and available in `PATH`
- `node` must be installed and available in `PATH`

## Default behavior

- Default output format is `pdf`
- Optional output format is `word`
- If the user explicitly asks for Word or `.docx`, pass `--output-format word`
- **Table of contents (TOC) defaults to `true`**: For PDF, this creates an interactive outline in the PDF reader's sidebar instead of a visible list at the top of the document body. For Word, this inserts a TOC field in the document body.
- Use `--inline-toc` to also include a visible TOC at the top of the document body (PDF only).
- Use `--no-toc` to disable TOC generation entirely.

## Default workflow

1. Run the bundled exporter script:

```bash
python scripts/export_markdown.py <input_md>
```

2. The script will:
   - scan the Markdown for fenced `mermaid` blocks
   - render each Mermaid block to PNG
   - preserve Mermaid Font Awesome icons by generating a local CSS file for the icons used in the document
   - replace each Mermaid block with an image reference in a preprocessed Markdown file
   - only add a figure caption when the Mermaid block includes an explicit caption marker
   - export PDF by default using `pandoc -> HTML -> browser PDF`
   - optionally export Word using `pandoc -> docx`
   - keep the current Word table enhancements for the `word` path
   - apply light table styling in PDF so borders and header emphasis remain visible

3. Report back:
   - the generated output path
   - the output format
   - the build directory path
   - whether Mermaid diagrams were rendered successfully

## Command interface

```bash
python scripts/export_markdown.py INPUT.md \
  [--output OUTPUT_PATH] \
  [--output-format pdf|word] \
  [--workdir BUILD_DIR] \
  [--keep-temp] \
  [--toc|--no-toc] \
  [--inline-toc]
```

- `--toc` (default): Generate a table of contents. For PDF, the TOC appears in the reader's sidebar/outline panel; for Word, it appears inline in the document body.
- `--no-toc`: Disable TOC generation.
- `--inline-toc` (PDF only): Also include a visible TOC at the top of the document body in addition to the sidebar outline.

Compatibility wrapper for explicit Word export:

```bash
python scripts/export_markdown_to_docx.py INPUT.md
```

## Skill directory

```text
skills/markdown-document-export/
├── SKILL.md
├── assets/
│   └── pdf.css
├── evals/
│   └── evals.json
├── examples/
│   └── sample-export.md
└── scripts/
    ├── export_markdown.py
    ├── export_markdown_to_docx.py
    └── render_html_to_pdf.mjs
```

## File roles

- `SKILL.md`
  - Skill trigger description, workflow contract, examples, output conventions, and Mermaid caption rules.
- `scripts/export_markdown.py`
  - Main entrypoint.
  - Reads Markdown, renders Mermaid to PNG, prepares intermediate Markdown or HTML, then exports either PDF or Word.
- `scripts/export_markdown_to_docx.py`
  - Compatibility wrapper.
  - For callers that still want an explicit Word-only command, it forwards to `export_markdown.py --output-format word`.
- `scripts/render_html_to_pdf.mjs`
  - Lightweight PDF renderer.
  - Loads the generated HTML in headless Chromium via Puppeteer and prints it to PDF.
- `assets/pdf.css`
  - PDF-only visual styling.
  - Controls Chinese font preference, table borders, header shading, image sizing, and print margins.
- `evals/evals.json`
  - Example prompts for validating the skill after changes.
- `examples/sample-export.md`
  - Minimal end-to-end sample.
  - Demonstrates Mermaid captions, local images, table styling, and math rendering in one file.

## Usage

Default PDF export:

```bash
python scripts/export_markdown.py ./立项-opus.md
```

Explicit Word export:

```bash
python scripts/export_markdown.py ./立项-opus.md --output-format word
```

Explicit custom output path:

```bash
python scripts/export_markdown.py ./立项-opus.md \
  --output ./输出/立项-opus.pdf
```

Sample file validation:

```bash
python scripts/export_markdown.py \
  examples/sample-export.md
```

## Final outputs

- Default output is `pdf`
  - If `--output` is omitted, output path is `<input-stem>.pdf`
- Optional output is `word`
  - If `--output-format word` is used and `--output` is omitted, output path is `<input-stem>.docx`
- PDF output keeps light print styling and embedded local resources.
- Word output keeps the current table enhancements:
  - all borders
  - light gray header row
  - bold header text
  - light cell padding

## Intermediate artefacts

The exporter writes intermediate files to a build directory. By default this is:

```text
<input-dir>/.markdown-document-export-build/
```

Expected contents:

- `preprocessed.md`
- `preprocessed.html` for PDF exports
- `mermaid/diagram-001.mmd`
- `mermaid/diagram-001.png`
- `logs/mmdc-001.log`
- `logs/pandoc-pdf.log` or `logs/pandoc-word.log`
- `logs/render-pdf.log` for PDF exports

Purpose of these intermediate files:

- `preprocessed.md`
  - Markdown after Mermaid blocks have been replaced with generated image references.
- `preprocessed.html`
  - Self-contained HTML used only for PDF generation.
- `mermaid/*.mmd`
  - Individual extracted Mermaid source blocks.
- `mermaid/*.png`
  - Rendered diagram images that replace Mermaid blocks in the exported document.
- `logs/*.log`
  - Execution logs for Mermaid rendering, Pandoc, and PDF printing.
  - These are the first place to inspect when an export fails.

## Failure handling

- If a Mermaid block fails to render, stop and surface the failing block number.
- If Pandoc cannot resolve a local image, stop and surface the missing resource error.
- If PDF rendering fails, stop and surface the PDF render log instead of silently falling back to Word.
- Do not silently drop Mermaid diagrams or images.

## Mermaid caption convention

If a Mermaid figure needs a caption, add a Mermaid comment line at the top of the block:

```mermaid
%% caption: Overall system architecture
flowchart LR
  A --> B
```

Rules:

- Use `%% caption: ...` as the standard form.
- `%% caption = ...` is also accepted.
- The caption marker must appear before the first real Mermaid statement.
- If no caption marker is present, the exported document will not show Mermaid caption text.

## Notes

- PDF is the default because it is the most presentation-ready output path in this skill.
- Word remains supported when the user needs downstream editing in Office.
- Mermaid figure captions are opt-in; if no caption marker is present, no figure caption text is emitted.
