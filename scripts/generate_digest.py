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
    """
    display_d = 日報名稱（生成當日，filename / header 用）
    data_d    = 資料收集範圍（D-1，文章篩選用）
    """
    if os.environ.get("TARGET_DATE"):
        display_d = datetime.strptime(os.environ["TARGET_DATE"], "%Y%m%d").replace(tzinfo=TAIPEI)
    else:
        display_d = datetime.now(TAIPEI)
    data_d = display_d - timedelta(days=1)
    return (
        display_d.strftime("%Y%m%d"),       # date_key
        display_d.strftime("%Y年%m月%d日"),  # display_date
        display_d.strftime("%Y-%m-%d"),      # date_iso
        data_d,                              # target_date（文章篩選）
        data_d.strftime("%Y-%m-%d"),         # data_date_iso（顯示用）
    )


# ── RSS 來源（PRD F2）────────────────────────────────────────────────────────────

RSS_FEEDS = [
    # A: 全球 AI & 科技
    ("TechCrunch",          "https://techcrunch.com/feed/"),
    ("VentureBeat",         "https://venturebeat.com/feed/"),
    ("The Verge",           "https://www.theverge.com/rss/index.xml"),
    ("Wired",               "https://www.wired.com/feed/rss"),
    ("Ars Technica",        "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Decoder",         "https://the-decoder.com/feed/"),
    ("AI News",             "https://www.artificialintelligence-news.com/feed/"),
    # B: AI 行銷 & 創作者
    ("MarTech",             "https://martech.org/feed/"),
    ("Crunchbase News",     "https://news.crunchbase.com/feed/"),
    ("Marketing AI Institute", "https://www.marketingaiinstitute.com/blog/rss.xml"),
    # C: SEO / 搜尋 / 社群（行銷通路專業媒體）
    ("Search Engine Land",     "https://searchengineland.com/feed"),
    ("Search Engine Roundtable", "https://www.seroundtable.com/index.rdf"),
    ("Social Media Today",     "https://www.socialmediatoday.com/feeds/news/"),
    # E: AI 影音／創作工具（2026-08-21 新增，補 Seedance 等生成式影音工具覆蓋率不足的缺口）
    ("No Film School",      "https://nofilmschool.com/rss.xml"),
    ("量子位",               "https://www.qbitai.com/feed"),
    # D: 台灣 & 繁中
    ("iThome",              "https://www.ithome.com.tw/rss"),
    ("科技新報",             "https://technews.tw/category/ai/feed/"),
    ("AI郵報",              "https://www.aiposthub.com/feed/"),
    # 數位時代、INSIDE 官方 RSS 已停用（2026-08-19 確認：數位時代 /rss 直接回傳網站首頁 HTML，
    # INSIDE 所有已知 RSS 路徑皆回 403）。改用 Google News 站內搜尋代理取得內容——
    # 代價是 source_urls 連結會先進 Google News 中繼頁、摘要也幾乎是空的，只有標題可參考。
    # 若日後官方 RSS 復活，優先換回官方來源。
    ("數位時代",             "https://news.google.com/rss/search?q=site:bnext.com.tw+AI&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ("INSIDE",              "https://news.google.com/rss/search?q=site:inside.com.tw+AI&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
]

# 內容角度分類（供選稿配額使用，避免產業新聞獨佔版面）
CONTENT_ANGLES = {
    "industry":          "產業 / 模型 / 算力 / 監管",
    "brand":             "品牌能見度 / 信任 / AI 搜尋",
    "workflow":          "深度工作者、行銷人、內容工作流",
    "consumer":          "一般大眾、手機、語音、教育、客服、隱私",
    "marketing_channel": "SEO、內容、社群、廣告、CRM、MarTech",
}

# 固定標籤池——每則新聞的 tags 必須從這裡選，不可另造新詞，避免同義詞每天各寫各的
# （例如「行銷科技」「AI 工具生態」「企業工具採購」其實是同一件事，卻拆成三個標籤）。
CONTENT_TAGS = [
    "AI 政策法規", "AI 產業佈局", "算力基礎建設", "AI 安全風險",
    "品牌信任危機", "AI 搜尋能見度", "品牌溝通策略",
    "AI 工作流風險", "行銷自動化", "職涯發展定位", "團隊協作規範",
    "使用者隱私", "AI 使用習慣", "消費者信任",
    "SEO 策略", "內容行銷", "社群內容策略", "媒體廣告投放", "行銷科技採購",
]

AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "llm", "gpt", "claude",
    "gemini", "chatgpt", "openai", "anthropic", "google ai", "meta ai",
    "midjourney", "suno", "generative", "agentic", "copilot", "nvidia",
    # AI 影音／創作工具品牌名——沒有這些的話，標題沒寫「AI」兩字的影音工具新聞會被濾掉
    "sora", "runway", "pika", "kling", "seedance", "veo", "heygen", "luma",
    "elevenlabs", "hailuo", "vidu",
    "人工智慧", "ai工具", "生成式", "大語言模型", "ai行銷", "大模型",
    "人工智能",  # 簡體中文用語，補齊量子位等中國來源
]


