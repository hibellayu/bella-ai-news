#!/usr/bin/env python3
"""
Convert AI daily news MD files to news.json for the web viewer.
Usage: python scripts/build.py
"""
import os
import json
import re
import glob
from datetime import datetime

MD_DIR = os.path.join(os.path.dirname(__file__), "../../日報AI新聞動態")
OUTPUT = os.path.join(os.path.dirname(__file__), "../news.json")


def md_to_html(md: str) -> str:
    """Simple MD → HTML converter (no dependencies)."""
    lines = md.split("\n")
    html_lines = []
    in_ul = False

    for line in lines:
        # Blockquote
        if line.startswith("> "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f'<blockquote>{line[2:]}</blockquote>')
            continue

        # H1
        if line.startswith("# "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f'<h1>{_inline(line[2:])}</h1>')
            continue

        # H2
        if line.startswith("## "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f'<h2>{_inline(line[3:])}</h2>')
            continue

        # H3
        if line.startswith("### "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f'<h3>{_inline(line[4:])}</h3>')
            continue

        # HR
        if re.match(r'^-{3,}$', line.strip()):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append('<hr>')
            continue

        # List item
        if line.startswith("- "):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f'<li>{_inline(line[2:])}</li>')
            continue

        # Numbered list
        m = re.match(r'^(\d+)\. (.+)', line)
        if m:
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f'<li>{_inline(m.group(2))}</li>')
            continue

        # Empty line
        if line.strip() == "":
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append("")
            continue

        # Italic line (footer note)
        if line.startswith("*") and line.endswith("*"):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f'<p class="footer-note">{_inline(line)}</p>')
            continue

        # Normal paragraph
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False
        html_lines.append(f'<p>{_inline(line)}</p>')

    if in_ul:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _inline(text: str) -> str:
    """Process inline MD: bold, italic, links."""
    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text* (not at start of line)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    return text


def strip_html(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html)


def parse_md_file(filepath: str) -> dict | None:
    filename = os.path.basename(filepath)
    m = re.match(r'AI日報_(\d{8})\.md', filename)
    if not m:
        return None
    date_str = m.group(1)
    date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")

    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # Extract title from first H1
    title_m = re.search(r'^# (.+)', raw, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else f"AI 日報｜{date}"

    # Extract summary (blockquote)
    summary_m = re.search(r'^> (.+)', raw, re.MULTILINE)
    summary = summary_m.group(1).strip() if summary_m else ""

    content_html = md_to_html(raw)
    content_text = strip_html(content_html).lower()

    return {
        "date": date,
        "title": title,
        "summary": summary,
        "content_html": content_html,
        "content_text": content_text,
    }


def main():
    md_dir = os.path.abspath(MD_DIR)
    if not os.path.isdir(md_dir):
        print(f"MD directory not found: {md_dir}")
        return

    files = sorted(glob.glob(os.path.join(md_dir, "AI日報_*.md")))
    print(f"Found {len(files)} MD files")

    entries = []
    for f in files:
        entry = parse_md_file(f)
        if entry:
            entries.append(entry)
            print(f"  ✓ {entry['date']}")
        else:
            print(f"  ✗ skipped: {os.path.basename(f)}")

    # Sort newest first
    entries.sort(key=lambda e: e["date"], reverse=True)

    output_path = os.path.abspath(OUTPUT)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(entries)} entries → {output_path}")


if __name__ == "__main__":
    main()
