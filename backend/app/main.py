import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

mimetypes.add_type("application/manifest+json", ".webmanifest")

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .auth import clear_session, is_authenticated, issue_session, require_auth, verify_password
from .config import settings
from .routers import invoices as invoices_router

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Invoice Scanner",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.include_router(invoices_router.router)


class LoginBody(BaseModel):
    password: str


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(body: LoginBody, response: Response) -> dict:
    if not verify_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    issue_session(response)
    return {"status": "ok"}


@app.post("/api/auth/logout")
def logout(response: Response) -> dict:
    clear_session(response)
    return {"status": "ok"}


@app.get("/api/auth/me")
def me(request: Request) -> dict:
    return {"authenticated": is_authenticated(request)}


@app.get("/api/secure/ping")
def secure_ping(request: Request) -> dict:
    require_auth(request)
    return {"status": "ok", "message": "authenticated"}


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    app.mount("/icons", StaticFiles(directory=STATIC_DIR / "icons"), name="icons")


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/{full_path:path}")
def spa(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return JSONResponse({"detail": "Frontend not built"}, status_code=503)
    return FileResponse(index)