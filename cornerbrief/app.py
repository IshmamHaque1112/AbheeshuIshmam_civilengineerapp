"""Web API and static UI."""
from pathlib import Path
import logging
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from .config import labels_enabled, load_env
from .data_loader import list_corners
from .email_delivery import EmailBlocked, allowlist, send_brief
from . import field as field_module
from . import library
from . import preview as preview_module
from . import search as search_module
from .trace import public_trace, redact
from .cost import hide_dollars
from .orchestrator import load_run, rerun_with_field, run_corner
from .review_export import NotApproved, approve, presented, site_visit_markdown, to_markdown

load_env()
MAX_UPLOAD = 60 * 1024 * 1024


def public(run: dict) -> dict:
    shown = {k: v for k, v in presented(run).items() if k != "agent_log"}
    shown.pop("trace_events", None)
    if shown.get("planning"):
        shown["planning"] = {**shown["planning"], "cost": hide_dollars(shown["planning"]["cost"])}
    shown["trace"] = public_trace(run)
    shown["features"] = {"email": bool(allowlist()), "labels_and_plans": labels_enabled(), "reading": library.enabled()}
    return redact(shown, hide_cost=True)


def error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


class WrongOrigin(Exception):
    pass


async def _body(request: Request) -> dict:
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.headers.get("host"):
        raise WrongOrigin()  # Another website can't release a packet or send email through a person's browser
    try:
        body = await request.json()
    except ValueError as exc:
        raise ValueError("The request wasn't valid JSON.") from exc
    if not isinstance(body, dict):
        raise ValueError("The request must be a JSON object.")
    return body


async def corners(request: Request):
    return JSONResponse(await run_in_threadpool(list_corners))


async def search_corners(request: Request):
    try:
        return JSONResponse(await run_in_threadpool(search_module.search, request.query_params.get("borough"), request.query_params.get("street")))
    except ValueError as exc:
        return error(str(exc), 400)
    except Exception:
        logging.getLogger("uvicorn.error").exception("NYC search failed")
        return error("NYC Open Data could not be reached or returned invalid data. Retry, narrow your search, or use the offline samples. The terminal has details.", 502)


async def reading(request: Request):
    try:
        return JSONResponse(await run_in_threadpool(library.search_books, request.query_params.get("q")))
    except ValueError as exc:
        return error(str(exc), 400)


async def preview(request: Request):
    """Synthetic only. This never reads or writes a corner, a run or a saved file."""
    if request.method == "GET":
        return JSONResponse(preview_module.defaults())
    try:
        return JSONResponse(preview_module.build_preview(await _body(request)))
    except ValueError as exc:
        return JSONResponse({"error": str(exc), "problems": getattr(exc, "problems", None)}, status_code=400)


async def pull_corner(request: Request):
    try:
        key = await run_in_threadpool(search_module.pull, request.path_params["corner_id"])
        return JSONResponse(public(await run_in_threadpool(run_corner, key)))
    except ValueError as exc:
        return error(str(exc), 400)
    except Exception:
        logging.getLogger("uvicorn.error").exception("Loading a real corner failed")
        return error("The real corner could not be loaded. Retry or use the offline samples. The terminal has details.", 502)


async def run(request: Request):
    try:
        return JSONResponse(public(await run_in_threadpool(run_corner, request.path_params["key"])))
    except KeyError:
        return error("That corner isn't in the demo list.", 404)
    except RuntimeError as exc:
        return error(str(exc), 400)


def _run(request: Request):
    return load_run(request.path_params["run_id"])


async def get_run(request: Request):
    try:
        return JSONResponse(public(_run(request)))
    except FileNotFoundError:
        return error("That run wasn't found.", 404)


async def approve_run(request: Request):
    try:
        body = await _body(request)
        return JSONResponse(public(await run_in_threadpool(approve, _run(request), body.get("reviewer"))))
    except FileNotFoundError:
        return error("That run wasn't found.", 404)
    except ValueError as exc:
        return error(str(exc), 400)


async def add_field(request: Request):
    try:
        if int(request.headers.get("content-length") or 0) > MAX_UPLOAD:
            return error("That upload is too large. Send fewer photos at once.", 413)
        body = await _body(request)
        return JSONResponse(public(await run_in_threadpool(rerun_with_field, _run(request), body.get("entries"), body.get("date"), body.get("by"))))
    except (FileNotFoundError, KeyError):
        return error("That run or corner wasn't found.", 404)
    except RuntimeError as exc:
        return error(str(exc), 400)
    except ValueError as exc:
        return error(str(exc), 400)


async def photo(request: Request):
    name = request.path_params["name"]
    path = field_module.PHOTOS / name
    if not name.replace(".", "").isalnum() or not path.is_file():
        return error("That photo wasn't found.", 404)
    return FileResponse(path)


async def download(request: Request):
    try:
        current = _run(request)
        return PlainTextResponse(to_markdown(current), media_type="text/markdown; charset=utf-8",
                                 headers={"Content-Disposition": f'attachment; filename="cornerbrief_{current["corner"]["key"]}.md"'})
    except FileNotFoundError:
        return error("That run wasn't found.", 404)
    except NotApproved as exc:
        return error(str(exc), 409)


async def site_visit(request: Request):
    try:
        current = _run(request)
    except FileNotFoundError:
        return error("That run wasn't found.", 404)
    return PlainTextResponse(site_visit_markdown(current), media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="cornerbrief_site_visit_{current["corner"]["key"]}.md"'})


async def email(request: Request):
    try:
        body = await _body(request)
        current = _run(request)
        if not current.get("approval"):
            raise EmailBlocked("A person must release this packet before it can be emailed.")
        return JSONResponse({"message": await run_in_threadpool(send_brief, current, body.get("to"), to_markdown(current))})
    except FileNotFoundError:
        return error("That run wasn't found.", 404)
    except EmailBlocked as exc:
        return error(str(exc), 409)
    except OSError:
        return error("The email couldn't be sent. Check the SMTP settings in .env.", 502)
    except ValueError as exc:
        return error(str(exc), 400)


async def server_error(request: Request, exc: Exception):
    return error("Something went wrong on the server. Check the terminal for details.", 500)


routes = [
    Route("/api/corners", corners),
    Route("/api/search", search_corners),
    Route("/api/reading", reading),
    Route("/api/preview", preview, methods=["GET", "POST"]),
    Route("/api/real/{corner_id}/run", pull_corner, methods=["POST"]),
    Route("/api/corners/{key}/run", run, methods=["POST"]),
    Route("/api/runs/{run_id}", get_run),
    Route("/api/runs/{run_id}/approve", approve_run, methods=["POST"]),
    Route("/api/runs/{run_id}/field", add_field, methods=["POST"]),
    Route("/api/photos/{name}", photo),
    Route("/api/runs/{run_id}/download", download),
    Route("/api/runs/{run_id}/site-visit", site_visit),
    Route("/api/runs/{run_id}/email", email, methods=["POST"]),
    Mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True)),
]
async def wrong_origin(request: Request, exc: WrongOrigin):
    return error("This request came from another website, so it was refused.", 403)


app = Starlette(routes=routes, exception_handlers={Exception: server_error, WrongOrigin: wrong_origin})
