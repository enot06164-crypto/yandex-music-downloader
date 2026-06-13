# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
GUI модуль - Пакет UI компонентов.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

from .widgets import (
    BaseWidget,
    CardWidget,
    LoadingWidget,
    EmptyStateWidget,
    IconButton,
    get_dark_stylesheet,
    DARK_THEME_STYLESHEET,
)

from .auth_dialog import AuthDialog

from .track_card import TrackCardWidget, TrackListWidgetItem

from .main_window import MainWindow, SearchWorker, DownloadWorker

from .icons import Icons, get_icon, get_pixmap

__all__ = [
    # Widgets
    'BaseWidget',
    'CardWidget',
    'LoadingWidget',
    'EmptyStateWidget',
    'IconButton',
    'get_dark_stylesheet',
    'DARK_THEME_STYLESHEET',
    
    # Dialogs
    'AuthDialog',
    
    # Track cards
    'TrackCardWidget',
    'TrackListWidgetItem',
    
    # Main window
    'MainWindow',
    'SearchWorker',
    'DownloadWorker',
    
    # Icons
    'Icons',
    'get_icon',
    'get_pixmap',
]
