# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
GUI модуль - Диалог скачивания по ссылке (обновлённый дизайн).

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

from PyQt5.QtWidgets import QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, \
    QLineEdit, QPushButton, QFrame, QRadioButton, QButtonGroup, QGroupBox, \
    QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer, QSize, QPoint
from PyQt5.QtGui import QFont, QColor, QIcon

from .icons import Icons, get_pixmap
from .animations import AnimationHelper


class DownloadLinkDialog(QDialog):
    """Диалог скачивания по ссылке с современным дизайном."""

    link_downloaded = pyqtSignal(str, str)  # link, type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Скачать по ссылке")
        self.setFixedSize(550, 480)
        self.setModal(True)

        self._setup_ui()
        self._setup_styles()
        self._setup_shadow()

    def _setup_ui(self):
        """Настройка интерфейса."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Контейнер
        self.container = QFrame()
        self.container.setObjectName("downloadContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(20)
        container_layout.setContentsMargins(28, 28, 28, 28)

        # ===== Заголовок =====
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(get_pixmap('link', 32, '#7aa2f7'))
        header_layout.addWidget(self.icon_label)

        self.title_label = QLabel("Скачать по ссылке")
        self.title_label.setObjectName("downloadTitleLabel")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()
        container_layout.addLayout(header_layout)

        # ===== Описание =====
        desc_frame = QFrame()
        desc_frame.setObjectName("downloadDescFrame")
        desc_layout = QVBoxLayout(desc_frame)
        desc_layout.setSpacing(8)
        desc_layout.setContentsMargins(16, 16, 16, 16)

        self.desc_label = QLabel("Вставьте ссылку на трек, альбом или плейлист:")
        self.desc_label.setObjectName("downloadDescLabel")
        desc_layout.addWidget(self.desc_label)

        self.example1_label = QLabel("Трек: https://music.yandex.ru/album/12345/track/67890")
        self.example1_label.setObjectName("downloadExampleLabel")
        desc_layout.addWidget(self.example1_label)

        self.example2_label = QLabel("Альбом: https://music.yandex.ru/album/12345")
        self.example2_label.setObjectName("downloadExampleLabel")
        desc_layout.addWidget(self.example2_label)

        self.example3_label = QLabel("Плейлист: https://music.yandex.ru/users/username/playlists/123")
        self.example3_label.setObjectName("downloadExampleLabel")
        desc_layout.addWidget(self.example3_label)

        container_layout.addWidget(desc_frame)

        # ===== Поле ввода =====
        input_label = QLabel("Ссылка:")
        input_label.setObjectName("downloadInputLabel")
        container_layout.addWidget(input_label)

        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("https://music.yandex.ru/...")
        self.link_input.setObjectName("downloadInput")
        self.link_input.setClearButtonEnabled(True)
        container_layout.addWidget(self.link_input)

        # ===== Тип контента =====
        type_group = QGroupBox("Тип контента")
        type_layout = QVBoxLayout(type_group)
        type_layout.setSpacing(10)

        self.type_auto = QRadioButton("Автоматически (рекомендуется)")
        self.type_auto.setChecked(True)
        self.type_auto.setObjectName("downloadRadio")
        type_layout.addWidget(self.type_auto)

        self.type_track = QRadioButton("Трек")
        self.type_track.setObjectName("downloadRadio")
        type_layout.addWidget(self.type_track)

        self.type_album = QRadioButton("Альбом")
        self.type_album.setObjectName("downloadRadio")
        type_layout.addWidget(self.type_album)

        self.type_playlist = QRadioButton("Плейлист")
        self.type_playlist.setObjectName("downloadRadio")
        type_layout.addWidget(self.type_playlist)

        container_layout.addWidget(type_group)

        # ===== Кнопки =====
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        buttons_layout.addStretch()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("downloadCancelButton")
        self.cancel_btn.setMinimumHeight(44)
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)

        self.download_btn = QPushButton("Скачать")
        self.download_btn.setObjectName("downloadButton")
        self.download_btn.setIcon(QIcon(get_pixmap('download', 18, '#1a1b26')))
        self.download_btn.setIconSize(QSize(18, 18))
        self.download_btn.setMinimumHeight(44)
        self.download_btn.clicked.connect(self._on_download)
        buttons_layout.addWidget(self.download_btn)

        container_layout.addLayout(buttons_layout)

        # ===== Статус =====
        self.status_label = QLabel("")
        self.status_label.setObjectName("downloadStatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        container_layout.addWidget(self.status_label)

        main_layout.addWidget(self.container)

    def _setup_styles(self):
        """Настройка стилей."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
            }

            #downloadContainer {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #1e2030, stop:1 #1a1b26);
                border-radius: 20px;
                border: 1px solid #24283b;
            }

            #downloadTitleLabel {
                font-size: 22px;
                font-weight: 700;
                color: #7aa2f7;
            }

            #downloadDescFrame {
                background-color: #16161e;
                border: 1px solid #24283b;
                border-radius: 12px;
            }

            #downloadDescLabel {
                font-size: 14px;
                color: #c0caf5;
                font-weight: 500;
            }

            #downloadExampleLabel {
                font-size: 12px;
                color: #565f89;
                font-family: 'Consolas', 'Courier New', monospace;
            }

            #downloadInputLabel {
                font-size: 13px;
                color: #a9b1d6;
                font-weight: 500;
            }

            #downloadInput {
                background-color: #24283b;
                border: 2px solid #414868;
                border-radius: 10px;
                padding: 14px 18px;
                color: #c0caf5;
                font-size: 14px;
                min-height: 50px;
            }

            #downloadInput:focus {
                border-color: #7aa2f7;
                background-color: #2f3549;
            }

            #downloadInput::placeholder {
                color: #565f89;
            }

            QGroupBox {
                background-color: #16161e;
                border: 1px solid #24283b;
                border-radius: 12px;
                margin-top: 16px;
                padding-top: 16px;
                font-weight: 600;
                font-size: 15px;
                color: #7aa2f7;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 16px;
                padding: 0 8px;
                color: #7aa2f7;
            }

            #downloadRadio {
                color: #c0caf5;
                spacing: 12px;
                font-size: 14px;
                font-weight: 500;
            }

            #downloadRadio::indicator {
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid #414868;
                background-color: #24283b;
            }

            #downloadRadio::indicator:checked {
                background-color: #7aa2f7;
                border-color: #7aa2f7;
            }

            #downloadCancelButton {
                background-color: #24283b;
                color: #a9b1d6;
                border: 2px solid #414868;
                border-radius: 10px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
            }

            #downloadCancelButton:hover {
                background-color: #414868;
            }

            #downloadButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                  stop:0 #7aa2f7, stop:1 #89b4fa);
                color: #1a1b26;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 14px;
            }

            #downloadButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                  stop:0 #89b4fa, stop:1 #7aa2f7);
            }

            #downloadStatusLabel {
                font-size: 13px;
                color: #565f89;
                margin-top: 8px;
                min-height: 20px;
            }
        """)

    def _setup_shadow(self):
        """Настройка тени для контейнера."""
        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.container.setGraphicsEffect(shadow)

    def _on_download(self):
        """Обработка нажатия кнопки скачать."""
        link = self.link_input.text().strip()

        if not link:
            self.status_label.setText("Введите ссылку")
            self.status_label.setStyleSheet("color: #f7768e; font-size: 13px; font-weight: 500;")
            self._shake_input()
            return

        # Определяем тип
        link_type = self._detect_link_type(link)

        if link_type is None:
            self.status_label.setText("Неверный формат ссылки")
            self.status_label.setStyleSheet("color: #f7768e; font-size: 13px; font-weight: 500;")
            return

        self.status_label.setText("✓ Ссылка принята! Начинаем загрузку...")
        self.status_label.setStyleSheet("color: #9ece6a; font-size: 13px; font-weight: 500;")
        
        self._status_fade = AnimationHelper.fade_in(self.status_label, 300)
        self._status_fade.start()

        self.link_downloaded.emit(link, link_type)
        self.accept()

    def _shake_input(self):
        """Анимация тряски поля ввода."""
        from PyQt5.QtCore import QPropertyAnimation, QPoint

        original_pos = self.link_input.pos()

        self._shake_animation = QPropertyAnimation(self.link_input, b"pos")
        self._shake_animation.setDuration(300)
        self._shake_animation.setKeyValueAt(0, original_pos)
        self._shake_animation.setKeyValueAt(0.1, original_pos + QPoint(-10, 0))
        self._shake_animation.setKeyValueAt(0.2, original_pos + QPoint(10, 0))
        self._shake_animation.setKeyValueAt(0.3, original_pos + QPoint(-10, 0))
        self._shake_animation.setKeyValueAt(0.4, original_pos + QPoint(10, 0))
        self._shake_animation.setKeyValueAt(0.5, original_pos)
        self._shake_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._shake_animation.finished.connect(self._shake_animation.deleteLater)
        self._shake_animation.start()

    def _detect_link_type(self, link: str) -> str:
        """
        Определение типа ссылки.

        Returns:
            str: 'track', 'album', 'playlist' или None
        """
        if '/track/' in link:
            return 'track'
        elif '/album/' in link and '/track/' not in link:
            return 'album'
        elif '/playlists/' in link or '/playlist/' in link:
            return 'playlist'

        return None
