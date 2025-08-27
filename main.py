import os

from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from app import create_app

# Create the main app
app = create_app()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host='0.0.0.0', port=port)

