#!/usr/bin/env python3
"""AI News Radar - AI 처리 스크립트
pending 항목을 AI로 분류/요약. 배달 전에 실행.
no_agent=true, 배달 크론에서 context_from으로 연결."""
import json, os, sys, subprocess
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(BASE_DIR, "queue.json")
KST = timezone(timedelta(hours=9))
MAX_PROCESS = 30  # 배달 시 최대 30건이므로 30건만 처리

def main():
    with open(QUEUE_FILE) as f:
        queue = json.load(f)

    today = datetime.now(KST).strftime("%Y-%m-%d")
    pending = [d for d in queue if d.get("status") == "pending" and d.get("collected_at", "").startswith(today)]

    if not pending:
        print(json.dumps({"processed": 0, "remaining": 0}))
        return

    # 아직 AI 처리 안 된 항목 (ai_processed가 없는 것)
    unprocessed = [d for d in pending if not d.get("ai_processed")]
    batch = unprocessed[:MAX_PROCESS]

    if not batch:
        print(json.dumps({"processed": 0, "remaining": len(pending)}))
        return

    # AI 처리할 항목 구성
    items_text = []
    for i, item in enumerate(batch):
        title = item.get("title", "")
        desc = item.get("description", "")
        source = item.get("source_name", "")
        items_text.append(f"[{i+1}] {title}\n    출처: {source}\n    내용: {desc[:200] if desc else '(없음)'}")

    input_text = "다음 뉴스 기사 목록을 분석하세요.\n\n" + "\n".join(items_text) + "\n\n"

    # 프롬프트
    prompt = input_text + """각 기사에 대해 카테고리와 한줄 요약(한국어, 50자 이내)을 작성하세요.
카테고리: LLM, Research, OpenSource, Products, Industry, Policy, Security 중 택1
중요도: high/mid/low

반드시 아래 JSON 형식만 출력. 다른 설명 금지.
{"results":[{"idx":1,"category":"LLM","importance":"mid","summary":"한줄요약"}]}"""

    import urllib.request
    api_url = os.environ.get("COMMAND_CODE_BASE_URL", "http://127.0.0.1:10100/v1")
    api_key = os.environ.get("COMMAND_CODE_API_KEY", "")
    if not api_key:
        for env_path in (os.path.expanduser("~/.hermes/.env"), os.path.expanduser("~/.env")):
            if os.path.exists(env_path):
                for line in open(env_path, encoding="utf-8", errors="replace"):
                    if line.startswith("COMMAND_CODE_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
                if api_key:
                    break
    if not api_key:
        print(json.dumps({"error": "COMMAND_CODE_API_KEY not set", "processed": 0}), file=sys.stderr)
        return

    payload = json.dumps({
        "model": "command-code/meta/muse-spark-1.3-contributor",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4000
    }).encode()

    req = urllib.request.Request(
        f"{api_url}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        content = result["choices"][0]["message"]["content"]
    except Exception as e:
        print(json.dumps({"error": str(e), "processed": 0}), file=sys.stderr)
        return

    # JSON 파싱
    try:
        # 응답에서 JSON 블록 추출
        import re
        json_match = re.search(r'\{.*"results".*\}', content, re.DOTALL)
        if json_match:
            ai_results = json.loads(json_match.group())
        else:
            ai_results = json.loads(content)
        results = ai_results.get("results", [])
    except json.JSONDecodeError:
        print(json.dumps({"error": "AI response parse failed", "raw": content[:200]}), file=sys.stderr)
        return

    # queue 업데이트
    url_to_item = {item.get("url"): item for item in batch}
    for r in results:
        idx = r.get("idx", 0) - 1
        if 0 <= idx < len(batch):
            item = batch[idx]
            item["ai_category"] = r.get("category", "Industry")
            item["ai_importance"] = r.get("importance", "mid")
            item["ai_summary"] = r.get("summary", "")
            item["ai_processed"] = True

    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "processed": len(results),
        "total_pending": len(pending),
        "batch_size": len(batch)
    }))

if __name__ == "__main__":
    main()
