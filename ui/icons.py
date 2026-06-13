# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
Модуль иконок - упрощённый.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

from pathlib import Path
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import QSize, Qt


# Путь к директории с иконками
ICONS_DIR = Path(__file__).parent.parent / 'resources' / 'icons'


def get_icon(name: str, size: int = 24, color: str = "#c0caf5") -> QIcon:
    """
    Получение QIcon для иконки.

    Args:
        name: Имя иконки
        size: Размер
        color: Цвет

    Returns:
        QIcon
    """
    return QIcon(get_pixmap(name, size, color))


def get_pixmap(name: str, size: int = 24, color: str = "#c0caf5") -> QPixmap:
    """
    Получение QPixmap для иконки.
    Пытается загрузить SVG/PNG файл из resources/icons, 
    иначе создаёт цветной квадрат как заглушку.

    Args:
        name: Имя иконки
        size: Размер
        color: Цвет

    Returns:
        QPixmap
    """
    # Пытаемся загрузить файл иконки
    for ext in ['.svg', '.png']:
        icon_path = ICONS_DIR / f'{name}{ext}'
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                # Масштабируем до нужного размера
                return pixmap.scaled(
                    size, size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
    
    # Если файл не найден, создаём цветной квадрат как заглушку
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(color))
    return pixmap


class Icons:
    """Класс для работы с иконками."""

    @staticmethod
    def get_icon(name: str, size: int = 24, color: str = "#c0caf5") -> QIcon:
        """Получение QIcon."""
        return QIcon(get_pixmap(name, size, color))

    @staticmethod
    def music(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('music', size, color)

    @staticmethod
    def user(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('user', size, color)

    @staticmethod
    def search(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('search', size, color)

    @staticmethod
    def download(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('download', size, color)

    @staticmethod
    def settings(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('settings', size, color)

    @staticmethod
    def check(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('check', size, color)

    @staticmethod
    def close(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('close', size, color)

    @staticmethod
    def error(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('error', size, color)

    @staticmethod
    def folder(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('folder', size, color)

    @staticmethod
    def link(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('link', size, color)

    @staticmethod
    def play(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('play', size, color)

    @staticmethod
    def loading(size: int = 24, color: str = "#c0caf5") -> QIcon:
        return Icons.get_icon('loading', size, color)
