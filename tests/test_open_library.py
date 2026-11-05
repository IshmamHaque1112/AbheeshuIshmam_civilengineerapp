"""Open Library reading stays useful, polite and separate from the checks."""
import io, json
import pytest
import cornerbrief.library as library
from cornerbrief.data_loader import load_corner
from cornerbrief.llm import ReplayClient
from cornerbrief.orchestrator import analyze
from cornerbrief.review_export import approve, to_markdown
from test_web_and_fetch import call, server  # noqa: F401


def book(title="Streets for People", key="/works/OL1W"):
    return dict(title=title, author_name=["A One", "B Two", "C Three", "D Four"], first_publish_year=1961, key=key)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(library, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(library, "MIN_GAP", 0)
    monkeypatch.setattr(library, "_unreachable_until", 0.0)
    monkeypatch.setattr("cornerbrief.orchestrator.RUNS", tmp_path / "runs")
    monkeypatch.setenv("OPEN_LIBRARY_CONTACT", "team@example.com")
    monkeypatch.setenv("DEMO_MODE", "true")


@pytest.fixture
def requests(monkeypatch):
    seen = []
    def fake(req, timeout=0):
        seen.append(req)
        q = req.full_url.split("q=")[1].split("&")[0]
        return io.BytesIO(json.dumps(dict(docs=[book(q, f"/works/{abs(hash(q))}W")])).encode())
    monkeypatch.setattr("urllib.request.urlopen", fake)
    return seen


def offline(monkeypatch):
    def fail(req, timeout=0):
        raise OSError("no route")
    monkeypatch.setattr("urllib.request.urlopen", fail)


def test_off_without_a_contact_and_makes_no_request(monkeypatch, requests):
    monkeypatch.delenv("OPEN_LIBRARY_CONTACT")
    assert library.search_books("architecture")["enabled"] is False and requests == []
    assert library.background_reading()["items"] == [] and requests == []


def test_search_identifies_the_app_and_keeps_citations_only(requests):
    result = library.search_books("  architecture   of  streets ")
    req = requests[0]
    assert "q=architecture+of+streets" in req.full_url and "limit=8" in req.full_url and "fields=title" in req.full_url
    assert "team@example.com" in req.get_header("User-agent")
    assert set(result["items"][0]) == {"title", "authors", "year", "url", "topic"}


def test_default_topics_include_architecture_and_no_corner_details(requests):
    library.search_books()
    urls = " ".join(r.full_url for r in requests)
    assert len(requests) == len(library.TOPICS) and "architecture" in urls
    assert "THOMSON" not in urls.upper() and "cornerid" not in urls


def test_repeat_search_uses_saved_results(requests):
    library.search_books("architecture")
    library.search_books("ARCHITECTURE")
    assert len(requests) == 1


def test_expired_results_are_requested_again(requests, monkeypatch):
    library.search_books("architecture")
    monkeypatch.setattr(library, "MAX_AGE", -1)
    library.search_books("architecture")
    assert len(requests) == 2


def test_older_results_are_used_when_offline(requests, monkeypatch):
    library.search_books("architecture")
    monkeypatch.setattr(library, "MAX_AGE", -1)
    offline(monkeypatch)
    result = library.search_books("architecture")
    assert result["items"] and "older" in result["note"]


def test_outage_gives_a_clear_note_and_stops_repeated_waiting(monkeypatch):
    calls = []
    def fail(req, timeout=0):
        calls.append(req)
        raise OSError("no route to secret-host")
    monkeypatch.setattr("urllib.request.urlopen", fail)
    result = library.search_books()
    assert result["items"] == [] and "couldn't be reached" in result["note"] and "secret-host" not in result["note"]
    assert len(calls) == 1
    library.search_books("architecture")
    assert len(calls) == 1


def test_one_failed_topic_keeps_the_others(monkeypatch):
    def partial(req, timeout=0):
        if "drainage" in req.full_url:
            raise OSError("no route")
        return io.BytesIO(json.dumps(dict(docs=[book(key="/works/" + str(abs(hash(req.full_url))))])).encode())
    monkeypatch.setattr("urllib.request.urlopen", partial)
    result = library.search_books()
    assert result["items"] and "older" in result["note"]


def test_no_matches_get_their_own_message(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=0: io.BytesIO(b'{"docs":[]}'))
    assert "no books" in library.search_books("zzzz")["note"]


@pytest.mark.parametrize("query", ["", " ", "a", "x" * 81, 5])
def test_bad_queries_are_refused(query, requests):
    with pytest.raises(ValueError):
        library.search_books(query)
    assert requests == []


def test_a_packet_never_waits_for_open_library(monkeypatch):
    def fail(req, timeout=0):
        raise AssertionError("A run must not call Open Library")
    monkeypatch.setattr("urllib.request.urlopen", fail)
    run = analyze(load_corner("standard"), client=ReplayClient("standard"))
    assert run["background"]["items"] == [] and run["state"]


def test_reading_cannot_change_any_result(requests):
    before = analyze(load_corner("standard"), client=ReplayClient("standard"))
    library.search_books()
    after = analyze(load_corner("standard"), client=ReplayClient("standard"))
    for field in ("state", "state_reason", "rule_results", "design_targets", "evidence", "site_visit", "brief"):
        assert before[field] == after[field]
    assert after["background"]["items"]


def test_reading_isnt_sent_to_agents(requests):
    library.search_books()
    seen = []
    class Spy(ReplayClient):
        def call(self, agent, attempt, system, payload, schema, tier="main"):
            seen.append(json.dumps(payload))
            return super().call(agent, attempt, system, payload, schema, tier)
    analyze(load_corner("standard"), client=Spy("standard"))
    assert seen and not any(topic.replace(" ", "+") in text or topic in text for text in seen for topic in library.TOPICS)


def test_released_packet_lists_saved_reading_with_authors(requests):
    run = analyze(load_corner("standard"), client=ReplayClient("standard"))
    library.search_books()
    text = to_markdown(approve(run, "R"))
    assert "Background reading" in text and "by A One, B Two, C Three" in text and "D Four" not in text and "1961" in text and "do not affect" in text


def test_reading_route(server, monkeypatch):
    monkeypatch.setattr(library, "fetch_topic", lambda q, contact, base=None, limit=3: [dict(title="T", authors=[], year=None, url="https://x/" + q, topic=q)])
    status, body = call(server + "/api/reading?q=architecture")
    assert status == 200 and json.loads(body)["items"]
    assert call(server + "/api/reading?q=a")[0] == 400
    run = json.loads(call(server + "/api/corners/standard/run", {})[1])
    assert run["features"]["reading"] is True
    monkeypatch.delenv("OPEN_LIBRARY_CONTACT")
    assert json.loads(call(server + "/api/reading?q=architecture")[1])["enabled"] is False
