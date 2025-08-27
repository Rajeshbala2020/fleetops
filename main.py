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
import os
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from app import create_app

# Build your ASGI app (FastAPI or Starlette) without heavy work at import time
app = create_app()

# Fast health check endpoint (works for both FastAPI and Starlette)
@app.route("/", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok"})

# Templates + static; don't crash if the folder isn't in the repo
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static", check_dir=False), name="static")

# Local dev entrypoint (Render will ignore this; it uses your Start Command)
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
