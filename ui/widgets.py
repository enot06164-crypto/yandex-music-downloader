# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
GUI модуль - Базовые компоненты и стили.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, \
    QProgressBar, QFrame, QScrollArea, QSizePolicy, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QIcon

from .icons import Icons, get_pixmap


# =============================================================================
# СТИЛИ (QSS) - Современный дизайн
# =============================================================================

DARK_THEME_STYLESHEET = """
/* ===== Глобальные стили ===== */
QWidget {
    background-color: #1a1b26;
    color: #a9b1d6;
    font-family: 'Segoe UI', 'Roboto', 'Inter', sans-serif;
    font-size: 14px;
}

/* ===== Главное окно ===== */
QMainWindow {
    background-color: #1a1b26;
}

QMainWindow::separator {
    background-color: #24283b;
    width: 1px;
}

/* ===== Кнопки ===== */
QPushButton {
    background-color: #7aa2f7;
    color: #1a1b26;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 14px;
    min-width: 100px;
}

QPushButton:hover {
    background-color: #89b4fa;
}

QPushButton:pressed {
    background-color: #5d87e5;
}

QPushButton:disabled {
    background-color: #24283b;
    color: #565f89;
}

QPushButton#primaryButton {
    background-color: #9ece6a;
    color: #1a1b26;
}

QPushButton#primaryButton:hover {
    background-color: #b4f98a;
}

QPushButton#dangerButton {
    background-color: #f7768e;
    color: #1a1b26;
}

QPushButton#dangerButton:hover {
    background-color: #ff94a6;
}

QPushButton#secondaryButton {
    background-color: #24283b;
    color: #a9b1d6;
    border: 1px solid #414868;
}

QPushButton#secondaryButton:hover {
    background-color: #414868;
}

QPushButton#loadMoreButton {
    background-color: transparent;
    color: #7aa2f7;
    border: 1px solid #414868;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 500;
    font-size: 14px;
    min-width: 200px;
    margin: 12px 0;
}

QPushButton#loadMoreButton:hover {
    background-color: #24283b;
    border-color: #7aa2f7;
}

QPushButton#loadMoreButton:disabled {
    color: #565f89;
    border-color: #24283b;
}

/* ===== Карточка трека (TrackCardWidget) — раньше дублировалась на каждый виджет ===== */
#cardFrame {
    background-color: #24283b;
    border-radius: 12px;
    border: 1px solid #414868;
}

#cardFrame:hover {
    background-color: #2f3549;
    border-color: #7aa2f7;
}

#coverLabel {
    background-color: #16161e;
    border-radius: 8px;
}

#trackTitleLabel {
    font-size: 16px;
    font-weight: 700;
    color: #c0caf5;
}

#trackArtistLabel {
    font-size: 14px;
    color: #7aa2f7;
}

#trackAlbumLabel {
    font-size: 12px;
    color: #565f89;
}

#trackDurationLabel {
    font-size: 12px;
    color: #565f89;
}

#trackSizeLabel {
    font-size: 11px;
    color: #73daca;
    font-weight: 500;
    margin-left: 8px;
}

#downloadButton {
    background-color: #9ece6a;
    color: #1a1b26;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 14px;
}

#downloadButton:hover {
    background-color: #b4f98a;
}

#downloadButton:pressed {
    background-color: #89dceb;
}

QPushButton#iconButton {
    min-width: 40px;
    max-width: 40px;
    padding: 10px;
}

QPushButton#searchButton {
    background-color: #7aa2f7;
    color: #1a1b26;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-weight: 600;
    font-size: 14px;
}

QPushButton#searchButton:hover {
    background-color: #89b4fa;
}

/* ===== Поля ввода ===== */
QLineEdit {
    background-color: #24283b;
    border: 2px solid #414868;
    border-radius: 8px;
    padding: 12px 16px;
    color: #c0caf5;
    selection-background-color: #7aa2f7;
    selection-color: #1a1b26;
}

QLineEdit:focus {
    border-color: #7aa2f7;
}

QLineEdit:disabled {
    background-color: #16161e;
    color: #565f89;
}

QLineEdit#searchLine {
    font-size: 15px;
    padding: 14px 18px;
    min-height: 48px;
}

/* ===== Прогресс бар ===== */
QProgressBar {
    background-color: #24283b;
    border: none;
    border-radius: 6px;
    text-align: center;
    height: 24px;
    color: #1a1b26;
    font-weight: bold;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #9ece6a, stop:1 #73daca);
    border-radius: 6px;
}

/* ===== ScrollArea ===== */
QScrollArea {
    background-color: #1a1b26;
    border: none;
}

QScrollBar:vertical {
    background-color: #1a1b26;
    width: 14px;
    border-radius: 7px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background-color: #414868;
    border-radius: 7px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #565f89;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #1a1b26;
    height: 14px;
    border-radius: 7px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background-color: #414868;
    border-radius: 7px;
    min-width: 30px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #565f89;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ===== Labels ===== */
QLabel {
    color: #a9b1d6;
    background-color: transparent;
}

QLabel#titleLabel {
    font-size: 28px;
    font-weight: 700;
    color: #7aa2f7;
    letter-spacing: 0.5px;
}

QLabel#subtitleLabel {
    font-size: 13px;
    color: #565f89;
}

QLabel#statusLabel {
    color: #73daca;
    font-weight: 500;
}

QLabel#errorLabel {
    color: #f7768e;
    font-weight: 500;
}

QLabel#successLabel {
    color: #9ece6a;
    font-weight: 500;
}

QLabel#headingLabel {
    font-size: 18px;
    font-weight: 600;
    color: #c0caf5;
}

/* ===== GroupBox ===== */
QGroupBox {
    background-color: #16161e;
    border: 1px solid #24283b;
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    font-size: 14px;
    color: #7aa2f7;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 8px;
    color: #7aa2f7;
}

/* ===== ComboBox ===== */
QComboBox {
    background-color: #24283b;
    border: 2px solid #414868;
    border-radius: 8px;
    padding: 10px 14px;
    color: #c0caf5;
    min-height: 24px;
}

QComboBox:hover {
    border-color: #565f89;
}

QComboBox:focus {
    border-color: #7aa2f7;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #a9b1d6;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #24283b;
    border: 1px solid #414868;
    border-radius: 8px;
    selection-background-color: #414868;
    color: #c0caf5;
    outline: none;
}

QComboBox QAbstractItemView::item {
    min-height: 40px;
    padding: 8px 12px;
}

/* ===== CheckBox ===== */
QCheckBox {
    color: #a9b1d6;
    spacing: 10px;
    font-weight: 500;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 5px;
    border: 2px solid #414868;
    background-color: #24283b;
}

QCheckBox::indicator:checked {
    background-color: #7aa2f7;
    border-color: #7aa2f7;
}

QCheckBox::indicator:hover {
    border-color: #7aa2f7;
}

/* ===== TabWidget ===== */
QTabWidget::pane {
    background-color: #16161e;
    border: 1px solid #24283b;
    border-radius: 12px;
}

QTabBar::tab {
    background-color: #24283b;
    color: #565f89;
    padding: 12px 24px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #1a1b26;
    color: #7aa2f7;
}

QTabBar::tab:hover:!selected {
    background-color: #414868;
    color: #a9b1d6;
}

/* ===== ToolTip ===== */
QToolTip {
    background-color: #24283b;
    color: #c0caf5;
    border: 1px solid #414868;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}

/* ===== Menu ===== */
QMenuBar {
    background-color: #1a1b26;
    color: #a9b1d6;
    padding: 6px;
    font-weight: 500;
}

QMenuBar::item:selected {
    background-color: #24283b;
    border-radius: 6px;
}

QMenu {
    background-color: #1a1b26;
    border: 1px solid #24283b;
    border-radius: 12px;
    padding: 6px;
}

QMenu::item {
    padding: 10px 20px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #24283b;
}

QMenu::separator {
    height: 1px;
    background-color: #24283b;
    margin: 6px 10px;
}

/* ===== StatusBar ===== */
QStatusBar {
    background-color: #16161e;
    border-top: 1px solid #24283b;
    color: #565f89;
    font-size: 13px;
}

/* ===== Slider ===== */
QSlider::groove:horizontal {
    background-color: #24283b;
    height: 8px;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background-color: #7aa2f7;
    width: 20px;
    margin: -6px 0;
    border-radius: 10px;
}

QSlider::handle:horizontal:hover {
    background-color: #89b4fa;
}

QSlider::sub-page:horizontal {
    background-color: #7aa2f7;
    border-radius: 4px;
}

/* ===== SpinBox ===== */
QSpinBox, QDoubleSpinBox {
    background-color: #24283b;
    border: 2px solid #414868;
    border-radius: 8px;
    padding: 10px 14px;
    color: #c0caf5;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #7aa2f7;
}

/* ===== ListWidget ===== */
QListWidget {
    background-color: #16161e;
    border: 1px solid #24283b;
    border-radius: 12px;
    outline: none;
    padding: 4px;
}

QListWidget::item {
    padding: 12px;
    border-radius: 8px;
    margin: 2px 4px;
    border-bottom: 1px solid #24283b;
}

QListWidget::item:selected {
    background-color: #24283b;
    color: #c0caf5;
}

QListWidget::item:hover {
    background-color: #24283b;
}

/* ===== TableWidget ===== */
QTableWidget {
    background-color: #16161e;
    border: 1px solid #24283b;
    border-radius: 12px;
    gridline-color: #24283b;
    outline: none;
}

QTableWidget::item {
    padding: 12px;
}

QTableWidget::item:selected {
    background-color: #24283b;
    color: #c0caf5;
}

QHeaderView::section {
    background-color: #24283b;
    color: #7aa2f7;
    padding: 12px;
    border: none;
    font-weight: 600;
    border-bottom: 2px solid #7aa2f7;
}

/* ===== Dialog ===== */
QDialog {
    background-color: #1a1b26;
}

QMessageBox {
    background-color: #1a1b26;
}

QMessageBox QLabel {
    color: #a9b1d6;
}

QMessageBox QPushButton {
    min-width: 100px;
}

/* ===== Frame/Card ===== */
QFrame#cardFrame {
    background-color: #24283b;
    border-radius: 12px;
    border: 1px solid #414868;
}

QFrame#cardFrame:hover {
    border-color: #7aa2f7;
    background-color: #2f3549;
}

QFrame#headerFrame {
    background-color: #16161e;
    border-radius: 16px;
    border: 1px solid #24283b;
}

QFrame#contentFrame {
    background-color: #16161e;
    border-radius: 12px;
    border: 1px solid #24283b;
}

QFrame#progressFrame {
    background-color: #16161e;
    border-radius: 12px;
    border: 1px solid #24283b;
}
"""


