#!/usr/bin/env python3
"""
Build news.json for the Bella AI News viewer.

Sources (JSON takes priority over MD for the same date):
  1. digests/*.json  — structured JSON (preferred)
  2. 日報AI新聞動態/AI日報_YYYYMMDD.md — MD backups, local-only fallback

Usage: python scripts/build.py
"""
import os, json, re, glob
from datetime import datetime

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JSON_DIR = os.path.join(BASE, "digests")
_md_path = os.path.join(BASE, "日報AI新聞動態")
MD_DIR   = _md_path if os.path.isdir(_md_path) else None
OUTPUT   = os.path.abspath(os.path.join(os.path.dirname(__file__), "../news.json"))


# ── JSON source ────────────────────────────────────────────────────────────────

def entry_from_json(filepath: str) -> dict | None:
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            d = json.load(f)
        except Exception as e:
            print(f"  JSON parse error {filepath}: {e}")
            return None

    if not isinstance(d, dict):
        return None

    date = d.get("date")
    if not date:
        return None

    title   = f"📰 AI 新聞日報｜{d.get('display_date', date)}"
    summary = d.get("summary", "")

    html_parts = [f"<h1>{title}</h1>"]

    # 資料收集說明
    data_date = d.get("data_date", "")
    if data_date:
        html_parts.append(
            f'<div class="data-note">'
            f'<p>📡 <strong>資料收集說明</strong></p>'
            f'<p>台灣媒體（iThome、數位時代、INSIDE、科技新報、AI郵報）<br>'
            f'收集 {data_date} 00:00–23:59（台北時間）發布的文章</p>'
            f'<p>國際媒體（TechCrunch、VentureBeat、Wired 等）<br>'
            f'以台北時間為基準收集 {data_date} 當日文章<br>'
            f'因美東時差約 -13 小時，對應美東前一日上午 ～ {data_date} 上午的報導</p>'
            f'</div>'
        )

    if summary:
        html_parts.append(f"<blockquote>{summary}</blockquote>")

    # Big news
    if d.get("big_news"):
        html_parts.append('<h2>🔥 大事件</h2>')
        for item in d["big_news"]:
            html_parts.append(f'<p><strong>{item["title"]}</strong></p>')
            html_parts.append(f'<p>{item["content"]}</p>')
            if item.get("source_urls"):
                links = "、".join(
                    f'<a href="{s["url"]}" target="_blank" rel="noopener">{s["name"]}</a>'
                    for s in item["source_urls"]
                )
                html_parts.append(f'<p class="sources">來源：{links}</p>')
            if item.get("tip"):
                html_parts.append(f'<p class="tip">💡 {item["tip"]}</p>')

    # Tool updates
    if d.get("tool_updates"):
        html_parts.append('<h2>🛠️ 工具更新</h2>')
        for item in d["tool_updates"]:
            html_parts.append(f'<p><strong>{item["title"]}</strong></p>')
            html_parts.append(f'<p>{item["content"]}</p>')
            if item.get("source_urls"):
                links = "、".join(
                    f'<a href="{s["url"]}" target="_blank" rel="noopener">{s["name"]}</a>'
                    for s in item["source_urls"]
                )
                html_parts.append(f'<p class="sources">來源：{links}</p>')
            if item.get("tip"):
                html_parts.append(f'<p class="tip">💡 {item["tip"]}</p>')

    # Trends
    if d.get("trends"):
        html_parts.append('<h2>📈 值得追蹤的趨勢</h2>')
        for item in d["trends"]:
            html_parts.append(f'<p><strong>{item["title"]}</strong></p>')
            html_parts.append(f'<p>{item["content"]}</p>')
            if item.get("tip"):
                html_parts.append(f'<p class="tip">💡 {item["tip"]}</p>')

    # Tips summary
    if d.get("tips_summary"):
        html_parts.append('<h2>💡 應用切角彙整</h2><ul>')
        for tip in d["tips_summary"]:
            html_parts.append(f'<li>{tip}</li>')
        html_parts.append('</ul>')

    if d.get("generated_at"):
        html_parts.append(f'<p class="footer-note">生成時間：{d["generated_at"]}</p>')

    content_html = "\n".join(html_parts)
    content_text = re.sub(r'<[^>]+>', '', content_html).lower()

    return {
        "date": date,
        "title": title,
        "summary": summary,
        "content_html": content_html,
        "content_text": content_text,
        "source": "json",
    }


