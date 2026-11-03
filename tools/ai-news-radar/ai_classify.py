#!/usr/bin/env python3
"""AI classification script — TypeSafe(Jev) 기반 분류.
기존 키워드 매칭 + 하드코딩 요약 사전을 Jev fan-out 호출로 교체 (2026-09-21).
- 카테고리(Choice) / 중요도(Score) / 관심도 게이트(Noul)를 1회 호출로 병렬 평가
- 통신은 영어 고정(마스터 규칙). 한글 제목은 그대로 전달해도 되지만
  지시문·기준은 영어. Jev는 다국어 처리 가능하나 영어가 최적.
- Jev 실패 시 기존 키워드 폴백 유지 (파이프라인 안 멈춤)
- ai_summary는 여전히 제목 기반(요약 생성은 LLM 영역 — Jev는 생성 불가)
"""
import json, os, sys, urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(BASE_DIR, "queue.json")

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

CATEGORIES = {
    "LLM": "Large language models, model releases, GPT/Claude/Gemini/Llama news",
    "Research": "Papers, studies, scientific breakthroughs, arxiv",
    "OpenSource": "Open source projects, GitHub, Hugging Face, OSS releases",
    "Products": "Product launches, releases, features, company offerings",
    "Industry": "Business, market, investment, chips, infrastructure, adoption",
    "Policy": "Government policy, regulation, legislation, patents",
    "Security": "Cybersecurity, vulnerabilities, breaches, threats",
}


