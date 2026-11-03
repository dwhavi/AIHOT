#!/usr/bin/env python3
"""AI News Radar 배달 스크립트 - no_agent용
AI 처리 결과(카테고리/요약/중요도)를 반영하여 배달."""
import json, os, sys, re
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(BASE_DIR, "queue.json")
KST = timezone(timedelta(hours=9))

# 중요도별 이모지
IMPORTANCE_EMOJI = {"high": "🔴", "mid": "🟡", "low": "⚪"}

MARKET_FILE_HINT = os.path.join(os.path.expanduser("~"), ".hermes", "cron", "output", "d9f081ba07c0")

def load_market_data():
    """당일 시장 데이터 수집 크론 출력에서 코스피/코스닥 읽기. 없으면 None."""
    try:
        today = datetime.now(KST).strftime("%Y-%m-%d")
        d = os.path.join(MARKET_FILE_HINT)
        if not os.path.isdir(d):
            return None
        cands = sorted(
            [f for f in os.listdir(d) if f.startswith(today)],
            reverse=True,
        )
        if not cands:
            return None
        text = open(os.path.join(d, cands[0]), encoding="utf-8", errors="replace").read()
        m = re.search(r"\{[\s\S]*\"코스피\"[\s\S]*\}", text)
        if not m:
            return None
        data = json.loads(m.group(0))
        kospi = data.get("코스피") or {}
        kosdaq = data.get("코스닥") or {}
        if not kospi and not kosdaq:
            return None
        return {"kospi": kospi, "kosdaq": kosdaq}
    except Exception:
        return None

def market_header_lines():
    market = load_market_data()
    if not market:
        return []
    lines = ["📈 증시"]
    k = market.get("kospi") or {}
    q = market.get("kosdaq") or {}
    if k.get("종가"):
        lines.append(f"  코스피 {k.get('종가')} ({k.get('전일대비', '-')}, {k.get('등락률', '-')})")
    if q.get("종가"):
        lines.append(f"  코스닥 {q.get('종가')} ({q.get('전일대비', '-')}, {q.get('등락률', '-')})")
    lines.append("")
    return lines

def main():
    with open(QUEUE_FILE) as f:
        queue = json.load(f)

    today = datetime.now(KST).strftime("%Y-%m-%d")
    today_items = [
        d for d in queue
        if d.get("status") == "pending"
        and d.get("collected_at", "").startswith(today)
    ]

    if not today_items:
        return  # silent

    # 중요도 정렬: high > mid > low
    imp_order = {"high": 0, "mid": 1, "low": 2}
    today_items.sort(key=lambda d: imp_order.get(d.get("ai_importance", "mid"), 1))

    now_kst = datetime.now(KST)

    # high 항목 카운트
    high_count = sum(1 for d in today_items if d.get("ai_importance") == "high")

    lines = [f"🤖 AI News Radar — {now_kst.strftime('%m/%d')}"]
    if high_count > 0:
        lines.append(f"🔴 중요: {high_count}건")
    lines.append("")
    lines.extend(market_header_lines())

    for item in today_items[:30]:
        title = item.get("ai_title_ko") or item.get("title", "제목 없음")
        summary = item.get("ai_summary", item.get("description", ""))
        url = item.get("url", "")
        source = item.get("source_name", "")
        category = item.get("ai_category", "")
        importance = item.get("ai_importance", "")

        # HTML 정리 (fallback)
        summary = re.sub(r"<[^>]+>", "", summary).strip()
        summary = re.sub(r"&nbsp;", " ", summary)
        summary = re.sub(r"\s+", " ", summary).strip()
        # title과 같으면 비움
        if summary and item.get("title", "").lower().replace(" - "," ").split()[:3] == summary.lower().replace(" - "," ").split()[:3]:
            summary = ""

        # URL 정리
        if len(url) > 100:
            url = ""

        imp_emoji = IMPORTANCE_EMOJI.get(importance, "🟡")
        cat_tag = f"[{category}] " if category else ""

        lines.append(f"{imp_emoji} {cat_tag}{title}")
        if summary:
            lines.append(f"  💬 {summary[:100]}")
        if source:
            lines.append(f"  📌 {source}")
        if url:
            lines.append(f"  🔗 {url}")
        lines.append("")

    # 카테고리별 집계
    from collections import Counter
    cats = Counter(d.get("ai_category", "?") for d in today_items)
    lines.append("──────────")
    lines.append(f"📊 오늘: {len(today_items)}건")
    if cats:
        cat_str = " | ".join(f"{c}:{n}" for c, n in cats.most_common())
        lines.append(f"🏷️ {cat_str}")
    lines.append(f"📋 대기: {len([d for d in queue if d.get('status')=='pending'])}건")
    print("\n".join(lines))

    # 배달한 항목 status → done
    delivered_ids = {d.get("url") for d in today_items[:30]}
    for item in queue:
        if item.get("url") in delivered_ids and item.get("status") == "pending":
            item["status"] = "done"

    # 7일 이상 된 done 항목 정리
    cutoff = (now_kst - timedelta(days=7)).strftime("%Y-%m-%d")
    queue = [d for d in queue if not (d.get("status") == "done" and d.get("collected_at", "") < cutoff)]

    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
