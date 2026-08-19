# TOC JSON Format

Use a JSON array of TOC item objects.

Minimal example:

```json
[
  {
    "level": 1,
    "title": "第一篇 总论",
    "printed_page": 1
  },
  {
    "level": 2,
    "title": "一、针灸术之沿革",
    "printed_page": 1
  }
]
```

Full example with explicit TOC-page placement:

```json
[
  {
    "level": 1,
    "title": "第一篇 总论",
    "printed_page": 1,
    "toc_pdf_page": 30,
    "rect": [53.0, 280.0, 980.0, 335.0]
  }
]
```

Rules:
- `level`: integer bookmark depth starting at `1`
- `title`: visible TOC text
- `printed_page`: printed page number from the TOC
- `toc_pdf_page`: 1-based PDF page number where the TOC row appears
- `rect`: optional rectangle on the TOC page in PDF coordinates `[x0, y0, x1, y1]`

`rect` is optional for automatic placement and required for `manual` mode.

For `scan` mode the script groups TOC items by `toc_pdf_page`. If `toc_pdf_page` is missing, it cannot assign items to the correct TOC page.
