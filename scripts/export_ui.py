#!/usr/bin/env python3
"""Export the actual app UI and Python-generated sample packets for Helix's static preview."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cornerbrief.app import public
from cornerbrief.data_loader import SAMPLE_KEYS, load_corner
from cornerbrief.llm import ReplayClient
from cornerbrief.orchestrator import analyze


def build():
    packets = {}
    for key in SAMPLE_KEYS:
        packet = public(analyze(load_corner(key), client=ReplayClient(key), save=False))
        packet.update(id=f"export-{key}", created="Saved sample preview", features=dict(email=False, labels_and_plans=False, static_export=True))
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
    print("Exported actual UI and saved sample packets to .helix/output/index.html. Live search, measurements and release require the local backend.")


if __name__ == "__main__":
    build()
