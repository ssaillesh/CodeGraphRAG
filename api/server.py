from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from api.routes import _home_page_html, router
from config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(router)

    @app.get("/", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        return HTMLResponse(_home_page_html())

    return app
