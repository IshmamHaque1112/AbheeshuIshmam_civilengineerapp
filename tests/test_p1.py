"""P1 contracts: real query bounds, trace request/response flow and human-work dependencies."""
import json
from types import SimpleNamespace
import pytest
from cornerbrief import search, config
from cornerbrief.app import public
from cornerbrief.data_loader import load_corner
from cornerbrief.llm import AgentOutputError, LiveClient, OfflineClient
from cornerbrief.models import RecordsOutput
from cornerbrief.orchestrator import analyze, rerun_with_field
from cornerbrief.trace import TracingClient, public_trace, redact
from scripts.role_test import template, validate
from test_web_and_fetch import server, call, LOC


@pytest.mark.parametrize("borough,street", [(None,None),("", " "),("wrong",None),(5,"THOMSON"),("QUEENS",5),(None,"%"),(None,"x"),(None,"a"*81),(None,"x\nOR 1=1")])
def test_search_rejects_invalid_or_unbounded_filters(borough, street, monkeypatch):
    monkeypatch.setattr(search.fetch, "get", lambda _: pytest.fail("Invalid input must not query NYC"))
    with pytest.raises(ValueError):
        search.search(borough, street)


def test_search_is_bounded_and_handles_unmatched_ids(monkeypatch):
    seen=[]
    def get(url):
        seen.append(url)
        return [{**LOC,"cornerid":i,"stname1":"THOMSON","stname2":"A"} for i in range(1,102)]
    monkeypatch.setattr(search.fetch,"get",get)
    out=search.search("QUEENS", "O'Brien")
    assert out["bounded"] and len(out["corners"])==100 and len(seen)==1
    assert "%24limit=101" in seen[0] and "O%27%27BRIEN" in seen[0]
    assert out["sources"][0]["url"]==seen[0]


def fake_nyc(url):
    if search.fetch.LOC in url:
        return [{**LOC,"stname1":"THOMSON","stname2":"TEST STREET"}]
    return []  # Missing progress/complaint joins must be preserved, not manufactured.


def test_pull_immutable_snapshots_unknown_units_and_rerun(tmp_path, monkeypatch):
    monkeypatch.setattr(search,"DATA",tmp_path)
    monkeypatch.setattr("cornerbrief.data_loader.DATA",tmp_path)
    from cornerbrief.paths import DATA
    for file in ("data_dictionary.yaml", "sample_data_dictionary.yaml"):
        (tmp_path/file).write_text((DATA/file).read_text())
    monkeypatch.setattr(search.fetch,"get",fake_nyc)
    monkeypatch.setattr("cornerbrief.orchestrator.RUNS",tmp_path/"runs")
    key=search.pull("1")
    corner=load_corner(key)
    assert corner["progress"]==[] and corner["complaints"]==[] and len(corner["source_provenance"])==3
    out=analyze(corner,client=OfflineClient())
    assert all(o["result"] in ("unknown","not applicable") and not o["preview"] for o in out["rule_results"])
    new=rerun_with_field(out,[dict(key="corner:sidewalk_width",value=9)],"2026-11-02","Actual measurer test fixture",client=OfflineClient())
    assert new["corner"]["key"]==key and new["approval"] is None
    assert load_corner(key)["locations"]==corner["locations"]
    assert new["planning"] is None


@pytest.mark.parametrize("cid", ["0","-1","1 OR 1=1","1.1","12345678901","../x"])
def test_pull_rejects_non_ids(cid):
    with pytest.raises(ValueError): search.pull(cid)


def test_pull_rejects_truncation_and_mismatched_ids(monkeypatch):
    monkeypatch.setattr(search.fetch,"get", lambda _: [LOC]*21)
    with pytest.raises(ValueError,match="bounded"):search.pull("1")
    monkeypatch.setattr(search.fetch,"get", lambda _: [{**LOC,"cornerid":2}])
    with pytest.raises(ValueError,match="mismatched"):search.pull("1")


def test_search_http_flow_and_errors(server, monkeypatch, tmp_path):
    monkeypatch.setattr(search,"DATA",tmp_path)
    monkeypatch.setattr("cornerbrief.data_loader.DATA",tmp_path)
    from cornerbrief.paths import DATA
    (tmp_path/"data_dictionary.yaml").write_text((DATA/"data_dictionary.yaml").read_text())
    monkeypatch.setattr(search.fetch,"get",fake_nyc)
    assert call(server+"/api/search")[0]==400
    status,body=call(server+"/api/search?borough=QUEENS&street=THOMSON")
    assert status==200 and json.loads(body)["corners"][0]["cornerid"]==1
    status,body=call(server+"/api/real/1/run",{})
    out=json.loads(body)
    assert status==200 and out["mode"]=="offline, no agents" and out["trace"]
    assert out["source_provenance"] and call(server+f"/api/runs/{out['id']}/download")[0]==409
    monkeypatch.setattr(search.fetch,"get",lambda _: [])
    assert json.loads(call(server+"/api/search?borough=QUEENS")[1])["corners"]==[]
    def fail(_):raise OSError("secret internal error")
    monkeypatch.setattr(search.fetch,"get",fail)
    status,body=call(server+"/api/search?borough=QUEENS")
    assert status==502 and b"secret internal" not in body


