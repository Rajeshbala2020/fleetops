# import os

# from starlette.staticfiles import StaticFiles
# from starlette.templating import Jinja2Templates

# from app import create_app

# app = create_app()
# templates = Jinja2Templates(directory="app/templates")
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

# if __name__ == '__main__':
#     import uvicorn
#     port = int(os.environ.get("PORT", 8000))
#     print(f"Starting server on port {port}")
#     uvicorn.run(app, host='0.0.0.0', port=port)
# main.py
# main.py
import os
import threading
from fastapi import FastAPI
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

# Create a tiny, always-light app FIRST so Render sees an open port quickly
app = FastAPI()

# Fast health check
@app.get("/")
async def health():
    return {"status": "ok"}

# Templates + static (won’t crash if the dir doesn’t exist)
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static", check_dir=False), name="static")

def wire_routes_and_heavy_deps():
    """
    Import anything heavy (torch, transformers, big models) here *after* the server starts.
    Also include routers/endpoints that rely on those deps.
    """
    # Optional: skip on Render free tier until you upgrade memory
    if os.getenv("SKIP_HEAVY", "0") == "1":
        print("[startup] SKIP_HEAVY=1 -> not loading heavy modules")
        return

    try:
        # Example: only import now (NOT at module import time)
        # import torch
        # from app.ml import load_model
        # model = load_model()

        # Bring in your actual app factory/routers now
        from app import create_app  # <-- if this imports heavy stuff, it's okay now
        heavy_app = create_app()
        # Mount your real API under /api (adjust if needed)
        app.mount("/api", heavy_app)

        print("[startup] Heavy modules and routes loaded.")
    except Exception as e:
        # Never crash the server on startup—log and keep the / health alive
        print(f"[startup] Failed to load heavy modules/routes: {e}")

# Kick off heavy loading in the background *after* uvicorn has started
@app.on_event("startup")
async def _kickoff():
    threading.Thread(target=wire_routes_and_heavy_deps, daemon=True).start()

# Local dev only. Render will ignore this because you’ll use a Start Command.
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

