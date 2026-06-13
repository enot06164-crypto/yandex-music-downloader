"""
Скрипт для генерации иконки приложения из PNG.
Создаёт .ico файл для Windows и PNG разных размеров.

Использует пользовательский логотип: yandexdownloaderico.png

Запуск:
    python scripts/generate_icon.py

Требования:
    pip install Pillow
"""

import os
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from PIL import Image
except ImportError:
    print("Установите Pillow: pip install Pillow")
    sys.exit(1)


def create_icon_from_png(source_png: Path, sizes: list) -> list:
    """
    Создание иконок разных размеров из PNG файла.
    
    Args:
        source_png: Путь к исходному PNG файлу.
        sizes: Список размеров для генерации.
        
    Returns:
        Список изображений разных размеров.
    """
    if not source_png.exists():
        print(f"Ошибка: Файл {source_png} не найден!")
        print("Положите файл yandexdownloaderico.png в корень проекта")
        sys.exit(1)
    
    # Открываем исходное изображение
    source_img = Image.open(source_png)
    
    # Конвертируем в RGBA если нужно
    if source_img.mode != 'RGBA':
        source_img = source_img.convert('RGBA')
    
    images = []
    
    for size in sizes:
        # Изменяем размер с высоким качеством
        img = source_img.resize(
            (size, size),
            Image.Resampling.LANCZOS
        )
        images.append(img)
    
    return images


def save_ico(images, output_path: Path):
    """
    Сохранение в формат .ico
    
    Args:
        images: Список изображений разных размеров.
        output_path: Путь для сохранения.
    """
    # Сохраняем первое изображение с остальными как дополнительные
    images[0].save(
        output_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )
    print(f"ICO сохранен: {output_path}")


def save_png(image, output_path: Path, size: int):
    """
    Сохранение в формат .png
    
    Args:
        image: Изображение.
        output_path: Путь для сохранения.
        size: Размер изображения.
    """
    image.save(output_path, format='PNG', quality=95)
    print(f"PNG ({size}x{size}) сохранен: {output_path}")


def create_svg_from_png(source_png: Path, output_svg: Path):
    """
    Создание SVG файла (копирование PNG с обёрткой в SVG).
    
    Примечание: Это не настоящий SVG, а PNG в SVG обёртке.
    Для настоящего SVG нужен векторный оригинал.
    
    Args:
        source_png: Путь к исходному PNG файлу.
        output_svg: Путь для сохранения SVG.
    """
    import base64
    
    if not source_png.exists():
        return
    
    # Читаем PNG файл
    with open(source_png, 'rb') as f:
        png_data = f.read()
    
    # Кодируем в base64
    png_base64 = base64.b64encode(png_data).decode('utf-8')
    
    # Создаём SVG с встроенным PNG
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
     viewBox="0 0 256 256" width="256" height="256">
    <image xlink:href="data:image/png;base64,{png_base64}" 
           width="256" height="256" x="0" y="0"/>
</svg>
'''
    
    with open(output_svg, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    
    print(f"SVG сохранен: {output_svg}")


def main():
    """Главная функция."""
    # Директория проекта
    project_dir = Path(__file__).parent.parent
    resources_dir = project_dir / 'resources'
    resources_dir.mkdir(exist_ok=True)
    
    # Исходный файл логотипа
    source_png = project_dir / 'yandexdownloaderico.png'
    source_ico = project_dir / 'yandexdownloaderico.ico'
    
    # Используем PNG если есть, иначе ICO
    if source_png.exists():
        source_file = source_png
        print(f"Используется источник: {source_file}")
    elif source_ico.exists():
        # Если только ICO, извлекаем из него
        try:
            ico_img = Image.open(source_ico)
            source_file = resources_dir / 'temp_logo.png'
            ico_img.save(source_file, 'PNG')
            print(f"Используется источник (из ICO): {source_file}")
        except Exception as e:
            print(f"Ошибка чтения ICO: {e}")
            sys.exit(1)
    else:
        print("Ошибка: Не найден yandexdownloaderico.png или yandexdownloaderico.ico")
        print("Положите файл логотипа в корень проекта")
        sys.exit(1)
    
    print("\nГенерация иконок...")
    
    # Размеры для генерации
    sizes = [16, 32, 64, 128, 256]
    
    # Создаём иконки
    images = create_icon_from_png(source_file, sizes)
    
    # Сохраняем в разных форматах
    save_ico(images, resources_dir / 'app.ico')
    
    for i, size in enumerate(sizes):
        save_png(images[i], resources_dir / f'app_{size}.png', size)
    
    # Создаём SVG
    create_svg_from_png(source_file, resources_dir / 'icon.svg')
    
    # Удаляем временный файл если был создан
    temp_file = resources_dir / 'temp_logo.png'
    if temp_file.exists():
        temp_file.unlink()
    
    print("\n✅ Генерация завершена!")
    print(f"Файлы сохранены в: {resources_dir}")
    print("\nСозданные файлы:")
    print("  - app.ico (Windows иконка)")
    print("  - app_256.png, app_128.png, app_64.png, app_32.png, app_16.png")
    print("  - icon.svg (SVG версия)")


if __name__ == '__main__':
    main()