def provider(tmp_path,monkeypatch,text):
    import cornerbrief.llm as llm
    monkeypatch.setattr(llm,"CACHE",tmp_path)
    monkeypatch.setenv("MAIN_MODEL","test-model")
    calls=[]
    def create(**request):
        calls.append(request)
        return SimpleNamespace(content=[SimpleNamespace(type="text",text=text)],usage=SimpleNamespace(input_tokens=17,output_tokens=9))
    client=LiveClient.__new__(LiveClient)
    client.client=SimpleNamespace(messages=SimpleNamespace(create=create))
    return client,calls


def test_provider_request_response_trace_and_cache(tmp_path,monkeypatch):
    response=json.dumps(dict(summary="Loaded records",labels=[]))
    live,calls=provider(tmp_path,monkeypatch,response)
    trace=TracingClient(live)
    payload={"corner":"test","evidence":[]}
    output,usage=trace.call("records",0,"system instruction",payload,RecordsOutput)
    assert calls[0]["model"]=="test-model" and json.loads(calls[0]["messages"][0]["content"])==payload
    assert "system instruction" in calls[0]["system"] and "summary" in calls[0]["system"]
    shown=public_trace({"trace_events":trace.calls})[0]
    assert shown["response"]==response and shown["request"]["input"]==payload
    assert shown["origin"]=="actual provider" and shown["tokens"]==dict(input=17,output=9)
    trace.call("records",0,"system instruction",payload,RecordsOutput)
    cached=public_trace({"trace_events":trace.calls})[1]
    assert len(calls)==1 and cached["origin"]=="cached provider response" and cached["tokens"]==dict(input=0,output=0)


def test_malformed_provider_response_retains_actual_usage(tmp_path,monkeypatch):
    live,calls=provider(tmp_path,monkeypatch,'{"api_key":"sk-ant-secret123"}')
    trace=TracingClient(live)
    with pytest.raises(AgentOutputError):trace.call("records",0,"instruction",{},RecordsOutput)
    shown=public_trace({"trace_events":trace.calls})[0]
    assert shown["tokens"]==dict(input=17,output=9) and shown["origin"]=="actual provider"
    assert "sk-ant-secret123" not in json.dumps(shown) and shown["status"]=="failed"


def test_replay_and_offline_are_not_model_usage():
    replay=public(analyze(load_corner("standard"),save=False))
    assert {t["origin"] for t in replay["trace"]}=={"saved replay"}
    offline=public(analyze(load_corner("standard"),client=OfflineClient(),save=False))
    assert {t["origin"] for t in offline["trace"]}=={"deterministic offline"}
    assert replay["tokens"]==offline["tokens"]==dict(input=0,output=0)
    assert all(t["request"]["response_schema"] and t["request"]["system"] for t in replay["trace"])


def test_trace_redacts_nested_keys_and_text():
    value=dict(password="hidden", input={"authorization":"hidden","nested":["Bearer hidden", 'api_key="hidden"', 'sk-ant-hidden']})
    assert "hidden" not in json.dumps(redact(value))


def test_planning_switch_does_not_supply_human_authorization(monkeypatch,tmp_path):
    monkeypatch.setenv("SHOW_LABELS_AND_PLANS","true")
    monkeypatch.setattr(config,"PLANNING_RELEASE",tmp_path/"absent")
    assert not config.labels_enabled()
    out=analyze(load_corner("standard"),save=False)
    assert out["planning"] is None and out["label"] is None


def test_recorded_authorization_still_needs_switch(planning_release,monkeypatch):
    monkeypatch.delenv("SHOW_LABELS_AND_PLANS",raising=False)
    assert not config.labels_enabled()
    monkeypatch.setenv("SHOW_LABELS_AND_PLANS","true")
    assert config.labels_enabled()
    record=json.loads(planning_release.read_text());record["r28_cases"]["10"]="pending"
    planning_release.write_text(json.dumps(record))
    assert not config.labels_enabled()


