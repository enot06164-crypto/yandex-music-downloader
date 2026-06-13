# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
GUI модуль - Виджет карточки трека.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

from typing import Any, Dict, Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, \
    QPushButton, QFrame, QSizePolicy, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap, QFont, QIcon

import requests

from .icons import Icons, get_pixmap

# Импорт config на уровне модуля — раньше был внутри _setup_ui
# (sys.path/sys.modules работа на каждую карточку).
from config import get_config as _get_config


def _audio_quality() -> str:
    """Текущее качество из конфига (читаем один раз на карточку)."""
    return _get_config().audio_quality


# Кэш иконок: каждый рендер SVG — десятки вызовов QPainter.
# При показе 20 карточек иконка нужна 1-2 раза на виджет, итого
# ~40 рендеров на один поиск. Кэшируем на уровне модуля.
_DEFAULT_COVER_PIXMAP = None  # иконка «music» 40x40 #565f89
_PLAY_ICON_PIXMAP = None      # иконка «play» 14x14 #565f89
_DOWNLOAD_ICON = None         # QIcon 18x18 #1a1b26


def _get_default_cover():
    global _DEFAULT_COVER_PIXMAP
    if _DEFAULT_COVER_PIXMAP is None:
        _DEFAULT_COVER_PIXMAP = get_pixmap('music', 40, '#565f89')
    return _DEFAULT_COVER_PIXMAP


def _get_play_icon():
    global _PLAY_ICON_PIXMAP
    if _PLAY_ICON_PIXMAP is None:
        _PLAY_ICON_PIXMAP = get_pixmap('play', 14, '#565f89')
    return _PLAY_ICON_PIXMAP


def _get_download_icon():
    global _DOWNLOAD_ICON
    if _DOWNLOAD_ICON is None:
        _DOWNLOAD_ICON = Icons.download(18, '#1a1b26')
    return _DOWNLOAD_ICON


# Битрейт по качеству — был внутри _setup_ui, вынесен сюда
_BITRATE_MAP = {
    'best': 320,
    'high': 320,
    'medium': 192,
    'low': 128,
}


