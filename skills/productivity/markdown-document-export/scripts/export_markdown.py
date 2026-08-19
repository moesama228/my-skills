#!/usr/bin/env python3
"""Export Markdown to PDF or DOCX, rendering Mermaid blocks to PNG first."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


MERMAID_FENCE_RE = re.compile(r"^```mermaid\b")
FENCE_END_RE = re.compile(r"^```\s*$")
FA_ICON_RE = re.compile(r"fa:fa-([a-z0-9-]+)")
WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WORD_NAMESPACE}

ET.register_namespace("w", WORD_NAMESPACE)


@dataclass
class MermaidBlock:
    index: int
    source: str
    caption: str | None


class ExportError(RuntimeError):
    """Raised when export fails in a user-visible way."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Markdown file to PDF or DOCX with Mermaid rendering."
    )
    parser.add_argument("input_md", help="Path to the input Markdown file.")
    parser.add_argument(
        "--output",
        help="Output document path. Defaults to INPUT stem with the format-specific extension.",
    )
    parser.add_argument(
        "--output-format",
        choices=("pdf", "word"),
        default="pdf",
        help="Target export format. Defaults to pdf.",
    )
    parser.add_argument(
        "--workdir",
        help="Build directory for intermediate artefacts. Defaults to .markdown-document-export-build next to the input file.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Retain intermediate artefacts. Currently informational; artefacts are preserved by default.",
    )
    toc_group = parser.add_mutually_exclusive_group()
    toc_group.add_argument(
        "--toc",
        action="store_true",
        default=True,
        dest="toc",
        help="Generate table of contents. For PDF, this creates an outline in the sidebar. Defaults to true.",
    )
    toc_group.add_argument(
        "--no-toc",
        action="store_false",
        dest="toc",
        help="Disable table of contents generation.",
    )
    parser.add_argument(
        "--inline-toc",
        action="store_true",
        default=False,
        help="Include an inline table of contents in the document body (visible in the page content).",
    )
    return parser.parse_args()


def ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise ExportError(f"Required tool '{name}' was not found in PATH.")
    return path


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_command(command: list[str], log_path: Path, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    log_body = [
        "$ " + " ".join(command),
        "",
        "stdout:",
        result.stdout,
        "",
        "stderr:",
        result.stderr,
    ]
    write_text(log_path, "\n".join(log_body))
    if result.returncode != 0:
        raise ExportError(
            f"Command failed with exit code {result.returncode}: {' '.join(command)}\n"
            f"See log: {log_path}\n{result.stderr.strip()}"
        )


def extract_mermaid_blocks(markdown: str) -> tuple[list[MermaidBlock], str]:
    lines = markdown.splitlines(keepends=True)
    blocks: list[MermaidBlock] = []
    output: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if not MERMAID_FENCE_RE.match(line):
            output.append(line)
            i += 1
            continue

        start = i
        i += 1
        content_lines: list[str] = []
        while i < len(lines) and not FENCE_END_RE.match(lines[i]):
            content_lines.append(lines[i])
            i += 1
        if i >= len(lines):
            raise ExportError("Found an opening ```mermaid fence without a closing ```.")
        i += 1

        block_index = len(blocks) + 1
        block_source = "".join(content_lines).rstrip() + "\n"
        caption = extract_mermaid_caption(block_source)
        blocks.append(MermaidBlock(index=block_index, source=block_source, caption=caption))
        image_ref = build_mermaid_image_ref(block_index, caption)
        if start > 0 and output and not output[-1].endswith("\n"):
            output.append("\n")
        output.append(image_ref)

    return blocks, "".join(output)


def extract_mermaid_caption(block_source: str) -> str | None:
    for raw_line in block_source.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith("%%"):
            break
        comment = line[2:].strip()
        match = re.match(r"(?i)caption\s*[:=]\s*(.+)$", comment)
        if match:
            caption = match.group(1).strip()
            return caption or None
    return None


def build_mermaid_image_ref(block_index: int, caption: str | None) -> str:
    image_path = f"mermaid/diagram-{block_index:03d}.png"
    if caption:
        escaped_caption = caption.replace("[", r"\[").replace("]", r"\]")
        return f"![{escaped_caption}]({image_path})\n\n"
    return f"![]({image_path})\n\n"


def locate_mermaid_assets(mmdc_path: str) -> tuple[Path, Path, Path, Path]:
    cli_path = Path(mmdc_path).resolve()
    package_dir = cli_path.parents[1]
    assets_dir = package_dir / "dist" / "assets"
    if not assets_dir.exists():
        raise ExportError(f"Could not find Mermaid CLI assets directory: {assets_dir}")

    bundle_candidates = sorted(assets_dir.glob("index-*.js"))
    woff_candidates = sorted(assets_dir.glob("fa-solid-900-*.woff2"))
    ttf_candidates = sorted(assets_dir.glob("fa-solid-900-*.ttf"))

    if not bundle_candidates or not woff_candidates or not ttf_candidates:
        raise ExportError(
            "Could not locate Mermaid CLI Font Awesome bundle assets under "
            f"{assets_dir}"
        )
    return package_dir, bundle_candidates[0], woff_candidates[0], ttf_candidates[0]


def extract_icon_css(bundle_path: Path, icon_names: set[str], woff_path: Path, ttf_path: Path) -> str:
    bundle = bundle_path.read_text(encoding="utf-8")
    woff_uri = woff_path.resolve().as_uri()
    ttf_uri = ttf_path.resolve().as_uri()
    rules = [
        "@font-face {",
        "  font-family: 'Font Awesome 6 Free';",
        "  font-style: normal;",
        "  font-weight: 900;",
        "  font-display: block;",
        f"  src: url('{woff_uri}') format('woff2'),",
        f"       url('{ttf_uri}') format('truetype');",
        "}",
        ".fa, .fas, .fa-solid {",
        "  font-family: 'Font Awesome 6 Free';",
        "  font-weight: 900;",
        "  font-style: normal;",
        "  display: inline-block;",
        "  line-height: 1;",
        "  text-rendering: auto;",
        "  -webkit-font-smoothing: antialiased;",
        "  -moz-osx-font-smoothing: grayscale;",
        "}",
    ]

    missing_icons: list[str] = []
    for icon_name in sorted(icon_names):
        pattern = re.compile(
            rf"\.fa-{re.escape(icon_name)}:before\{{content:\"([^\"]+)\"\}}"
        )
        match = pattern.search(bundle)
        if not match:
            missing_icons.append(icon_name)
            continue
        rules.append(f'.fa-{icon_name}:before {{ content: "{match.group(1)}"; }}')

    if missing_icons:
        raise ExportError(
            "Could not resolve Font Awesome icon definitions for: "
            + ", ".join(missing_icons)
        )
    return "\n".join(rules) + "\n"


def render_mermaid_blocks(blocks: list[MermaidBlock], workdir: Path, mmdc_path: str) -> Path:
    mermaid_dir = workdir / "mermaid"
    logs_dir = workdir / "logs"
    mermaid_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    package_dir, bundle_path, woff_path, ttf_path = locate_mermaid_assets(mmdc_path)
    all_icon_names: set[str] = set()
    for block in blocks:
        all_icon_names.update(FA_ICON_RE.findall(block.source))

    css_path = workdir / "mermaid-fontawesome.css"
    if all_icon_names:
        write_text(css_path, extract_icon_css(bundle_path, all_icon_names, woff_path, ttf_path))

    puppeteer_path = workdir / "puppeteer-config.json"
    write_text(
        puppeteer_path,
        json.dumps({"args": ["--no-sandbox"]}, ensure_ascii=True, indent=2) + "\n",
    )

    mermaid_config = {
        "securityLevel": "loose",
        "flowchart": {"htmlLabels": True},
    }
    mermaid_config_path = workdir / "mermaid-config.json"
    write_text(
        mermaid_config_path,
        json.dumps(mermaid_config, ensure_ascii=True, indent=2) + "\n",
    )

    for block in blocks:
        source_path = mermaid_dir / f"diagram-{block.index:03d}.mmd"
        output_path = mermaid_dir / f"diagram-{block.index:03d}.png"
        write_text(source_path, block.source)

        command = [
            mmdc_path,
            "-i",
            str(source_path),
            "-o",
            str(output_path),
            "-e",
            "png",
            "-b",
            "transparent",
            "-s",
            "2",
            "-p",
            str(puppeteer_path),
            "-c",
            str(mermaid_config_path),
            "-q",
        ]
        if all_icon_names:
            command.extend(["-C", str(css_path)])
        run_command(command, logs_dir / f"mmdc-{block.index:03d}.log")
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ExportError(
                f"Mermaid block {block.index} did not produce a valid PNG: {output_path}"
            )

    return package_dir


def build_resource_path(input_path: Path, workdir: Path) -> str:
    candidates = [
        input_path.parent.resolve(),
        input_path.parent.parent.resolve(),
        workdir.resolve(),
        (workdir / "mermaid").resolve(),
    ]
    unique_paths: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_str = str(candidate)
        if candidate_str not in seen:
            unique_paths.append(candidate_str)
            seen.add(candidate_str)
    return os.pathsep.join(unique_paths)


def make_w_tag(name: str) -> str:
    return f"{{{WORD_NAMESPACE}}}{name}"


def set_border(parent: ET.Element, tag_name: str, color: str) -> None:
    border = parent.find(f"w:{tag_name}", NS)
    if border is None:
        border = ET.SubElement(parent, make_w_tag(tag_name))
    border.set(make_w_tag("val"), "single")
    border.set(make_w_tag("sz"), "4")
    border.set(make_w_tag("space"), "0")
    border.set(make_w_tag("color"), color)


def ensure_table_borders(tbl_pr: ET.Element) -> None:
    tbl_borders = tbl_pr.find("w:tblBorders", NS)
    if tbl_borders is None:
        tbl_borders = ET.SubElement(tbl_pr, make_w_tag("tblBorders"))
    for tag_name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        set_border(tbl_borders, tag_name, "BFBFBF")


def ensure_cell_borders(tc_pr: ET.Element) -> None:
    tc_borders = tc_pr.find("w:tcBorders", NS)
    if tc_borders is None:
        tc_borders = ET.SubElement(tc_pr, make_w_tag("tcBorders"))
    for tag_name in ("top", "left", "bottom", "right"):
        set_border(tc_borders, tag_name, "BFBFBF")


def ensure_header_fill(tc_pr: ET.Element) -> None:
    shading = tc_pr.find("w:shd", NS)
    if shading is None:
        shading = ET.SubElement(tc_pr, make_w_tag("shd"))
    shading.set(make_w_tag("val"), "clear")
    shading.set(make_w_tag("color"), "auto")
    shading.set(make_w_tag("fill"), "F2F2F2")


def ensure_cell_margins(tc_pr: ET.Element) -> None:
    tc_mar = tc_pr.find("w:tcMar", NS)
    if tc_mar is None:
        tc_mar = ET.SubElement(tc_pr, make_w_tag("tcMar"))
    for side, width in (("top", "80"), ("bottom", "80"), ("left", "100"), ("right", "100")):
        margin = tc_mar.find(f"w:{side}", NS)
        if margin is None:
            margin = ET.SubElement(tc_mar, make_w_tag(side))
        margin.set(make_w_tag("w"), width)
        margin.set(make_w_tag("type"), "dxa")


def ensure_vertical_align(tc_pr: ET.Element, alignment: str) -> None:
    v_align = tc_pr.find("w:vAlign", NS)
    if v_align is None:
        v_align = ET.SubElement(tc_pr, make_w_tag("vAlign"))
    v_align.set(make_w_tag("val"), alignment)


def ensure_run_bold(run: ET.Element) -> None:
    run_pr = run.find("w:rPr", NS)
    if run_pr is None:
        run_pr = ET.Element(make_w_tag("rPr"))
        run.insert(0, run_pr)
    bold = run_pr.find("w:b", NS)
    if bold is None:
        bold = ET.SubElement(run_pr, make_w_tag("b"))
    bold.set(make_w_tag("val"), "1")
    bold_cs = run_pr.find("w:bCs", NS)
    if bold_cs is None:
        bold_cs = ET.SubElement(run_pr, make_w_tag("bCs"))
    bold_cs.set(make_w_tag("val"), "1")


def style_header_cell(cell: ET.Element, tc_pr: ET.Element) -> None:
    ensure_header_fill(tc_pr)
    ensure_vertical_align(tc_pr, "center")
    for run in cell.findall(".//w:r", NS):
        ensure_run_bold(run)


def style_document_tables(xml_path: Path) -> None:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    for table in root.findall(".//w:tbl", NS):
        tbl_pr = table.find("w:tblPr", NS)
        if tbl_pr is None:
            tbl_pr = ET.Element(make_w_tag("tblPr"))
            table.insert(0, tbl_pr)
        ensure_table_borders(tbl_pr)

        rows = table.findall("w:tr", NS)
        if not rows:
            continue

        for row_index, row in enumerate(rows):
            for cell in row.findall("w:tc", NS):
                tc_pr = cell.find("w:tcPr", NS)
                if tc_pr is None:
                    tc_pr = ET.Element(make_w_tag("tcPr"))
                    cell.insert(0, tc_pr)
                ensure_cell_borders(tc_pr)
                ensure_cell_margins(tc_pr)
                if row_index == 0:
                    style_header_cell(cell, tc_pr)

    tree.write(xml_path, encoding="utf-8", xml_declaration=True)


def postprocess_docx_tables(docx_path: Path) -> None:
    with TemporaryDirectory(prefix="markdown_to_word_") as temp_dir:
        temp_root = Path(temp_dir)
        with ZipFile(docx_path, "r") as zf:
            zf.extractall(temp_root)

        document_xml = temp_root / "word" / "document.xml"
        if not document_xml.exists():
            raise ExportError(f"Generated DOCX is missing word/document.xml: {docx_path}")
        style_document_tables(document_xml)

        rebuilt_docx = temp_root / "rebuilt.docx"
        with ZipFile(rebuilt_docx, "w", compression=ZIP_DEFLATED) as zf:
            for file_path in sorted(temp_root.rglob("*")):
                if file_path.is_dir() or file_path == rebuilt_docx:
                    continue
                zf.write(file_path, file_path.relative_to(temp_root))

        shutil.copyfile(rebuilt_docx, docx_path)


def export_word(input_path: Path, output_path: Path, workdir: Path, pandoc_path: str, *, toc: bool = True) -> None:
    preprocessed_path = workdir / "preprocessed.md"
    logs_dir = workdir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    command = [
        pandoc_path,
        str(preprocessed_path),
        "--from",
        "markdown+raw_html",
        "--to",
        "docx",
        "--output",
        str(output_path),
        "--resource-path",
        build_resource_path(input_path, workdir),
    ]
    if toc:
        command.append("--toc")
    run_command(command, logs_dir / "pandoc-word.log")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ExportError(f"Word output was not created correctly: {output_path}")
    postprocess_docx_tables(output_path)


def export_pdf(
    input_path: Path,
    output_path: Path,
    workdir: Path,
    pandoc_path: str,
    mermaid_package_dir: Path,
    script_dir: Path,
    *,
    toc: bool = True,
    inline_toc: bool = False,
) -> None:
    logs_dir = workdir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    html_path = workdir / "preprocessed.html"
    katex_dir = mermaid_package_dir / "node_modules" / "katex" / "dist"
    if not katex_dir.exists():
        raise ExportError(f"Local KaTeX assets were not found: {katex_dir}")
    katex_path = str(katex_dir.resolve()) + "/"

    command = [
        pandoc_path,
        str(workdir / "preprocessed.md"),
        "--from",
        "markdown+raw_html",
        "--to",
        "html5",
        "--standalone",
        "--embed-resources",
        "--output",
        str(html_path),
        "--css",
        str((script_dir.parent / "assets" / "pdf.css").resolve()),
        f"--katex={katex_path}",
        "--resource-path",
        build_resource_path(input_path, workdir),
    ]
    if inline_toc:
        command.append("--toc")
    run_command(command, logs_dir / "pandoc-pdf.log")

    if not html_path.exists() or html_path.stat().st_size == 0:
        raise ExportError(f"Intermediate HTML was not created correctly: {html_path}")

    node_path = ensure_tool("node")
    env = os.environ.copy()
    env["MERMAID_PUPPETEER_BASE"] = str(mermaid_package_dir)
    command = [
        node_path,
        str((script_dir / "render_html_to_pdf.mjs").resolve()),
        str(html_path),
        str(output_path),
        str(toc).lower(),
    ]
    run_command(command, logs_dir / "render-pdf.log", env=env)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ExportError(f"PDF output was not created correctly: {output_path}")


def resolve_output_path(input_path: Path, output: str | None, output_format: str) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    suffix = ".pdf" if output_format == "pdf" else ".docx"
    return input_path.with_suffix(suffix)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_md).expanduser().resolve()
    if not input_path.exists():
        raise ExportError(f"Input Markdown file does not exist: {input_path}")
    if not input_path.is_file():
        raise ExportError(f"Input path is not a file: {input_path}")

    output_path = resolve_output_path(input_path, args.output, args.output_format)
    workdir = (
        Path(args.workdir).expanduser().resolve()
        if args.workdir
        else input_path.parent / ".markdown-document-export-build"
    )
    workdir.mkdir(parents=True, exist_ok=True)

    pandoc_path = ensure_tool("pandoc")
    mmdc_path = ensure_tool("mmdc")
    script_dir = Path(__file__).resolve().parent

    markdown = input_path.read_text(encoding="utf-8")
    mermaid_blocks, preprocessed_markdown = extract_mermaid_blocks(markdown)
    write_text(workdir / "preprocessed.md", preprocessed_markdown)

    mermaid_package_dir = Path(mmdc_path).resolve().parents[1]
    if mermaid_blocks:
        mermaid_package_dir = render_mermaid_blocks(mermaid_blocks, workdir, mmdc_path)

    if args.output_format == "word":
        export_word(input_path, output_path, workdir, pandoc_path, toc=args.toc)
    else:
        export_pdf(
            input_path,
            output_path,
            workdir,
            pandoc_path,
            mermaid_package_dir,
            script_dir,
            toc=args.toc,
            inline_toc=args.inline_toc,
        )

    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "output_format": args.output_format,
        "workdir": str(workdir),
        "mermaid_blocks": len(mermaid_blocks),
        "kept_temp": True,
    }
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ExportError as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1)
