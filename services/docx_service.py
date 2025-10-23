# services/docx_service.py
from docx import Document
import os

def create_docx(content: str, title: str) -> str:
    """Создает DOCX файл из текста."""
    print(f"Создаю DOCX файл: {title}.docx")
    doc = Document()
    doc.add_heading(title, 0)
    
    doc.add_paragraph(content)
    
    if not os.path.exists("output"):
        os.makedirs("output")
        
    file_path = os.path.join("output", f"{title.replace(' ', '_')}.docx")
    doc.save(file_path)
    
    print(f"Файл сохранен по пути: {file_path}")
    return file_path