def test_role_capture_starts_pending_and_rejects_role_play():
    pending=template()
    assert pending["status"]=="pending human participation" and validate(pending)
    assert all(not s["actual_human"] and s["corrections"] is None for s in pending["sessions"])
    assert any("actual human" in issue for issue in validate(pending))


def capture_fixture():
    """Synthetic schema fixture only. Not a participant result."""
    result=template()
    result.update(corner_id="fixture",packet_run_id="fixture",app_commit="fixture",data_kind="SAMPLE DATA",facilitator="Test",source_urls=["https://example.test"])
    for session in result["sessions"]:
        session.update(participant="Synthetic validation fixture",actual_human=True,started_at="2026-01-01T00:00:00+00:00",ended_at="2026-01-01T00:01:00+00:00",elapsed_seconds=60,corrections=[],missed_issues=[],permission_misreads=[],notes="Synthetic validator test only")
    return result


def test_role_capture_requires_metrics_times_and_permission_followup():
    fixture=capture_fixture()
    assert validate(fixture)==[]
    fixture["sessions"][0]["elapsed_seconds"]=1
    assert validate(fixture)
    fixture=capture_fixture();fixture["sessions"][1]["permission_misreads"]=["Thought release meant proceed"]
    assert any("follow-up" in issue for issue in validate(fixture))
    fixture["follow_up"]="Stop demo and change release wording; retest with a real person."
    assert validate(fixture)==[]


def test_real_snapshot_provenance_survives_release_and_download(monkeypatch,tmp_path):
    from cornerbrief.review_export import approve, to_markdown
    monkeypatch.setattr('cornerbrief.orchestrator.RUNS',tmp_path)
    run=analyze(load_corner('real_1024569_c83661efedaa'),client=OfflineClient(),save=False)
    assert run['source_provenance'] and all(o['result'] in ('unknown','not applicable') for o in run['rule_results'])
    packet=to_markdown(approve(run,'Test release only'))
    assert '1024569' in packet and 'NYC source retrievals' in packet and '2026-11-05T15:48' in packet
    assert 'not a compliance decision' in packet and '$' not in packet


def test_role_cli_creates_pending_capture_and_refuses_to_overwrite(tmp_path):
    import subprocess,sys
    capture=tmp_path/'pending.json'
    command=[sys.executable,'scripts/role_test.py']
    init=subprocess.run(command+['init',str(capture)],capture_output=True,text=True)
    assert init.returncode==0 and 'actual human' in init.stdout
    before=capture.read_bytes()
    again=subprocess.run(command+['init',str(capture)],capture_output=True,text=True)
    assert again.returncode!=0 and capture.read_bytes()==before
    check=subprocess.run(command+['check',str(capture)],capture_output=True,text=True)
    assert check.returncode==1 and 'actual human participation' in check.stdout


@pytest.mark.parametrize('value',["1.5","NaN","Infinity","-1",None,True])
def test_nyc_id_normalization_never_rounds_invalid_ids(value):
    assert search.fetch.num([dict(cornerid=value)])[0]['cornerid'] is None


def test_city_trace_hides_costs_and_currency_even_for_legacy_saved_runs():
    trace=public_trace(dict(agent_log=[dict(agent='brief_writer',attempt=0,input=dict(cost=dict(label='Test',lines=[dict(item='concrete',quantity=1,rate=100,amount=100)],base=100)),output={'summary':'$100 or USD 200'},usage={})]))
    text=json.dumps(trace)
    assert '$100' not in text and 'USD 200' not in text and '"base"' not in text and '"rate"' not in text
    from cornerbrief.guards import check_text
    assert check_text('$100',{'value':100})


@pytest.mark.parametrize('bad',[[],None,{},dict(decision='enable provisional concepts',reviewed_by='Reviewer',reviewed_on='2099-01-01'),dict(decision='enable provisional concepts',reviewed_by='Reviewer',reviewed_on='2026-01-01',tested_commit=5)])
def test_malformed_release_fails_closed(bad,monkeypatch,tmp_path):
    path=tmp_path/'release.json';path.write_text(json.dumps(bad))
    monkeypatch.setattr(config,'PLANNING_RELEASE',path)
    monkeypatch.setenv('SHOW_LABELS_AND_PLANS','true')
    assert config.labels_enabled() is False


@pytest.mark.parametrize('seconds',[float('nan'),float('inf'),-1,True])
def test_role_capture_requires_finite_real_elapsed_time(seconds):
    fixture=capture_fixture();fixture['sessions'][0]['elapsed_seconds']=seconds
    assert any('elapsed seconds' in issue for issue in validate(fixture))