# ── 抓取 RSS ─────────────────────────────────────────────────────────────────────

import re as _re

def clean_summary(raw_summary, title):
    """去掉 RSS 摘要裡的 HTML 標籤；若摘要其實只是重複標題（Google News 代理常見情況），
    回傳空字串，讓下游明確知道「這則沒有真正的摘要」，而不是塞一堆沒用的 HTML 進 prompt。"""
    text = _re.sub(r"<[^>]+>", " ", raw_summary or "")
    text = _re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    # Google News 代理的摘要幾乎都是「標題 + 來源名」，跟標題高度重疊時視同無摘要
    if title and (text.startswith(title[:20]) or title[:20] in text[:60]):
        return ""
    return text[:600]


def fetch_articles(target_date):
    articles = []
    for source_name, url in RSS_FEEDS:
        raw_count = matched_count = 0
        try:
            feed = feedparser.parse(url)
            raw_count = len(feed.entries)
            if getattr(feed, "bozo", 0) and raw_count == 0:
                # feedparser 對連線/格式錯誤通常不丟例外，只會回傳空 entries，
                # 沒有這行的話來源掛掉會完全無聲無息（我們已經踩過這個坑一次）。
                print(f"  ⚠️  {source_name}: feed 解析失敗或無內容（{feed.bozo_exception if hasattr(feed, 'bozo_exception') else 'unknown'}）")
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
                matched_count += 1
                title = entry.get("title", "").strip()
                articles.append({
                    "source": source_name,
                    "title": title,
                    "summary": clean_summary(entry.get("summary", ""), title),
                    "url": entry.get("link", ""),
                })
        except Exception as e:
            print(f"  ⚠️  {source_name}: {e}")
        print(f"  · {source_name}：抓到 {raw_count} 篇，符合日期+關鍵字 {matched_count} 篇")
    return articles


# ── 內容角度分類與配額選稿 ────────────────────────────────────────────────────────
# 目的：避免「產業重大新聞」把版面全部吃掉，確保行銷工作流、SEO/內容/社群/廣告、
# 使用者端／大眾使用情境每天都有名額，而不是靠 prompt 期望 Claude 自己平衡。

POOL_SIZE = 22
MIN_PER_ANGLE = {"industry": 4, "brand": 3, "workflow": 3, "consumer": 3, "marketing_channel": 4}
MAX_INDUSTRY_SHARE = 0.4  # industry 角度最多佔選稿池 40%（有下限也要有上限，避免兩極化）

_RELEVANCE_ORDER = {"high": 0, "medium": 1, "low": 2}


