#!/usr/bin/env python3
"""AI News Radar 수집 스크립트: RSS 피드 → queue.json"""
import json, hashlib, os, sys, re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCES_FILE = os.path.join(BASE_DIR, "sources.json")
QUEUE_FILE = os.path.join(BASE_DIR, "queue.json")
MAX_QUEUE = 200  # 큐 최대 보관 수


def load_sources():
    with open(SOURCES_FILE) as f:
        return json.load(f)["sources"]


def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE) as f:
            return json.load(f)
    return []


def _sort_key(item):
    return item.get("collected_at", "")


def save_queue(queue):
    done_items = sorted(
        (i for i in queue if i.get("status") == "done"),
        key=_sort_key,
        reverse=True,
    )[:100]
    active_items = sorted(
        (i for i in queue if i.get("status") != "done"),
        key=_sort_key,
        reverse=True,
    )
    active_cap = max(0, MAX_QUEUE - len(done_items))
    active_items = active_items[:active_cap]
    queue = active_items + done_items
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def url_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def get_existing_hashes(queue):
    return {i.get("hash") for i in queue}


def title_fingerprint(title):
    return re.sub(r'[\s\-:,.]+', '', title.lower())[:80]


def get_existing_title_fps(queue):
    return {title_fingerprint(i.get("title", "")) for i in queue if i.get("title")}


def fetch_rss(feed_url):
    req = urllib.request.Request(
        urllib.parse.quote(feed_url, safe="/:?=&"),
        headers={"User-Agent": "Mozilla/5.0 (compatible; AI-News-Radar/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        # BOM 및 잘못된 인코딩 수정
        if raw.startswith(b'\xef\xbb\xbf'):
            raw = raw[3:]
        return raw.decode("utf-8", errors="replace").encode("utf-8")


def parse_rss(xml_bytes, source_info):
    items = []
    root = ET.fromstring(xml_bytes)
    # RSS 2.0
    for entry in root.findall(".//item"):
        item = {}
        title_el = entry.find("title")
        link_el = entry.find("link")
        desc_el = entry.find("description")
        date_el = entry.find("pubDate")
        if title_el is None or link_el is None:
            continue
        item["title"] = title_el.text.strip() if title_el.text else ""
        item["url"] = link_el.text.strip() if link_el.text else ""
        item["hash"] = url_hash(item["url"])
        item["source_id"] = source_info["id"]
        item["source_name"] = source_info["name"]
        item["language"] = source_info["language"]
        item["categories"] = source_info.get("category", [])
        item["tier"] = source_info["tier"]
        raw_desc = (desc_el.text or "") if desc_el is not None and desc_el.text else ""
        clean_desc = re.sub(r"<[^>]+>", "", raw_desc).strip()
        clean_desc = re.sub(r"&nbsp;", " ", clean_desc)
        clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
        # title과 description이 같으면 description 비움
        if clean_desc and item.get("title", "").lower().replace(" - "," ").split()[:3] == clean_desc.lower().replace(" - "," ").split()[:3]:
            clean_desc = ""
        item["description"] = clean_desc[:300] if clean_desc else ""
        if date_el is not None and date_el.text:
            try:
                dt = parsedate_to_datetime(date_el.text)
                item["published_at"] = dt.astimezone(timezone.utc).isoformat()
            except Exception:
                item["published_at"] = datetime.now(KST).isoformat()
        else:
            item["published_at"] = datetime.now(KST).isoformat()
        item["collected_at"] = datetime.now(KST).isoformat()
        item["status"] = "pending"
        if item["title"] and item["url"]:
            items.append(item)
    # Atom feed 지원
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        item = {}
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link", ns)
        summary_el = entry.find("atom:summary", ns)
        date_el = entry.find("atom:updated", ns) or entry.find("atom:published", ns)
        if title_el is None or title_el.text is None:
            continue
        item["title"] = title_el.text.strip()
        item["url"] = link_el.get("href", "") if link_el is not None else ""
        item["hash"] = url_hash(item["url"])
        item["source_id"] = source_info["id"]
        item["source_name"] = source_info["name"]
        item["language"] = source_info["language"]
        item["categories"] = source_info.get("category", [])
        item["tier"] = source_info["tier"]
        raw_desc = (summary_el.text or "") if summary_el is not None and summary_el.text else ""
        clean_desc = re.sub(r"<[^>]+>", "", raw_desc).strip()
        clean_desc = re.sub(r"&nbsp;", " ", clean_desc)
        clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
        if clean_desc and item.get("title", "").lower().replace(" - "," ").split()[:3] == clean_desc.lower().replace(" - "," ").split()[:3]:
            clean_desc = ""
        item["description"] = clean_desc[:300] if clean_desc else ""
        if date_el is not None and date_el.text:
            try:
                dt = datetime.fromisoformat(date_el.text.replace("Z", "+00:00"))
                item["published_at"] = dt.astimezone(timezone.utc).isoformat()
            except Exception:
                item["published_at"] = datetime.now(KST).isoformat()
        else:
            item["published_at"] = datetime.now(KST).isoformat()
        item["collected_at"] = datetime.now(KST).isoformat()
        item["status"] = "pending"
        if item["title"] and item["url"]:
            items.append(item)
    return items


def main():
    sources = load_sources()
    queue = load_queue()
    existing = get_existing_hashes(queue)
    existing_title_fps = get_existing_title_fps(queue)
    total_new = 0
    total_skipped = 0
    errors = []

    for src in sources:
        if not src.get("enabled", True):
            continue
        try:
            xml_bytes = fetch_rss(src["url"])
            items = parse_rss(xml_bytes, src)
            max_items = src.get("max_items", 0)
            if max_items > 0:
                items = items[:max_items]
            for item in items:
                if item["hash"] in existing:
                    total_skipped += 1
                    continue
                tfp = title_fingerprint(item.get("title", ""))
                if tfp in existing_title_fps:
                    total_skipped += 1
                    continue
                queue.append(item)
                existing.add(item["hash"])
                total_new += 1
        except Exception as e:
            errors.append(f"{src['id']}: {e}")
            continue

    save_queue(queue)

    now = datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S")
    stats = {
        "last_scan": now,
        "new": total_new,
        "skipped": total_skipped,
        "errors": errors,
        "queue_size": len(queue)
    }

    # stdout 출력 (크론에서 읽음)
    print(json.dumps(stats, ensure_ascii=False))

    # 에러가 있으면 exit code 1
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
