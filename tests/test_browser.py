"""Browser checks for quick clicks and slow responses. These skip if Playwright isn't installed."""
import base64, socket, threading, time
import pytest

playwright_api = pytest.importorskip("playwright.sync_api")
import uvicorn  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 40


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    import cornerbrief.orchestrator as orch
    import cornerbrief.field as field
    orch.RUNS = tmp_path_factory.mktemp("runs")
    field.PHOTOS = tmp_path_factory.mktemp("photos")
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


@pytest.fixture(scope="module")
def browser():
    with playwright_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium isn't available: {exc}")
        yield b
        b.close()


@pytest.fixture
def page(browser, base):
    context = browser.new_context()
    pg = context.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    pg.goto(base + "/")
    pg.wait_for_selector(".status strong")
    yield pg
    assert pg.errors == []
    context.close()


def pick(page, n):
    key = {1: "standard", 2: "constrained", 3: "missing_or_stale"}[n]
    page.click(f'#picker button[data-key="{key}"]')


def slow(page, pattern, seconds=0.6):
    def handler(route):
        time.sleep(seconds)
        route.continue_()
    page.route(pattern, handler)


def test_late_response_cant_replace_the_chosen_corner(page):
    slow(page, "**/api/corners/constrained/run")
    pick(page, 2)
    pick(page, 3)
    page.wait_for_selector(".status.stop")
    page.wait_for_timeout(900)
    assert page.locator(".status.stop").count() == 1 and "rebuilt" in page.inner_text(".lead")


def test_photo_without_a_value_gets_a_message(page):
    page.fill("#by", "A B")
    page.set_input_files('#field input[type=file] >> nth=0', files=[dict(name="a.png", mimeType="image/png", buffer=PNG)])
    page.click("#rerun")
    page.wait_for_selector("#fieldmsg.error")
    assert "photo" in page.inner_text("#fieldmsg").lower() and page.locator(".changes").count() == 0


def test_switching_during_a_rerun_keeps_the_entry_with_its_corner(page):
    slow(page, "**/field")
    page.fill("#by", "A B")
    page.fill('#field [data-key="corner:sidewalk_width"]', "10")
    page.click("#rerun")
    pick(page, 2)
    page.wait_for_function("document.querySelector('.lead')?.innerText.includes('complex')")
    page.wait_for_timeout(900)
    assert page.locator(".changes").count() == 0
    pick(page, 1)
    page.wait_for_selector(".changes")
    assert page.input_value('#field [data-key="corner:sidewalk_width"]') == "10"


def test_release_and_rerun_cant_cross(page):
    page.fill("#reviewer", "R")
    page.fill("#by", "A B")
    page.fill('#field [data-key="corner:sidewalk_width"]', "10")
    page.evaluate("document.querySelector('#approve').click(); document.querySelector('#rerun').click()")
    page.wait_for_selector("#release a.button")
    page.wait_for_timeout(300)
    assert page.locator(".changes").count() == 0
    page.click("#rerun")
    page.wait_for_selector(".changes")
    assert page.locator("#approve").count() == 1


def test_reload_returns_to_the_same_corner(page):
    pick(page, 3)
    page.wait_for_selector(".status.stop")
    page.reload()
    page.wait_for_selector(".status.stop")
    assert page.get_attribute('#picker button[data-key="missing_or_stale"]', "aria-current") == "true"


def test_missing_saved_version_falls_back_to_the_records(page):
    page.evaluate("sessionStorage.setItem('latest:constrained', 'gone123')")
    pick(page, 2)
    page.wait_for_function("document.querySelector('.lead')?.innerText.includes('complex')")
    assert page.evaluate("sessionStorage.getItem('latest:constrained')") is None


def test_server_error_shows_a_readable_message(page):
    page.route("**/api/corners/constrained/run", lambda r: r.fulfill(status=500, body="Internal Server Error", content_type="text/plain"))
    pick(page, 2)
    page.wait_for_selector(".empty.error")
    assert "Unexpected" not in page.inner_text(".empty.error") and "JSON" not in page.inner_text(".empty.error")


def test_preview_tags_dont_read_as_permission(page):
    text = page.inner_text("#main")
    assert "Within limit if confirmed" not in text and "Calculation within limit, unreviewed" in text


def search_result(label="THOMSON and TEST", cid=1):
    import json
    return json.dumps(dict(corners=[dict(cornerid=cid,label=label)],note="First 100 ramp rows only.",sources=[dict(dataset="ufzp-rrqu",url="https://data.cityofnewyork.us/resource/ufzp-rrqu.json")]))