def classify_articles(client, articles):
    """幫每篇候選新聞標記 content_angle 與 marketing_relevance，供配額選稿使用。"""
    listing = "\n".join(
        f"[{i+1}] 來源：{a['source']}｜標題：{a['title']}｜摘要開頭：{a['summary'][:120]}"
        for i, a in enumerate(articles)
    )
    angle_desc = "\n".join(f"- {k}：{v}" for k, v in CONTENT_ANGLES.items())

    system_prompt = f"""你是內容編輯助理，任務是幫每篇候選新聞標記「內容角度」與「行銷相關度」，
只需要分類，不要摘要、不要判讀。

內容角度（content_angle，每篇選最貼切的 1 個）：
{angle_desc}

行銷相關度（marketing_relevance）：
- high：對數位行銷人／品牌決策直接有參考價值
- medium：有間接關聯，值得留意
- low：關聯薄弱（純學術、純財報數字、與行銷完全無關的產業八卦）

輸出純 JSON 陣列（不要 markdown code block），格式：
[{{"i": 1, "angle": "industry", "relevance": "high"}}, ...]
陣列長度必須跟候選新聞數量一致，i 對應候選新聞的編號。"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": f"候選新聞：\n{listing}"}],
    )
    raw = message.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    parsed = json.loads(raw)
    labels = {item["i"]: item for item in parsed if "i" in item}

    # 防禦：回應被截斷或漏標會讓部分新聞靜默套用預設角度，稀釋配額的準確性——
    # 與其這樣，不如直接判定分類失敗，讓外層 fallback 改用全部候選新聞（不做配額）。
    missing = len(articles) - len(labels)
    if missing > 0:
        raise ValueError(f"分類結果只有 {len(labels)}/{len(articles)} 篇，可能被截斷")

    for i, a in enumerate(articles, start=1):
        label = labels[i]
        a["angle"] = label.get("angle", "industry")
        a["relevance"] = label.get("relevance", "medium")
    return articles


def select_balanced_pool(articles, pool_size=POOL_SIZE):
    """依內容角度配額，從已分類的候選新聞中選出平衡的選稿池給寫作階段使用。"""
    by_angle: dict[str, list[dict]] = {}
    for a in articles:
        by_angle.setdefault(a.get("angle", "industry"), []).append(a)
    for group in by_angle.values():
        group.sort(key=lambda a: _RELEVANCE_ORDER.get(a.get("relevance", "medium"), 1))

    selected: list[dict] = []
    selected_ids = set()

    def take(a):
        if id(a) not in selected_ids:
            selected.append(a)
            selected_ids.add(id(a))

    # 1) 保底：非產業角度先保留名額
    for angle, min_n in MIN_PER_ANGLE.items():
        for a in by_angle.get(angle, [])[:min_n]:
            take(a)

    # 2) 依相關度補滿剩餘名額，industry 角度設上限避免獨佔
    industry_cap = int(pool_size * MAX_INDUSTRY_SHARE)
    industry_count = sum(1 for a in selected if a.get("angle") == "industry")
    remaining = sorted(
        (a for a in articles if id(a) not in selected_ids),
        key=lambda a: _RELEVANCE_ORDER.get(a.get("relevance", "medium"), 1),
    )
    for a in remaining:
        if len(selected) >= pool_size:
            break
        if a.get("angle") == "industry":
            if industry_count >= industry_cap:
                continue
            industry_count += 1
        take(a)

    # 3) 名額還沒滿（角度不足以填滿），放寬 industry 上限補齊
    if len(selected) < pool_size:
        for a in remaining:
            if len(selected) >= pool_size:
                break
            take(a)

    return selected


# ── Claude API 整理 ───────────────────────────────────────────────────────────────

def generate_digest(client, articles, date_key, display_date, date_iso, data_date_iso):
    angle_label = lambda a: CONTENT_ANGLES.get(a.get("angle", "industry"), a.get("angle", ""))
    articles_text = "\n\n".join([
        f"[{i+1}] 來源：{a['source']}｜內容角度：{a.get('angle', 'industry')}（{angle_label(a)}）"
        f"｜行銷相關度：{a.get('relevance', 'medium')}\n"
        f"標題：{a['title']}\n摘要：{a['summary']}\nURL：{a['url']}"
        for i, a in enumerate(articles)
    ])
    tag_pool = "、".join(CONTENT_TAGS)

    system_prompt = f"""你是一位擁有 15 年以上經驗的資深數位行銷與品牌策略專家，品牌方與代理商都待過，
看過從 SEO、社群、短影音到 AI 好幾輪的平台典範轉移。你在幫 Bella 整理「AI 日報」，
但這不是新聞轉述，是你自己的專業判讀——讀者要看到的是「一個資深行銷人怎麼看這件事」，
不是新聞摘要的再包裝。寫的時候把自己當成正在跟後輩或客戶開會，直接講重話、講立場，
不要各打五十大板、不要用「這是一把雙面刃」這種安全牌講法。

選稿已經先依內容角度（industry／brand／workflow／consumer／marketing_channel）配好額度給你，
每篇候選新聞前面都標了角度與行銷相關度——寫的時候要對應著角度寫，不要每則都寫成「產業新聞」的語氣。
角度不是拿來重述用的標籤，是提醒你這則新聞該從哪個行銷人會關心的切角下手。

候選新聞數量超過各欄位可發布名額時，選文優先順序固定是：
1. 先看「行銷相關度」，high 優先於 medium，medium 優先於 low
2. 相關度相同時，才比事件本身的重要性／時效性
也就是說，一則行銷相關度 high 的小型工具更新，要優先於一則行銷相關度 low 的重大產業新聞——
除非該產業新聞剛好落在「big_news 至少 1–2 條 industry」的底線內。

