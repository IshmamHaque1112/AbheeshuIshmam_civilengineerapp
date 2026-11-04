"""Optional Open Library background reading. Only citation details are stored. This never reaches checks or rates."""
import json, os, urllib.parse, urllib.request
from .paths import CACHE

TOPICS = ["street pavement design", "urban drainage design", "pedestrian accessibility design"]
SEARCH = os.environ.get("CB_OPEN_LIBRARY", "https://openlibrary.org")


def fetch_topic(topic: str, contact: str, base: str = SEARCH) -> list[dict]:
    q = urllib.parse.urlencode({"q": topic, "limit": 3, "fields": "title,author_name,first_publish_year,key"})
    req = urllib.request.Request(f"{base}/search.json?{q}", headers={"User-Agent": f"CornerBriefDemo/0.1 ({contact})"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        docs = json.load(resp).get("docs", [])
    return [dict(title=d.get("title", "Untitled"), authors=d.get("author_name", [])[:3], year=d.get("first_publish_year"),
                 url=f"{base}{d['key']}", topic=topic) for d in docs if d.get("key")]


def background_reading() -> dict:
    contact = os.environ.get("OPEN_LIBRARY_CONTACT", "")
    if not contact:
        return {"items": [], "note": "Background reading isn't loaded. Set OPEN_LIBRARY_CONTACT to turn it on."}
    CACHE.mkdir(exist_ok=True)
    path = CACHE / "open_library.json"
    if path.exists():
        return {"items": json.loads(path.read_text(encoding="utf-8")), "note": "Background only. These books do not affect any rule, rate or design value."}
    try:
        items = [row for topic in TOPICS for row in fetch_topic(topic, contact)]
    except Exception as exc:
        return {"items": [], "note": f"Open Library couldn't be reached: {exc}"}
    path.write_text(json.dumps(items, indent=1), encoding="utf-8")
    return {"items": items, "note": "Background only. These books do not affect any rule, rate or design value."}
