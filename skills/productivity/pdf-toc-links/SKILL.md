---
name: pdf-toc-links
description: Add PDF sidebar bookmarks and clickable hyperlinks on printed table-of-contents pages. Use when Codex needs to turn a PDF TOC into navigable PDF links, preserve the original TOC page layout, or handle both text-based PDFs and scanned/image PDFs that need clickable TOC rows.
---

# PDF TOC Links

Add navigation to PDFs in two layers:
- sidebar bookmarks via `set_toc()`
- clickable transparent link annotations over the original TOC pages

Use the copied bookmark workflow from the original skill, then add TOC-page hyperlinks with the same normalized TOC list.

## Workflow

### 1. Prepare the TOC list

Represent each TOC item as a dict:

```python
{
    "level": 1,
    "title": "第一篇 总论",
    "printed_page": 1,
    "toc_pdf_page": 30,   # optional until link placement
    "rect": None,         # optional until link placement
}
```

Required keys are `level`, `title`, and `printed_page`.

### 2. Extract TOC pages as images

Use the copied extractor for visual inspection or scan-layout analysis:

```python
from scripts.extract_toc_images import extract_toc_images

extract_toc_images(
    pdf_path="/path/to/file.pdf",
    toc_start_page=30,
    toc_end_page=33,
    output_dir="/tmp/toc_images",
)
```

### 3. Determine `page_offset`

Compute:

```text
page_offset = actual_pdf_page - printed_page
```

Always verify the offset against at least one known TOC entry.

### 4. Add sidebar bookmarks

Use the normalized TOC list with:

```python
from scripts.add_bookmarks import add_bookmarks

add_bookmarks(
    pdf_path="/path/to/input.pdf",
    toc_list=toc_items,
    page_offset=33,
    output_path="/path/to/bookmarked.pdf",
)
```

### 5. Add clickable TOC-page links

Use `scripts/add_toc_links.py` after bookmarks or in a single pass:

```bash
python3 scripts/add_toc_links.py \
  --pdf /path/to/input.pdf \
  --toc-json /path/to/toc.json \
  --page-offset 33 \
  --output /path/to/output.pdf \
  --mode auto
```

Modes:
- `auto`: choose text-native placement when the TOC page has extractable text, else use scan-layout placement
- `text`: force text-native placement
- `scan`: force scan-layout placement
- `manual`: require explicit `rect` data in the TOC JSON

### 6. Inspect and patch ambiguous rows

For text PDFs, the script records unresolved rows when title search fails.

For scanned PDFs, the script can auto-generate row rectangles from page image layout. If a page's detected row count does not match the TOC items assigned to that page, inspect the page image and rerun with manual rect overrides.

Read [references/toc-json-format.md](./references/toc-json-format.md) when building or editing the TOC JSON file.

## Placement Strategy

### Text PDFs

Use PDF-native coordinates first:
- `page.search_for(title)`
- fallback to `page.get_text("words")`
- normalize whitespace and punctuation before matching
- expand the matched box horizontally so the whole TOC row is clickable

### Scanned/Image PDFs

Do not depend on OCR by default.

Instead:
- render TOC pages to images
- threshold to dark/light pixels
- compute horizontal dark-pixel density
- group density peaks into row bands
- map row bands back into PDF coordinates
- span each row across the title and page-number columns

This is semi-automatic: the script proposes rectangles and only requires manual overrides for ambiguous rows.

## Scripts

- `scripts/extract_toc_images.py`: render TOC pages for inspection
- `scripts/add_bookmarks.py`: add sidebar bookmarks from normalized TOC items
- `scripts/add_toc_links.py`: add clickable link annotations on TOC pages

## Example

For `承淡安中国针灸治疗学.pdf`:
- TOC pages are PDF 30-33
- `page_offset` is `33`
- use `scan` or `auto` mode because the TOC pages are image-only
- verify that TOC row `第一篇 总论` jumps to PDF 34 and `跋` jumps to PDF 274