有些候選新聞（標記來源為數位時代、INSIDE）摘要是空的，只有標題可以參考——這是資料來源限制，
不是要你憑空腦補。遇到摘要是空的新聞：
- 如果你自己知道這則新聞在講什麼（是你本來就掌握的真實事件），可以照常寫判讀
- 如果標題資訊量不足以支撐一段有實質內容的判讀，不要硬寫、不要編造標題沒提到的細節，
  寧可不選這則，換選有完整摘要、能寫出具體判讀的候選新聞

判讀的核心立場，永遠是這一句：這則 AI 新聞代表外部環境變了，所以行銷人要重新理解
品牌入口、內容被引用方式、工具採購、社群互動、工作流與使用者習慣——
而不是只停在「某公司推出模型／某平台競爭升級／某產業投資增加」就結束。
每則判讀寫完後自己檢查：這段有沒有連到行銷人真正要做的事，還是只是在轉述誰做了什麼。

應用切角（tip）必須包含三層：
【What】不是重述新聞內容，是點出這則新聞底層在動搖行銷人習以為常的哪個假設
（例如「AI 算力無限供應」「內容原創性天生稀缺」這類前提）
【So What】站在資深行銷人的立場給判斷：誰會贏、誰會輸、什麼樣的品牌或團隊現在最危險、
什麼樣的反而有機會——要有具體畫面感，不要寫「需要留意」「值得關注」這種沒有立場的話
【Now What】一個可行的具體小行動（不空泛、不用指定時間，要可執行）

避免的寫法（AI 味太重、沒有觀點）：
- 「品牌需要重新評估」「行銷人應該關注」「值得留意的是」這類沒有立場的安全語句
- 把 So What 寫成 What 的同義句重複
- 每則語氣都一樣、沒有輕重之分——真正關鍵的新聞，語氣可以更重、更直接

每則新聞（big_news / tool_updates / trends）都要附上 tags：剛好從下面這個固定標籤池選 2 個，
不可以自己另外造詞（就算池子裡的詞不是最精準的形容，也要選最接近的，不要新創同義詞）：
{tag_pool}
這個池子每天都一樣，是為了讓讀者依主題篩選時，同類新聞會累積在同一個標籤下，而不是被
「行銷科技」「AI 工具生態」「企業工具採購」這種意思相同但用詞不同的標籤拆散。

trends（趨勢觀察）也要附上 source_urls，即使一則趨勢是跨好幾篇新聞歸納出來的觀察，也要把
內文裡實際點名引用的來源都列出來（可以不只一個）——讀者要能點連結回頭查證你講的是哪幾則新聞，
不能寫了「今天同時有三則新聞指向同一個結構」卻不給那三則新聞的連結。

除了逐則判讀，還要做一次「應用切角彙整」（applications）：跳脫個別新聞，用資深行銷人的視角，
把今天所有動態放在一起看，從六個固定面向分別給一段判讀（每段 80–120 字）：
品牌策略、數位行銷、內容行銷、社群應用、媒體廣告、團隊流程。
每段寫法：
1. 先講今天這批新聞讓這個面向出現了什麼結構性變化——是提煉跨新聞的共同訊號，不是重述新聞
2. 再給一個具體、小範圍、可以馬上開始的起手動作，量詞要具體（例如「從 1 個主力產品頁開始…」）
若某個面向今天沒有直接相關動態，仍要從既有 AI 產業脈絡誠實延伸判斷，不要留空、也不要硬掰。

聚焦優先順序：品牌內容策略 > 社群自媒體 > 行銷自動化 > 數據分析 > 職涯定位

排版：中文與英文之間加半形空格，例如「使用 Claude API」
語氣：自然、像朋友對話但有主見，不生硬、不打安全牌
避免：「旨在」「總的來說」等冗詞"""

    user_prompt = f"""今天是 {display_date}（台北時間）。
以下是從各 AI 媒體抓取到的昨日（{data_date_iso}）新聞，請整理成日報 JSON。

新聞列表：
{articles_text}

