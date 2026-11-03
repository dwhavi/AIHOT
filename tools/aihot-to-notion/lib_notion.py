"""Shared Notion helpers for aihot-to-notion. stdlib only."""
import json
import os
import urllib.request
import urllib.error

NOTION_VERSION = "2022-06-28"
PARENT_PAGE_ID = "40c6ba6f-0931-8053-a92d-fb8cd9241fc0"


def load_api_key(env_path="~/.hermes/.env"):
    env = {}
    with open(os.path.expanduser(env_path)) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env.get("NOTION_API_KEY", "")


def call(method, ep, body=None, key=None, timeout=60):
    key = key or load_api_key()
    url = "https://api.notion.com/v1/" + ep
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + key,
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:500]
        raise RuntimeError(f"{method} {ep} -> HTTP {e.code}: {detail}")


def rt(text):
    out = []
    text = text or ""
    while text:
        out.append({"type": "text", "text": {"content": text[:1900]}})
        text = text[1900:]
    return out


def H3(t):
    return {"type": "heading_3", "heading_3": {"rich_text": rt(t)}}


def B(t):
    return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt(t)}}


def N(t):
    return {"type": "numbered_list_item", "numbered_list_item": {"rich_text": rt(t)}}


def P(t):
    return {"type": "paragraph", "paragraph": {"rich_text": rt(t)}}


def Q(t):
    return {"type": "quote", "quote": {"rich_text": rt(t)}}


def CODE(t, lang="bash"):
    return {"type": "code", "code": {"rich_text": rt(t), "language": lang}}


def DIV():
    return {"type": "divider", "divider": {}}


def BM(url):
    return {"type": "bookmark", "bookmark": {"url": url}}


def get_child_page_titles(page_id=PARENT_PAGE_ID, key=None):
    """Return {title: block_id} for direct child_page blocks."""
    titles = {}
    cursor = None
    while True:
        ep = f"blocks/{page_id}/children?page_size=100"
        if cursor:
            ep += f"&start_cursor={cursor}"
        res = call("GET", ep, key=key)
        for b in res.get("results", []):
            if b.get("type") == "child_page":
                title = (b.get("child_page") or {}).get("title", "")
                if title:
                    titles[title] = b["id"]
        if res.get("has_more"):
            cursor = res.get("next_cursor")
        else:
            break
    return titles


def delete_block(block_id, key=None):
    call("DELETE", f"blocks/{block_id}", key=key)
