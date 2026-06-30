# PRD — Bella AI 日報自動化系統 v2

**版本**：1.0
**建立日期**：2026-06-30
**作者**：Bella（黃于芹）
**狀態**：已確認，進入 SDD 階段

---

## 一、問題定義

### 現況架構

| 項目 | 說明 |
|------|------|
| 觸發方式 | 手動呼叫 Claude Code Skill（`SKILL-daily-digest.md`） |
| 執行環境 | 本機 Mac |
| 流程 | 搜尋新聞 → 整理 JSON → build.py → git push |
| 核心瓶頸 | **Mac 關機 / 休眠 = 日報停擺**，且每次需人工確認推送 |

### 問題陳述

目前 AI 日報的生成與推送完全依賴本機電腦維持開機狀態，導致假日、外出或電腦休眠時日報無法自動更新。這不符合「LifeOS 自動運行」的設計精神。

---

## 二、目標

> 每日自動彙整 AI 新聞、生成日報、推送至網頁，**全程不依賴 Mac 是否開機**。

### 成功標準

- 每天台北時間 07:00 自動完成更新，無需任何人工操作
- 與現行日報格式（JSON + 網頁閱讀器）完全相容，無需改版前端
- 執行異常時有通知（email 至 bella.lomo@gmail.com）
- 支援手動補跑（可補生成任一日期的日報）

---

## 三、使用者需求

- 早上開電腦，日報已在網頁上自動更新 ✅
- 不需要記得手動觸發 ✅
- 需要時仍可手動補生成（如出差、假日補跑） ✅
- 不想管理複雜的伺服器或額外訂閱服務 ✅

---

## 四、功能需求

| 編號 | 功能 | 說明 |
|------|------|------|
| F1 | 定時觸發 | 每日 07:00 台北時間（UTC+8）自動執行 |
| F2 | 新聞搜尋 | 呼叫搜尋 API，抓取前一天 AI 重點新聞（8–15 條），依媒體來源清單篩選 |
| F3 | AI 彙整生成 | 呼叫 Claude API，依日報格式輸出結構化 JSON，含三層深度應用切角 |
| F4 | 建置 news.json | 執行 `build.py`，合併歷史資料，保持格式一致 |
| F5 | 自動推送 | commit + push 至 `hibellayu/bella-ai-news`，GitHub Pages 網頁即時更新 |
| F6 | 失敗通知 | 執行失敗時寄信通知 `bella.lomo@gmail.com` |
| F7 | 手動補跑 | 支援手動觸發（可指定日期補生成） |

---

## 五、F2 新聞來源定義

### 類別 A｜全球 AI 工具 & 產業（英文，主力來源）

| 媒體 | 網域 | 聚焦方向 |
|------|------|----------|
| TechCrunch | techcrunch.com | AI 新創、工具發布、融資 |
| VentureBeat | venturebeat.com | AI 產業深度、企業應用 |
| The Verge | theverge.com | 消費者向 AI 產品 |
| Wired | wired.com | AI 趨勢、科技文化 |
| MIT Technology Review | technologyreview.com | 技術深度與趨勢預測 |
| Ars Technica | arstechnica.com | 模型研究、開發者向 |

### 類別 B｜AI 行銷 & 創作者（職涯直接相關）

| 媒體 | 網域 | 聚焦方向 |
|------|------|----------|
| MarTech | martech.org | 行銷科技工具更新 |
| Marketing AI Institute | marketingaiinstitute.com | AI 行銷應用案例 |
| Crunchbase News | news.crunchbase.com | 新創融資動態 |

### 類別 C｜原廠官方（第一手資訊）

- OpenAI Blog（openai.com/news）
- Anthropic News（anthropic.com/news）
- Google DeepMind（deepmind.google）
- Meta AI（ai.meta.com）
- Midjourney 公告
- Suno 公告

### 類別 D｜台灣 & 繁中媒體