def load_api_key():
    for env_path in (os.path.expanduser("~/.hermes/.env"), os.path.expanduser("~/.env")):
        if os.path.exists(env_path):
            for line in open(env_path, encoding="utf-8", errors="replace"):
                if line.startswith("TYPESAFE_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("TYPESAFE_API_KEY", "")


def fallback_classify(item):
    """기존 키워드 방식 (Jev 실패 시 폴백)"""
    title = item.get("title", "").lower()
    if any(kw in title for kw in ["llm", "gpt", "claude", "gemini", "openai", "anthropic", "chatgpt", "language model", "mistral", "llama"]):
        cat = "LLM"
    elif any(kw in title for kw in ["research", "paper", "study", "arxiv", "breakthrough"]):
        cat = "Research"
    elif any(kw in title for kw in ["open source", "open-source", "github", "hugging face", "oss", "오픈소스"]):
        cat = "OpenSource"
    elif any(kw in title for kw in ["policy", "regulation", "government", "law", "정책", "정부"]):
        cat = "Policy"
    elif any(kw in title for kw in ["security", "cyber", "vulnerability", "breach", "보안"]):
        cat = "Security"
    else:
        cat = "Industry"
    if any(kw in title for kw in ["trillion", "breakthrough", "중국", "china ai"]):
        imp = "high"
    elif any(kw in title for kw in ["launch", "release", "new", "출시"]):
        imp = "mid"
    else:
        imp = "low"
    return cat, imp


def load_cc_key():
    for env_path in (os.path.expanduser("~/.hermes/.env"), os.path.expanduser("~/.env")):
        if os.path.exists(env_path):
            for line in open(env_path, encoding="utf-8", errors="replace"):
                if line.startswith("COMMAND_CODE_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("COMMAND_CODE_API_KEY", "")


CC_BASE_URL = os.environ.get("COMMAND_CODE_BASE_URL", "http://127.0.0.1:10100/v1")
CC_MODEL = "command-code/meta/muse-spark-1.3-contributor"


def translate_titles_ko(items, api_key):
    """영어 제목 → 한글 제목 일괄 번역 (NIM). 실패 시 {} 반환."""
    targets = [(it["idx"], it.get("title", "")) for it in items
               if it.get("title") and any(ord(c) < 128 for c in it["title"][:20])]
    if not targets or not api_key:
        return {}
    lines = [f"[{i}] {t[:150]}" for i, t in targets]
    system = ("Translate the following news headlines to Korean. "
              "Keep proper nouns (company/model/tech terms) in English. "
              "Output ONLY translations, one per line, same [N] format. No explanation.")
    body = json.dumps({
        "model": CC_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": "\n".join(lines)}],
        "temperature": 0.3,
        "max_tokens": 3000,
    }).encode()
    req = urllib.request.Request(
        f"{CC_BASE_URL}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            msg = json.loads(resp.read().decode())["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
    except Exception as e:
        print(f"NIM 제목번역 오류, 원문 유지: {e}", file=sys.stderr)
        return {}
    if not content or not isinstance(content, str):
        print("NIM 제목번역 빈 응답, 원문 유지", file=sys.stderr)
        return {}
    import re
    out = {}
    for m in re.finditer(r"\[(\d+)\]\s*(.+)", content):
        idx, trans = int(m.group(1)), m.group(2).strip()
        if any(i == idx for i, _ in targets):
            out[idx] = trans
    return out


def jev_classify(items, api_key):
    """Jev fan-out: 항목당 category(Choice) + importance(Score) + 관심도(Noul)"""
    state = {
        "items": [
            {
                "idx": i,
                "title": it.get("title", "")[:200],
                "description": (it.get("description") or "")[:200],
                "source": it.get("source_name", ""),
            }
            for i, it in enumerate(items)
        ],
        "user_profile": (
            "solo game developer, AI automation enthusiast, value investor "
            "tracking Korean stock market, heavy user of AI coding agents"
        ),
    }
    questions = {}
    for i in range(len(items)):
        questions[f"cat_{i}"] = {
            "type": "choice",
            "instructions": f"Best category for items[{i}]",
            "criteria": CATEGORIES,
        }
        questions[f"imp_{i}"] = {
            "type": "score",
            "instructions": f"How important is items[{i}] for user_profile?",
            "criteria": [
                "Routine news, low value",
                "Noteworthy, worth scanning",
                "Major news, must read",
            ],
        }
    body = json.dumps({"state": state, "model": MODEL, "questions": questions}).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode())


def main():
    import subprocess
    result = subprocess.run(["python3", os.path.join(BASE_DIR, "preprocess.py")],
                          capture_output=True, text=True, cwd=BASE_DIR)
    items = []
    for line in result.stdout.strip().split("\n"):
        if line.startswith("["):
            items = json.loads(line)
            break
    if not items:
        print("0")
        return

    with open(QUEUE_FILE) as f:
        queue = json.load(f)
    url_to_idx = {q.get("url", ""): i for i, q in enumerate(queue)}

    api_key = load_api_key()
    jev_answers = {}
    if api_key and items:
        try:
            resp = jev_classify(items, api_key)
            jev_answers = resp.get("answers", {})
            usage = resp.get("usage", {})
            print(f"Jev: {len(items)}건 분류 (input {usage.get('input_tokens','?')} tok)", file=sys.stderr)
        except Exception as e:
            print(f"Jev 오류, 키워드 폴백: {e}", file=sys.stderr)
            jev_answers = {}

    # 영어 제목 → 한글 번역 (NIM, 실패 시 원문 유지)
    ko_titles = translate_titles_ko(items, load_cc_key())

    count = 0
    for item in items:
        url = item.get("url", "")
        if url not in url_to_idx:
            continue
        idx = item["idx"]
        qi = url_to_idx[url]

        cat_ans = jev_answers.get(f"cat_{idx}", {})
        imp_ans = jev_answers.get(f"imp_{idx}", {})
        category = cat_ans.get("choice")
        score = imp_ans.get("score")

        if category in CATEGORIES and score is not None:
            importance = "high" if score >= 1.5 else ("mid" if score >= 0.5 else "low")
        else:
            category, importance = fallback_classify(item)

        # 요약은 제목 기반 (생성은 Jev 영역 아님)
        title = item.get("title", "")
        summary = title[:97] + "..." if len(title) > 100 else title

        queue[qi]["ai_category"] = category
        queue[qi]["ai_importance"] = importance
        queue[qi]["ai_summary"] = summary
        queue[qi]["ai_title_ko"] = ko_titles.get(idx, title)
        queue[qi]["ai_processed"] = True
        count += 1

    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
    print(count)


if __name__ == "__main__":
    main()
