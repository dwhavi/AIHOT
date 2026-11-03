#!/usr/bin/env python3
"""AI Hot News Daily -> Notion 101 Ai Hot News 하위 페이지로 매일 아침 누적.
- 소스: cronjob/ai-news-radar/queue.json 당일분(collected_at KST 오늘)
- 구성: 핵심(high) / 개발 이슈(OpenSource,Products,LLM,Research,Security) / 전체 브리핑(최대 30) / 집계
- 중복방지: 같은 제목 있으면 SKIP 종료. Notion 100블록 제한 대응 분할 POST.
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta

from lib_notion import (
    PARENT_PAGE_ID,
    B,
    BM,
    DIV,
    H3,
    P,
    Q,
    call,
    get_child_page_titles,
)

KST = timezone(timedelta(hours=9))
QUEUE_CANDIDATES = [
    "/Users/dwhavi/cronjob/ai-news-radar/queue.json",
    "/home/dwhavi/cronjob/ai-news-radar/queue.json",
]
DEV_CATS = {"OpenSource", "Products", "LLM", "Research", "Security"}
MAX_ITEMS = 30
IMP_ORDER = {"high": 0, "mid": 1, "low": 2}
IMP_EMOJI = {"high": "🔴", "mid": "🟡", "low": "⚪"}


def find_queue():
    for p in QUEUE_CANDIDATES:
        if os.path.exists(p):
            return p
    return QUEUE_CANDIDATES[0]


def load_day(queue_path):
    with open(queue_path, encoding="utf-8") as f:
        q = json.load(f)
    today = datetime.now(KST).strftime("%Y-%m-%d")
    day = [x for x in q if (x.get("collected_at") or "").startswith(today)]
    return today, day


def sort_key(d):
    imp = IMP_ORDER.get(d.get("ai_importance"), 3)
    proc = 0 if d.get("ai_processed") else 1
    return (imp, proc, d.get("collected_at", ""))


def title_of(d):
    return d.get("ai_title_ko") or d.get("title") or "(제목 없음)"


def summary_of(d):
    s = d.get("ai_summary") or d.get("description") or ""
    s = s.replace("\n", " ").strip()
    return s[:150]


def item_blocks(d):
    emo = IMP_EMOJI.get(d.get("ai_importance"), "⚪")
    cat = d.get("ai_category") or "미분류"
    t = title_of(d)
    s = summary_of(d)
    src = d.get("source_name") or ""
    url = (d.get("url") or "").strip()
    line = f"{emo} [{cat}] {t}"
    if s:
        line += f" — {s[:100]}"
    blocks = [B(line)]
    meta = src
    if url and len(url) <= 2000:
        blocks.append(BM(url))
    elif meta:
        blocks.append(P(f"📌 {meta}"))
    return blocks


def build_children(today, day):
    children = []
    total = len(day)
    proc_n = sum(1 for x in day if x.get("ai_processed"))
    high = sorted([x for x in day if x.get("ai_importance") == "high"], key=sort_key)
    dev = sorted([x for x in day if (x.get("ai_category") in DEV_CATS)], key=sort_key)
    all_sorted = sorted(day, key=sort_key)[:MAX_ITEMS]

    children.append(P(f"기준: {today} (KST) collected_at 당일분 {total}건 (AI처리 {proc_n}건) · 큐: ai-news-radar/queue.json"))
    children.append(DIV())

    children.append(H3(f"🔴 오늘의 핵심 ({len(high)}건)"))
    if high:
        for d in high:
            children.extend(item_blocks(d))
    else:
        children.append(P("오늘 high 없음 (AI 미처리含む — 05시 처리 후 06:10 집계 기준)"))
    children.append(DIV())

    children.append(H3(f"🛠️ 개발 이슈 ({len(dev)}건)"))
    children.append(P("기준: ai_category ∈ OpenSource / Products / LLM / Research / Security"))
    if dev:
        for d in dev[:20]:
            children.extend(item_blocks(d))
        if len(dev) > 20:
            children.append(P(f"… 외 {len(dev) - 20}건 생략 (전체 브리핑 참조)"))
    else:
        children.append(P("해당 카테고리 당일분 없음"))
    children.append(DIV())

    children.append(H3(f"📋 전체 브리핑 (당일 전체, 중요도순 최대 {MAX_ITEMS}건)"))
    if all_sorted:
        for d in all_sorted:
            children.extend(item_blocks(d))
    else:
        children.append(P("당일 수집분 없음 (수집 크론 2h 간격 — 06:00 배달 후 확인)"))
    children.append(DIV())

    cats = Counter(d.get("ai_category") or "미처리" for d in day)
    imps = Counter(d.get("ai_importance") or "미처리" for d in day)
    children.append(H3("📊 집계"))
    children.append(B(f"수집: {total}건 | AI처리: {proc_n}건 | 미처리: {total - proc_n}건"))
    if cats:
        children.append(B("카테고리: " + " | ".join(f"{k}:{v}" for k, v in cats.most_common())))
    if imps:
        children.append(B("중요도: " + " | ".join(f"{k}:{v}" for k, v in imps.most_common())))
    return children


def create_page_chunked(title, children):
    first = children[:100]
    res = call("POST", "pages", {
        "parent": {"page_id": PARENT_PAGE_ID},
        "properties": {"title": [{"text": {"content": title}}]},
        "children": first,
    })
    pid = res.get("id")
    print("subpage_id:", pid)
    print("subpage_url:", res.get("url"))
    rest = children[100:]
    for i in range(0, len(rest), 90):
        chunk = rest[i:i + 90]
        call("PATCH", f"blocks/{pid}/children", {"children": chunk})
        print(f"appended {100 + i + len(chunk)}/{len(children)}")
    return pid


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "AI Hot News"
    qp = find_queue()
    if not os.path.exists(qp):
        print(f"queue not found: {qp}")
        return 1
    today, day = load_day(qp)
    print(f"queue: {qp} day={today} n={len(day)}")
    title = f"{today} - {topic}"
    print("title:", title)
    existing = get_child_page_titles(PARENT_PAGE_ID)
    if title in existing:
        print(f"SKIP: '{title}' already exists ({existing[title][:8]}).")
        return 0
    children = build_children(today, day)
    print("blocks:", len(children))
    create_page_chunked(title, children)
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
