"""OpcHub Frontend Standalone Web Server & Gateway Proxy.

Serves the compiled Vue 3 + Vite production application on port 3000,
and transparently reverse-proxies /api to the backend unified gateway on port 8000.
Zero reference to documentation prototype demo files.
"""
import os
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx

app = FastAPI(title="OpcHub Frontend Web Console")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent
DIST_DIR = FRONTEND_DIR / "dist"
ASSETS_DIR = DIST_DIR / "assets"
BACKEND_BASE_URL = os.getenv("OPCHUB_BACKEND_URL", "http://127.0.0.1:8000")

# Mount built static assets
if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/health")
async def health_check():
    return {
        "status": "UP",
        "service": "opchub_frontend_vue3",
        "backend_target": BACKEND_BASE_URL,
        "dist_built": (DIST_DIR / "index.html").is_file(),
    }


@app.get("/")
@app.get("/app")
@app.get("/console")
@app.get("/index.html")
async def serve_index():
    index_file = DIST_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(
            index_file,
            media_type="text/html; charset=utf-8",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return HTMLResponse(
        """
        <div style="font-family: sans-serif; text-align: center; padding: 60px;">
            <h2>OpcHub Frontend Dist Not Found</h2>
            <p>Please run <code>cd frontend && npm run build</code> to compile the Vue 3 application.</p>
        </div>
        """,
        status_code=404,
    )


def _get_product_logo_svg() -> str:
    candidates = [
        DIST_DIR / "logo.svg",
        DIST_DIR / "favicon.svg",
        FRONTEND_DIR / "public" / "logo.svg",
    ]
    for p in candidates:
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return ""


@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/favicon.svg", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/logo.svg", methods=["GET", "HEAD"], include_in_schema=False)
async def serve_brand_icon():
    svg_content = _get_product_logo_svg()
    if svg_content:
        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "no-cache, must-revalidate",
            },
        )
    return Response(status_code=404)


_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=200, keepalive_expiry=30.0)
        _http_client = httpx.AsyncClient(timeout=30.0, trust_env=False, limits=limits)
    return _http_client


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_api_to_backend(path: str, request: Request):
    """Transparently proxy /api requests to backend gateway with persistent connection pool."""
    target_url = f"{BACKEND_BASE_URL}/api/{path}"
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    body = await request.body()
    params = request.query_params

    client = get_http_client()
    try:
        resp = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=params,
            content=body,
        )
        excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        forward_headers = {
            k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers
        }
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=forward_headers,
            media_type=resp.headers.get("content-type"),
        )
    except Exception as e:
        return Response(
            content=f'{{"code": 502, "message": "Failed to connect to backend: {str(e)}"}}',
            status_code=502,
            media_type="application/json",
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("FRONTEND_PORT", "3000"))
    host = os.getenv("FRONTEND_HOST", "0.0.0.0")
    uvicorn.run("frontend.server:app", host=host, port=port, reload=False)
