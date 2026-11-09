"""Roadmap M3 (contractor demonstration) and M4 (structures sandbox). Both are labeled, never saved and make no structural, legal or approval claims."""
import json
import math

import pytest
from starlette.testclient import TestClient

from cornerbrief import contractor_demo, structures
from cornerbrief.app import app
from cornerbrief.paths import RUNS

client = TestClient(app)


@pytest.fixture(autouse=True)
def demos_on(monkeypatch, request):
    if "demos_off" not in request.keywords:
        monkeypatch.setenv("SHOW_ROADMAP_DEMOS", "true")
FORBIDDEN = ("compliant", "approved", "is safe", "safe to", "load capacity", "rated for", "$")


def test_m3_stamps_everything_and_names_the_fictional_company():
    d = contractor_demo.build("real_test")
    assert d["stamp"] == "DEMONSTRATION" and "fictional" in d["notice"] and "(fictional)" in d["company"]["name"]
    assert "hypothesis" in d["persona_note"]


def test_m3_brief_items_have_a_source_or_say_unknown():  # M3.1
    for b in contractor_demo.build("real_test")["brief"]:
        assert b["source"] or b["value"] == "unknown"
    assert next(b for b in contractor_demo.build("real_test")["brief"] if b["item"] == "Location")["value"] == "THOMSON AVENUE and VAN DAM STREET"


def test_m3_capabilities_use_verified_records_only():  # M3.2
    caps = {c["step"]: c for c in contractor_demo.build("standard")["capabilities"]}
    assert caps["Install the detectable warning surface"]["status"] == "unknown"
    assert caps["Sawcut the existing surface and curb"]["status"] == "matched" and caps["Sawcut the existing surface and curb"]["record"]
    assert all(c["status"] == "unknown" for c in caps.values() if "prequalified" in c["step"])


def test_m3_logistics_cover_every_area_and_flag_active_permits():  # M3.3
    items = {l["item"]: l for l in contractor_demo.build("real_test", "2026-11-12")["logistics"]}
    for area in ("Staging area", "Delivery access", "Concrete lead time", "Pedestrian access during work", "Demolition and waste removal", "Street work permits", "Utility markout"):
        assert items[area]["source"] or "unknown" in items[area]["value"]
    assert items["Other active permits on the block"]["status"] == "conflict" and "Q012026257A57" in items["Other active permits on the block"]["value"]
    assert "newyork-811.com" in items["Utility markout"]["source"]


def test_m3_sequence_shows_conflicts_and_never_invents_durations():  # M3.4
    seq = contractor_demo.build("real_test", "2026-11-12")["sequence"]
    assert any("isn't available" in c["text"] for c in seq["conflicts"]) and any("Q012026257A57" in c["text"] for c in seq["conflicts"])
    durations = {r["step"]: r for r in seq["rows"]}
    assert durations["Cure the concrete"]["duration_days"] is None and durations["Cure the concrete"]["duration_basis"] == "unknown"
    assert all(r["duration_days"] is None or "Fictional record" in r["duration_basis"] for r in seq["rows"])
    first_unknown = next(i for i, r in enumerate(seq["rows"]) if r["duration_days"] is None)
    assert all(r["start"] is None for r in seq["rows"][first_unknown + 1:])


def test_m3_never_applies_an_agreement_to_a_job_it_doesnt_name():  # M3.5
    rules = contractor_demo.build("standard")["labor_rules"]
    assert rules["status"] == "unknown" and rules["agreement"] is None and "SAMPLE-JOB-002" in rules["note"]


def test_m3_drafts_are_never_sent_and_payroll_differences_are_found():  # M3.6
    d = contractor_demo.build("standard")["drafts"]
    assert all(r["status"] == "Draft, not sent" for r in d["rfis"]) and d["material_request"]["status"] == "Draft, not sent"
    assert len(d["payroll_check"]["issues"]) == 3 and "nothing is submitted" in d["payroll_check"]["status"]


def test_m3_has_no_dollars_rates_or_permission_words():
    text = json.dumps(contractor_demo.build("real_test")).lower()
    assert not any(word in text for word in FORBIDDEN)


def test_m3_route_saves_nothing_and_rejects_bad_input():
    before = sorted(RUNS.glob("*.json")) if RUNS.exists() else []
    assert client.get("/api/demo/contractor?corner=real_test").status_code == 200
    assert (sorted(RUNS.glob("*.json")) if RUNS.exists() else []) == before
    assert client.get("/api/demo/contractor?corner=nope").status_code == 404
    assert client.get("/api/demo/contractor?corner=standard&start=11/12/2026").status_code == 400


DEFAULTS = {m: {k: v["default"] for k, v in structures.MODELS[m]["fields"].items()} for m in structures.MODELS}


def test_m4_pratt_truss_counts_and_diagonal_direction():
    t = structures.build(dict(model="truss", **DEFAULTS["truss"]))
    n = DEFAULTS["truss"]["panels"]
    assert t["groups"]["diagonal"] == 2 * (n - 2) and t["groups"]["vertical"] == 2 * (n - 1)
    mid = DEFAULTS["truss"]["span_ft"] / 2
    for line in (l for l in t["lines"] if l["group"] == "diagonal"):
        top, bottom = (line["a"], line["b"]) if line["a"][2] > line["b"][2] else (line["b"], line["a"])
        assert abs(bottom[0] - mid) < abs(top[0] - mid)  # Pratt diagonals run down toward midspan


def test_m4_tower_tapers_and_braces_every_face():
    t = structures.build(dict(model="tower", **DEFAULTS["tower"]))
    s = DEFAULTS["tower"]["sections"]
    assert t["groups"] == {"horizontal": 4 * (s + 1), "leg": 4 * s, "brace": 8 * s}