class CoverLoader(QThread):
    """Поток для загрузки обложки без блокировки UI."""

    loaded = pyqtSignal(QPixmap)
    error = pyqtSignal()

    def __init__(self, url: str, size: int = 80, parent=None):
        super().__init__(parent)
        self.url = url
        self.size = size
        self._cancelled = False
        self.finished.connect(self.deleteLater)

    def cancel(self):
        """Кооперативная отмена загрузки обложки."""
        self._cancelled = True

    def run(self):
        """Загрузка обложки в отдельном потоке."""
        if self._cancelled:
            return
        response = None
        try:
            if '%%' in self.url:
                url = self.url.replace('%%', '200x200')
            else:
                url = self.url

            response = requests.get(url, timeout=5, stream=True)

            if self._cancelled:
                return

            if response.status_code == 200:
                # Stream=True + iter_content, чтобы можно было прервать
                content = b''.join(
                    chunk for chunk in response.iter_content(chunk_size=8192)
                    if not self._cancelled
                )
                if self._cancelled or not content:
                    return

                pixmap = QPixmap()
                if not pixmap.loadFromData(content):
                    self.error.emit()
                    return

                scaled_pixmap = pixmap.scaled(
                    self.size, self.size,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                if not self._cancelled:
                    self.loaded.emit(scaled_pixmap)
            else:
                if not self._cancelled:
                    self.error.emit()
        except Exception:
            if not self._cancelled:
                self.error.emit()
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass


class TrackCardWidget(QFrame):
    """Виджет карточки трека для отображения в результатах поиска."""
    
    download_clicked = pyqtSignal(dict)
    card_clicked = pyqtSignal(dict)
    
    def __init__(self, track_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._track_data = track_data
        self._setup_ui()
        # Стили и тень не навешиваем — CSS-селекторы по objectName
        # живут в глобальном DARK_THEME_STYLESHEET (один парс на приложение),
        # а QGraphicsDropShadowEffect на 20 виджетах сжирал CPU на offscreen-рендере.
        self._load_cover()
    
    def _setup_ui(self):
        """Настройка интерфейса карточки трека."""
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("cardFrame")
        self.setCursor(Qt.PointingHandCursor)
        
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Обложка
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(80, 80)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setObjectName("coverLabel")
        # Устанавливаем иконку по умолчанию (кэшируется на уровне модуля)
        self.cover_label.setPixmap(_get_default_cover())
        main_layout.addWidget(self.cover_label)
        
        # Информация о треке
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        # Название трека
        self.title_label = QLabel(self._track_data.get('title', 'Без названия'))
        self.title_label.setObjectName("trackTitleLabel")
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)
        
        # Исполнитель
        artist = self._track_data.get('artist', 'Неизвестный исполнитель')
        self.artist_label = QLabel(artist)
        self.artist_label.setObjectName("trackArtistLabel")
        info_layout.addWidget(self.artist_label)
        
        # Альбом и год
        album_info = self._track_data.get('album', {})
        if album_info:
            album_text = album_info.get('title', '')
            year = album_info.get('year')
            if year:
                album_text = f"{album_text} ({year})"
            
            if album_text:
                self.album_label = QLabel(album_text)
                self.album_label.setObjectName("trackAlbumLabel")
                info_layout.addWidget(self.album_label)
        
        # Длительность с иконкой
        duration_ms = self._track_data.get('duration_ms', 0)
        if duration_ms:
            duration_sec = duration_ms // 1000
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            duration_str = f"{minutes}:{seconds:02d}"

            # Рассчитываем примерный размер файла на основе настроек.
            # config импортируется на уровне модуля ниже — здесь
            # только dict-lookup, без sys.path/sys.modules работы.
            bitrate = _BITRATE_MAP.get(_audio_quality(), 320)
            size_mb = (duration_sec * bitrate * 1000) / (8 * 1024 * 1024)
            size_str = f"~{size_mb:.1f} МБ"

            self.duration_layout = QHBoxLayout()
            self.duration_icon = QLabel()
            self.duration_icon.setPixmap(_get_play_icon())
            self.duration_layout.addWidget(self.duration_icon)

            self.duration_label = QLabel(duration_str)
            self.duration_label.setObjectName("trackDurationLabel")
            self.duration_layout.addWidget(self.duration_label)

            # Размер файла
            self.size_label = QLabel(size_str)
            self.size_label.setObjectName("trackSizeLabel")
            self.duration_layout.addWidget(self.size_label)

            self.duration_layout.addStretch()

            info_layout.addLayout(self.duration_layout)
        
        info_layout.addStretch()
        main_layout.addLayout(info_layout, 1)

        # Кнопки управления
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)

        # Кнопка скачать с иконкой
        self.download_btn = QPushButton("Скачать")
        self.download_btn.setIcon(_get_download_icon())
        self.download_btn.setObjectName("downloadButton")
        self.download_btn.setMinimumSize(110, 40)
        self.download_btn.clicked.connect(self._on_download_clicked)
        buttons_layout.addWidget(self.download_btn)

        main_layout.addLayout(buttons_layout)

    def _load_cover(self):
        """Загрузка обложки трека в отдельном потоке."""
        cover_url = self._track_data.get('cover_url')

        if not cover_url:
            return

        # Создаём и запускаем поток для загрузки.
        # self как parent → поток живёт в дереве виджетов и
        # удалится вместе с карточкой; на всякий случай также
        # подключаем destroyed → cancel.
        self._cover_loader = CoverLoader(cover_url, 80, parent=self)
        self._cover_loader.loaded.connect(self._on_cover_loaded)
        self._cover_loader.error.connect(self._on_cover_error)
        self.destroyed.connect(self._cover_loader.cancel)
        self._cover_loader.start()
    
    def _on_cover_loaded(self, pixmap: QPixmap):
        """Обработка загруженной обложки."""
        try:
            if self.cover_label is not None:
                self.cover_label.setPixmap(pixmap)
        except RuntimeError:
            # Виджет уже удалён (между сигналом и доставкой)
            pass
    
    def _on_cover_error(self):
        """Обработка ошибки загрузки обложки."""
        pass  # Оставляем иконку по умолчанию
    
    def _on_download_clicked(self):
        """Обработка нажатия кнопки скачивания."""
        self.download_clicked.emit(self._track_data)
    
    def mousePressEvent(self, event):
        """
        Обработка клика по карточке.
        Сейчас вся логика — на кнопке «Скачать» (download_clicked).
        Клик по самой карточке ничего не делает (можно расширить в будущем).
        """
        super().mousePressEvent(event)
    
    def get_track_data(self) -> Dict[str, Any]:
        """Получение данных трека."""
        return self._track_data
    
    def set_available(self, available: bool):
        """Установка доступности трека."""
        if not available:
            self.download_btn.setEnabled(False)
            self.download_btn.setText("Недоступен")
            self.setOpacity(0.5)
        else:
            self.download_btn.setEnabled(True)
            self.download_btn.setText("Скачать")
            self.setOpacity(1.0)
    
    def setOpacity(self, opacity: float):
        """
        Установка прозрачности карточки через QGraphicsOpacityEffect.

        Раньше делалось через CSS opacity в stylesheet (т.к. QGraphicsEffect
        и QGraphicsDropShadowEffect на одном виджете конфликтуют). После
        удаления тени конфликта нет — используем нативный эффект, который
        не трогает глобальный stylesheet.
        """
        opacity = max(0.0, min(1.0, float(opacity)))
        eff = getattr(self, '_opacity_effect', None)
        if eff is None:
            eff = QGraphicsOpacityEffect(self)
            eff.setOpacity(opacity)
            self.setGraphicsEffect(eff)
            self._opacity_effect = eff
        else:
            eff.setOpacity(opacity)


