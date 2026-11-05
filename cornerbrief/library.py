"""Optional Open Library background reading. Only citation details are stored.

This never reaches the checks, rates or agents. Default topics are fixed, so no corner details are sent.
"""
import hashlib, json, logging, os, threading, time, urllib.parse, urllib.request
from .paths import CACHE

TOPICS = ["architecture and street design", "accessible design architecture", "pedestrian accessibility design", "street pavement design", "urban drainage design"]
SEARCH = os.environ.get("CB_OPEN_LIBRARY", "https://openlibrary.org")
BACKGROUND_NOTE = "Background only. These books do not affect any rule, rate or design value."
MAX_AGE = 30 * 24 * 3600
MIN_GAP = 0.4  # Open Library allows 3 identified requests per second
RETRY_AFTER = 60
_lock = threading.Lock()
_last_request = 0.0
_unreachable_until = 0.0


def enabled() -> bool:
    return bool(os.environ.get("OPEN_LIBRARY_CONTACT", "").strip())


def clean_query(query) -> str:
    text = " ".join(query.split()) if isinstance(query, str) else ""
    if not 2 <= len(text) <= 80:
        raise ValueError("Enter 2 to 80 characters to search Open Library.")
    return text


def fetch_topic(topic: str, contact: str, base: str | None = None, limit: int = 3) -> list[dict]:
    base = base or SEARCH
    q = urllib.parse.urlencode({"q": topic, "limit": limit, "fields": "title,author_name,first_publish_year,key"})
    req = urllib.request.Request(f"{base}/search.json?{q}", headers={"User-Agent": f"CornerBriefDemo/0.1 ({contact})"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        docs = json.load(resp).get("docs", [])
    return [dict(title=d.get("title", "Untitled"), authors=d.get("author_name", [])[:3], year=d.get("first_publish_year"),
                 url=f"{base}{d['key']}", topic=topic) for d in docs if d.get("key")]


def _path(query: str, limit: int):
    return CACHE / "open_library" / (hashlib.sha256(f"{query.lower()}|{limit}".encode()).hexdigest() + ".json")


def _saved(query: str, limit: int, fresh_only: bool = True):
    path = _path(query, limit)
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return saved["items"] if not fresh_only or time.time() - saved["fetched"] < MAX_AGE else None


def _fetch(query: str, contact: str, limit: int) -> list[dict]:
    """Space out requests and save citations, so a repeat search makes no request."""
    global _last_request
    with _lock:
        wait = _last_request + MIN_GAP - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
    items = fetch_topic(query, contact, limit=limit)
    path = _path(query, limit)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{threading.get_ident()}.tmp")
    temporary.write_text(json.dumps(dict(fetched=time.time(), items=items), indent=1), encoding="utf-8")
    os.replace(temporary, path)
    return items


def _get(query: str, contact: str, limit: int) -> tuple[list[dict], bool]:
    """Return the citations, and whether a network problem left them older or missing."""
    global _unreachable_until
    fresh = _saved(query, limit)
    if fresh is not None:
        return fresh, False
    if time.monotonic() >= _unreachable_until:
        try:
            return _fetch(query, contact, limit), False
        except Exception:
            _unreachable_until = time.monotonic() + RETRY_AFTER  # One outage shouldn't slow every topic and packet
            logging.getLogger("uvicorn.error").exception("Open Library request failed")
    return _saved(query, limit, fresh_only=False) or [], True


def search_books(query=None) -> dict:
    """Search one query, or the default topics. A network problem never affects the packet."""
    contact = os.environ.get("OPEN_LIBRARY_CONTACT", "").strip()
    if not contact:
        return dict(enabled=False, items=[], note="Set OPEN_LIBRARY_CONTACT to turn on background reading.")
    query = clean_query(query) if query is not None else None
    limit = 8 if query else 3
    items, seen, problem = [], set(), False
    for topic in [query] if query else TOPICS:
        rows, failed = _get(topic, contact, limit)
        problem = problem or failed
        for row in rows:
            if row["url"] not in seen:
                seen.add(row["url"])
                items.append(row)
    if problem and not items:
        note = "Open Library couldn't be reached. The packet isn't affected, so try again shortly."
    elif problem:
        note = f"Some results may be older, because Open Library couldn't be reached. {BACKGROUND_NOTE}"
    elif not items:
        note = "Open Library found no books for this search. Try a broader term."
    else:
        note = BACKGROUND_NOTE
    return dict(enabled=True, items=items, note=note)


def background_reading() -> dict:
    """Return the default topics already saved, for the packet. This makes no network request, so it can't slow a run."""
    if not enabled():
        return {"items": [], "note": "Background reading isn't loaded. Set OPEN_LIBRARY_CONTACT to turn it on."}
    items, seen = [], set()
    for topic in TOPICS:
        for row in _saved(topic, 3, fresh_only=False) or []:
            if row["url"] not in seen:
                seen.add(row["url"])
                items.append(row)
    return {"items": items, "note": BACKGROUND_NOTE}
