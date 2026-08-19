#!/usr/bin/env python3
"""
Add clickable links over TOC rows for text and scanned PDFs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz
import numpy as np
from PIL import Image


@dataclass
class TocItem:
    level: int
    title: str
    printed_page: int
    toc_pdf_page: int | None = None
    rect: list[float] | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "TocItem":
        return cls(
            level=int(data["level"]),
            title=data["title"],
            printed_page=int(data["printed_page"]),
            toc_pdf_page=int(data["toc_pdf_page"]) if data.get("toc_pdf_page") else None,
            rect=[float(v) for v in data["rect"]] if data.get("rect") else None,
        )


def normalize_title(text: str) -> str:
    replacements = {
        " ": "",
        "\u3000": "",
        "\t": "",
        "\n": "",
        "(": "（",
        ")": "）",
        ",": "，",
        ":": "：",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def load_toc(path: str) -> list[TocItem]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [TocItem.from_dict(item) for item in data]


def resolve_destination_page(item: TocItem, page_offset: int) -> int:
    return item.printed_page + page_offset


def insert_link(page: fitz.Page, rect: fitz.Rect, destination_page_one_based: int):
    page.insert_link(
        {
            "kind": fitz.LINK_GOTO,
            "from": rect,
            "page": destination_page_one_based - 1,
            "zoom": 0.0,
        }
    )


def find_text_rect(page: fitz.Page, item: TocItem) -> fitz.Rect | None:
    matches = page.search_for(item.title)
    if matches:
        return expand_row_rect(matches[0], page.rect)

    target = normalize_title(item.title)
    words = page.get_text("words")
    by_line: dict[tuple[int, int, int], list[tuple]] = {}
    for word in words:
        block_no, line_no, word_no = int(word[5]), int(word[6]), int(word[7])
        by_line.setdefault((block_no, line_no, word_no // 999999), []).append(word)

    grouped_by_line: dict[tuple[int, int], list[tuple]] = {}
    for word in words:
        grouped_by_line.setdefault((int(word[5]), int(word[6])), []).append(word)

    for line_words in grouped_by_line.values():
        line_words = sorted(line_words, key=lambda w: (w[1], w[0]))
        joined = normalize_title("".join(w[4] for w in line_words))
        if target and target in joined:
            x0 = min(w[0] for w in line_words)
            y0 = min(w[1] for w in line_words)
            x1 = max(w[2] for w in line_words)
            y1 = max(w[3] for w in line_words)
            return expand_row_rect(fitz.Rect(x0, y0, x1, y1), page.rect)

    return None


def expand_row_rect(rect: fitz.Rect, page_rect: fitz.Rect) -> fitz.Rect:
    height = rect.y1 - rect.y0
    pad_y = max(3.0, height * 0.25)
    left = max(page_rect.x0 + page_rect.width * 0.05, rect.x0 - page_rect.width * 0.02)
    right = min(page_rect.x1 - page_rect.width * 0.05, page_rect.x1 - page_rect.width * 0.05)
    return fitz.Rect(left, rect.y0 - pad_y, right, rect.y1 + pad_y)


def render_page_to_array(page: fitz.Page, zoom: float = 2.0) -> tuple[np.ndarray, tuple[float, float]]:
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    gray = np.array(img.convert("L"))
    scale_x = page.rect.width / gray.shape[1]
    scale_y = page.rect.height / gray.shape[0]
    return gray, (scale_x, scale_y)


def detect_scan_rects(page: fitz.Page, items: list[TocItem]) -> list[fitz.Rect]:
    gray, (scale_x, scale_y) = render_page_to_array(page, zoom=2.0)
    height, width = gray.shape
    y_start = int(height * 0.08)
    y_end = int(height * 0.92)
    x_start = int(width * 0.06)
    x_end = int(width * 0.96)

    cropped = gray[y_start:y_end, x_start:x_end]
    filtered: list[tuple[int, int]] = []
    row_density = None
    for relative_threshold, merge_gap in ((0.12, 6), (0.08, 4), (0.05, 2)):
        content = cropped < 220
        row_density = content.sum(axis=1)
        threshold = max(8, int(row_density.max() * relative_threshold))
        indices = np.where(row_density > threshold)[0]
        if len(indices) == 0:
            continue

        bands: list[tuple[int, int]] = []
        start = prev = int(indices[0])
        for idx in indices[1:]:
            idx = int(idx)
            if idx <= prev + merge_gap:
                prev = idx
                continue
            bands.append((start, prev))
            start = prev = idx
        bands.append((start, prev))

        filtered = []
        for y0, y1 in bands:
            if y1 - y0 < 6:
                continue
            if row_density[y0:y1 + 1].max() < threshold:
                continue
            region = content[y0:y1 + 1]
            col_density = region.sum(axis=0)
            cols = np.where(col_density > 0)[0]
            if len(cols) == 0:
                continue
            left_edge = int(cols[0])
            right_edge = int(cols[-1])
            span = right_edge - left_edge + 1
            if span < content.shape[1] * 0.35:
                continue
            if left_edge > content.shape[1] * 0.22:
                continue
            filtered.append((y0 + y_start, y1 + y_start))

        if len(filtered) >= len(items):
            break

    if len(filtered) < len(items):
        if len(filtered) >= 2:
            filtered = interpolate_missing_rows(filtered, len(items))
        else:
            raise ValueError(
                f"Detected only {len(filtered)} candidate rows for {len(items)} TOC items on page {page.number + 1}"
            )

    if len(filtered) > len(items):
        filtered = select_best_rows(filtered, gray, len(items))

    page_width = page.rect.width
    x0 = page.rect.x0 + page_width * 0.07
    x1 = page.rect.x1 - page_width * 0.07
    rects = []
    for y0, y1 in filtered:
        pdf_y0 = y0 * scale_y - 2
        pdf_y1 = (y1 + 1) * scale_y + 2
        rects.append(fitz.Rect(x0, pdf_y0, x1, pdf_y1))
    return rects


def select_best_rows(bands: list[tuple[int, int]], gray: np.ndarray, target_count: int) -> list[tuple[int, int]]:
    if len(bands) <= target_count:
        return bands

    if target_count == 1:
        return [bands[len(bands) // 2]]

    sampled = []
    for idx in range(target_count):
        src_index = round(idx * (len(bands) - 1) / (target_count - 1))
        sampled.append(bands[src_index])
    return sampled


def interpolate_missing_rows(bands: list[tuple[int, int]], target_count: int) -> list[tuple[int, int]]:
    centers = [(y0 + y1) / 2 for y0, y1 in bands]
    heights = [y1 - y0 + 1 for y0, y1 in bands]
    median_height = int(np.median(heights))
    if target_count == 1:
        center = centers[0]
        return [(int(center - median_height / 2), int(center + median_height / 2))]

    step = (centers[-1] - centers[0]) / (target_count - 1)
    half = max(4, median_height // 2)
    generated = []
    for idx in range(target_count):
        center = centers[0] + idx * step
        generated.append((int(center - half), int(center + half)))
    return generated


def assign_scan_rects(doc: fitz.Document, items: list[TocItem]) -> list[TocItem]:
    grouped: dict[int, list[TocItem]] = {}
    for item in items:
        if not item.toc_pdf_page:
            raise ValueError("scan mode requires toc_pdf_page for every item")
        grouped.setdefault(item.toc_pdf_page, []).append(item)

    for toc_pdf_page, page_items in grouped.items():
        page = doc[toc_pdf_page - 1]
        rects = detect_scan_rects(page, page_items)
        if len(rects) != len(page_items):
            raise ValueError(f"Rect count mismatch on TOC page {toc_pdf_page}")
        for item, rect in zip(page_items, rects):
            item.rect = [rect.x0, rect.y0, rect.x1, rect.y1]
    return items


def assign_text_rects(doc: fitz.Document, items: list[TocItem]) -> tuple[list[TocItem], list[TocItem]]:
    unresolved = []
    for item in items:
        if not item.toc_pdf_page:
            unresolved.append(item)
            continue
        page = doc[item.toc_pdf_page - 1]
        rect = find_text_rect(page, item)
        if rect is None:
            unresolved.append(item)
            continue
        item.rect = [rect.x0, rect.y0, rect.x1, rect.y1]
    return items, unresolved


def auto_assign_rects(doc: fitz.Document, items: list[TocItem]) -> tuple[list[TocItem], list[TocItem]]:
    textable_pages = {
        item.toc_pdf_page
        for item in items
        if item.toc_pdf_page and len(doc[item.toc_pdf_page - 1].get_text("text").strip()) > 0
    }
    text_items = [item for item in items if item.toc_pdf_page in textable_pages]
    scan_items = [item for item in items if item.toc_pdf_page not in textable_pages]

    unresolved = []
    if text_items:
        _, missing = assign_text_rects(doc, text_items)
        unresolved.extend(missing)
    if scan_items:
        assign_scan_rects(doc, scan_items)
    return items, unresolved


def save_unresolved(path: str | None, items: Iterable[TocItem]):
    if not path:
        return
    payload = [
        {
            "level": item.level,
            "title": item.title,
            "printed_page": item.printed_page,
            "toc_pdf_page": item.toc_pdf_page,
        }
        for item in items
    ]
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--toc-json", required=True)
    parser.add_argument("--page-offset", required=True, type=int)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=["auto", "text", "scan", "manual"], default="auto")
    parser.add_argument("--unresolved-output")
    args = parser.parse_args()

    doc = fitz.open(args.pdf)
    items = load_toc(args.toc_json)

    if args.mode == "text":
        items, unresolved = assign_text_rects(doc, items)
    elif args.mode == "scan":
        items = assign_scan_rects(doc, items)
        unresolved = []
    elif args.mode == "manual":
        unresolved = [item for item in items if item.rect is None or item.toc_pdf_page is None]
        if unresolved:
            raise ValueError("manual mode requires toc_pdf_page and rect for every TOC item")
    else:
        items, unresolved = auto_assign_rects(doc, items)

    save_unresolved(args.unresolved_output, unresolved)
    if unresolved:
        print(f"Unresolved items: {len(unresolved)}")

    added = 0
    for item in items:
        if not item.toc_pdf_page or not item.rect:
            continue
        page = doc[item.toc_pdf_page - 1]
        rect = fitz.Rect(*item.rect)
        insert_link(page, rect, resolve_destination_page(item, args.page_offset))
        added += 1

    doc.save(args.output)
    doc.close()
    print(f"Added {added} TOC links to {args.output}")


if __name__ == "__main__":
    main()