class TrackListWidgetItem(QWidget):
    """Альтернативный виджет трека для отображения в списке."""
    
    download_clicked = pyqtSignal(dict)
    
    def __init__(self, track_data: Dict[str, Any], index: int = 0, parent=None):
        super().__init__(parent)
        self._track_data = track_data
        self._index = index
        self._setup_ui()
        self._setup_styles()
    
    def _setup_ui(self):
        """Настройка интерфейса."""
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Номер трека
        self.index_label = QLabel(str(self._index + 1))
        self.index_label.setFixedSize(28, 28)
        self.index_label.setAlignment(Qt.AlignCenter)
        self.index_label.setObjectName("indexLabel")
        layout.addWidget(self.index_label)
        
        # Информация
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        title = self._track_data.get('title', 'Без названия')
        artist = self._track_data.get('artist', '')
        
        self.title_label = QLabel(f"{title} - {artist}")
        self.title_label.setObjectName("titleLabel")
        info_layout.addWidget(self.title_label)
        
        album = self._track_data.get('album', {})
        if album:
            album_title = album.get('title', '')
            if album_title:
                self.album_label = QLabel(album_title)
                self.album_label.setObjectName("albumLabel")
                info_layout.addWidget(self.album_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout, 1)
        
        # Длительность
        duration_ms = self._track_data.get('duration_ms', 0)
        if duration_ms:
            duration_sec = duration_ms // 1000
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            duration_str = f"{minutes}:{seconds:02d}"
            
            self.duration_label = QLabel(duration_str)
            self.duration_label.setObjectName("durationLabel")
            layout.addWidget(self.duration_label)
        
        # Кнопка скачать с иконкой
        self.download_btn = QPushButton()
        self.download_btn.setIcon(Icons.download(16, "#1a1b26"))
        self.download_btn.setObjectName("downloadButton")
        self.download_btn.setFixedSize(36, 36)
        self.download_btn.setToolTip("Скачать трек")
        self.download_btn.clicked.connect(self._on_download_clicked)
        layout.addWidget(self.download_btn)
    
    def _setup_styles(self):
        """Настройка стилей."""
        self.setStyleSheet("""
            TrackListWidgetItem {
                background-color: #24283b;
                border-radius: 8px;
            }
            
            TrackListWidgetItem:hover {
                background-color: #2f3549;
            }
            
            #indexLabel {
                color: #565f89;
                font-size: 13px;
                font-weight: 600;
                background-color: #16161e;
                border-radius: 6px;
            }
            
            #titleLabel {
                color: #c0caf5;
                font-size: 14px;
                font-weight: 600;
            }
            
            #albumLabel {
                color: #565f89;
                font-size: 12px;
            }
            
            #durationLabel {
                color: #565f89;
                font-size: 12px;
                min-width: 45px;
            }
            
            #downloadButton {
                background-color: #9ece6a;
                border: none;
                border-radius: 6px;
            }
            
            #downloadButton:hover {
                background-color: #b4f98a;
            }

            #playlistButton {
                background-color: #24283b;
                color: #7aa2f7;
                border: 1px solid #414868;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 500;
                font-size: 12px;
            }

            #playlistButton:hover {
                background-color: #414868;
                border-color: #7aa2f7;
            }
        """)
    
    def _on_download_clicked(self):
        """Обработка нажатия кнопки скачивания."""
        self.download_clicked.emit(self._track_data)
    
    def get_track_data(self) -> Dict[str, Any]:
        """Получение данных трека."""
        return self._track_data