# =============================================================================
# БАЗОВЫЕ ВИДЖЕТЫ
# =============================================================================

class BaseWidget(QWidget):
    """Базовый класс для всех виджетов приложения."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_styles()
    
    def setup_ui(self):
        """Настройка интерфейса. Переопределяется в подклассах."""
        pass
    
    def setup_styles(self):
        """Настройка стилей. Переопределяется в подклассах."""
        pass


class CardWidget(QFrame):
    """Виджет карточки для отображения элементов."""
    
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_styles()
        self._setup_shadow()
    
    def _setup_ui(self):
        """Настройка UI карточки."""
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("cardFrame")
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(16, 16, 16, 16)
        
        self.title_label = QLabel("Название")
        self.title_label.setObjectName("headingLabel")
        self.title_label.setWordWrap(True)
        
        self.subtitle_label = QLabel("Доп. информация")
        self.subtitle_label.setObjectName("subtitleLabel")
        self.subtitle_label.setWordWrap(True)
        
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.subtitle_label)
    
    def _setup_styles(self):
        """Настройка стилей карточки."""
        pass
    
    def _setup_shadow(self):
        """Добавление тени."""
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(20)
        self._shadow.setXOffset(0)
        self._shadow.setYOffset(4)
        self._shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(self._shadow)
    
    def set_data(self, title: str, subtitle: str = ""):
        """Установка данных карточки."""
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)
    
    def mousePressEvent(self, event):
        """Обработка нажатия на карточку."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class LoadingWidget(QWidget):
    """Виджет индикатора загрузки."""
    
    def __init__(self, parent=None, message: str = "Загрузка..."):
        super().__init__(parent)
        self._setup_ui(message)
        self._setup_styles()
        self.hide()
    
    def _setup_ui(self, message: str):
        """Настройка UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(300)
        self.progress.setObjectName("loadingProgress")
        
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setObjectName("loadingMessage")
        
        layout.addWidget(self.progress)
        layout.addWidget(self.message_label)
    
    def _setup_styles(self):
        """Настройка стилей."""
        self.setStyleSheet("""
            LoadingWidget {
                background-color: rgba(26, 27, 38, 0.95);
            }
            #loadingProgress {
                background-color: #24283b;
                border: none;
                border-radius: 6px;
                height: 8px;
            }
            #loadingProgress::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #7aa2f7, stop:1 #bb9af7);
                border-radius: 6px;
            }
            #loadingMessage {
                color: #a9b1d6;
                font-size: 14px;
                margin-top: 12px;
                font-weight: 500;
            }
        """)
    
    def set_message(self, message: str):
        """Установка сообщения."""
        self.message_label.setText(message)


class EmptyStateWidget(QWidget):
    """Виджет пустого состояния."""
    
    def __init__(self, parent=None, message: str = "Ничего не найдено"):
        super().__init__(parent)
        self._setup_ui(message)
        self._setup_styles()
    
    def _setup_ui(self, message: str):
        """Настройка UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(24)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Контейнер для центрирования иконки
        icon_container = QWidget()
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setAlignment(Qt.AlignCenter)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        # Иконка с использованием SVG - по центру
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(128, 128)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setPixmap(get_pixmap('music', 96, '#565f89'))
        icon_layout.addWidget(self.icon_label)
        
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setObjectName("emptyMessage")
        
        layout.addWidget(icon_container)
        layout.addWidget(self.message_label)
    
    def _setup_styles(self):
        """Настройка стилей."""
        self.setStyleSheet("""
            EmptyStateWidget {
                background-color: transparent;
            }
            #emptyMessage {
                font-size: 16px;
                margin-top: 16px;
                color: #565f89;
            }
        """)
    
    def set_message(self, message: str):
        """Установка сообщения."""
        self.message_label.setText(message)


class IconButton(QPushButton):
    """Кнопка с SVG иконкой."""
    
    def __init__(self, icon_name: str = "", text: str = "", parent=None,
                 icon_size: int = 20, icon_color: str = "#1a1b26"):
        super().__init__(parent)
        self._setup_ui(icon_name, text, icon_size, icon_color)
    
    def _setup_ui(self, icon_name: str, text: str, 
                  icon_size: int = 20, icon_color: str = "#1a1b26"):
        """Настройка UI."""
        if icon_name:
            icon = Icons.get_icon(icon_name, icon_size, icon_color)
            self.setIcon(icon)
            self.setIconSize(QSize(icon_size, icon_size))
        
        if text:
            self.setText(text)


def get_dark_stylesheet() -> str:
    """Получение таблицы стилей для темной темы."""
    return DARK_THEME_STYLESHEET