| 媒體 | 網域 | 聚焦方向 |
|------|------|----------|
| iThome | ithome.com.tw | 台灣 IT 產業 AI 動態 |
| 數位時代 | bnext.com.tw | 台灣新創、行銷科技 |
| INSIDE | inside.com.tw | 台灣科技產業 |
| TNL 媒體人 | thenewslens.com | 深度評論 |
| 經理人月刊 | managertoday.com.tw | 管理、品牌、行銷策略 |
| 動腦雜誌 | brain.com.tw | 廣告、品牌、行銷產業 |

### 篩選規則

**✅ 收錄**
- AI 工具新功能 / 定價變動
- AI 新創融資 / 產品發布
- 數位行銷 AI 應用與案例
- 自媒體創作者 AI 工具
- 重大政策或監管（影響工具可用性）
- 科技股 / AI 產業投資動態

**❌ 排除**
- 純學術論文（無實際應用場景）
- AI 軍事、武器相關
- 與 AI 無直接關聯的科技新聞
- 重複報導同一事件（只取最早或最完整來源）

---

## 六、F3 應用切角品質規格

應用切角（`tip`）是本系統最具差異化的輸出，需聚焦數位行銷面向，提供三層深度洞察：

### 三層結構

| 層次 | 說明 | 範例 |
|------|------|------|
| **What**（這件事是什麼） | 一句話說清楚這個 AI 動態對行銷的意義 | Adobe GenStudio 加入品牌合規審查 |
| **So What**（對數位行銷的影響） | 這代表什麼改變？誰受影響？競爭格局如何演變？ | 內容生產流程中「審查」環節開始被 AI 取代，品牌主對代理商的要求門檻將提高 |
| **Now What**（可採取的行動） | 具體到「這週可以做什麼」的建議，不空泛 | 盤點現有內容審查流程，先從品牌聲音一致性檢查導入 AI，評估節省的審查工時 |

### 應用切角聚焦面向（依優先順序）

1. **品牌內容策略**：AI 如何影響品牌定位、內容創作、聲音一致性
2. **社群與自媒體**：IG / YouTube / LinkedIn 的 AI 工具應用場景
3. **行銷自動化**：AI 代理如何改變行銷作業流程與人力配置
4. **數據與分析**：AI 分析工具對行銷決策的影響
5. **職涯與產業定位**：AI 如何重塑資深行銷人的角色與市場價值

---

## 七、非功能需求

| 項目 | 要求 |
|------|------|
| 基礎設施 | 零自建伺服器，不管理 Docker |
| 費用 | 每月費用可預期，以免費或低固定費用方案優先 |
| 可維護性 | 執行紀錄可查（GitHub Actions log） |
| 時區 | 所有時間戳記使用台北時間（Asia/Taipei, UTC+8） |
| 相容性 | 輸出格式與現行 `build.py` 及網頁閱讀器完全相容 |

---

## 八、範疇外（Out of Scope）

- 網頁前端改版
- 多語言版本
- Line / Telegram 推播（列入 v3 規劃）
- 網頁閱讀器 UI 優化

---

## 九、採用方案

**GitHub Actions + Claude API**

| 項目 | 說明 |
|------|------|
| 排程 | GitHub Actions cron（`0 23 * * *` = UTC 23:00 = 台北 07:00） |
| 新聞搜尋 | Perplexity API 或 Tavily API（支援即時網路搜尋） |
| AI 彙整 | Claude API（`claude-sonnet-4-6`） |
| 儲存庫 | `hibellayu/bella-ai-news`（現有 repo） |
| 費用 | GitHub Actions 免費，API 依用量計費 |

---

## 十、後續階段

| 階段 | 文件 | 狀態 |
|------|------|------|
| 需求定義 | PRD（本文件） | ✅ 完成 |
| 系統設計 | SDD | 進行中 |
| 執行規格 | Spec | 待定 |
| 實作 | GitHub Actions Workflow | 待定 |
