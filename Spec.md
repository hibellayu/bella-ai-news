# Spec — Bella AI 日報自動化系統 v2

**版本**：1.0
**建立日期**：2026-06-30
**作者**：Bella（黃于芹）
**狀態**：待實作
**依據文件**：PRD.md v1.0、SDD.md v1.0

---

## 變更紀錄

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.0 | 2026-06-30 | 初版建立 |

---

## 執行順序總覽

| 步驟 | 項目 | 執行者 | 預計時間 |
|------|------|--------|----------|
| S1 | 歷史資料遷移 | Luca | 5 分鐘 |
| S2 | 修改 build.py | Luca | 5 分鐘 |
| S3 | 更新 SKILL-daily-digest.md | Luca | 10 分鐘 |
| S4 | 安全性處理（移除硬編碼 Token） | Luca | 5 分鐘 |
| S5 | 設定 GitHub Token 環境變數 | Bella | 5 分鐘 |
| S6 | 建立 Claude Code Remote Trigger | Luca | 5 分鐘 |
| S7 | 驗證第一次雲端執行 | 共同 | 10 分鐘 |

---

## S1｜歷史資料遷移

將 `ai-news-github/digests/` 內所有 JSON 複製進 `bella-ai-news/digests/`。

```bash
mkdir -p /Users/bella2022/Desktop/Bella-Agent/bella-ai-news/digests
cp /Users/bella2022/Desktop/Bella-Agent/ai-news-github/digests/*.json \
   /Users/bella2022/Desktop/Bella-Agent/bella-ai-news/digests/
```

確認檔案數量一致：

```bash
ls /Users/bella2022/Desktop/Bella-Agent/bella-ai-news/digests/ | wc -l
```

---

## S2｜修改 build.py

**目標**：讓 build.py 讀取 repo 內的 `./digests/`，不再依賴本機絕對路徑。

修改 `bella-ai-news/scripts/build.py` 第 14–16 行：

**修改前：**
```python
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
JSON_DIR = os.path.join(BASE, "ai-news-github/digests")
MD_DIR   = os.path.join(BASE, "日報AI新聞動態")
```

**修改後：**
```python
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JSON_DIR = os.path.join(BASE, "digests")
MD_DIR   = os.path.join(BASE, "日報AI新聞動態") if os.path.isdir(
              os.path.join(BASE, "日報AI新聞動態")) else None
```

> 說明：`MD_DIR` 改為條件判斷——本機環境存在此資料夾時正常讀取，雲端環境不存在時自動略過，不報錯。

修改後本機驗證：

```bash
cd /Users/bella2022/Desktop/Bella-Agent/bella-ai-news
python3 scripts/build.py
```

輸出應包含歷史所有筆數，且 `news.json` 正常更新。

---

## S3｜更新 SKILL-daily-digest.md

在 `bella-ai-news/` 建立 `.github/` 資料夾，放入更新版 Skill 檔。

更新重點：
1. 搜尋媒體來源改為 PRD F2 清單（含台灣媒體 + 行銷媒體）
2. 應用切角改為三層格式（What / So What / Now What）
3. 路徑改為雲端相對路徑（`digests/YYYYMMDD.json`）
4. Token 改為環境變數 `$GITHUB_TOKEN`（不寫死）

完整內容：