# ── MD source ──────────────────────────────────────────────────────────────────

def _inline(text: str) -> str:
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    return text

def md_to_html(md: str) -> str:
    lines = md.split("\n")
    html_lines = []
    in_ul = False
    for line in lines:
        if line.startswith("> "):
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<blockquote>{_inline(line[2:])}</blockquote>'); continue
        if line.startswith("# "):
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<h1>{_inline(line[2:])}</h1>'); continue
        if line.startswith("## "):
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<h2>{_inline(line[3:])}</h2>'); continue
        if line.startswith("### "):
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<h3>{_inline(line[4:])}</h3>'); continue
        if re.match(r'^-{3,}$', line.strip()):
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append('<hr>'); continue
        if line.startswith("- "):
            if not in_ul: html_lines.append("<ul>"); in_ul = True
            html_lines.append(f'<li>{_inline(line[2:])}</li>'); continue
        m = re.match(r'^(\d+)\. (.+)', line)
        if m:
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<li>{_inline(m.group(2))}</li>'); continue
        if line.strip() == "":
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(""); continue
        if line.startswith("*") and line.endswith("*"):
            if in_ul: html_lines.append("</ul>"); in_ul = False
            html_lines.append(f'<p class="footer-note">{_inline(line)}</p>'); continue
        if in_ul: html_lines.append("</ul>"); in_ul = False
        html_lines.append(f'<p>{_inline(line)}</p>')
    if in_ul:
        html_lines.append("</ul>")
    return "\n".join(html_lines)

def entry_from_md(filepath: str) -> dict | None:
    m = re.match(r'AI日報_(\d{8})\.md', os.path.basename(filepath))
    if not m:
        return None
    date = datetime.strptime(m.group(1), "%Y%m%d").strftime("%Y-%m-%d")

    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    title_m = re.search(r'^# (.+)', raw, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else f"AI 日報｜{date}"
    summary_m = re.search(r'^> (.+)', raw, re.MULTILINE)
    summary = summary_m.group(1).strip() if summary_m else ""

    content_html = md_to_html(raw)
    content_text = re.sub(r'<[^>]+>', '', content_html).lower()

    return {
        "date": date,
        "title": title,
        "summary": summary,
        "content_html": content_html,
        "content_text": content_text,
        "source": "md",
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    entries: dict[str, dict] = {}

    # 1. Load MD files first (lower priority, local-only)
    if MD_DIR:
        for f in glob.glob(os.path.join(MD_DIR, "AI日報_*.md")):
            entry = entry_from_md(f)
            if entry:
                entries[entry["date"]] = entry

    # 2. Overwrite with JSON files (higher priority, skip manifest.json)
    for f in glob.glob(os.path.join(JSON_DIR, "????????.json")):
        entry = entry_from_json(f)
        if entry:
            entries[entry["date"]] = entry

    sorted_entries = sorted(entries.values(), key=lambda e: e["date"], reverse=True)

    # Remove internal 'source' field before writing
    for e in sorted_entries:
        e.pop("source", None)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(sorted_entries, f, ensure_ascii=False, indent=2)

    json_count = sum(1 for f in glob.glob(os.path.join(JSON_DIR, "????????.json")))
    md_count   = sum(1 for f in glob.glob(os.path.join(MD_DIR, "AI日報_*.md"))) if MD_DIR else 0
    print(f"JSON 來源：{json_count} 篇　MD 來源：{md_count} 篇　合計輸出：{len(sorted_entries)} 篇")
    print(f"→ {OUTPUT}")


if __name__ == "__main__":
    main()
