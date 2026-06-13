# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
Skeleton Loading виджет.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QLinearGradient, QPalette, QColor


class SkeletonLine(QFrame):
    """Анимированная строка skeleton loading."""

    def __init__(self, width: int = None, height: int = 16, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        if width:
            self.setFixedWidth(width)
        else:
            self.setMinimumWidth(100)
        self._setup_styles()
        self._start_animation()

    def _setup_styles(self):
        """Настройка стилей с градиентом."""
        self.setObjectName("skeletonLine")
        self.setStyleSheet("""
            #skeletonLine {
                background-color: #24283b;
                border-radius: 8px;
            }
        """)

    def _start_animation(self):
        """Запуск анимации мерцания."""
        from PyQt5.QtWidgets import QGraphicsOpacityEffect
        from PyQt5.QtCore import QPropertyAnimation

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.5)
        self.setGraphicsEffect(self._opacity_effect)

        self._animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._animation.setDuration(1500)
        self._animation.setStartValue(0.3)
        self._animation.setKeyValueAt(0.5, 0.8)
        self._animation.setEndValue(0.3)
        self._animation.setLoopCount(-1)  # Бесконечный цикл
        self._animation.setEasingCurve(QEasingCurve.InOutSine)
        self._animation.start()


class SkeletonCard(QFrame):
    """Карточка skeleton loading."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)  # Минимальная высота карточки
        self._setup_ui()
        self._setup_styles()

    def _setup_ui(self):
        """Настройка UI."""
        self.setObjectName("skeletonCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Левая часть - обложка (квадрат)
        cover_skeleton = SkeletonLine(80, 80)
        cover_skeleton.setObjectName("skeletonCover")
        layout.addWidget(cover_skeleton)

        # Правая часть - информация
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)

        # Заголовок
        title_skeleton = SkeletonLine(None, 18)
        title_skeleton.setObjectName("skeletonTitle")
        info_layout.addWidget(title_skeleton)

        # Подзаголовок
        subtitle_skeleton = SkeletonLine(250, 14)
        subtitle_skeleton.setObjectName("skeletonSubtitle")
        info_layout.addWidget(subtitle_skeleton)

        # Дополнительная информация
        extra_skeleton = SkeletonLine(180, 12)
        extra_skeleton.setObjectName("skeletonExtra")
        info_layout.addWidget(extra_skeleton)

        info_layout.addStretch()
        layout.addLayout(info_layout)

    def _setup_styles(self):
        """Настройка стилей."""
        self.setStyleSheet("""
            #skeletonCard {
                background-color: #16161e;
                border-radius: 12px;
                border: 1px solid #24283b;
            }
            #skeletonCover {
                border-radius: 8px;
            }
            #skeletonTitle {
                border-radius: 8px;
            }
            #skeletonSubtitle {
                border-radius: 6px;
            }
            #skeletonExtra {
                border-radius: 5px;
            }
        """)


class SkeletonLoadingWidget(QWidget):
    """Виджет skeleton loading для отображения во время загрузки."""

    def __init__(self, count: int = 5, parent=None):
        super().__init__(parent)
        self._count = count
        self._setup_ui()
        self._setup_styles()

    def _setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Создаём несколько skeleton карточек
        for _ in range(self._count):
            card = SkeletonCard()
            layout.addWidget(card)

        layout.addStretch()

    def _setup_styles(self):
        """Настройка стилей."""
        self.setStyleSheet("""
            SkeletonLoadingWidget {
                background-color: transparent;
            }
        """)

    def set_count(self, count: int):
        """Установка количества skeleton карточек."""
        self._count = count
        # Пересоздаём виджеты
        while self.layout().count():
            child = self.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for _ in range(count):
            card = SkeletonCard()
            self.layout().addWidget(card)

        self.layout().addStretch()
