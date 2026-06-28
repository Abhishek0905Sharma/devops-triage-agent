import json
import os
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from buggy_app.routers.users import router as users_router
import triage as triage_module

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DevOps Incident Triage Demo - Users API",
    description="A simple, intentionally buggy FastAPI service paired with an AI triage agent.",
    version="2.0.0",
)

app.include_router(users_router, tags=["Users"])

# Serve static files (the SPA lives at static/index.html, project root)
STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─── Root → serve SPA ─────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def read_root():
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return HTMLResponse("<h1>UI not found. Run the build step first.</h1>", status_code=404)
    return HTMLResponse(content=index.read_text(encoding="utf-8"))


# ─── /triage — SSE streaming endpoint ─────────────────────────────────────────
@app.post("/triage")
async def triage_endpoint(request: Request):
    """
    Accepts an error-log JSON body and streams the agent's reasoning
    as Server-Sent Events (SSE).  The stream ends with a 'done' event.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = os.environ.get("TRIAGE_MODEL", "claude-3-5-sonnet-latest")

    def event_stream():
        try:
            for event in triage_module.run_triage(body, model):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"
        finally:
            yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
