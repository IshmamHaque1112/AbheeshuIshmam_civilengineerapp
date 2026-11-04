import json
import socket
import threading
import time
import urllib.error
import urllib.request
import importlib.util
from pathlib import Path
import pytest
import uvicorn

spec = importlib.util.spec_from_file_location("fetch_corners", Path(__file__).parent.parent / "scripts" / "fetch_corners.py")
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    import cornerbrief.orchestrator as orch
    import os
    tmp = tmp_path_factory.mktemp("runs")
    orch.RUNS = tmp
    os.environ["DEMO_MODE"] = "true"
    from cornerbrief.app import app
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    while not srv.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    thread.join(5)


def call(url, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_review_flow_over_http(server):
    status, page = call(server + "/")
    assert status == 200 and b"CornerBrief" in page
    status, corners = call(server + "/api/corners")
    assert [c["key"] for c in json.loads(corners)] == ["standard", "constrained", "missing_or_stale"]
    status, body = call(server + "/api/corners/standard/run", {})
    run = json.loads(body)
    assert status == 200 and run["corner"]["data_kind"] == "SAMPLE DATA" and "agent_log" not in run
    assert call(server + f"/api/runs/{run['id']}/download")[0] == 409
    assert call(server + f"/api/runs/{run['id']}/email", {"to": "x@example.com"})[0] == 409
    assert call(server + f"/api/runs/{run['id']}/approve", {"reviewer": ""})[0] == 400
    assert call(server + f"/api/runs/{run['id']}/approve", {"reviewer": "Pat"})[0] == 200
    status, text = call(server + f"/api/runs/{run['id']}/download")
    assert status == 200 and "not a compliance decision".encode() in text


def test_unknown_corner_and_bad_run_id(server):
    assert call(server + "/api/corners/nope/run", {})[0] == 404
    assert call(server + "/api/runs/..%2F..%2Fsecret/download")[0] == 404


LOC = dict(cornerid=1, rampid=2, geocyclora="2023-01-01", ramp_running_slope_total="6", ramp_cross_slope="1", ramp_width="60", ramp_length="6",
           lnd_width="60", lnd_length="60", lnd_cross_slope="1", curb_reveal="0.2", obstacles_ramp="None", obstacles_landing="None")


def test_classify_standard():
    assert fetch.classify([LOC], [{"construc_1": "2022/01/01", "construc_2": "Constructed"}]) == "standard"


def test_classify_stale_placeholder_and_complex():
    assert fetch.classify([LOC], [{"construc_1": "2025/01/01", "construc_2": "Constructed"}]) == "missing_or_stale"
    assert fetch.classify([{**LOC, "curb_reveal": "999"}], [{"construc_2": "Constructed"}]) == "missing_or_stale"
    assert fetch.classify([LOC], [{"construc_2": "Complex Planned Construction"}]) == "constrained"
    assert fetch.classify([{**LOC, "obstacles_landing": "Utility Vault"}], [{"construc_2": "Constructed"}]) == "constrained"


def test_location_filter_uses_borough_code_and_street():
    where = fetch.build_where("Queens", "Thomson")
    assert "borough=4" in where and "like '%THOMSON%'" in where and "stname2" in where
    assert "''" in fetch.build_where(None, "O'Brien")
    with pytest.raises(ValueError):
        fetch.build_where("Jersey City")


def test_list_candidates_sends_the_filter(monkeypatch):
    seen = {}
    def fake(dataset, **params):
        seen.setdefault(dataset, params)
        return []
    monkeypatch.setattr(fetch, "query", fake)
    fetch.list_candidates(10, "QUEENS", "THOMSON")
    assert "borough=4" in seen[fetch.LOC]["where"]


def test_real_corner_fixture_runs_with_unknown_limits(tmp_path, monkeypatch):
    from cornerbrief.llm import ReplayClient
    from cornerbrief.orchestrator import analyze
    corner = dict(key="standard", label="A and B", data_kind="NYC Open Data", context=dict(inside_nyc=True, work_type="corner_ramp_row", road_control="not_recorded"),
                  locations=[{**LOC, "gutter_slope": "1", "counter_slope": "2"}], progress=[{"cornerid": 1, "construc_2": "Constructed", "construc_1": "2022/01/01"}], complaints=[])
    monkeypatch.setattr("cornerbrief.orchestrator.RUNS", tmp_path)
    run = analyze(corner, client=ReplayClient("standard"))
    assert all(o["result"] in ("unknown", "not applicable") for o in run["rule_results"])
    assert run["planning"] is None


def test_fetch_caches_api_responses(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(fetch, "ROOT", tmp_path)
    monkeypatch.setattr(fetch, "_download", lambda url: calls.append(url) or {"ok": 1})
    assert fetch.get("https://example.test/a") == {"ok": 1}
    assert fetch.get("https://example.test/a") == {"ok": 1}
    assert len(calls) == 1
    monkeypatch.setitem(fetch.REFRESH, "on", True)
    fetch.get("https://example.test/a")
    assert len(calls) == 2


def test_site_measurement_rerun_over_http(server):
    status, body = call(server + "/api/corners/missing_or_stale/run", {})
    first = json.loads(body)
    assert status == 200 and first["state"].startswith("stop") and first["field_inputs"]
    key = next(f["key"] for f in first["field_inputs"] if f["field"] == "sidewalk_width")
    status, body = call(f"{server}/api/runs/{first['id']}/field", {"entries": [{"key": key, "value": "9"}], "date": "2099-01-01", "by": "A B"})
    assert status == 400 and b"future" in body
    status, body = call(f"{server}/api/runs/{first['id']}/field", {"entries": [{"key": key, "value": "9"}], "date": "2026-11-02", "by": "A B"})
    second = json.loads(body)
    assert status == 200 and second["changes"]["inputs"] and second["previous_run_id"] == first["id"] and second["features"]["labels_and_plans"] is False
    assert call(f"{server}/api/runs/{second['id']}/download")[0] == 409
    status, body = call(f"{server}/api/runs/{second['id']}")
    assert status == 200 and json.loads(body)["id"] == second["id"] and "agent_log" not in json.loads(body)
    assert call(f"{server}/api/runs/nothere")[0] == 404
    assert call(f"{server}/api/photos/..%2Fsecret")[0] == 404


def _raw(url, body):
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


@pytest.mark.parametrize("path", ["approve", "field", "email"])
@pytest.mark.parametrize("body", [b"not json", b"[1, 2]", b'"text"'])
def test_bad_request_bodies_get_a_clear_error(server, path, body):
    run = json.loads(call(server + "/api/corners/standard/run", {})[1])
    status, out = _raw(f"{server}/api/runs/{run['id']}/{path}", body)
    assert status == 400 and "error" in json.loads(out)


@pytest.mark.parametrize("path,data", [("approve", {"reviewer": 5}), ("approve", {"reviewer": None}), ("email", {"to": None}), ("email", {"to": 5}), ("field", {"entries": "x", "date": "2026-11-02", "by": "A B"}), ("field", {"entries": [{"key": "corner:sidewalk_width", "value": 9}], "date": "2026-11-02", "by": 5})])
def test_wrong_value_types_get_a_clear_error(server, path, data):
    run = json.loads(call(server + "/api/corners/standard/run", {})[1])
    status, out = call(f"{server}/api/runs/{run['id']}/{path}", data)
    assert status in (400, 409) and "error" in json.loads(out)


def test_run_from_an_older_version_is_treated_as_missing(server):
    import cornerbrief.orchestrator as orch
    (orch.RUNS / "oldrun1.json").write_text(json.dumps(dict(id="oldrun1", status="unknown", corner=dict(key="standard"))), encoding="utf-8")
    assert call(server + "/api/runs/oldrun1")[0] == 404
    assert call(server + "/api/runs/oldrun1/field", {"entries": [], "date": "2026-11-02", "by": "A B"})[0] == 404


def test_email_failure_gets_a_clear_error(server, monkeypatch):
    run = json.loads(call(server + "/api/corners/standard/run", {})[1])
    call(f"{server}/api/runs/{run['id']}/approve", {"reviewer": "R"})
    def fail(*a, **k):
        raise OSError("no route")
    monkeypatch.setattr("smtplib.SMTP", fail)
    for k, v in dict(EMAIL_ALLOWLIST="t@example.com", EMAIL_ENABLED="true", EMAIL_FROM="a@example.com", SMTP_HOST="h", SMTP_USER="u", SMTP_PASSWORD="p").items():
        monkeypatch.setenv(k, v)
    status, out = call(f"{server}/api/runs/{run['id']}/email", {"to": "t@example.com"})
    assert status == 502 and "error" in json.loads(out) and "p" != json.loads(out)["error"]


def test_smtp_verifies_the_server_certificate(monkeypatch):
    from cornerbrief.email_delivery import SmtpProvider
    seen = {}
    class FakeSMTP:
        def __init__(self, host, port, timeout=0): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, context=None): seen["context"] = context
        def login(self, user, password): pass
        def send_message(self, mail): pass
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    for k, v in dict(EMAIL_FROM="a@example.com", SMTP_HOST="h", SMTP_USER="u", SMTP_PASSWORD="p").items():
        monkeypatch.setenv(k, v)
    SmtpProvider().send(dict(to="t@example.com", subject="s", body="b"))
    assert seen["context"] is not None and seen["context"].check_hostname
