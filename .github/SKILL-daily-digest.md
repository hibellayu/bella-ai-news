# 每日 AI 新聞日報任務 v2（雲端版）

你是 Bella 的 AI 助理，現在執行每日 AI 新聞日報任務。

---

## 步驟一：確認日期

```bash
TZ=Asia/Taipei date
```

昨天 = 今天 - 1 天。DATE_KEY 格式為 YYYYMMDD（昨天）。DISPLAY_DATE 格式為「YYYY年MM月DD日」。

---

## 步驟二：Clone repo

```bash
git clone https://$GITHUB_TOKEN@github.com/hibellayu/bella-ai-news.git
cd bella-ai-news
git config user.email "bella.lomo@gmail.com"
git config user.name "Bella AI Bot"
```

---

## 步驟三：搜尋新聞（WebSearch × 6）

鎖定昨天日期，每組取 2–3 條最有價值的結果：

1. `AI tools update launch [昨日日期] site:techcrunch.com OR site:venturebeat.com OR site:theverge.com`
2. `ChatGPT Claude Gemini Midjourney Suno update [昨日年月]`
3. `AI startup funding investment [昨日日期] site:news.crunchbase.com OR site:venturebeat.com`
4. `AI 數位行銷 內容行銷 自媒體 [昨日年月] site:brain.com.tw OR site:bnext.com.tw OR site:managertoday.com.tw OR site:inside.com.tw`
5. `AI marketing brand content creator tools [昨日日期] site:martech.org OR site:marketingaiinstitute.com`
6. `artificial intelligence major announcement policy regulation [昨日日期]`

篩選標準：
- ✅ AI 工具新功能／定價變動、AI 新創融資、數位行銷 AI 應用、重大政策監管、科技股 AI 投資動態
- ❌ 純學術論文、軍事、與 AI 無關科技新聞、重複報導（只取最早或最完整來源）

目標：big_news 3–5 條、tool_updates 3–5 條、trends 2–3 條

---

## 步驟四：生成 JSON

整理為以下格式，存至 `digests/YYYYMMDD.json`：

```json
{
  "date": "YYYY-MM-DD",
  "date_key": "YYYYMMDD",
  "display_date": "YYYY年MM月DD日",
  "summary": "今日精選：N 條 AI 相關動態｜聚焦 [2–3 個關鍵詞]",
  "big_news": [
    {
      "title": "新聞標題",
      "content": "2–3 句摘要說明",
      "source_urls": [{"name": "來源名稱", "url": "https://..."}],
      "tip": "【What】這個 AI 動態對數位行銷的具體意義。【So What】對競爭格局或行銷作業的影響是什麼、誰受影響。【Now What】這週可以採取的一個具體行動（不空泛）。"
    }
  ],
  "tool_updates": [
    {
      "title": "工具名稱 — 更新重點",
      "content": "2–3 句更新說明",
      "source_urls": [{"name": "來源名稱", "url": "https://..."}],
      "tip": "【What】【So What】【Now What】三層洞察，聚焦數位行銷實務。"
    }
  ],
  "trends": [
    {
      "title": "趨勢標題",
      "content": "2–3 句趨勢觀察",
      "tip": "【What】【So What】【Now What】三層洞察。"
    }
  ],
  "tips_summary": [
    "新聞縮寫 → 可執行的行動建議（一句話，具體到這週能做的事）"
  ],
  "generated_at": "YYYY-MM-DD 07:00"
}
```

應用切角聚焦優先順序：
1. 品牌內容策略（AI 如何影響品牌定位、內容創作、聲音一致性）
2. 社群與自媒體（IG / YouTube / LinkedIn 工具應用場景）
3. 行銷自動化（AI 代理如何改變行銷作業流程與人力配置）
4. 數據與分析（AI 分析工具對行銷決策的影響）
5. 職涯與產業定位（AI 如何重塑資深行銷人的角色與市場價值）

---

## 步驟五：建置與推送

```bash
python3 scripts/build.py
git add digests/ news.json
git commit -m "auto: daily update YYYYMMDD"
git push
```

---

## 完成確認

輸出以下訊息：

```
✅ 日報已推送：https://hibellayu.github.io/bella-ai-news/
📊 本次蒐集：X 條新聞（大事件 X 條、工具更新 X 條、趨勢 X 條）
🕐 生成時間：YYYY-MM-DD 07:00
```