def test_real_search_loading_empty_error_and_input_validation(page):
    page.click('#search-form button')
    assert "Choose a borough" in page.inner_text('#search-status')
    page.select_option('#borough','QUEENS')
    page.route('**/api/search?**', lambda route: route.fulfill(status=200,content_type='application/json',body='{"corners":[],"note":"First 100 ramp rows only.","sources":[]}'))
    page.click('#search-form button')
    page.wait_for_function("document.querySelector('#search-status').innerText.includes('No corners found')")
    page.unroute('**/api/search?**')
    page.route('**/api/search?**',lambda route: route.fulfill(status=502,content_type='application/json',body='{"error":"NYC unavailable. Use offline samples."}'))
    page.click('#search-form button')
    page.wait_for_function("document.querySelector('#search-status').innerText.includes('NYC unavailable')")
    assert page.locator('.status').count()==1  # Samples stay usable.


def test_real_search_response_after_sample_selection_is_discarded(page):
    page.select_option('#borough','QUEENS')
    # Hold the actual HTTP request until a different selection expresses newer intent.
    page.route('**/api/search?**', lambda route: route.fulfill(status=200,content_type='application/json',body=search_result()))
    page.evaluate('''() => {
      const original = window.fetch;
      window.fetch = async (...args) => {
        const result = await original(...args);
        if (String(args[0]).startsWith('/api/search')) await new Promise(resolve => window.resumeSearch = resolve);
        return result;
      };
    }''')
    page.click('#search-form button')
    page.wait_for_function('!!window.resumeSearch')
    pick(page,3)
    page.wait_for_selector('.status.stop')
    page.evaluate('window.resumeSearch()')
    page.wait_for_timeout(100)
    assert page.locator('[data-real]').count()==0


def test_late_real_pull_cannot_replace_sample_and_trace_is_inspectable(page, base):
    import json
    from cornerbrief.orchestrator import analyze
    from cornerbrief.data_loader import load_corner
    from cornerbrief.app import public
    packet=public(analyze(load_corner('standard'),save=False))
    packet['corner'].update(key='real_1_aaaaaaaaaaaa',data_kind='NYC Open Data',label='THOMSON and TEST — HTTP fixture')
    page.route('**/api/search?**',lambda route: route.fulfill(status=200,content_type='application/json',body=search_result()))
    page.route('**/api/real/1/run',lambda route: route.fulfill(status=200,content_type='application/json',body=json.dumps(packet)))
    page.evaluate('''() => {
      const original = window.fetch;
      window.fetch = async (...args) => {
        const result = await original(...args);
        if (String(args[0]).includes('/api/real/')) await new Promise(resolve => window.resumePull = resolve);
        return result;
      };
    }''')
    page.select_option('#borough','QUEENS');page.click('#search-form button')
    page.wait_for_selector('[data-real]');page.click('[data-real]')
    assert "Loading this corner" in page.inner_text('#main')
    page.wait_for_function('!!window.resumePull')
    pick(page,3);page.wait_for_selector('.status.stop')
    page.evaluate('window.resumePull()');page.wait_for_timeout(100)
    assert page.locator('.status.stop').count()==1
    pick(page,1);page.wait_for_selector('.status')
    heading=page.get_by_role('heading',name='Agent trace',exact=True)
    section=heading.locator('..')
    assert 'saved replay' in section.inner_text() and 'input tokens 0' in section.inner_text()
    section.locator('summary').first.click()
    assert 'response_schema' in section.locator('pre').first.inner_text()
    assert '<script>' not in section.inner_html()


def test_static_export_is_actual_ui_without_backend_calls(browser):
    from pathlib import Path
    context=browser.new_context()
    pg=context.new_page();errors=[];requests=[]
    pg.on('pageerror',lambda e:errors.append(str(e)))
    pg.on('request',lambda r:requests.append(r.url))
    pg.goto((Path(__file__).resolve().parent.parent/'.helix/output/index.html').as_uri())
    pg.wait_for_selector('.status')
    assert 'saved sample' in pg.inner_text('#search-status')
    assert pg.locator('#search-form button').is_disabled()
    pick(pg,3);pg.wait_for_selector('.status.stop')
    assert pg.get_by_role('heading',name='Agent trace',exact=True).count()==1
    assert not errors and all(url.startswith('file:') for url in requests)
    context.close()


