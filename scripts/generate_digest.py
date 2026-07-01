#!/usr/bin/env python3
"""
Generate daily AI news digest for Bella.
Fetches RSS feeds, filters AI-relevant articles, then uses Claude to analyze and format.
"""
import os, sys, json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import feedparser
import anthropic

TAIPEI = ZoneInfo("Asia/Taipei")

# ── 日期 ────────────────────────────────────────────────────────────────────────

def get_target_date():
    if os.environ.get("TARGET_DATE"):
        d = datetime.strptime(os.environ["TARGET_DATE"], "%Y%m%d").replace(tzinfo=TAIPEI)
    else:
        d = datetime.now(TAIPEI)
    return d.strftime("%Y%m%d"), d.strftime("%Y年%m月%d日"), d.strftime("%Y-%m-%d"), d


# ── RSS 來源（PRD F2）────────────────────────────────────────────────────────────

RSS_FEEDS = [
    # A: 全球 AI & 科技
    ("TechCrunch",          "https://techcrunch.com/feed/"),
    ("VentureBeat",         "https://venturebeat.com/feed/"),
    ("The Verge",           "https://www.theverge.com/rss/index.xml"),
    ("Wired",               "https://www.wired.com/feed/rss"),
    ("Ars Technica",        "https://feeds.arstechnica.com/arstechnica/index"),
    # B: AI 行銷 & 創作者
    ("MarTech",             "https://martech.org/feed/"),
    ("Crunchbase News",     "https://news.crunchbase.com/feed/"),
    # D: 台灣 & 繁中
    ("iThome",              "https://www.ithome.com.tw/rss"),
    ("數位時代",             "https://www.bnext.com.tw/rss"),
    ("INSIDE",              "https://www.inside.com.tw/feed"),
]

AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "llm", "gpt", "claude",
    "gemini", "chatgpt", "openai", "anthropic", "google ai", "meta ai",
    "midjourney", "suno", "generative", "agentic", "copilot", "nvidia",
    "人工智慧", "ai工具", "生成式", "大語言模型", "ai行銷", "大模型",
]


# ── 抓取 RSS ─────────────────────────────────────────────────────────────────────

def fetch_articles(target_date):
    articles = []
    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:40]:
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if not pub:
                    continue
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc).astimezone(TAIPEI)
                if pub_dt.date() != target_date.date():
                    continue
                text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
                if not any(kw in text for kw in AI_KEYWORDS):
                    continue
                articles.append({
                    "source": source_name,
                    "title": entry.get("title", "").strip(),
                    "summary": entry.get("summary", "")[:600].strip(),
                    "url": entry.get("link", ""),
                })
        except Exception as e:
            print(f"  ⚠️  {source_name}: {e}")
    return articles


# ── Claude API 整理 ───────────────────────────────────────────────────────────────

def generate_digest(articles, date_key, display_date, date_iso):
    client = anthropic.Anthropic()

    articles_text = "\n\n".join([
        f"[{i+1}] 來源：{a['source']}\n標題：{a['title']}\n摘要：{a['summary']}\nURL：{a['url']}"
        for i, a in enumerate(articles)
    ])

    system_prompt = """你是 Bella（資深數位行銷與品牌策略專家）的 AI 助理 Luca。
你的任務是將今日 AI 新聞整理成結構化日報 JSON，語言使用繁體中文。

應用切角（tip）必須包含三層，聚焦數位行銷實務：
【What】這個 AI 動態對數位行銷的具體意義
【So What】對競爭格局或行銷作業的影響，誰受影響
【Now What】這週可採取的一個具體行動（不空泛，要可執行）

聚焦優先順序：品牌內容策略 > 社群自媒體 > 行銷自動化 > 數據分析 > 職涯定位

排版：中文與英文之間加半形空格，例如「使用 Claude API」
語氣：自然，像朋友對話，不生硬
避免：「旨在」「總的來說」等冗詞"""

    user_prompt = f"""今天是 {display_date}（台北時間）。
以下是從各 AI 媒體抓取到的昨日新聞，請整理成日報 JSON。

新聞列表：
{articles_text}

請輸出以下 JSON 格式（純 JSON，不要加 markdown code block）：
{{
  "date": "{date_iso}",
  "date_key": "{date_key}",
  "display_date": "{display_date}",
  "summary": "今日精選：N 條 AI 相關動態｜聚焦 [2–3 個關鍵詞]",
  "big_news": [
    {{
      "title": "新聞標題",
      "content": "2–3 句摘要說明",
      "source_urls": [{{"name": "來源名稱", "url": "https://..."}}],
      "tip": "【What】...【So What】...【Now What】..."
    }}
  ],
  "tool_updates": [
    {{
      "title": "工具名稱 — 更新重點",
      "content": "2–3 句更新說明",
      "source_urls": [{{"name": "來源名稱", "url": "https://..."}}],
      "tip": "【What】...【So What】...【Now What】..."
    }}
  ],
  "trends": [
    {{
      "title": "趨勢標題",
      "content": "2–3 句趨勢觀察",
      "tip": "【What】...【So What】...【Now What】..."
    }}
  ],
  "tips_summary": [
    "新聞縮寫 → 可執行的行動建議（具體到這週能做的事）"
  ],
  "generated_at": "{datetime.now(TAIPEI).strftime('%Y-%m-%d %H:%M')}"
}}

要求：big_news 3–5 條、tool_updates 3–5 條、trends 2–3 條
排除：純學術論文、軍事、與 AI 無關科技新聞、重複報導"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()
    # 防禦性處理：移除偶爾出現的 markdown code block
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


# ── Main ──────────────────────────────────────────────────────────────────────────

def main():
    date_key, display_date, date_iso, target_date = get_target_date()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, f"../digests/{date_key}.json")

    if os.path.exists(output_path):
        print(f"⏭️  {date_key}.json 已存在，跳過")
        sys.exit(0)

    print(f"📅 目標日期：{display_date}")
    print(f"📡 抓取 RSS 來源（{len(RSS_FEEDS)} 個）...")
    articles = fetch_articles(target_date)
    print(f"✅ 找到 {len(articles)} 條 AI 相關文章")

    if len(articles) < 3:
        print("⚠️  文章數量不足（< 3 條），嘗試放寬條件...")
        # 放寬：不過濾關鍵字，只過濾日期
        articles = []
        for source_name, url in RSS_FEEDS:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:40]:
                    pub = entry.get("published_parsed") or entry.get("updated_parsed")
                    if not pub:
                        continue
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc).astimezone(TAIPEI)
                    if pub_dt.date() == target_date.date():
                        articles.append({
                            "source": source_name,
                            "title": entry.get("title", "").strip(),
                            "summary": entry.get("summary", "")[:600].strip(),
                            "url": entry.get("link", ""),
                        })
            except Exception:
                pass
        print(f"📡 放寬後找到 {len(articles)} 條文章")

    if len(articles) < 1:
        print("❌ 無法取得任何文章，日報生成中止")
        sys.exit(1)

    print("🤖 呼叫 Claude API 整理日報...")
    digest = generate_digest(articles, date_key, display_date, date_iso)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)

    n_big   = len(digest.get("big_news", []))
    n_tool  = len(digest.get("tool_updates", []))
    n_trend = len(digest.get("trends", []))
    print(f"✅ 日報已儲存：digests/{date_key}.json")
    print(f"📊 大事件 {n_big} 條、工具更新 {n_tool} 條、趨勢 {n_trend} 條")


if __name__ == "__main__":
    main()
