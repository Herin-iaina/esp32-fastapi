from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.config import settings

router = APIRouter()

templates = Jinja2Templates(directory=settings.templates_dir)

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("main.html", {
        "request": request, 
        "active_page": "dashboard",
        "settings": settings
    })

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {
        "request": request, 
        "active_page": "settings",
        "settings": settings
    })

@router.post("/settings/save")
async def save_settings(
    request: Request,
    app_name: str = Form(...),
    refresh_rate: int = Form(...),
    theme_mode: str = Form(...)
):
    # In a real app, you would save these to the database or .env file
    # For now, we'll just print them and redirect
    print(f"Saving Settings: App={app_name}, Rate={refresh_rate}, Theme={theme_mode}")
    return RedirectResponse(url="/settings", status_code=303)
