"""Routes for viewer interface."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os

router = APIRouter()


@router.get("/viewer", response_class=HTMLResponse)
def get_viewer():
    """Возвращает HTML интерфейс viewer.html"""
    # Ищем viewer.html в корне проекта
    viewer_path = os.path.join(os.path.dirname(__file__), "..", "..", "viewer.html")
    if not os.path.exists(viewer_path):
        # Альтернативный путь (если запускается из Docker)
        viewer_path = os.path.join("/app", "viewer.html")
    if os.path.exists(viewer_path):
        with open(viewer_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Viewer not found</h1>", status_code=404)

