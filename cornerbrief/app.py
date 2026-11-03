"""Web API and static UI."""
from pathlib import Path
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from .config import load_env
from .data_loader import list_corners
from .email_delivery import EmailBlocked, allowlist, send_brief
from .orchestrator import load_run, run_corner
from .review_export import NotApproved, approve, presented, to_markdown

load_env()


def public(run: dict) -> dict:
    shown = {k: v for k, v in presented(run).items() if k != "agent_log"}
    shown["features"] = {"email": bool(allowlist())}
    return shown


def error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


async def corners(request: Request):
    return JSONResponse(list_corners())


async def run(request: Request):
    try:
        return JSONResponse(public(run_corner(request.path_params["key"])))
    except KeyError:
        return error("That corner isn't in the demo list.", 404)
    except RuntimeError as exc:
        return error(str(exc), 400)


def _run(request: Request):
    return load_run(request.path_params["run_id"])


async def approve_run(request: Request):
    body = await request.json()
    try:
        return JSONResponse(public(approve(_run(request), body.get("reviewer", ""))))
    except FileNotFoundError:
        return error("That run wasn't found.", 404)
    except ValueError as exc:
        return error(str(exc), 400)


async def download(request: Request):
    try:
        current = _run(request)
        return PlainTextResponse(to_markdown(current), media_type="text/markdown; charset=utf-8",
                                 headers={"Content-Disposition": f'attachment; filename="cornerbrief_{current["corner"]["key"]}.md"'})
    except FileNotFoundError:
        return error("That run wasn't found.", 404)
    except NotApproved as exc:
        return error(str(exc), 409)


async def email(request: Request):
    body = await request.json()
    try:
        current = _run(request)
        if not current.get("approval"):
            raise EmailBlocked("A person must approve this brief before it can be emailed.")
        return JSONResponse({"message": send_brief(current, body.get("to", ""), to_markdown(current))})
    except FileNotFoundError:
        return error("That run wasn't found.", 404)
    except EmailBlocked as exc:
        return error(str(exc), 409)


routes = [
    Route("/api/corners", corners),
    Route("/api/corners/{key}/run", run, methods=["POST"]),
    Route("/api/runs/{run_id}/approve", approve_run, methods=["POST"]),
    Route("/api/runs/{run_id}/download", download),
    Route("/api/runs/{run_id}/email", email, methods=["POST"]),
    Mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True)),
]
app = Starlette(routes=routes)
