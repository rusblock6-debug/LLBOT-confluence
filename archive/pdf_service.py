# services/pdf_service.py (версия с поддержкой кириллицы)
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_JUSTIFY
import markdown
import os

# --- РЕГИСТРАЦИЯ ШРИФТОВ С ПОДДЕРЖКОЙ КИРИЛЛИЦЫ ---
# Регистрируем шрифт Arial, который есть на всех Windows
try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics.registerFontFamily('Arial', TTFont('Arial', 'arial.ttf'))
except Exception as e:
    print(f"Не удалось зарегистрировать шрифт Arial: {e}")
    print("Пожалуйста, убедитесь, что файл arial.ttf доступен в системе.")
    # Если Arial не найден, можно попробовать DejaVu Sans, но это требует его установки
    # from reportlab.pdfbase.ttfonts import TTFont
    # from reportlab.lib.fonts import addMapping
    # addMapping('DejaVu Sans', 'DejaVuSans', 'DejaVuSans-Bold', 'DejaVuSans-Oblique', 'DejaVuSans-BoldOblique')
    # pdfmetrics.registerFont(TTFont('DejaVu Sans', 'DejaVuSans.ttf'))
    # pdfmetrics.registerFontFamily('DejaVu Sans', TTFont('DejaVu Sans', 'DejaVuSans.ttf'))


def create_pdf(content: str, title: str) -> str:
    """
    Конвертирует Markdown-текст в PDF-файл с поддержкой кириллицы.
    """
    print(f"Создаю PDF файл (с поддержкой кириллицы): {title}.pdf")
    
    # 1. Конвертируем Markdown в HTML
    html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
    
    # 2. Создаем PDF документ
    doc = SimpleDocTemplate(f"output/{title.replace(' ', '_')}.pdf", pagesize=A4)
    
    # 3. Получаем стили и создаем свой стиль для кириллического текста
    styles = getSampleStyleSheet()
    
    # Создаем стиль для обычного текста с поддержкой кириллицы
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Arial',  # <-- УКАЗЫВАЕМ НАШ ШРИФТ
        fontSize=12,
        spaceAfter=12,
        leading=14,
        alignment=TA_JUSTIFY,
    )
    
    # Создаем стиль для заголовков
    heading_style = ParagraphStyle(
        'Heading1',
        parent=styles['Heading1'],
        fontName='Arial', # <-- И ЗДЕСЬ ТОЖЕ
        fontSize=18,
        spaceAfter=20,
        textColor='#2c3e50',
    )

    story = []
    
    # 4. Добавляем заголовок
    story.append(Paragraph(title, heading_style))
    story.append(Spacer(1, 12))

    # 5. Добавляем основной контент, используя наш новый стиль
    lines = html_content.split('\n')
    for line in lines:
        if line.strip():
            if line.startswith('###'):
                p = Paragraph(line[3:].strip(), styles['Heading3'])
            elif line.startswith('##'):
                p = Paragraph(line[2:].strip(), styles['Heading2'])
            elif line.startswith('#'):
                p = Paragraph(line[1:].strip(), styles['Heading1'])
            else:
                p = Paragraph(line.strip(), body_style) # <-- ИСПОЛЬЗУЕМ НАШ СТИЛЬ
            story.append(p)
            story.append(Spacer(1, 6))
        else:
            story.append(Spacer(1, 6))

    # 6. Строим документ
    doc.build(story)
    
    file_path = os.path.join("output", f"{title.replace(' ', '_')}.pdf")
    print(f"Файл сохранен по пути: {file_path}")
    return file_path