# services/html_service.py
import markdown
import os

def create_html(content: str, title: str) -> str:
    """
    Конвертирует Markdown-текст в красивый HTML-файл.
    """
    print(f"Создаю HTML файл: {title}.html")
    
    # 1. Конвертируем Markdown в HTML
    html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
    
    # 2. Создаем полную HTML-страницу с базовыми стилями
    full_html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f4f4f4;
            }}
            h1, h2, h3, h4, h5, h6 {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
                background-color: #f2f2f2;
            }}
            th {{
                font-weight: bold;
            }}
            pre {{
                background-color: #282c34;
                color: #fff;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                font-family: 'Courier New', Courier, monospace;
            }}
            blockquote {{
                border-left: 5px solid #ccc;
                margin-left: 20px;
                padding-left: 15px;
                color: #777;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        {html_content}
    </body>
    </html>
    """
    
    # 3. Сохраняем файл
    if not os.path.exists("output"):
        os.makedirs("output")
        
    file_path = os.path.join("output", f"{title.replace(' ', '_')}.html")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
        
    print(f"Файл сохранен по пути: {file_path}")
    return file_path