def test_static_export_preview_orbits_the_python_built_model(browser):
    from pathlib import Path
    context=browser.new_context(viewport=dict(width=1280,height=900))
    pg=context.new_page();errors=[];requests=[]
    pg.on('pageerror',lambda e:errors.append(str(e)))
    pg.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
    pg.on('request',lambda r:requests.append(r.url))
    pg.goto((Path(__file__).resolve().parent.parent/'.helix/output/index.html').as_uri())
    pg.wait_for_selector('.status')
    pg.click('#preview-link');pg.wait_for_selector('#quantities tr')
    assert '55 sf' in pg.inner_text('#quantities') and 'Editing dimensions needs the local' in pg.inner_text('#status')
    assert pg.locator('#width_ft').is_disabled() and 'Synthetic exploration' in pg.inner_text('#notice')
    box=pg.locator('#scene').bounding_box();before=pixels(pg)
    pg.mouse.move(box['x']+200,box['y']+200);pg.mouse.down();pg.mouse.move(box['x']+300,box['y']+230);pg.mouse.up()
    assert pixels(pg)!=before
    pg.click('text=Back to corner packets');pg.wait_for_selector('.status')
    assert not errors and all(url.startswith('file:') for url in requests)
    context.close()


def test_selecting_real_corner_renders_saved_actual_data_and_provenance(page, monkeypatch, tmp_path):
    # The pull endpoint writes a snapshot; keep browser-test writes outside source data.
    import shutil
    from cornerbrief import search, data_loader
    test_data = tmp_path / "data"
    shutil.copytree(data_loader.DATA, test_data)
    monkeypatch.setattr(search, "DATA", test_data)
    monkeypatch.setattr(data_loader, "DATA", test_data)
    """Browser/HTTP flow uses the attributable live snapshot, not another live network request."""
    from cornerbrief.data_loader import load_corner
    from cornerbrief import search
    snapshot=load_corner('real_1024569_c83661efedaa')
    def get(url):
        if search.fetch.LOC in url:return snapshot['locations']
        if search.fetch.PROG in url:return snapshot['progress']
        return snapshot['complaints']
    monkeypatch.setattr(search.fetch,'get',get)
    page.select_option('#borough','QUEENS');page.fill('#street','THOMSON')
    page.click('#search-form button');page.wait_for_selector('[data-real="1024569"]')
    page.click('[data-real="1024569"]');page.wait_for_selector('.status.stop')
    assert 'Real test corner from NYC Open Data' in page.inner_text('.alert')
    assert 'ufzp-rrqu' in page.inner_text('#main') and 'Source retrievals' in page.inner_text('#main')
    assert 'deterministic offline' in page.inner_text('#main')
    assert page.locator('#approve').count()==1 and page.locator('#model').count()==0
    page.reload();page.wait_for_selector('.status.stop')
    assert 'Real test corner from NYC Open Data' in page.inner_text('.alert')


def test_external_search_label_is_rendered_as_text(page):
    label='<img src=x onerror="window.injected=true">'
    page.route('**/api/search?**',lambda route:route.fulfill(status=200,content_type='application/json',body=search_result(label=label)))
    page.select_option('#borough','QUEENS');page.click('#search-form button')
    page.wait_for_selector('[data-real]')
    assert label in page.inner_text('[data-real]')
    assert page.locator('#search-results img').count()==0 and not page.evaluate('!!window.injected')


def test_search_doesnt_leave_a_loading_corner_stuck(page):
    slow(page, "**/api/corners/constrained/run")
    page.route("**/api/search?**", lambda r: r.fulfill(status=200, content_type="application/json", body='{"corners":[],"note":"n","sources":[]}'))
    pick(page, 2)
    page.select_option("#borough", "QUEENS")
    page.click("#search-form button")
    page.wait_for_function("document.querySelector('.lead')?.innerText.includes('complex')", timeout=5000)


def test_choosing_a_corner_doesnt_leave_search_status_stuck(page):
    page.evaluate('''() => { const f = window.fetch; window.fetch = async (...a) => { if (String(a[0]).startsWith('/api/search')) await new Promise(() => {}); return f(...a); }; }''')
    page.select_option("#borough", "QUEENS")
    page.click("#search-form button")
    pick(page, 3)
    page.wait_for_selector(".status.stop")
    assert "Searching" not in page.inner_text("#search-status")