請輸出以下 JSON 格式（純 JSON，不要加 markdown code block）：
{{
  "date": "{date_iso}",
  "date_key": "{date_key}",
  "display_date": "{display_date}",
  "data_date": "{data_date_iso}",
  "summary": "今日精選：N 條 AI 相關動態｜聚焦 [2–3 個關鍵詞]",
  "big_news": [
    {{
      "title": "新聞標題",
      "content": "2–3 句摘要說明",
      "source_urls": [{{"name": "來源名稱", "url": "https://..."}}],
      "tags": ["主題標籤1", "主題標籤2"],
      "angle": "industry | brand | workflow | consumer | marketing_channel",
      "tip": "【What】...【So What】...【Now What】..."
    }}
  ],
  "tool_updates": [
    {{
      "title": "工具名稱 — 更新重點",
      "content": "2–3 句更新說明",
      "source_urls": [{{"name": "來源名稱", "url": "https://..."}}],
      "tags": ["主題標籤1", "主題標籤2"],
      "angle": "industry | brand | workflow | consumer | marketing_channel",
      "tip": "【What】...【So What】...【Now What】..."
    }}
  ],
  "trends": [
    {{
      "title": "趨勢標題",
      "content": "2–3 句趨勢觀察",
      "source_urls": [{{"name": "來源名稱", "url": "https://..."}}],
      "tags": ["主題標籤1", "主題標籤2"],
      "angle": "industry | brand | workflow | consumer | marketing_channel",
      "tip": "【What】...【So What】...【Now What】..."
    }}
  ],
  "tips_summary": [
    "新聞縮寫 → 可執行的具體行動建議（不用指定時間）"
  ],
  "applications": [
    {{"dimension": "品牌策略", "content": "80–120 字，跨新聞的結構性變化＋具體起手動作"}},
    {{"dimension": "數位行銷", "content": "同上"}},
    {{"dimension": "內容行銷", "content": "同上"}},
    {{"dimension": "社群應用", "content": "同上"}},
    {{"dimension": "媒體廣告", "content": "同上"}},
    {{"dimension": "團隊流程", "content": "同上"}}
  ],
  "generated_at": "{datetime.now(TAIPEI).strftime('%Y-%m-%d %H:%M')}"
}}

要求：big_news 3–5 條（其中至少 1–2 條要是 industry 角度——產業重大新聞仍然要保留代表性，
不能因為想強調行銷觀點就把它排除）、tool_updates 3–5 條、trends 2–3 條、
applications 固定 6 條（六個面向都要有）
排除：純學術論文、軍事、與 AI 無關科技新聞、重複報導"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()
    # 防禦性處理：移除偶爾出現的 markdown code block
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


# ── Main ──────────────────────────────────────────────────────────────────────────

def main():
    date_key, display_date, date_iso, target_date, data_date_iso = get_target_date()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, f"../digests/{date_key}.json")

    if os.path.exists(output_path):
        print(f"⏭️  {date_key}.json 已存在，跳過")
        sys.exit(0)

    print(f"📅 日報日期：{display_date}｜資料收集：{data_date_iso}")
    print(f"📡 抓取 RSS 來源（{len(RSS_FEEDS)} 個）...")
    articles = fetch_articles(target_date)
    print(f"✅ 找到 {len(articles)} 條 AI 相關文章")

    if len(articles) < 3:
        print("⚠️  文章數量不足（< 3 條），嘗試放寬條件...")
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
                        title = entry.get("title", "").strip()
                        articles.append({
                            "source": source_name,
                            "title": title,
                            "summary": clean_summary(entry.get("summary", ""), title),
                            "url": entry.get("link", ""),
                        })
            except Exception:
                pass
        print(f"📡 放寬後找到 {len(articles)} 條文章")

    if len(articles) < 1:
        print("❌ 無法取得任何文章，日報生成中止")
        sys.exit(1)

    client = anthropic.Anthropic()

    print("🏷️  幫候選新聞標記內容角度（industry/brand/workflow/consumer/marketing_channel）...")
    try:
        articles = classify_articles(client, articles)
        pool = select_balanced_pool(articles)
        angle_counts = {}
        for a in pool:
            angle_counts[a["angle"]] = angle_counts.get(a["angle"], 0) + 1
        print(f"📊 選稿池 {len(pool)} 篇（原始 {len(articles)} 篇）｜角度分佈：{angle_counts}")
    except Exception as e:
        print(f"  ⚠️  角度分類失敗（{e}），改用全部候選新聞")
        pool = articles

    print("🤖 呼叫 Claude API 整理日報...")
    digest = generate_digest(client, pool, date_key, display_date, date_iso, data_date_iso)

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
