import os
import sys
from pathlib import Path
import mammoth
from docx2python import docx2python
import re

def clean_filename(filename):
    # Удаляем недопустимые символы из имени файла
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def convert_docx_to_md(docx_path, output_dir):
    try:
        # Создаем имя выходного файла с расширением .md
        md_filename = os.path.splitext(os.path.basename(docx_path))[0] + '.md'
        md_path = os.path.join(output_dir, md_filename)
        
        # Конвертируем docx в html
        with open(docx_path, 'rb') as docx_file:
            result = mammoth.convert_to_markdown(docx_file)
            markdown = result.value
        
        # Сохраняем в файл
        with open(md_path, 'w', encoding='utf-8') as md_file:
            md_file.write(markdown)
            
        print(f"Converted: {docx_path} -> {md_path}")
        return True
        
    except Exception as e:
        print(f"Error converting {docx_path}: {str(e)}")
        return False

def main():
    input_dir = 'data'
    output_dir = 'data2'
    
    # Создаем выходную директорию, если её нет
    os.makedirs(output_dir, exist_ok=True)
    
    # Обрабатываем все .docx файлы в директории
    converted = 0
    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.docx'):
            input_path = os.path.join(input_dir, filename)
            if convert_docx_to_md(input_path, output_dir):
                converted += 1
    
    # Копируем существующие .md файлы
    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.md'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            with open(input_path, 'r', encoding='utf-8') as src, \
                 open(output_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            print(f"Copied: {input_path} -> {output_path}")
            converted += 1
    
    print(f"\nConversion complete. Converted/copied {converted} files.")

if __name__ == "__main__":
    main()