def test_saved_real_snapshot_renders_on_desktop_and_phone(browser, base):
    for viewport in (dict(width=1440, height=900), dict(width=390, height=800)):
        context = browser.new_context(viewport=viewport)
        pg = context.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/")
        pg.wait_for_selector(".status strong")
        pg.evaluate("sessionStorage.clear()")
        pg.evaluate("fetch('/api/corners/real_1024569_c83661efedaa/run',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).then(r=>r.json()).then(o=>{sessionStorage.setItem('latest:'+o.corner.key,o.id);sessionStorage.setItem('chosen',o.corner.key);})")
        pg.wait_for_function("sessionStorage.getItem('chosen')")
        pg.reload()
        pg.wait_for_selector(".status.stop")
        text = pg.inner_text("#main")
        assert "Real test corner" in text and "VAN DAM" in text and "road owner" in text
        assert pg.evaluate("document.documentElement.scrollWidth > innerWidth") is False
        assert errors == []
        context.close()


READING = '{"enabled":true,"items":[{"title":"<b>Streets</b> for People","authors":["A One"],"year":1961,"url":"https://openlibrary.org/works/OL1W","topic":"x"}],"note":"Background only. These books do not affect any rule, rate or design value."}'


def test_reading_is_hidden_unless_turned_on(page):
    assert page.locator("#reading").count() == 0


def test_reading_loads_after_the_packet_and_searches(browser, base, monkeypatch):
    monkeypatch.setenv("OPEN_LIBRARY_CONTACT", "team@example.com")
    context = browser.new_context()
    pg = context.new_page()
    urls = []
    def answer(route):
        urls.append(route.request.url)
        route.fulfill(status=200, content_type="application/json", body=READING)
    pg.route("**/api/reading**", answer)
    pg.goto(base + "/")
    pg.wait_for_selector("#reading-list a")
    item = pg.inner_text("#reading-list li")
    assert "<b>Streets</b> for People" in item and "A One" in item and "1961" in item
    pg.fill("#reading-q", "architecture of streets")
    pg.click("#reading-form button")
    pg.wait_for_function("document.querySelector('#reading-note').innerText.includes('Background only')")
    assert any("q=architecture" in u for u in urls)
    pg.unroute("**/api/reading**")
    pg.route("**/api/reading**", lambda r: r.fulfill(status=400, content_type="application/json", body='{"error":"Enter 2 to 80 characters to search Open Library."}'))
    pg.fill("#reading-q", "a")
    pg.click("#reading-form button")
    pg.wait_for_function("document.querySelector('#reading-note').innerText.includes('Enter 2 to 80')")
    assert pg.locator(".status").count() == 1
    context.close()


def test_site_visit_list_downloads_without_a_release(page):
    assert page.locator("#approve").count() == 1
    with page.expect_download() as info:
        page.click("#site-visit-download")
    download = info.value
    assert download.suggested_filename == "cornerbrief_site_visit_standard.md"
    text = open(download.path(), encoding="utf-8").read()
    assert "What to do" in text and "no affiliation" in text and "Value found" in text


def test_demo_list_shows_the_real_corner_in_order(page):
    assert page.eval_on_selector_all("#picker button", "b => b.map(x => x.dataset.key)") == ["standard", "constrained", "real_test", "missing_or_stale"]
    page.click('#picker button[data-key="real_test"]')
    page.wait_for_selector(".status.stop")
    assert "VAN DAM" in page.inner_text("#main") and "Real test corner" in page.inner_text("#main")


@pytest.fixture
def preview_page(browser, base):
    context = browser.new_context(viewport=dict(width=1280, height=900))
    pg = context.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    pg.on("console", lambda m: pg.errors.append(m.text) if m.type == "error" else None)
    pg.goto(base + "/preview.html")
    pg.wait_for_selector("#quantities tr")
    yield pg
    assert pg.errors == []  # Includes console errors, so a routine typing mistake mustn't log a failed request
    context.close()


def pixels(page):
    return page.evaluate("document.querySelector('#scene').toDataURL()")


def test_preview_renders_and_is_labeled_synthetic(preview_page):
    assert "Synthetic exploration" in preview_page.inner_text("#notice")
    filled = preview_page.evaluate("""() => { const c = document.querySelector('#scene'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n / (d.length / 4); }""")
    assert filled > 0.2
    assert "Rise 4.3 in" in preview_page.get_attribute("#scene", "aria-label")


