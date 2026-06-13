# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
Модуль анимаций и визуальных эффектов.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

from PyQt5.QtCore import (QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
                          QSequentialAnimationGroup, QPauseAnimation, pyqtProperty,
                          QObject, QTimer)
from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor


class AnimationHelper(QObject):
    """Помощник для создания анимаций."""

    @staticmethod
    def fade_in(widget: QWidget, duration: int = 300) -> QPropertyAnimation:
        """Плавное появление виджета."""
        opacity_effect = QGraphicsOpacityEffect(widget)
        opacity_effect.setParent(widget)
        widget.setGraphicsEffect(opacity_effect)

        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.finished.connect(lambda: animation.deleteLater())

        return animation

    @staticmethod
    def fade_out(widget: QWidget, duration: int = 300) -> QPropertyAnimation:
        """Плавное исчезновение виджета."""
        opacity_effect = QGraphicsOpacityEffect(widget)
        opacity_effect.setParent(widget)
        widget.setGraphicsEffect(opacity_effect)

        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.InCubic)
        animation.finished.connect(lambda: animation.deleteLater())

        return animation

    @staticmethod
    def slide_in(widget: QWidget, direction: str = 'left', duration: int = 400) -> QPropertyAnimation:
        """Плавное появление со сдвигом."""
        opacity_effect = QGraphicsOpacityEffect(widget)
        opacity_effect.setParent(widget)
        widget.setGraphicsEffect(opacity_effect)

        # Начальная позиция
        if direction == 'left':
            widget.move(-50, widget.y())
        elif direction == 'right':
            widget.move(widget.width() + 50, widget.y())
        elif direction == 'top':
            widget.move(widget.x(), -50)
        elif direction == 'bottom':
            widget.move(widget.x(), widget.height() + 50)

        # Анимация прозрачности
        opacity_animation = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_animation.setDuration(duration)
        opacity_animation.setStartValue(0.0)
        opacity_animation.setEndValue(1.0)
        opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
        opacity_animation.finished.connect(lambda: opacity_animation.deleteLater())

        return opacity_animation

    @staticmethod
    def create_shadow(widget: QWidget, 
                      blur_radius: int = 20,
                      offset: tuple = (0, 4),
                      color: tuple = (0, 0, 0, 80)) -> QGraphicsDropShadowEffect:
        """Создание тени для виджета."""
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur_radius)
        shadow.setXOffset(offset[0])
        shadow.setYOffset(offset[1])
        shadow.setColor(QColor(*color))
        widget.setGraphicsEffect(shadow)
        return shadow

    @staticmethod
    def animate_shadow_hover(widget: QWidget, 
                             normal_shadow: QGraphicsDropShadowEffect,
                             hover_shadow: QGraphicsDropShadowEffect,
                             duration: int = 200) -> QPropertyAnimation:
        """Анимация тени при наведении."""
        animation = QPropertyAnimation(normal_shadow, b"blurRadius")
        animation.setDuration(duration)
        animation.setStartValue(normal_shadow.blurRadius())
        animation.setEndValue(hover_shadow.blurRadius())
        animation.setEasingCurve(QEasingCurve.OutCubic)
        return animation


class HoverAnimation:
    """Анимации при наведении мыши."""

    @staticmethod
    def setup_hover_effect(widget: QWidget, 
                           normal_style: str = "",
                           hover_style: str = ""):
        """
        Настройка эффекта при наведении.
        
        Args:
            widget: Виджет для анимации
            normal_style: Обычный стиль
            hover_style: Стиль при наведении
        """
        widget.setProperty("normal_style", normal_style)
        widget.setProperty("hover_style", hover_style)
        widget.setStyleSheet(normal_style)

    @staticmethod
    def enter_event(widget: QWidget):
        """Обработка входа мыши."""
        hover_style = widget.property("hover_style")
        if hover_style:
            widget.setStyleSheet(hover_style)

    @staticmethod
    def leave_event(widget: QWidget):
        """Обработка выхода мыши."""
        normal_style = widget.property("normal_style")
        if normal_style:
            widget.setStyleSheet(normal_style)


class SequentialCardAnimation:
    """Последовательная анимация появления карточек."""

    @staticmethod
    def animate_cards(cards: list, delay: int = 50, duration: int = 300):
        """
        Анимация последовательного появления карточек.

        Args:
            cards: Список виджетов карточек
            delay: Задержка между карточками (мс)
            duration: Длительность анимации одной карточки (мс)
        """
        for i, card in enumerate(cards):
            # Скрываем карточку
            card.setGraphicsEffect(None)
            card.hide()

            # Показываем с задержкой
            QTimer.singleShot(i * delay, lambda c=card, d=duration: SequentialCardAnimation._show_card(c, d))

    @staticmethod
    def _show_card(card, duration):
        """Показать карточку с анимацией."""
        card.show()
        AnimationHelper.fade_in(card, duration).start()
