# SDD — Bella AI 日報自動化系統 v2

**版本**：1.0
**建立日期**：2026-06-30
**作者**：Bella（黃于芹）
**狀態**：已確認，進入 Spec 階段
**依據文件**：PRD.md

---

## 一、現有架構問題

```
本機 Mac（必須開機）
  └── ai-news-github/digests/   ← 本地資料夾，非 git repo
  └── 日報AI新聞動態/            ← 本地資料夾，非 git repo
  └── bella-ai-news/            ← ✅ git repo（hibellayu/bella-ai-news）
        └── scripts/build.py    ← 讀取上兩層本地路徑，雲端無法使用
```

雲端 session 無法存取本機路徑，必須將架構改為**單一 repo 自給自足**。

---

## 二、目標架構

```
Claude Code Remote（雲端，每日 07:00 台北時間自動觸發）
  ↓
  clone hibellayu/bella-ai-news
  ↓
  WebSearch（6 組查詢，依 PRD 媒體來源清單）
  ↓
  Claude 整理 → 生成 digests/YYYYMMDD.json
  ↓
  python3 scripts/build.py → 更新 news.json
  ↓
  git commit + push
  ↓
  GitHub Pages 自動更新（網頁即時可見）
```

Mac 完全不在流程中。

---

## 三、Repo 結構調整

### 現行結構

```
bella-ai-news/
  index.html
  news.json
  PRD.md
  scripts/
    build.py
    auto_update.sh
```

### 調整後結構

```
bella-ai-news/
  index.html
  news.json
  PRD.md
  SDD.md
  digests/                      ← 新增，從 ai-news-github/digests/ 遷移
    20260624.json
    20260625.json
    20260627.json
    20260629.json
    20260630.json
    manifest.json
  scripts/
    build.py                    ← 修改讀取路徑，改為 repo 內相對路徑
    auto_update.sh
  .github/
    SKILL-daily-digest.md       ← 移入 repo，雲端 session 可讀取
```

---

## 四、build.py 路徑修改

### 現行（讀本機絕對路徑，雲端不可用）

```python
BASE     = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
JSON_DIR = os.path.join(BASE, "ai-news-github/digests")
MD_DIR   = os.path.join(BASE, "日報AI新聞動態")
```

### 修改後（讀 repo 內相對路徑）

```python
BASE     = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JSON_DIR = os.path.join(BASE, "digests")
MD_DIR   = None  # 雲端不產生 MD 備份；本機手動補跑時可選擇性輸出
```

---

## 五、Claude Code Remote Trigger 設計

### 排程設定

| 項目 | 設定值 |
|------|--------|
| Cron expression | `0 23 * * *` |
| 對應時間 | UTC 23:00 = 台北時間 07:00 |
| 模式 | `create_new_session_on_fire: true`（每次開新 session） |
| 失敗通知 | `email: true`（寄至 bella.lomo@gmail.com） |

### Trigger Prompt

觸發時發送給雲端 session 的完整指令：

```
你是 Bella 的 AI 助理，現在執行每日 AI 新聞日報任務。

## 步驟一：確認日期
執行 `date` 確認今天台北時間（Asia/Taipei）。
昨天 = 今天 - 1 天，DATE_KEY 格式為 YYYYMMDD（昨天）。

## 步驟二：clone repo
```bash
git clone https://[GITHUB_TOKEN]@github.com/hibellayu/bella-ai-news.git
cd bella-ai-news
```

## 步驟三：搜尋新聞（WebSearch）
依序執行以下 6 組搜尋，鎖定昨天日期，每組取 2–3 條最有價值的結果：

1. AI tools update launch [昨日日期] site:techcrunch.com OR site:venturebeat.com OR site:theverge.com
2. ChatGPT Claude Gemini Midjourney Suno update [昨日年月]
3. AI startup funding investment [昨日日期] site:news.crunchbase.com OR site:venturebeat.com
4. AI 數位行銷 內容行銷 自媒體 [昨日年月] site:brain.com.tw OR site:bnext.com.tw OR site:managertoday.com.tw OR site:inside.com.tw
5. AI marketing brand content creator tools [昨日日期] site:martech.org OR site:marketingaiinstitute.com
6. artificial intelligence major announcement policy regulation [昨日日期]

篩選標準（PRD F2）：
✅ AI 工具新功能／定價變動、AI 新創融資、數位行銷 AI 應用、重大政策監管
❌ 純學術論文、軍事、與 AI 無關科技新聞、重複報導

## 步驟四：生成 JSON（PRD F3 三層應用切角）
整理為標準格式，每條 tip 須包含三層：
- What：這個 AI 動態對行銷的具體意義
- So What：對數位行銷競爭格局的影響
- Now What：這週可執行的具體行動（不空泛）

聚焦順序：品牌內容策略 > 社群自媒體 > 行銷自動化 > 數據分析 > 職涯定位

存至：digests/YYYYMMDD.json

## 步驟五：建置與推送
```bash
python3 scripts/build.py
git add digests/ news.json
git commit -m "auto: daily update YYYYMMDD"
git push
```

完成後輸出：
✅ 日報已推送：https://hibellayu.github.io/bella-ai-news/
📊 本次蒐集：X 條新聞（大事件 X、工具更新 X、趨勢 X）
🕐 生成時間：YYYY-MM-DD 07:00
```