def test_preview_edit_updates_model_and_quantities(preview_page):
    before, revision = pixels(preview_page), preview_page.inner_text("#revision")
    assert "55 sf" in preview_page.inner_text("#quantities")
    preview_page.fill("#length_ft", "8")
    preview_page.wait_for_function("document.querySelector('#quantities').innerText.includes('65 sf')")
    assert pixels(preview_page) != before and preview_page.inner_text("#revision") != revision
    assert "+10" in preview_page.inner_text("#quantities")
    assert "Ramp length 8 ft" in preview_page.get_attribute("#scene", "aria-label")


def test_preview_slider_updates_the_model(preview_page):
    preview_page.evaluate("""() => { const r = document.querySelector('#width_ft-range'); r.value = 8; r.dispatchEvent(new Event('input', {bubbles: true})); }""")
    preview_page.wait_for_function("document.querySelector('#scene').getAttribute('aria-label').includes('Ramp width 8 ft')")
    assert preview_page.input_value("#width_ft") == "8"


def test_preview_invalid_dimension_keeps_the_last_model_and_explains(preview_page):
    numbers, revision = preview_page.inner_text("#quantities"), preview_page.inner_text("#revision")
    preview_page.fill("#width_ft", "-3")
    preview_page.wait_for_selector("#error-width_ft:not(:empty)")
    assert "from 1 to 20" in preview_page.inner_text("#error-width_ft") and "nothing was guessed" in preview_page.inner_text("#status")
    assert preview_page.inner_text("#quantities") == numbers and preview_page.inner_text("#revision") == revision
    # The old model and quantities stay, but they're clearly marked as not matching the inputs
    assert "Not updated: fix Ramp width" in preview_page.inner_text("#stale")
    assert preview_page.get_attribute("#scene", "aria-label").startswith("Not updated. Fix Ramp width")
    assert "isstale" in preview_page.get_attribute("#quantity-section", "class")
    preview_page.fill("#width_ft", "")
    preview_page.wait_for_function("document.querySelector('#error-width_ft').innerText.includes('must be a number')")
    preview_page.click("#reset")
    preview_page.wait_for_function("document.querySelector('#status').innerText.includes('up to date')")
    assert preview_page.input_value("#width_ft") == "5" and preview_page.is_hidden("#stale")
    assert preview_page.get_attribute("#scene", "aria-label").startswith("Synthetic 3D model")


def test_preview_revision_change_flags_dependent_estimates(preview_page):
    first = preview_page.inner_text("#revision").split()[1].rstrip(".")
    preview_page.fill("#landing_length_ft", "7")
    preview_page.wait_for_function("document.querySelector('#scene').getAttribute('aria-label').includes('Landing length 7 ft')")
    text = preview_page.inner_text("#revision")
    assert f"Changed from revision {first}" in text and f"built on {first} must be recalculated" in text


def test_preview_shows_what_is_synthetic_assumed_and_unknown(preview_page):
    basis = preview_page.inner_text("#basis")
    assert "Ramp width 5 ft" in preview_page.inner_text("#basis-synthetic")
    assert "Slab thickness 4 in" in preview_page.inner_text("#basis-assumed")
    assert "Sidewalk width" in preview_page.inner_text("#basis-unknown") and "Not modeled" in basis


def test_preview_dimension_labels_stay_readable_while_orbiting(preview_page):
    box = preview_page.locator("#scene").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    overlap = """() => { const b = document.querySelector('#scene').labelBoxes, c = document.querySelector('#scene'); let n = 0;
      for (const p of b) { if (p.x < 0 || p.y < 0 || p.x + p.w > c.clientWidth || p.y + p.h > c.clientHeight) n++;
        for (const q of b) if (p !== q && p.x < q.x + q.w && q.x < p.x + p.w && p.y < q.y + q.h && q.y < p.y + p.h) n++; }
      return [b.length, n]; }"""
    for step in range(10):
        preview_page.mouse.move(cx, cy); preview_page.mouse.down(); preview_page.mouse.move(cx + 55, cy + (12 if step % 2 else -12)); preview_page.mouse.up()
        assert preview_page.evaluate(overlap) == [5, 0]


