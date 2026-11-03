#!/usr/bin/env python3
"""AI News Radar - AI 전처리 스크립트 (no_agent)
pending 항목 중 AI 처리가 안 된 것을 추출해서 JSON으로 출력.
배달 크론의 context_from으로 사용."""
import json, os, sys
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(BASE_DIR, "queue.json")
KST = timezone(timedelta(hours=9))
MAX_PROCESS = 30

def main():
    with open(QUEUE_FILE) as f:
        queue = json.load(f)

    today = datetime.now(KST).strftime("%Y-%m-%d")
    pending = [d for d in queue if d.get("status") == "pending" and d.get("collected_at", "").startswith(today)]
    unprocessed = [d for d in pending if not d.get("ai_processed")]
    batch = unprocessed[:MAX_PROCESS]

    if not batch:
        return  # silent

    # AI 처리할 항목 구성
    items = []
    for d in batch:
        items.append({
            "idx": len(items),
            "title": d.get("title", ""),
            "description": d.get("description", "")[:200],
            "source": d.get("source_name", ""),
            "url": d.get("url", "")
        })

    print(f"AI_PROCESS_NEEDED: {len(items)}건")
    print(json.dumps(items, ensure_ascii=False))

if __name__ == "__main__":
    main()
