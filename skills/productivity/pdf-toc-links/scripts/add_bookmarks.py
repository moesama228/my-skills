#!/usr/bin/env python3
"""
Add PDF bookmarks from a normalized TOC structure.
"""

import json
import sys

import fitz


def _normalize_item(item):
    if isinstance(item, dict):
        return int(item["level"]), item["title"], int(item["printed_page"])
    if isinstance(item, (list, tuple)) and len(item) == 3:
        return int(item[0]), item[1], int(item[2])
    raise ValueError(f"Unsupported TOC item: {item!r}")


def add_bookmarks(pdf_path, toc_list, page_offset, output_path):
    doc = fitz.open(pdf_path)
    toc_with_offset = []
    for item in toc_list:
        level, title, printed_page = _normalize_item(item)
        toc_with_offset.append([level, title, printed_page + page_offset])

    doc.set_toc(toc_with_offset)
    doc.save(output_path)
    doc.close()
    return len(toc_with_offset)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python add_bookmarks.py <pdf_path> <toc_json> <page_offset> <output_path>")
        sys.exit(1)

    with open(sys.argv[2], "r", encoding="utf-8") as fh:
        toc_list = json.load(fh)

    count = add_bookmarks(sys.argv[1], toc_list, int(sys.argv[3]), sys.argv[4])
    print(f"Added {count} bookmarks to {sys.argv[4]}")
