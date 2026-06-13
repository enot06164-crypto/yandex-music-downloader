# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
GUI модуль - Окно настроек (обновлённый дизайн).

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, \
    QLineEdit, QPushButton, QFrame, QComboBox, QCheckBox, QFileDialog, \
    QGroupBox, QSpinBox, QDoubleSpinBox, QGraphicsDropShadowEffect, QScrollArea
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QFont, QColor

from .icons import Icons, get_pixmap
from .animations import AnimationHelper
from config import Config


class SettingsDialog(QDialog):
    """Диалог настроек приложения с современным дизайном."""

    settings_saved = pyqtSignal()

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Настройки")
        self.setFixedSize(550, 520)
        self.setModal(True)

        self._setup_ui()
        self._setup_styles()
        self._setup_shadow()
        self._load_settings()

    def _setup_ui(self):
        """Настройка интерфейса."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ScrollArea для содержимого
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("settingsScrollArea")

        # Контейнер
        self.container = QFrame()
        self.container.setObjectName("settingsContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(12)
        container_layout.setContentsMargins(18, 14, 18, 14)

        # ===== Заголовок =====
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(get_pixmap('settings', 22, '#7aa2f7'))
        header_layout.addWidget(self.icon_label)

        self.title_label = QLabel("Настройки")
        self.title_label.setObjectName("settingsTitleLabel")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()
        container_layout.addLayout(header_layout)

        # ===== Группа: Загрузка =====
        download_group = QGroupBox("Загрузка")
        download_layout = QVBoxLayout(download_group)
        download_layout.setSpacing(10)
        download_layout.setContentsMargins(14, 12, 14, 12)

        # Путь сохранения
        path_label = QLabel("Папка для музыки:")
        path_label.setObjectName("settingsFieldLabel")
        download_layout.addWidget(path_label)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setObjectName("settingsInput")
        path_layout.addWidget(self.path_input, 1)

        self.browse_btn = QPushButton("Обзор")
        self.browse_btn.setObjectName("settingsBrowseButton")
        self.browse_btn.setFixedHeight(40)
        self.browse_btn.clicked.connect(self._browse_folder)
        path_layout.addWidget(self.browse_btn)

        download_layout.addLayout(path_layout)

        # Качество аудио
        quality_label = QLabel("Качество аудио:")
        quality_label.setObjectName("settingsFieldLabel")
        download_layout.addWidget(quality_label)

        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Лучшее (320 кбит/с)", "best")
        self.quality_combo.addItem("Высокое (320 кбит/с)", "high")
        self.quality_combo.addItem("Среднее (192 кбит/с)", "medium")
        self.quality_combo.addItem("Низкое (128 кбит/с)", "low")
        self.quality_combo.setObjectName("settingsCombo")
        self.quality_combo.setMinimumHeight(40)
        download_layout.addWidget(self.quality_combo)

        container_layout.addWidget(download_group)

        # ===== Группа: Интерфейс =====
        ui_group = QGroupBox("Интерфейс")
        ui_layout = QVBoxLayout(ui_group)
        ui_layout.setSpacing(8)
        ui_layout.setContentsMargins(14, 10, 14, 10)

        self.notifications_check = QCheckBox("Показывать уведомления о завершении")
        self.notifications_check.setObjectName("settingsCheckBox")
        ui_layout.addWidget(self.notifications_check)

        self.cover_check = QCheckBox("Встраивать обложку в файл")
        self.cover_check.setObjectName("settingsCheckBox")
        ui_layout.addWidget(self.cover_check)

        self.lyrics_check = QCheckBox("Встраивать текст песни (если доступен)")
        self.lyrics_check.setObjectName("settingsCheckBox")
        ui_layout.addWidget(self.lyrics_check)

        container_layout.addWidget(ui_group)

        # ===== Группа: API =====
        api_group = QGroupBox("API и сеть")
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(10)
        api_layout.setContentsMargins(14, 10, 14, 10)

        # Задержка API
        delay_layout = QHBoxLayout()
        delay_label = QLabel("Задержка между запросами:")
        delay_label.setObjectName("settingsFieldLabel")
        delay_layout.addWidget(delay_label)
        delay_layout.addStretch()

        # Задержка API — QDoubleSpinBox, потому что дефолт 0.5 сек,
        # а int(QSpinBox) при загрузке .api_delay=0.5 давал 0 и
        # обнулял конфиг при каждом «Сохранить» без изменений.
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 5.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setDecimals(1)
        self.delay_spin.setSuffix(" сек")
        self.delay_spin.setObjectName("settingsSpin")
        self.delay_spin.setMinimumWidth(80)
        self.delay_spin.setMaximumWidth(80)
        delay_layout.addWidget(self.delay_spin)

        api_layout.addLayout(delay_layout)

        # Таймаут
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("Таймаут запросов:")
        timeout_label.setObjectName("settingsFieldLabel")
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addStretch()

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setSingleStep(5)
        self.timeout_spin.setSuffix(" сек")
        self.timeout_spin.setObjectName("settingsSpin")
        self.timeout_spin.setMinimumWidth(80)
        self.timeout_spin.setMaximumWidth(80)
        timeout_layout.addWidget(self.timeout_spin)

        api_layout.addLayout(timeout_layout)
        container_layout.addWidget(api_group)

        # ===== Кнопки =====
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.reset_btn = QPushButton("Сбросить")
        self.reset_btn.setObjectName("settingsResetButton")
        self.reset_btn.setMinimumHeight(44)
        self.reset_btn.clicked.connect(self._reset_settings)
        buttons_layout.addWidget(self.reset_btn)

        buttons_layout.addStretch()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("settingsCancelButton")
        self.cancel_btn.setMinimumHeight(44)
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("settingsSaveButton")
        self.save_btn.setMinimumHeight(44)
        self.save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(self.save_btn)

        container_layout.addLayout(buttons_layout)

        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)

    def _setup_styles(self):
        """Настройка стилей."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
            }

            #settingsScrollArea {
                background-color: transparent;
                border: none;
            }

            #settingsScrollArea > QWidget {
                background-color: transparent;
            }

            #settingsContainer {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #1e2030, stop:1 #1a1b26);
                border-radius: 20px;
                border: 1px solid #24283b;
            }

            #settingsTitleLabel {
                font-size: 18px;
                font-weight: 700;
                color: #7aa2f7;
            }

            QGroupBox {
                background-color: #16161e;
                border: 1px solid #24283b;
                border-radius: 12px;
                margin-top: 16px;
                padding-top: 24px;
                font-weight: 600;
                font-size: 15px;
                color: #7aa2f7;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 16px;
                top: 6px;
                padding: 0 8px;
                color: #7aa2f7;
            }

            #settingsFieldLabel {
                color: #a9b1d6;
                font-size: 13px;
                font-weight: 500;
            }

            #settingsInput {
                background-color: #24283b;
                border: 2px solid #414868;
                border-radius: 8px;
                padding: 10px 14px;
                color: #c0caf5;
                font-size: 13px;
            }

            #settingsInput:focus {
                border-color: #7aa2f7;
            }

            #settingsCombo {
                background-color: #24283b;
                border: 2px solid #414868;
                border-radius: 8px;
                padding: 10px 14px;
                color: #c0caf5;
                font-size: 14px;
            }

            #settingsCombo:focus {
                border-color: #7aa2f7;
            }

            #settingsCheckBox {
                color: #c0caf5;
                spacing: 12px;
                font-size: 14px;
                font-weight: 500;
            }

            #settingsCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 6px;
                border: 2px solid #414868;
                background-color: #24283b;
            }

            #settingsCheckBox::indicator:checked {
                background-color: #7aa2f7;
                border-color: #7aa2f7;
            }

            #settingsSpin {
                background-color: #24283b;
                border: 2px solid #414868;
                border-radius: 8px;
                padding: 10px 14px;
                padding-right: 24px;
                color: #c0caf5;
                font-size: 14px;
            }

            #settingsSpin:focus {
                border-color: #7aa2f7;
            }

            #settingsSpin::up-button,
            #settingsSpin::down-button {
                width: 14px;
                height: 8px;
                background-color: transparent;
            }

            #settingsSpin::up-arrow {
                width: 5px;
                height: 3px;
            }

            #settingsSpin::down-arrow {
                width: 5px;
                height: 3px;
            }

            #settingsBrowseButton {
                background-color: #24283b;
                color: #7aa2f7;
                border: 2px solid #414868;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 13px;
            }

            #settingsBrowseButton:hover {
                background-color: #414868;
                border-color: #7aa2f7;
            }

            #settingsResetButton {
                background-color: #24283b;
                color: #f7768e;
                border: 2px solid #f7768e;
                border-radius: 10px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
            }

            #settingsResetButton:hover {
                background-color: #f7768e;
                color: #1a1b26;
            }

            #settingsCancelButton {
                background-color: #24283b;
                color: #a9b1d6;
                border: 2px solid #414868;
                border-radius: 10px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
            }

            #settingsCancelButton:hover {
                background-color: #414868;
            }

            #settingsSaveButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                  stop:0 #9ece6a, stop:1 #73daca);
                color: #1a1b26;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 14px;
            }

            #settingsSaveButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                  stop:0 #b4f98a, stop:1 #9ece6a);
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

    def _load_settings(self):
        """Загрузка настроек."""
        self.path_input.setText(str(self._config.music_path))

        quality = self._config.audio_quality
        index = self.quality_combo.findData(quality)
        if index >= 0:
            self.quality_combo.setCurrentIndex(index)

        self.notifications_check.setChecked(self._config.get('show_notifications', True))
        self.cover_check.setChecked(self._config.get('embed_cover', True))
        self.lyrics_check.setChecked(self._config.get('embed_lyrics', False))

        self.delay_spin.setValue(float(self._config.api_delay))
        self.timeout_spin.setValue(int(self._config.request_timeout))

    def _browse_folder(self):
        """Выбор папки."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для музыки",
            str(self._config.music_path)
        )

        if folder:
            self.path_input.setText(folder)

    def _save_settings(self):
        """Сохранение настроек."""
        self._config.music_path = Path(self.path_input.text())

        quality = self.quality_combo.currentData()
        self._config.audio_quality = quality

        self._config.set('show_notifications', self.notifications_check.isChecked())
        self._config.set('embed_cover', self.cover_check.isChecked())
        self._config.set('embed_lyrics', self.lyrics_check.isChecked())

        self._config.api_delay = float(self.delay_spin.value())
        self._config.request_timeout = int(self.timeout_spin.value())

        self._config.save()

        self.settings_saved.emit()
        self.accept()

    def _reset_settings(self):
        """Сброс настроек к дефолтам.

        Сохраняем на диск сразу — иначе после «Сбросить» → «Отмена»
        значения в памяти обнулятся, а в файле останутся старые.
        """
        self._config.reset()
        self._config.save()
        self._load_settings()
