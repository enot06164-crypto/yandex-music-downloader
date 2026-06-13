# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
GUI модуль - Диалог авторизации (упрощённый).

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

import webbrowser
from typing import Optional

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, \
    QLineEdit, QPushButton, QFrame, QWidget, QTextBrowser
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRectF
from PyQt5.QtGui import QFont, QIcon, QPainter, QColor, QPen, QFontMetrics

from .icons import Icons, get_pixmap


class UserIconWidget(QLabel):
    """Виджет для отрисовки иконки пользователя."""

    def __init__(self, size: int = 72, parent=None):
        super().__init__(parent)
        self._icon_size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        """Отрисовка иконки пользователя."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Фон - круг
        painter.setBrush(QColor("#24283b"))
        painter.setPen(QPen(QColor("#7aa2f7"), 2))
        painter.drawEllipse(2, 2, self._icon_size - 4, self._icon_size - 4)

        # Голова
        head_radius = (self._icon_size - 4) * 0.2
        head_center_y = (self._icon_size - 4) * 0.35 + 2
        painter.setBrush(QColor("#c0caf5"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            QRectF(
                (self._icon_size - head_radius * 2) / 2,
                head_center_y - head_radius,
                head_radius * 2,
                head_radius * 2
            )
        )

        # Тело
        body_top = head_center_y + head_radius + (self._icon_size - 4) * 0.15
        body_width = (self._icon_size - 4) * 0.5
        body_left = (self._icon_size - body_width) / 2
        painter.drawEllipse(
            QRectF(
                body_left,
                body_top,
                body_width,
                body_width * 0.8
            )
        )

        painter.end()


class AuthDialog(QDialog):
    """Диалог авторизации в Яндекс.Музыке."""

    token_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Авторизация")
        self.setFixedSize(580, 720)
        self.setModal(True)

        self._setup_ui()
        self._setup_styles()

    def _setup_ui(self):
        """Настройка интерфейса диалога."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 32, 32, 32)

        # ===== Заголовок =====
        self.title_label = QLabel("Вход в Яндекс.Музыку")
        self.title_label.setObjectName("authTitleLabel")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Для работы необходим токен Яндекс.Музыки")
        self.subtitle_label.setObjectName("authSubtitleLabel")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle_label)

        # ===== Иконка =====
        icon_container = QWidget()
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setAlignment(Qt.AlignCenter)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        self.user_icon = UserIconWidget(size=72)
        icon_layout.addWidget(self.user_icon)
        layout.addWidget(icon_container)

        # ===== Инструкция =====
        steps_frame = QFrame()
        steps_frame.setObjectName("authStepsFrame")
        steps_layout = QVBoxLayout(steps_frame)
        steps_layout.setSpacing(0)
        steps_layout.setContentsMargins(20, 16, 20, 16)

        # HTML инструкция
        self.instructions_text = QTextBrowser()
        self.instructions_text.setOpenExternalLinks(False)
        self.instructions_text.setReadOnly(True)
        self.instructions_text.setObjectName("authInstructionsText")
        self.instructions_text.setFrameShape(QFrame.NoFrame)
        self.instructions_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.instructions_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        html_content = """
        <div style="text-align: center; margin-bottom: 12px;">
            <span style="color: #7aa2f7; font-size: 15px; font-weight: 600;">Как получить токен</span>
        </div>
        <div style="color: #3b3d54; height: 1px; margin-bottom: 12px;"></div>
        <div style="color: #c0caf5; font-size: 14px; line-height: 1.8;">
            <div style="margin-bottom: 6px;">1. Нажмите кнопку «Получить токен»</div>
            <div style="margin-bottom: 6px;">2. Войдите в аккаунт Яндекс в браузере</div>
            <div style="margin-bottom: 6px;">3. Скопируйте URL из адресной строки</div>
            <div style="margin-bottom: 6px;">4. Вставьте ссылку в поле ввода ниже</div>
        </div>
        <div style="color: #3b3d54; height: 1px; margin: 12px 0;"></div>
        <div style="text-align: center; color: #565f89; font-size: 12px; font-family: Consolas, monospace;">
            Формат токена: <span style="color: #7aa2f7;">y0__...</span> или <span style="color: #7aa2f7;">y1__...</span>
        </div>
        """
        self.instructions_text.setHtml(html_content)
        self.instructions_text.document().setDocumentMargin(0)
        self.instructions_text.setMinimumHeight(200)

        steps_layout.addWidget(self.instructions_text)

        layout.addWidget(steps_frame)

        # ===== Разделитель =====
        separator = QFrame()
        separator.setObjectName("authSeparator")
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)

        # ===== Поле ввода =====
        input_label = QLabel("Вставьте ссылку или токен:")
        input_label.setObjectName("authInputLabel")
        layout.addWidget(input_label)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("https://music.yandex.ru/#access_token=y0__...")
        self.token_input.setObjectName("authInput")
        self.token_input.setClearButtonEnabled(True)
        layout.addWidget(self.token_input)

        # ===== Кнопки =====
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        self.get_token_btn = QPushButton("Получить токен")
        self.get_token_btn.setObjectName("authGetTokenButton")
        self.get_token_btn.setIcon(QIcon(get_pixmap('link', 18, '#1a1b26')))
        self.get_token_btn.setIconSize(QSize(18, 18))
        self.get_token_btn.setMinimumHeight(48)
        self.get_token_btn.clicked.connect(self._open_token_page)
        buttons_layout.addWidget(self.get_token_btn)

        self.login_btn = QPushButton("✓ Войти")
        self.login_btn.setObjectName("authLoginButton")
        self.login_btn.setMinimumHeight(48)
        self.login_btn.clicked.connect(self._on_login_clicked)
        buttons_layout.addWidget(self.login_btn)

        layout.addLayout(buttons_layout)

        # ===== Статус =====
        self.status_label = QLabel("")
        self.status_label.setObjectName("authStatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def _setup_styles(self):
        """Настройка стилей диалога."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1b26;
            }

            #authTitleLabel {
                font-size: 26px;
                font-weight: 700;
                color: #7aa2f7;
                letter-spacing: 0.5px;
            }

            #authSubtitleLabel {
                font-size: 14px;
                color: #a9b1d6;
            }

            #authStepsFrame {
                background-color: #16161e;
                border: 1px solid #24283b;
                border-radius: 12px;
            }

            #authInstructionsText {
                background-color: transparent;
                border: none;
                color: #c0caf5;
                font-size: 14px;
                font-family: 'Segoe UI', 'Roboto', sans-serif;
            }

            #authSeparator {
                color: #24283b;
                background-color: #24283b;
                min-height: 1px;
                max-height: 1px;
            }

            #authInputLabel {
                font-size: 13px;
                color: #a9b1d6;
                font-weight: 500;
            }

            #authInput {
                background-color: #24283b;
                border: 2px solid #414868;
                border-radius: 10px;
                padding: 14px 18px;
                color: #c0caf5;
                font-size: 14px;
                min-height: 50px;
            }

            #authInput:focus {
                border-color: #7aa2f7;
                background-color: #2f3549;
            }

            #authInput::placeholder {
                color: #565f89;
            }

            #authGetTokenButton {
                background-color: #7aa2f7;
                color: #1a1b26;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
            }

            #authGetTokenButton:hover {
                background-color: #89b4fa;
            }

            #authLoginButton {
                background-color: #9ece6a;
                color: #1a1b26;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
            }

            #authLoginButton:hover {
                background-color: #b4f98a;
            }

            #authStatusLabel {
                font-size: 12px;
                color: #565f89;
                margin-top: 8px;
                min-height: 20px;
            }
        """)

    def _open_token_page(self):
        """Открытие страницы для получения токена."""
        url = "https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d"

        try:
            import webbrowser
            webbrowser.open(url)

            self.status_label.setText("✓ Браузер открыт. Скопируйте URL и вставьте в поле выше")
            self.status_label.setStyleSheet("color: #9ece6a; font-size: 13px; font-weight: 500;")
        except Exception as e:
            self.status_label.setText(f"Ошибка: {e}")
            self.status_label.setStyleSheet("color: #f7768e; font-size: 13px;")

    def _on_login_clicked(self):
        """Обработка нажатия кнопки входа."""
        input_text = self.token_input.text().strip()

        if not input_text:
            self.status_label.setText("Введите ссылку или токен")
            self.status_label.setStyleSheet("color: #f7768e; font-size: 13px; font-weight: 500;")
            self.token_input.setFocus()
            return

        # Извлекаем токен из ссылки или используем как есть
        token = self._extract_token(input_text)

        if not token:
            self.status_label.setText("Не удалось извлечь токен")
            self.status_label.setStyleSheet("color: #f7768e; font-size: 13px; font-weight: 500;")
            return

        if len(token) < 10:
            self.status_label.setText("Некорректный формат токена")
            self.status_label.setStyleSheet("color: #f7768e; font-size: 13px; font-weight: 500;")
            return

        # Проверяем формат токена Яндекс
        if not token.startswith('y0__') and not token.startswith('y1__'):
            self.status_label.setText(
                f"Неверный формат (начинается с '{token[:5]}', должно быть 'y0__' или 'y1__')"
            )
            self.status_label.setStyleSheet("color: #f7768e; font-size: 13px; font-weight: 500;")
            return

        # Токен получен
        self.status_label.setText("✓ Токен получен! Выполняется вход...")
        self.status_label.setStyleSheet("color: #9ece6a; font-size: 13px; font-weight: 500;")

        self.token_received.emit(token)
        self.accept()

    def _extract_token(self, text: str) -> str:
        """
        Извлечение токена из URL или возврат как есть.

        Args:
            text (str): URL или токен.

        Returns:
            str: Токен или пустая строка.
        """
        import re

        # Если текст уже похож на токен (начинается с y0__ или y1__)
        if text.startswith('y0__') or text.startswith('y1__'):
            return text.strip()

        # Проверяем, есть ли в тексте URL с токеном
        parts = re.split(r'[#?]', text)

        for part in parts:
            # Ищем access_token= в каждой части
            match = re.search(r'access_token=([^&\s]+)', part)
            if match:
                token = match.group(1)
                token = token.rstrip('&').strip()
                return token

            # Запасной вариант
            match = re.search(r'token=([^&\s]+)', part)
            if match:
                token = match.group(1)
                token = token.rstrip('&').strip()
                return token

        # Если не нашли, возвращаем как есть (вдруг это уже токен)
        return text.strip()

    def set_error(self, message: str):
        """Установка сообщения об ошибке."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #f7768e; font-size: 13px; font-weight: 500;")

    def set_success(self, message: str):
        """Установка сообщения об успехе."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #9ece6a; font-size: 13px; font-weight: 500;")

    def get_token(self) -> Optional[str]:
        """Получение введенного токена (извлекает из ссылки если нужно)."""
        input_text = self.token_input.text().strip()
        if not input_text:
            return None

        # Извлекаем токен из ссылки или возвращаем как есть
        return self._extract_token(input_text)
