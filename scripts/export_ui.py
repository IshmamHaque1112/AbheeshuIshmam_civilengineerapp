#!/usr/bin/env python3
"""Export the actual app UI and Python-generated sample packets for Helix's static preview."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cornerbrief import preview
from cornerbrief.app import public
from cornerbrief.data_loader import list_corners, load_corner
from cornerbrief.llm import OfflineClient, ReplayClient
from cornerbrief.orchestrator import analyze


def build():
    packets = {}
    for choice in list_corners():
        key = choice["key"]
        corner = load_corner(key)
        client = ReplayClient(key) if corner.get("data_kind") == "SAMPLE DATA" else OfflineClient()
        packet = public(analyze(corner, client=client, save=False))
        packet.update(id=f"export-{key}", created="Saved record preview", features=dict(email=False, labels_and_plans=False, static_export=True))
        packet.update(label=None, label_reason="", planning=None, options=[], approval=None)
        packets[key] = packet
    source = Path(__file__).resolve().parent.parent / "cornerbrief" / "static"
    html = (source / "index.html").read_text(encoding="utf-8")
    css = (source / "style.css").read_text(encoding="utf-8")
    js = (source / "app.js").read_text(encoding="utf-8")
    payload = json.dumps(packets, ensure_ascii=True).replace("<", "\\u003c")
    html = html.replace('<link rel="stylesheet" href="/style.css">', f"<style>{css}</style>")
    html = html.replace('<script src="/app.js"></script>', f"<script>window.CORNERBRIEF_EXPORT = {payload};</script>\n<script>{js}</script>")
    out = source.parent.parent / ".helix" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    # The 3D preview's default model comes from the same Python code the local app uses. Editing needs the backend.
    defaults = preview.defaults()
    first = preview.build_preview({f["id"]: f["default"] for f in defaults["fields"]})
    payload = json.dumps(dict(defaults=defaults, model=first), ensure_ascii=True).replace("<", "\\u003c")
    page = (source / "preview.html").read_text(encoding="utf-8")
    page = page.replace('<link rel="stylesheet" href="/style.css">', f"<style>{css}</style>")
    page = page.replace('<script src="/preview.js"></script>', f"<script>window.CORNERBRIEF_PREVIEW_EXPORT = {payload};</script>\n<script>{(source / 'preview.js').read_text(encoding='utf-8')}</script>")
    (out / "preview.html").write_text(page, encoding="utf-8")
    print("Exported actual UI, saved sample packets and the default 3D preview to .helix/output/. Live search, measurements, release and dimension edits require the local backend.")


if __name__ == "__main__":
    build()
