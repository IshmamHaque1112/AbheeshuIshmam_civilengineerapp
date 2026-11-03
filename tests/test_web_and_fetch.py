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


def test_real_corner_fixture_runs_with_unknown_limits(tmp_path, monkeypatch):
    from cornerbrief.llm import ReplayClient
    from cornerbrief.orchestrator import analyze
    corner = dict(key="standard", label="A and B", data_kind="NYC Open Data", context=dict(inside_nyc=True, work_type="corner_ramp_row", road_control="not_recorded"),
                  locations=[{**LOC, "gutter_slope": "1", "counter_slope": "2"}], progress=[{"cornerid": 1, "construc_2": "Constructed", "construc_1": "2022/01/01"}], complaints=[])
    monkeypatch.setattr("cornerbrief.orchestrator.RUNS", tmp_path)
    run = analyze(corner, client=ReplayClient("standard"))
    assert all(o["result"] in ("unknown", "not applicable") for o in run["rule_results"])
    assert run["planning"] is None