def test_preview_orbit_zoom_and_pan_change_the_view(preview_page):
    box = preview_page.locator("#scene").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    start = pixels(preview_page)
    preview_page.mouse.move(cx, cy); preview_page.mouse.down(); preview_page.mouse.move(cx + 70, cy + 25); preview_page.mouse.up()
    orbit = pixels(preview_page); assert orbit != start
    preview_page.mouse.wheel(0, -400); preview_page.wait_for_timeout(100)
    zoom = pixels(preview_page); assert zoom != orbit
    preview_page.mouse.move(cx, cy); preview_page.mouse.down(button="right"); preview_page.mouse.move(cx + 60, cy - 40); preview_page.mouse.up(button="right")
    pan = pixels(preview_page); assert pan != zoom
    preview_page.click("#view-reset")
    assert pixels(preview_page) == start
    preview_page.click("#zoom-in"); assert pixels(preview_page) != start
    preview_page.click("#exaggerate")


def test_preview_makes_no_packet_requests_and_main_page_links_to_it(browser, base):
    context = browser.new_context()
    pg = context.new_page()
    urls = []
    pg.on("request", lambda r: urls.append(r.url))
    pg.goto(base + "/preview.html")
    pg.wait_for_selector("#quantities tr")
    pg.fill("#length_ft", "9")
    pg.wait_for_function("document.querySelector('#scene').getAttribute('aria-label').includes('Ramp length 9 ft')")
    assert not [u for u in urls if "/api/" in u and "/api/preview" not in u]
    assert not [u for u in urls if not u.startswith(base)]
    pg.click("text=Back to corner packets")
    pg.wait_for_selector("#preview-link")
    pg.click("#preview-link")
    pg.wait_for_selector("#notice")
    context.close()


def test_preview_draft_needs_recalculation_until_rebuilt(preview_page):
    preview_page.wait_for_function("document.querySelectorAll('#draft-steps tr').length === 7")
    assert preview_page.locator("#draft-stale").is_hidden() and preview_page.locator("#draft-rebuild").is_hidden()
    first = preview_page.inner_text("#draft-status")
    preview_page.fill("#width_ft", "7")
    preview_page.wait_for_function("!document.querySelector('#draft-stale').hidden")
    assert "Needs recalculation" in preview_page.inner_text("#draft-stale") and preview_page.inner_text("#draft-status") == first
    preview_page.click("#draft-rebuild")
    preview_page.wait_for_function("document.querySelector('#draft-stale').hidden")
    assert preview_page.inner_text("#draft-status") != first and "Unknown" in preview_page.inner_text("#draft-steps")


def test_roadmap_demos_are_hidden_by_default(browser, base):
    pg = browser.new_page(viewport=dict(width=1280, height=900))
    pg.goto(base + "/")
    pg.wait_for_selector("#picker button")
    pg.wait_for_timeout(300)
    assert pg.locator("#demo-links").is_hidden()
    assert pg.goto(base + "/demo/contractor.html").status == 404 and pg.goto(base + "/contractor.html").status == 404


def test_contractor_demo_page_is_stamped_and_lists_conflicts(browser, base, monkeypatch):
    monkeypatch.setenv("SHOW_ROADMAP_DEMOS", "true")
    pg = browser.new_page(viewport=dict(width=1280, height=900))
    pg.goto(base + "/")
    pg.wait_for_function("!document.querySelector('#demo-links').hidden")
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/demo/contractor.html")
    pg.wait_for_selector("text=4. Team and equipment sequence")
    assert pg.inner_text("#notice").startswith("DEMONSTRATION") and "Conflicts, not resolved" in pg.inner_text("#out")
    assert pg.locator("#out .demo-chip").count() == 6 and pg.locator("#out .kind.k-fictional").count() > 5 and pg.locator("#out .kind.k-real").count() > 3
    assert "$" not in pg.inner_text("body") and not errors


def test_structures_sandbox_draws_every_model(browser, base, monkeypatch):
    monkeypatch.setenv("SHOW_ROADMAP_DEMOS", "true")
    pg = browser.new_page(viewport=dict(width=1280, height=900))
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/demo/structures.html")
    pg.wait_for_selector("#fact-list li")
    for model, word in (("truss", "diagonals"), ("tower", "braces"), ("dome", "65 struts"), ("gears", "not involute")):
        pg.select_option("#model-choice", model)
        pg.wait_for_function(f"document.querySelector('#fact-list').textContent.includes('{word}')")
    assert pg.locator("#play").is_visible() and "no loads" in pg.inner_text("#notice").lower()
    pg.fill("#teeth_1", "3")
    pg.wait_for_function("document.querySelector('#teeth_1-error').textContent.length > 0")
    assert not errors
