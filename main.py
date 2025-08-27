from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from app import create_app

app = create_app()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
