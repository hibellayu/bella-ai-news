#!/bin/bash
# 每日自動更新 bella-ai-news
# 由 cron 排程呼叫：每天 08:00 執行

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$HOME/.bella-ai-news-update.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') ── 開始更新" >> "$LOG"

cd "$REPO_DIR" || exit 1

python3 scripts/build.py >> "$LOG" 2>&1

git add news.json >> "$LOG" 2>&1

if git diff --staged --quiet; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') ── 沒有新內容，略過 push" >> "$LOG"
  exit 0
fi

git commit -m "auto: daily update $(date '+%Y-%m-%d')" >> "$LOG" 2>&1
git push >> "$LOG" 2>&1 && \
  echo "$(date '+%Y-%m-%d %H:%M:%S') ── push 成功" >> "$LOG" || \
  echo "$(date '+%Y-%m-%d %H:%M:%S') ── push 失敗" >> "$LOG"