```markdown
# 每日 AI 新聞日報任務 v2（雲端版）

你是 Bella 的 AI 助理，現在執行每日 AI 新聞日報任務。

## 步驟一：確認日期
```bash
TZ=Asia/Taipei date
```
昨天 = 今天 - 1 天，DATE_KEY 格式為 YYYYMMDD。
DISPLAY_DATE 格式為「YYYY年MM月DD日」。

## 步驟二：Clone repo
```bash
git clone https://$GITHUB_TOKEN@github.com/hibellayu/bella-ai-news.git
cd bella-ai-news
git config user.email "bella.lomo@gmail.com"
git config user.name "Bella AI Bot"
```

## 步驟三：搜尋新聞（WebSearch × 6）
鎖定昨天日期，每組取 2–3 條最有價值的結果：

1. `AI tools update launch [昨日日期] site:techcrunch.com OR site:venturebeat.com OR site:theverge.com`
2. `ChatGPT Claude Gemini Midjourney Suno update [昨日年月]`
3. `AI startup funding investment [昨日日期] site:news.crunchbase.com OR site:venturebeat.com`
4. `AI 數位行銷 內容行銷 自媒體 [昨日年月] site:brain.com.tw OR site:bnext.com.tw OR site:managertoday.com.tw OR site:inside.com.tw`
5. `AI marketing brand content creator tools [昨日日期] site:martech.org OR site:marketingaiinstitute.com`
6. `artificial intelligence major announcement policy regulation [昨日日期]`

篩選標準：
✅ AI 工具新功能／定價、新創融資、數位行銷應用、重大政策
❌ 純學術、軍事、與 AI 無關科技新聞、重複報導

目標：big_news 3–5 條、tool_updates 3–5 條、trends 2–3 條

## 步驟四：生成 JSON

存至 `digests/YYYYMMDD.json`，格式如下：

```json
{
  "date": "YYYY-MM-DD",
  "date_key": "YYYYMMDD",
  "display_date": "YYYY年MM月DD日",
  "summary": "今日精選：N 條 AI 相關動態｜聚焦 [2–3 個關鍵詞]",
  "big_news": [
    {
      "title": "新聞標題",
      "content": "2–3 句摘要",
      "source_urls": [{"name": "來源名稱", "url": "https://..."}],
      "tip": "【What】一句說明對行銷的意義。【So What】對數位行銷競爭格局的影響。【Now What】這週可執行的具體行動。"
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
    "新聞縮寫 → 可執行的行動建議（一句話）"
  ],
  "generated_at": "YYYY-MM-DD 07:00"
}
```

應用切角聚焦順序：
1. 品牌內容策略
2. 社群與自媒體
3. 行銷自動化
4. 數據與分析
5. 職涯與產業定位

## 步驟五：建置與推送
```bash
python3 scripts/build.py
git add digests/ news.json
git commit -m "auto: daily update YYYYMMDD"
git push
```

## 完成確認
輸出：
- ✅ 日報已推送：https://hibellayu.github.io/bella-ai-news/
- 📊 本次蒐集：X 條（大事件 X、工具更新 X、趨勢 X）
- 🕐 生成時間：YYYY-MM-DD 07:00
```

---

## S4｜安全性處理

`push_digest.sh` 內有硬編碼 Token，需移除。

```bash
# 備份後刪除整個檔案（功能已由 Trigger Prompt 取代）
rm /Users/bella2022/Desktop/Bella-Agent/ai-news-github/push_digest.sh
```

若 Token 曾被 commit 進 git 歷史，需確認：

```bash
git -C /Users/bella2022/Desktop/Bella-Agent/bella-ai-news \
  log --all --oneline -- push_digest.sh
```

若有歷史紀錄，需進一步清理（Spec 執行時確認是否需要）。

---

## S5｜設定 GitHub Token 環境變數（Bella 執行）

雲端 session 無法存取 Mac 的 Keychain，Token 必須設定為 Claude Code Remote 環境變數。

**確認現有 Token 有效性：**

```bash
curl -s -H "Authorization: token $(security find-internet-password \
  -s github.com -w 2>/dev/null)" \
  https://api.github.com/user | grep login
```

若回傳 `"login": "hibellayu"` 表示 Token 有效。

**所需 Token 權限：**
- `repo`（完整 repo 讀寫，含 push）

**設定方式：**
在 Claude Code 設定中，將 Token 加入環境變數：
- 變數名稱：`GITHUB_TOKEN`
- 值：現有的 GitHub Personal Access Token

> 具體操作路徑：Claude Code → Settings → Environment Variables → 新增 `GITHUB_TOKEN`

---

## S6｜建立 Claude Code Remote Trigger

由 Luca 執行，建立每日排程觸發器：

```
名稱：bella-ai-news-daily
Cron：0 23 * * *（UTC 23:00 = 台北 07:00）
模式：create_new_session_on_fire = true
通知：email = true
Prompt：S3 中的完整 SKILL 內容
```

建立後確認：
- Trigger ID 記錄至本文件
- 下一次預計觸發時間正確顯示

---

## S7｜驗證第一次雲端執行

建立 Trigger 後，以手動觸發（`fire_trigger`）進行第一次測試：

確認項目：
- [ ] 雲端 session 正常啟動
- [ ] WebSearch 搜尋正常執行（6 組查詢）
- [ ] JSON 格式正確，含三層應用切角
- [ ] build.py 執行無錯誤
- [ ] git push 成功
- [ ] 網頁 https://hibellayu.github.io/bella-ai-news/ 顯示最新日報
- [ ] 日報日期正確（昨天的日期）

---

## 附錄｜Trigger Prompt 完整版

> 存放於 `.github/SKILL-daily-digest.md`，與 S3 內容相同。
> Trigger 觸發時直接使用此檔案內容作為指令。

---

## 後續規劃（v3）

| 功能 | 說明 | 優先度 |
|------|------|--------|
| Line 推播 | 日報生成後推播至 Line Notify | 中 |
| 週報彙整 | 每週日自動生成當週 AI 重點回顧 | 中 |
| 關鍵字監控 | 特定工具（Suno、Midjourney）有重大更新時即時通知 | 低 |
