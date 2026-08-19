#!/usr/bin/env python3
"""
Extract table-of-contents pages from a PDF as images.
"""

import os
import sys

import fitz


def extract_toc_images(pdf_path, toc_start_page, toc_end_page, output_dir, zoom=2.0):
    doc = fitz.open(pdf_path)
    os.makedirs(output_dir, exist_ok=True)

    for page_num in range(toc_start_page - 1, toc_end_page):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        output_path = os.path.join(output_dir, f"page_{page_num + 1:03d}.png")
        pix.save(output_path)
        print(f"Saved: {output_path}")

    doc.close()
    print(f"Extracted {toc_end_page - toc_start_page + 1} TOC pages to {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) not in {5, 6}:
        print(
            "Usage: python extract_toc_images.py <pdf_path> <start_page> <end_page> <output_dir> [zoom]"
        )
        sys.exit(1)

    zoom = float(sys.argv[5]) if len(sys.argv) == 6 else 2.0
    extract_toc_images(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], zoom=zoom)
