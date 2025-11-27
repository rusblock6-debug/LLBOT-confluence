"""Routes for feedback submission."""
from fastapi import APIRouter
from datetime import datetime
import os

from app.models.requests import FeedbackRequestModel

router = APIRouter()


@router.post("/feedback")
def submit_feedback(request: FeedbackRequestModel):
    """Принимает правку к документации и сохраняет её в локальный markdown-файл."""
    try:
        os.makedirs("feedback", exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        author = (request.author or "unknown").replace("@", "").replace(" ", "_")
        filename = f"{timestamp}_{author}_feedback.md"
        file_path = os.path.join("feedback", filename)

        content_lines = [
            "# Правка документации",
            "",
            f"- Автор: {request.author or '-'}",
            f"- Тип документа: {request.doc_type or '-'}",
            f"- Документ/раздел: {request.doc_ref or '-'}",
            f"- Операция: {request.operation or '-'}",
            "",
            "## Было",
            (request.old_text or "-"),
            "",
            "## Стало",
            (request.new_text or "-"),
            "",
            "## Комментарий",
            (request.comment or "-"),
            "",
        ]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))

        print(f"Правка сохранена в файл: {file_path}")
        return {"status": "success", "file_path": file_path}

    except Exception as e:
        return {"status": "error", "message": f"Не удалось сохранить правку: {e}"}