---

## 六、資料流（Data Flow）

```
[每日 UTC 23:00]
    │
    ▼
Claude Code Remote Trigger 觸發
    │
    ▼
新 Cloud Session 啟動
    │
    ├── date → 確認昨日 DATE_KEY
    │
    ├── git clone bella-ai-news
    │
    ├── WebSearch × 6 組查詢
    │       └── 篩選 8–15 條有效新聞
    │
    ├── Claude 整理 → digests/YYYYMMDD.json
    │       └── big_news / tool_updates / trends / tips_summary
    │
    ├── python3 scripts/build.py
    │       └── 讀 digests/*.json → 輸出 news.json
    │
    └── git commit + push
            │
            ├── ✅ 成功 → GitHub Pages 更新，網頁即時可見
            └── ❌ 失敗 → email 通知 bella.lomo@gmail.com
```

---

## 七、錯誤處理

| 情境 | 處理方式 |
|------|----------|
| 搜尋結果不足（< 5 條） | 重試第 1、6 組查詢，仍不足則記錄並繼續 |
| JSON 格式錯誤 | build.py 自動跳過，不影響歷史資料 |
| git push 失敗 | Trigger 標記失敗，觸發 email 通知 |
| Session 整體失敗 | `email: true` 自動寄信告知 |

---

## 八、手動補跑

| 方式 | 說明 |
|------|------|
| 本機 Claude Code 對話 | 直接執行 Skill，指定日期，流程同現行（適合需要微調的情況） |
| Trigger 即時觸發 | `fire_trigger` 加上補跑日期作為額外訊息，全自動補生成 |

---

## 九、安全性

| 項目 | 處理方式 |
|------|----------|
| GitHub Token | 存為 Claude Code Remote 環境變數（Secrets），不寫入任何檔案 |
| 硬編碼 Token | `push_digest.sh` 內現有 `ghp_...` 需在 Spec 階段移除並清理 git 歷史 |
| 公開 repo | `digests/*.json` 內容為公開新聞摘要，無隱私疑慮 |

---

## 十、遷移步驟摘要

| 順序 | 動作 | 說明 |
|------|------|------|
| 1 | 將 `ai-news-github/digests/*.json` 複製進 `bella-ai-news/digests/` | 歷史資料遷移 |
| 2 | 修改 `scripts/build.py` 路徑 | 改讀本地 `./digests/` |
| 3 | 將 `SKILL-daily-digest.md` 更新後移入 `.github/` | 雲端 session 可讀取 |
| 4 | 建立 Claude Code Remote Trigger | 設定 cron + email 通知 |
| 5 | 移除 `push_digest.sh` 內硬編碼 Token | 安全性處理 |
| 6 | 第一次雲端自動執行驗證 | 確認全流程正常 |

---

## 十一、後續階段

| 階段 | 文件 | 狀態 |
|------|------|------|
| 需求定義 | PRD.md | ✅ 完成 |
| 系統設計 | SDD.md（本文件） | ✅ 完成 |
| 執行規格 | Spec.md | 進行中 |
| 實作 | — | 待定 |