@pytest.mark.parametrize("frequency,struts", [(1, 10), (2, 65), (4, 250)])
def test_m4_dome_struts_sit_on_the_sphere_and_ground(frequency, struts):
    d = structures.build(dict(model="dome", radius_ft=20, frequency=frequency))
    assert d["members"] == struts and min(min(l["a"][2], l["b"][2]) for l in d["lines"]) == 0


def test_m4_gears_stay_meshed_while_turning():
    g = structures.build(dict(model="gears", **DEFAULTS["gears"]))["gears"]
    for t in [i * 0.05 for i in range(120)]:
        for a, b in zip(g, g[1:]):
            pa, pb, cp = 2 * math.pi / a["teeth"], 2 * math.pi / b["teeth"], math.pi * DEFAULTS["gears"]["module_in"]
            sa = a["pitch_radius"] * ((a["phase"] + a["speed"] * t) % pa)
            sb = b["pitch_radius"] * ((math.pi - (b["phase"] + b["speed"] * t)) % pb)
            assert abs(((sb - sa - cp / 2) + cp / 2) % cp - cp / 2) < 1e-6
    assert g[1]["speed"] < 0 < g[2]["speed"]


@pytest.mark.parametrize("raw,field", [(dict(model="truss", **dict(DEFAULTS["truss"], panels=7)), "panels"), (dict(model="tower", **dict(DEFAULTS["tower"], top_ft=40)), "top_ft"),
                                       (dict(model="dome", radius_ft="x", frequency=2), "radius_ft"), (dict(model="bridge"), "model")])
def test_m4_bad_parameters_are_named(raw, field):
    r = client.post("/api/demo/structures", json=raw)
    assert r.status_code == 400 and field in r.json()["problems"]


def test_m4_makes_no_structural_claims():
    for m in structures.MODELS:
        text = json.dumps(structures.build(dict(model=m, **DEFAULTS[m]))).lower()
        assert "no loads" in text and not any(word in text for word in FORBIDDEN)


@pytest.mark.demos_off
def test_demos_are_off_by_default():
    assert client.get("/api/demo").json() == {"enabled": False}
    for path in ("/api/demo/contractor?corner=standard", "/api/demo/structures", "/demo/contractor.html", "/demo/structures.js", "/contractor.html", "/structures.html"):
        assert client.get(path).status_code == 404, path


def test_demo_pages_serve_only_known_files():
    assert client.get("/demo/contractor.html").status_code == 200 and client.get("/demo/structures.js").status_code == 200
    for path in ("/demo/sample_company.yaml", "/demo/notes.txt", "/demo/"):
        assert client.get(path).status_code == 404, path


def test_every_m3_value_says_where_it_came_from():
    d = contractor_demo.build("real_test", "2026-11-12")
    allowed = set(contractor_demo.KINDS)
    rows = d["brief"] + d["capabilities"] + d["logistics"] + d["sequence"]["conflicts"] + d["drafts"]["rfis"] + d["drafts"]["material_request"]["items"]
    rows += [d["labor_rules"], d["drafts"]["daily_report"], d["drafts"]["payroll_check"]]
    assert all(r["kinds"] and set(r["kinds"]) <= allowed for r in rows)
    for r in d["sequence"]["rows"]:
        assert {r["team_kind"], r["duration_kind"], r["quantity_kind"]} <= allowed and all(e["kind"] in allowed for e in r["equipment"])
    permit_conflict = next(c for c in d["sequence"]["conflicts"] if "Q012026257A57" in c["text"])
    assert permit_conflict["kinds"] == ["real", "fictional"] and "fictional schedule" in permit_conflict["text"]
    assert all(r["duration_kind"] == "fictional" for r in d["sequence"]["rows"] if r["duration_days"])


def test_demo_code_cant_write_to_packets():
    import ast, inspect
    banned = {"save_run", "approve", "validate_entries", "merge_entries", "rerun_with_field", "send_brief", "save_photo", "pull", "run_corner"}
    for module in (contractor_demo, structures):
        tree = ast.parse(inspect.getsource(module))
        names = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
        assert not names & banned, (module.__name__, names & banned)
        for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "analyze"):
            assert any(k.arg == "save" and getattr(k.value, "value", True) is False for k in call.keywords)


def test_no_fictional_value_reaches_a_real_packet():
    from cornerbrief.data_loader import list_corners, load_corner
    from cornerbrief.llm import OfflineClient
    from cornerbrief.orchestrator import analyze
    contractor_demo.build("real_test")
    for c in list_corners():
        text = json.dumps(analyze(load_corner(c["key"]), client=OfflineClient(), save=False))
        for marker in ("SAMPLE-CAP", "SAMPLE-EQ", "SAMPLE-JOB", "SAMPLE-SUP", "SAMPLE-AGREEMENT", "Sample team", "Sample worker", "Sample Concrete Co", "(fictional)"):
            assert marker not in text, (c["key"], marker)


def test_register_must_declare_itself_fictional(tmp_path, monkeypatch):
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "sample_company.yaml").write_text("company: {name: Real Co}\n")
    monkeypatch.setattr(contractor_demo, "DATA", tmp_path)
    with pytest.raises(ValueError, match="fictional: true"):
        contractor_demo.load_company()


@pytest.mark.parametrize("key", ["../demo/sample_company", "demo/sample_company", "sample_company"])
def test_packets_cant_load_demo_files(key):
    from cornerbrief.data_loader import load_corner
    with pytest.raises(KeyError):
        load_corner(key)
