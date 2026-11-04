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
    page.click(f"#picker button:nth-child({n})")


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
    assert page.get_attribute("#picker button:nth-child(3)", "aria-current") == "true"


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
