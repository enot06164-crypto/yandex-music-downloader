# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
GUI модуль - Главное окно приложения.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, \
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame, QProgressBar, \
    QStatusBar, QMenuBar, QMenu, QAction, QSizePolicy, QSpacerItem, \
    QMessageBox, QFileDialog, QApplication, QStackedWidget, QComboBox, \
    QGroupBox
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QMetaObject, QTimer, QSize
from PyQt5.QtGui import QFont, QIcon, QKeySequence

from .widgets import get_dark_stylesheet, EmptyStateWidget, LoadingWidget, CardWidget
from .auth_dialog import AuthDialog
from .track_card import TrackCardWidget
from .settings_dialog import SettingsDialog
from .download_link_dialog import DownloadLinkDialog
from .icons import Icons, get_pixmap
from .animations import AnimationHelper, SequentialCardAnimation
from .skeleton_loading import SkeletonLoadingWidget

from config import Config, get_config
from crypto import TokenCrypto
from api_client import YandexMusicClient
from downloader import AudioDownloader, DownloadError
from statistics import DownloadStatistics

logger = logging.getLogger(__name__)


class SearchWorker(QThread):
    """Поток для выполнения поиска без блокировки UI."""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, client: YandexMusicClient, query: str,
                 search_type: str = 'track', limit: int = 20,
                 page: int = 0, artist_id=None, parent=None):
        super().__init__(parent)
        self._client = client
        self._query = query
        self._search_type = search_type
        self._limit = limit
        self._page = page
        # Кэш artist_id для «Исполнитель» (ищется на стр.0,
        # используется на всех следующих страницах)
        self._artist_id = artist_id
        self._cancelled = threading.Event()
        self.finished.connect(self.deleteLater)
        self.cancelled.connect(self.deleteLater)

    def cancel(self):
        """Кооперативная отмена (без terminate)."""
        self._cancelled.set()

    def run(self):
        """Выполнение поиска в отдельном потоке."""
        try:
            if self._cancelled.is_set():
                self.cancelled.emit()
                return

            if self._search_type == 'track':
                results = self._client.search_tracks(
                    self._query, self._limit, self._page
                )
            elif self._search_type == 'album':
                results = self._client.search_albums(
                    self._query, self._limit, self._page
                )
            elif self._search_type == 'artist':
                # «Исполнитель»: на стр.0 ищем первого артиста,
                # запоминаем его ID. На стр.>0 используем кэш.
                if self._page == 0:
                    artists_result = self._client.search_artists(
                        self._query, 1
                    )
                    artists_list = (artists_result.get('items', [])
                                    if isinstance(artists_result, dict)
                                    else artists_result)
                    if self._cancelled.is_set():
                        self.cancelled.emit()
                        return
                    if artists_list and len(artists_list) > 0:
                        self._artist_id = artists_list[0].get('id')
                    else:
                        self._artist_id = None

                if self._artist_id:
                    results = self._client.get_artist_tracks(
                        self._artist_id,
                        page=self._page,
                        limit=self._limit,
                    )
                    # Гарантируем наличие ключей
                    if not isinstance(results, dict):
                        results = {
                            'items': results or [],
                            'total': len(results or []),
                            'page': self._page,
                            'limit': self._limit,
                            'has_more': False,
                            'artist_id': self._artist_id,
                        }
                    else:
                        results.setdefault('artist_id', self._artist_id)
                else:
                    results = {
                        'items': [], 'total': 0,
                        'page': self._page, 'limit': self._limit,
                        'has_more': False, 'artist_id': None,
                    }
            elif self._search_type == 'artist_tracks':
                # Прямой поиск треков артиста по ID
                results = self._client.get_artist_tracks(
                    self._query,
                    page=self._page,
                    limit=self._limit,
                )
                if not isinstance(results, dict):
                    results = {
                        'items': results or [],
                        'total': len(results or []),
                        'page': self._page,
                        'limit': self._limit,
                        'has_more': False,
                        'artist_id': self._query,
                    }
            else:
                results = {
                    'items': [],
                    'total': 0,
                    'page': self._page,
                    'limit': self._limit,
                    'has_more': False,
                }

            if self._cancelled.is_set():
                self.cancelled.emit()
                return

            self.finished.emit(results)
        except Exception as e:
            if self._cancelled.is_set():
                self.cancelled.emit()
                return
            logger.error(f"Ошибка поиска: {e}")
            self.error.emit(str(e))


class DownloadWorker(QThread):
    """Поток для загрузки треков без блокировки UI."""

    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(str, bool)
    error = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, downloader: AudioDownloader, client: YandexMusicClient,
                 track_data: Dict[str, Any], save_path: Path, parent=None):
        super().__init__(parent)
        self._downloader = downloader
        self._client = client
        self._track_data = track_data
        self._save_path = save_path
        self._cancelled = threading.Event()
        self.finished.connect(self.deleteLater)
        self.cancelled.connect(self.deleteLater)
        self._done_emitted = False

    def cancel(self):
        """Кооперативная отмена (без terminate)."""
        self._cancelled.set()

    def _emit_finished_once(self, file_path: str, success: bool):
        if not self._done_emitted:
            self._done_emitted = True
            self.finished.emit(file_path, success)

    def _emit_error_once(self, msg: str):
        if not self._done_emitted:
            self._done_emitted = True
            self.error.emit(msg)

    def run(self):
        """Выполнение загрузки в отдельном потоке."""
        if self._cancelled.is_set():
            self.cancelled.emit()
            return

        try:
            track_id = self._track_data.get('id')

            if not track_id:
                self._emit_error_once("ID трека не указан")
                return

            url = self._client.get_track_download_url(track_id)

            if self._cancelled.is_set():
                self.cancelled.emit()
                return
            if not url:
                self._emit_error_once("Не удалось получить URL для скачивания")
                return

            self._track_data['download_url'] = url

            if self._cancelled.is_set():
                self.cancelled.emit()
                return

            file_path = self._downloader._generate_file_path(
                self._track_data,
                self._save_path
            )

            def progress_callback(downloaded, total):
                if self._cancelled.is_set():
                    raise DownloadError("Загрузка отменена")
                self.progress.emit(
                    self._track_data.get('title', ''), downloaded, total
                )

            self._downloader.download_track(
                url, file_path, track_info=self._track_data,
                progress_callback=progress_callback
            )

            if self._cancelled.is_set():
                self.cancelled.emit()
                return

            self._emit_finished_once(str(file_path), True)

        except DownloadError as e:
            if self._cancelled.is_set():
                self.cancelled.emit()
                return
            logger.error(f"Ошибка загрузки: {e}")
            self._emit_error_once(str(e))
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")
            self._emit_error_once(str(e))


class MainWindow(QMainWindow):
    """Главное окно приложения Yandex Music Downloader."""
    
    def __init__(self, config: Optional[Config] = None,
                 token: Optional[str] = None):
        super().__init__()

        self._config = config or get_config()
        self._token = token
        self._crypto = TokenCrypto()
        self._client: Optional[YandexMusicClient] = None
        self._downloader = AudioDownloader(self._config)
        self._statistics = DownloadStatistics()

        self._search_worker: Optional[SearchWorker] = None
        self._download_worker: Optional[DownloadWorker] = None

        # Состояние текущего поиска (для пагинации)
        self._search_query: str = ''
        self._search_type: str = 'track'
        self._search_page: int = 0
        self._search_has_more: bool = False
        self._search_total: int = 0
        self._load_more_btn: Optional[QPushButton] = None
        # Кэш ID артиста для режима «Исполнитель» между страницами
        self._current_artist_id: Optional[Union[str, int]] = None

        # Для отслеживания времени загрузки
        self._download_start_time = 0
        self._download_start_size = 0
        self._current_download_title = 'Трек'

        # Skeleton loading
        self.skeleton_widget = None

        # Tray icon (ленивая инициализация)
        self._tray_icon = None

        # Инициализация UI до инициализации клиента
        self._setup_ui()
        self._setup_styles()
        self._setup_shortcuts()

        # Инициализация клиента после UI
        self._init_client()

        logger.info("Главное окно инициализировано")
    
    def _setup_ui(self):
        """Настройка интерфейса главного окна."""
        self.setWindowTitle("Yandex Music Downloader")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # ===== Заголовок =====
        header_frame = self._create_header()
        main_layout.addWidget(header_frame)
        
        # ===== Панель поиска =====
        search_frame = self._create_search_panel()
        main_layout.addWidget(search_frame)

        # ===== Область результатов =====
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_scroll.setObjectName("resultsScrollArea")

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.results_layout.setSpacing(12)

        self._show_empty_state("Введите поисковый запрос для начала")

        self.results_scroll.setWidget(self.results_container)
        main_layout.addWidget(self.results_scroll, 1)

        # ===== Панель прогресса =====
        progress_frame = self._create_progress_panel()
        main_layout.addWidget(progress_frame)

        # ===== Строка состояния =====
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")

        # ===== Меню =====
        self._create_menu_bar()
    
    def _create_header(self) -> QFrame:
        """Создание заголовка."""
        frame = QFrame()
        frame.setObjectName("headerFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        
        # Логотип и название
        title_layout = QVBoxLayout()
        
        self.title_label = QLabel("Yandex Music Downloader")
        self.title_label.setObjectName("titleLabel")
        title_layout.addWidget(self.title_label)
        
        self.subtitle_label = QLabel("Скачивайте музыку в лучшем качестве")
        self.subtitle_label.setObjectName("subtitleLabel")
        title_layout.addWidget(self.subtitle_label)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Инфо о пользователе
        user_layout = QHBoxLayout()

        self.user_icon = QLabel()
        self.user_icon.setFixedSize(32, 32)
        self.user_icon.setPixmap(get_pixmap('user', 24, '#7aa2f7'))
        user_layout.addWidget(self.user_icon)

        self.user_label = QLabel("Не авторизован")
        self.user_label.setObjectName("statusLabel")
        user_layout.addWidget(self.user_label)

        layout.addLayout(user_layout)

        return frame
    
    def _create_search_panel(self) -> QFrame:
        """Создание панели поиска."""
        frame = QFrame()
        frame.setObjectName("contentFrame")
        layout = QHBoxLayout(frame)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Тип поиска (выпадающий список)
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItem(Icons.music(16, "#1a1b26"), "Треки")
        self.search_type_combo.addItem(Icons.user(16, "#1a1b26"), "Исполнитель (все треки)")
        self.search_type_combo.addItem(Icons.folder(16, "#1a1b26"), "Альбомы")
        self.search_type_combo.setObjectName("searchTypeCombo")
        self.search_type_combo.setMinimumWidth(180)
        self.search_type_combo.setMinimumHeight(48)
        layout.addWidget(self.search_type_combo)

        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.setObjectName("searchLine")
        self.search_input.returnPressed.connect(self._on_search)
        layout.addWidget(self.search_input, 1)

        # Кнопка поиска
        self.search_btn = QPushButton()
        self.search_btn.setIcon(Icons.search(14, "#1a1b26"))
        self.search_btn.setIconSize(QSize(14, 14))
        self.search_btn.setObjectName("iconButton")
        self.search_btn.setFixedSize(36, 36)
        self.search_btn.setToolTip("Поиск")
        self.search_btn.clicked.connect(self._on_search)
        layout.addWidget(self.search_btn)

        # Кнопка настроек
        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(Icons.settings(14, "#a9b1d6"))
        self.settings_btn.setIconSize(QSize(14, 14))
        self.settings_btn.setObjectName("settingsButton")
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setToolTip("Настройки")
        self.settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self.settings_btn)

        return frame
    
    def _create_progress_panel(self) -> QFrame:
        """Создание панели прогресса."""
        frame = QFrame()
        frame.setObjectName("progressFrame")
        layout = QVBoxLayout(frame)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Заголовок прогресса
        progress_header = QHBoxLayout()

        self.progress_icon = QLabel()
        self.progress_icon.setPixmap(get_pixmap('loading', 20, '#7aa2f7'))
        progress_header.addWidget(self.progress_icon)

        self.progress_label = QLabel("Готов к работе")
        self.progress_label.setObjectName("headingLabel")
        progress_header.addWidget(self.progress_label)

        progress_header.addStretch()

        # ETA (оставшееся время)
        self.eta_label = QLabel("")
        self.eta_label.setObjectName("statusLabel")
        self.eta_label.hide()
        progress_header.addWidget(self.eta_label)

        self.progress_status = QLabel("")
        self.progress_status.setObjectName("statusLabel")
        progress_header.addWidget(self.progress_status)

        # Кнопка отмены
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setIcon(Icons.close(16, "#1a1b26"))
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setMinimumHeight(30)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.hide()  # Скрыта по умолчанию
        progress_header.addWidget(self.cancel_btn)

        layout.addLayout(progress_header)

        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ожидание...")
        self.progress_bar.setObjectName("progressBar")
        layout.addWidget(self.progress_bar)

        # Статистика загрузок
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)

        self.stats_downloads_label = QLabel(f"Всего: {self._statistics.get_total_downloads()}")
        self.stats_downloads_label.setObjectName("statsLabel")
        stats_layout.addWidget(self.stats_downloads_label)

        self.stats_size_label = QLabel(f"{self._statistics.format_size(self._statistics.get_total_size())}")
        self.stats_size_label.setObjectName("statsLabel")
        stats_layout.addWidget(self.stats_size_label)

        self.stats_today_label = QLabel(f"Сегодня: {self._statistics.get_today_downloads()}")
        self.stats_today_label.setObjectName("statsLabel")
        stats_layout.addWidget(self.stats_today_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        return frame
    
    def _setup_styles(self):
        """Настройка стилей главного окна."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1b26;
            }

            #headerFrame {
                background-color: #16161e;
                border-radius: 16px;
                border: 1px solid #24283b;
            }

            #contentFrame {
                background-color: #16161e;
                border-radius: 12px;
                border: 1px solid #24283b;
            }

            #searchTypeCombo {
                background-color: #24283b;
                border: 2px solid #414868;
                border-radius: 8px;
                padding: 10px 14px;
                color: #c0caf5;
                font-size: 14px;
                font-weight: 500;
            }

            #searchTypeCombo:focus {
                border-color: #7aa2f7;
            }

            #searchTypeCombo::drop-down {
                border: none;
                width: 30px;
            }

            #searchTypeCombo::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #a9b1d6;
                margin-right: 10px;
            }

            #searchLine {
                background-color: #24283b;
                border: 2px solid #414868;
                border-radius: 8px;
                padding: 14px 18px;
                color: #c0caf5;
                font-size: 15px;
                min-height: 48px;
            }

            #searchLine:focus {
                border-color: #7aa2f7;
            }

            #searchButton {
                background-color: #7aa2f7;
                color: #1a1b26;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 14px;
                min-height: 48px;
            }

            #searchButton:hover {
                background-color: #89b4fa;
            }

            #secondaryButton {
                background-color: #24283b;
                color: #a9b1d6;
                border: 1px solid #414868;
                border-radius: 8px;
            }
            
            #secondaryButton:hover {
                background-color: #414868;
            }

            #iconButton {
                background-color: #7aa2f7;
                color: #1a1b26;
                border: none;
                border-radius: 18px;
                padding: 11px;
                min-width: 36px;
                max-width: 36px;
            }

            #iconButton:hover {
                background-color: #89b4fa;
            }

            #settingsButton {
                background-color: #24283b;
                color: #a9b1d6;
                border: 1px solid #414868;
                border-radius: 18px;
                padding: 11px;
                min-width: 36px;
                max-width: 36px;
            }

            #settingsButton:hover {
                background-color: #414868;
                border-color: #7aa2f7;
            }

            #resultsScrollArea {
                background-color: transparent;
                border: none;
            }
            
            #progressFrame {
                background-color: #16161e;
                border-radius: 12px;
                border: 1px solid #24283b;
            }
            
            #progressBar {
                background-color: #24283b;
                border: none;
                border-radius: 6px;
                text-align: center;
                height: 24px;
                color: #1a1b26;
                font-weight: bold;
            }
            
            #progressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #9ece6a, stop:1 #73daca);
                border-radius: 6px;
            }

            #statsLabel {
                color: #565f89;
                font-size: 12px;
                font-weight: 500;
            }
        """)
    
    def _create_menu_bar(self):
        """Создание меню приложения."""
        menubar = self.menuBar()
        
        # Меню Файл
        file_menu = menubar.addMenu("Файл")
        
        open_folder_action = QAction("Открыть папку с музыкой", self)
        open_folder_action.triggered.connect(self._open_music_folder)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню Инструменты отключено (поиск по ссылке через главное поле)
        # tools_menu = menubar.addMenu("Инструменты")
        
        # Меню Аккаунт
        account_menu = menubar.addMenu("Аккаунт")
        
        logout_action = QAction("Выйти", self)
        logout_action.triggered.connect(self.logout)
        account_menu.addAction(logout_action)
        
        # Меню Помощь
        help_menu = menubar.addMenu("Помощь")
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _init_client(self):
        """Инициализация клиента API."""
        encrypted_token = self._config.encrypted_token
        
        if encrypted_token:
            try:
                token = self._crypto.decrypt(encrypted_token)
                self._token = token
                logger.info("Токен успешно расшифрован")
            except Exception as e:
                logger.warning(f"Не удалось расшифровать токен: {e}")
                self._token = None
                self._config.clear_token()
        
        if self._token:
            self._client = YandexMusicClient(self._token, self._config)
            self.status_bar.showMessage("Авторизован")
            self.user_label.setText("Авторизован")
            self.user_label.setObjectName("successLabel")
        else:
            QTimer.singleShot(100, self._show_auth_dialog)
    
    def _show_auth_dialog(self):
        """Показ диалога авторизации."""
        dialog = AuthDialog(self)
        dialog.token_received.connect(self._on_token_received)
        
        if dialog.exec_() == AuthDialog.Accepted:
            pass
        else:
            self.status_bar.showMessage("Требуется авторизация", 5000)
    
    def _on_token_received(self, token: str):
        """Обработка полученного токена."""
        try:
            client = YandexMusicClient(token, self._config)
            
            if client.is_authenticated:
                self._token = token
                self._client = client
                
                encrypted = self._crypto.encrypt(token)
                self._config.encrypted_token = encrypted
                self._config.save()
                
                self.status_bar.showMessage("Успешная авторизация", 3000)
                self.user_label.setText("Авторизован")
                self.user_label.setObjectName("successLabel")
                logger.info("Пользователь успешно авторизован")
            else:
                raise Exception("Не удалось авторизоваться")
                
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            QMessageBox.critical(
                self, "Ошибка авторизации",
                f"Не удалось войти с указанным токеном.\n\n{str(e)}"
            )
            self._show_auth_dialog()
    
    def _on_search(self):
        """Обработка нажатия кнопки поиска (новая выдача с 1-й страницы)."""
        query = self.search_input.text().strip()

        if not query:
            self.status_bar.showMessage("Введите поисковый запрос", 3000)
            self.search_input.setFocus()
            return

        if not self._client or not self._client.is_authenticated:
            self.status_bar.showMessage("Требуется авторизация", 3000)
            self._show_auth_dialog()
            return

        # Проверяем, не является ли запрос ссылкой
        parsed = self._client.parse_link(query)
        if parsed:
            self._on_link_download(query, parsed.get('type', 'track'))
            return

        # Определяем тип поиска
        search_type_index = self.search_type_combo.currentIndex()
        search_type_map = ['track', 'artist', 'album']
        search_type = search_type_map[search_type_index] if search_type_index < len(search_type_map) else 'track'

        # Сбрасываем состояние пагинации и запускаем с 1-й страницы
        self._search_query = query
        self._search_type = search_type
        self._start_search(0)

    def _start_search(self, page: int):
        """Запуск поиска на указанной странице."""
        # Отменяем предыдущий поиск, если он активен
        if self._search_worker:
            try:
                running = self._search_worker.isRunning()
            except RuntimeError:
                running = False
            if running:
                self._search_worker.cancel()
                try:
                    self._search_worker.wait(2000)
                except RuntimeError:
                    pass
        self._search_worker = None

        # При первой странице — очищаем выдачу, иначе добавляем
        if page == 0:
            self._set_searching_state(True)
            self._clear_results()
            self._show_skeleton_loading()
        else:
            self._set_load_more_state(True)

        self._search_page = page
        # Для «Исполнитель» на стр.>0 нужен кэшированный artist_id
        worker_artist_id = None
        if self._search_type == 'artist' and page > 0:
            worker_artist_id = self._current_artist_id
        # На стр.0 сбрасываем кэш
        if page == 0 and self._search_type == 'artist':
            self._current_artist_id = None

        self._search_worker = SearchWorker(
            self._client, self._search_query,
            self._search_type, limit=20, page=page,
            artist_id=worker_artist_id,
        )
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.cancelled.connect(self._on_search_cancelled)
        self._search_worker.start()

    def _on_load_more(self):
        """Обработка нажатия «Показать ещё» — следующая страница."""
        if not self._search_query:
            return
        if self._search_worker:
            try:
                running = self._search_worker.isRunning()
            except RuntimeError:
                running = False
            if running:
                # Уже идёт загрузка — игнорируем
                return
        self._start_search(self._search_page + 1)

    def _on_search_finished(self, result: Dict[str, Any]):
        """Обработка результатов поиска (одна страница)."""
        self._set_searching_state(False)
        self._set_load_more_state(False)
        # deleteLater в SearchWorker удалил C++-объект, но Python-обёртка
        # ещё жива — сбрасываем, иначе следующий _on_search/_on_load_more
        # упадёт на isRunning() с RuntimeError.
        self._search_worker = None

        items = result.get('items', []) if isinstance(result, dict) else result
        has_more = result.get('has_more', False) if isinstance(result, dict) else False
        total = result.get('total', 0) if isinstance(result, dict) else 0
        # Кэшируем artist_id для режима «Исполнитель» (нужен на стр.>0)
        new_artist_id = (result.get('artist_id') if isinstance(result, dict)
                         else None)
        if self._search_type == 'artist' and new_artist_id:
            self._current_artist_id = new_artist_id
        self._search_has_more = has_more
        self._search_total = total

        logger.info(f"Поиск стр. {self._search_page}: получено {len(items)} "
                    f"элементов, has_more={has_more}, total={total}")

        # Если страница пустая и это page=0 — ничего не нашли
        if not items and self._search_page == 0:
            self._show_empty_state("Ничего не найдено по вашему запросу")
            self.status_bar.showMessage("Ничего не найдено", 3000)
            return

        # Если пришла пустая страница (page>0) — больше нет
        if not items and self._search_page > 0:
            self._remove_load_more_btn()
            return

        # Убираем старую кнопку «Показать ещё» перед добавлением
        # новых карточек (для page>0 — не трогаем уже отрисованные).
        if self._search_page == 0:
            self._remove_load_more_btn()

        search_type_index = self.search_type_combo.currentIndex()
        logger.info(f"Создание {len(items)} карточек")
        # Блокируем обновления контейнера результатов на время пакетной
        # вставки: 20 addWidget подряд = 20 relayout+repaint. С
        # setUpdatesEnabled(False) — один repaint в конце.
        # ВАЖНО: убрать блокировку в finally — иначе UI замёрзнет при
        # исключении в одном из TrackCardWidget.
        self.results_container.setUpdatesEnabled(False)
        try:
            for track_data in items:
                if search_type_index == 2 and track_data.get('type') == 'album':
                    card = self._create_album_card(track_data)
                else:
                    card = TrackCardWidget(track_data)
                card.download_clicked.connect(self._on_download_track)
                self.results_layout.addWidget(card)

            # Кнопка «Показать ещё» (если есть ещё)
            if has_more:
                self._add_load_more_btn()
        finally:
            self.results_container.setUpdatesEnabled(True)
            self.results_container.update()

        # Принудительно обновляем scroll area
        if self._search_page == 0:
            self.results_scroll.verticalScrollBar().setValue(0)
        self.results_scroll.update()
        self.results_container.updateGeometry()

        total_text = f" стр. {self._search_page + 1}" if self._search_page > 0 else ""
        self.status_bar.showMessage(
            f"Найдено: {len(items)} (эта страница{total_text})", 3000
        )
        logger.info(f"Поиск завершен, найдено {len(items)} на стр. {self._search_page}")

    def _load_more_label(self) -> str:
        """Текст кнопки «Показать ещё» с учётом типа поиска."""
        # 'album' → «…альбомов», всё остальное → «…треков»
        # (в т.ч. «Исполнитель», где отображаются именно треки артиста)
        if self._search_type == 'album':
            return "Показать ещё 20 альбомов"
        return "Показать ещё 20 треков"

    def _add_load_more_btn(self):
        """Добавление кнопки «Показать ещё» в конец списка."""
        if self._load_more_btn is not None:
            return
        btn = QPushButton(self._load_more_label())
        btn.setObjectName("loadMoreButton")
        btn.setMinimumHeight(44)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._on_load_more)
        self.results_layout.addWidget(btn)
        self._load_more_btn = btn

    def _remove_load_more_btn(self):
        """Удаление кнопки «Показать ещё» из layout."""
        if self._load_more_btn is None:
            return
        btn = self._load_more_btn
        self._load_more_btn = None
        try:
            self.results_layout.removeWidget(btn)
        except RuntimeError:
            pass
        try:
            btn.deleteLater()
        except RuntimeError:
            # C++ уже удалён
            pass

    def _set_load_more_state(self, loading: bool):
        """Блокировка/разблокировка кнопки «Показать ещё» при подгрузке."""
        if self._load_more_btn is None:
            return
        self._load_more_btn.setEnabled(not loading)
        self._load_more_btn.setText(
            "Загрузка..." if loading else self._load_more_label()
        )
    
    def _create_album_card(self, album_data: Dict[str, Any]) -> TrackCardWidget:
        """Создание карточки альбома."""
        # Для альбома создаём упрощённую карточку
        track_count = album_data.get('track_count', 0)
        album_data['title'] = f"{album_data.get('title', 'Альбом')} ({track_count} треков)"
        return TrackCardWidget(album_data)
    
    def _on_search_error(self, error: str):
        """Обработка ошибки поиска."""
        self._set_searching_state(False)
        self._show_empty_state(f"Ошибка поиска: {error}")
        self.status_bar.showMessage("Ошибка поиска", 3000)
        logger.error(f"Ошибка поиска: {error}")
        self._search_worker = None

    def _on_search_cancelled(self):
        """Поиск отменён пользователем."""
        self._set_searching_state(False)
        self._show_empty_state("Поиск отменён")
        self.status_bar.showMessage("Поиск отменён", 3000)
        self._search_worker = None
    
    def _prepare_track_for_download(self, track_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Подготовка данных трека перед загрузкой: получение прямой ссылки
        и (опционально) текста песни.
        """
        track_id = track_data.get('id')
        if not track_id:
            raise DownloadError("ID трека не указан")

        url = self._client.get_track_download_url(track_id)
        if not url:
            raise DownloadError("Не удалось получить URL для скачивания")
        track_data['download_url'] = url

        if self._config.get('embed_lyrics', False) and not track_data.get('lyrics'):
            # get_track_lyrics сам подгрузит Track и lyrics за один заход
            try:
                track_data['lyrics'] = self._client.get_track_lyrics(track_id)
            except Exception as e:
                logger.debug(f"Не удалось получить текст песни для {track_id}: {e}")
                track_data['lyrics'] = None

        return track_data

    def _on_download_track(self, track_data: Dict[str, Any]):
        """Обработка нажатия кнопки скачивания трека."""
        if not self._client or not self._client.is_authenticated:
            self.status_bar.showMessage("Требуется авторизация", 3000)
            return

        track_title = track_data.get('title', 'Трек')
        self._current_download_title = track_title

        # Обновляем индикаторы
        self.progress_label.setText(f"Загрузка: {track_title}")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Загрузка... 0%")
        self.progress_status.setText("")
        self.eta_label.hide()
        self.cancel_btn.show()
        self.progress_icon.setPixmap(get_pixmap('download', 20, '#9ece6a'))

        # Запоминаем время начала загрузки
        self._download_start_time = time.time()
        self._download_start_size = 0

        # Подготовка (URL + lyrics) — синхронно
        try:
            track_data = self._prepare_track_for_download(track_data)
        except DownloadError as e:
            self._on_download_error(str(e))
            return
        except Exception as e:
            self._on_download_error(f"Ошибка подготовки: {e}")
            return

        # Отменяем предыдущую загрузку кооперативно
        if self._download_worker:
            try:
                running = self._download_worker.isRunning()
            except RuntimeError:
                running = False
            if running:
                self._download_worker.cancel()
                try:
                    self._download_worker.wait(2000)
                except RuntimeError:
                    pass
        self._download_worker = None

        self._download_worker = DownloadWorker(
            self._downloader, self._client, track_data, self._config.music_path
        )
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.cancelled.connect(self._on_download_cancelled)
        self._download_worker.start()

    def _on_download_progress(self, title: str, downloaded: int, total: int):
        """Обработка прогресса загрузки."""
        if total > 0:
            percent = int(downloaded * 100 / total)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"Загрузка... {percent}%")
            elapsed = time.time() - self._download_start_time
            if downloaded > 0:
                speed = downloaded / elapsed if elapsed > 0 else 0
                eta = (total - downloaded) / speed if speed > 0 else 0
                self.eta_label.setText(
                    f"ETA: {int(eta // 60)}:{int(eta % 60):02d}"
                )
                self.eta_label.show()
            self.progress_status.setText(
                f"{downloaded // 1024} КБ / {total // 1024} КБ"
            )
    
    def _on_download_finished(self, file_path: str, success: bool):
        """Обработка завершения загрузки."""
        if not success:
            self._on_download_error("Загрузка не удалась")
            return

        elapsed = time.time() - self._download_start_time

        try:
            file_size = Path(file_path).stat().st_size
        except (OSError, FileNotFoundError):
            file_size = 0

        self._statistics.record_download(
            track_title=self._current_download_title,
            file_size=file_size,
            duration=elapsed,
            file_path=file_path
        )
        self._update_stats_display()

        self.progress_label.setText("Готово")
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("✓ Завершено")
        self.progress_status.setText(f"Скачано: {Path(file_path).name}")
        self.eta_label.hide()
        self.progress_icon.setPixmap(get_pixmap('check', 20, '#9ece6a'))
        self.cancel_btn.hide()

        self.status_bar.showMessage(f"Скачано: {Path(file_path).name}", 5000)
        logger.info(f"Загрузка завершена: {file_path}")

        if self._config.get('show_notifications', True):
            self._show_notification(
                "Загрузка завершена",
                f"Трек сохранён в:\n{file_path}"
            )
        self._download_worker = None

    def _on_download_error(self, error: str):
        """Обработка ошибки загрузки."""
        self.progress_label.setText("Ошибка")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("✗ Ошибка")
        self.progress_status.setText(str(error))
        self.progress_icon.setPixmap(get_pixmap('error', 20, '#f7768e'))
        self.cancel_btn.hide()
        self.status_bar.showMessage(f"Ошибка: {error}", 5000)
        logger.error(f"Ошибка загрузки: {error}")
        self._download_worker = None

    def _on_download_cancelled(self):
        """Обработка отмены загрузки."""
        self.progress_label.setText("Отменено")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("✗ Отменено")
        self.progress_status.setText("")
        self.progress_icon.setPixmap(get_pixmap('close', 20, '#f7768e'))
        self.cancel_btn.hide()
        self.status_bar.showMessage("Загрузка отменена", 3000)
        self._download_worker = None

    def _init_tray_icon(self):
        """Ленивая инициализация одиночного QSystemTrayIcon."""
        if self._tray_icon is not None:
            return self._tray_icon
        from PyQt5.QtWidgets import QSystemTrayIcon
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None
        self._tray_icon = QSystemTrayIcon(self.windowIcon(), self)
        self._tray_icon.setToolTip("Yandex Music Downloader")
        self._tray_icon.show()
        return self._tray_icon

    def _show_notification(self, title: str, message: str):
        """Показ уведомления о завершении."""
        from PyQt5.QtWidgets import QSystemTrayIcon

        tray = self._init_tray_icon()
        if tray is None:
            # Fallback если tray недоступен — НЕ спамим QMessageBox
            # (только в status bar)
            self.status_bar.showMessage(f"{title}: {message[:100]}", 5000)
            return

        # showMessage() — нативное уведомление ОС, иконка в трее
        # не мерцает (используем постоянный tray).
        tray.showMessage(title, message, QSystemTrayIcon.Information, 5000)
    
    def _set_searching_state(self, searching: bool):
        """Установка состояния поиска."""
        self.search_input.setEnabled(not searching)
        self.search_btn.setEnabled(not searching)
        self.settings_btn.setEnabled(not searching)
        self.search_type_combo.setEnabled(not searching)

        if searching:
            self._show_loading_state("Поиск...")
        else:
            self._hide_loading_state()

    def _on_cancel(self):
        """Отмена текущей операции."""
        # Не мешаем закрытию модальных диалогов (настройки, авторизация)
        if self.activeModalWidget() is not None:
            return

        # Отменяем поиск, если он выполняется
        if self._search_worker:
            try:
                running = self._search_worker.isRunning()
            except RuntimeError:
                running = False
            if running:
                self._search_worker.cancel()
                self._search_worker = None
                self._set_searching_state(False)
                self._show_empty_state("Поиск отменён")
                self.status_bar.showMessage("Поиск отменён", 3000)
            return

        # Отменяем загрузку
        if self._download_worker:
            try:
                running = self._download_worker.isRunning()
            except RuntimeError:
                running = False
            if running:
                self._download_worker.cancel()
                try:
                    self._download_worker.wait(2000)
                except RuntimeError:
                    pass
            self._download_worker = None

            self.progress_label.setText("Отменено")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("✗ Отменено")
            self.progress_status.setText("")
            self.progress_icon.setPixmap(get_pixmap('close', 20, '#f7768e'))
            self.cancel_btn.hide()
            self.status_bar.showMessage("Загрузка отменена", 3000)
    
    def _show_empty_state(self, message: str):
        """Показ пустого состояния."""
        self._clear_results()
        empty_widget = EmptyStateWidget(message=message)
        self.results_layout.addWidget(empty_widget)
        self.results_layout.addStretch()
    
    def _show_loading_state(self, message: str):
        """Показ состояния загрузки."""
        self._clear_results()
        loading_widget = LoadingWidget(message=message)
        loading_widget.show()
        self.results_layout.addWidget(loading_widget)
    
    def _hide_loading_state(self):
        """Скрытие состояния загрузки."""
        # Удаляем все LoadingWidget и SkeletonLoadingWidget из результатов
        for i in reversed(range(self.results_layout.count())):
            item = self.results_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget.__class__.__name__ in ('LoadingWidget', 'SkeletonLoadingWidget'):
                    try:
                        widget.deleteLater()
                    except RuntimeError:
                        pass
        # Сбрасываем ссылку на скелетон, чтобы не держать мёртвый
        # Python-wrapper при повторном вызове _clear_results
        if hasattr(self, 'skeleton_widget') and self.skeleton_widget is not None:
            self.skeleton_widget = None
    
    def _clear_results(self):
        """Очистка контейнера результатов."""
        # Удаляем skeleton widget если есть
        if hasattr(self, 'skeleton_widget') and self.skeleton_widget:
            w = self.skeleton_widget
            self.skeleton_widget = None
            try:
                w.deleteLater()
            except RuntimeError:
                # C++ уже удалён — игнорируем (но Python-ссылку уже сбросили)
                pass

        # Сбрасываем ссылку на кнопку «Показать ещё»
        # (deleteLater сработает при удалении из layout ниже)
        self._load_more_btn = None

        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                try:
                    w.deleteLater()
                except RuntimeError:
                    # C++ уже удалён
                    pass
    
    def _open_settings(self):
        """Открытие окна настроек."""
        dialog = SettingsDialog(self._config, self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec_()
    
    def _on_settings_saved(self):
        """Обработка сохранения настроек."""
        self.status_bar.showMessage("Настройки сохранены", 3000)
        # Пересоздаём загрузчик с новыми настройками
        self._downloader = AudioDownloader(self._config)
    
    def _open_music_folder(self):
        """Открытие папки с музыкой."""
        music_path = self._config.music_path
        
        if music_path.exists():
            import os
            os.startfile(str(music_path))
        else:
            QMessageBox.warning(self, "Папка не найдена",
                              f"Папка не существует:\n{music_path}")
    
    def _on_link_download(self, link: str, link_type: str):
        """Обработка ссылки для скачивания."""
        if not self._client or not self._client.is_authenticated:
            self.status_bar.showMessage("Требуется авторизация", 3000)
            return

        # Парсим ссылку
        parsed = self._client.parse_link(link)

        if not parsed:
            self.status_bar.showMessage("Не удалось распознать ссылку", 3000)
            return

        link_type = parsed.get('type', link_type)
        self.progress_label.setText(f"Загрузка: {link_type}")
        self.progress_bar.setFormat("Обработка...")
        self.cancel_btn.show()
        self.progress_icon.setPixmap(get_pixmap('download', 20, '#9ece6a'))

        # В зависимости от типа
        if link_type == 'track':
            self._download_track_by_id(parsed['id'])
        elif link_type == 'album':
            self._download_album_by_id(parsed['id'])
        elif link_type == 'playlist':
            self._download_playlist_by_id(parsed.get('user_id'), parsed['id'])
        else:
            self.status_bar.showMessage("Неподдерживаемый тип ссылки", 3000)
            self.cancel_btn.hide()

    def _download_track_by_id(self, track_id: str):
        """Загрузка трека по ID."""
        track_data = self._client.get_track(track_id)
        if track_data:
            url = self._client.get_track_download_url(track_data['id'])
            if url:
                track_data['download_url'] = url
                self._start_download(track_data)
                self.status_bar.showMessage(f"Загрузка трека...", 3000)
            else:
                self.status_bar.showMessage("Не удалось получить URL", 3000)
                self.cancel_btn.hide()
        else:
            self.status_bar.showMessage("Трек не найден", 3000)
            self.cancel_btn.hide()

    def _download_album_by_id(self, album_id: str):
        """Загрузка альбома."""
        album_data = self._client.get_album(album_id)
        if album_data:
            tracks = album_data.get('tracks', [])
            if tracks:
                title = album_data.get('title', 'Альбом')
                self.status_bar.showMessage(
                    f"Альбом «{title}»: {len(tracks)} треков", 5000
                )
                album_meta = {
                    'title': title,
                    'year': album_data.get('year'),
                    'cover_url': album_data.get('cover_url'),
                }
                self._download_album_tracks(
                    tracks, 0, source_title=title, album_meta=album_meta
                )
            else:
                self.status_bar.showMessage("Альбом пуст", 3000)
                self.cancel_btn.hide()
        else:
            self.status_bar.showMessage("Альбом не найден", 3000)
            self.cancel_btn.hide()

    def _download_album_tracks(self, tracks: list, index: int = 0,
                               source_title: str = "Альбом",
                               error_count: int = 0,
                               album_meta: Optional[Dict[str, Any]] = None):
        """Последовательная загрузка треков альбома/плейлиста."""
        if index >= len(tracks):
            self.progress_label.setText(f"{source_title}: готово")
            self.progress_bar.setFormat("✓ Готово")
            if error_count:
                self.status_bar.showMessage(
                    f"{source_title}: загружено {index - error_count} из {index}, "
                    f"ошибок: {error_count}", 8000
                )
            else:
                self.status_bar.showMessage(
                    f"{source_title}: загружено {index} из {index}", 5000
                )
            self.cancel_btn.hide()
            return

        track = tracks[index]
        # Берём минимальные данные из списка альбома/плейлиста и догружаем
        track_artists = track.get('artists', [])
        track_data = {
            'id': track['id'],
            'title': track.get('title', f'Трек {index + 1}'),
            'artists': track_artists,
            'artist': ', '.join(track_artists)
                       or track.get('artist', 'Unknown Artist'),
            'duration_ms': track.get('duration_ms', 0),
        }
        # Подмешиваем метаданные альбома для ID3-тегов (обложка, год, название)
        if album_meta:
            cover_url = album_meta.get('cover_url')
            if cover_url:
                track_data['cover_url'] = cover_url
            album_info = {}
            if album_meta.get('title'):
                album_info['title'] = album_meta['title']
            if album_meta.get('year'):
                album_info['year'] = album_meta['year']
            if album_info:
                track_data['album'] = album_info
        try:
            track_data = self._prepare_track_for_download(track_data)
        except DownloadError as e:
            logger.error(f"«{track_data.get('title')}»: {e}")
            self.status_bar.showMessage(
                f"Ошибка: {track_data.get('title')} — пропущен", 3000
            )
            self._download_album_tracks(
                tracks, index + 1, source_title, error_count + 1
            )
            return

        self.progress_label.setText(
            f"Загрузка: {track_data.get('title')} ({index+1}/{len(tracks)})"
        )
        self.progress_bar.setFormat(f"{index+1}/{len(tracks)}")

        track_start_time = time.time()

        self._download_worker = DownloadWorker(
            self._downloader, self._client, track_data, self._config.music_path
        )
        self._download_worker.finished.connect(
            lambda path, success, idx=index, st=track_start_time:
                self._on_album_track_downloaded(
                    path, success, tracks, idx, source_title, error_count, st
                )
        )
        self._download_worker.error.connect(
            lambda error, idx=index: self._on_album_track_error(
                error, tracks, idx, source_title, error_count
            )
        )
        self._download_worker.cancelled.connect(
            lambda: self._on_album_track_cancelled(tracks, index, source_title)
        )
        self._download_worker.start()

    def _on_album_track_downloaded(self, path, success, tracks: list, index: int,
                                   source_title: str, error_count: int,
                                   start_time: float = 0.0):
        """Обработка загрузки трека альбома/плейлиста."""
        if success:
            try:
                file_size = Path(path).stat().st_size
            except (OSError, FileNotFoundError):
                file_size = 0
            elapsed = time.time() - start_time if start_time else 0.0
            track_title = tracks[index].get('title', f'#{index+1}') \
                if index < len(tracks) else f'#{index+1}'
            self._statistics.record_download(
                track_title=track_title,
                file_size=file_size,
                duration=elapsed,
                file_path=path
            )
            self._update_stats_display()
            self._download_worker = None
            self._download_album_tracks(
                tracks, index + 1, source_title, error_count
            )
        else:
            title = tracks[index].get('title', f'#{index+1}') \
                if index < len(tracks) else f'#{index+1}'
            logger.error(f"Ошибка загрузки «{title}»: {path}")
            self.status_bar.showMessage(
                f"Ошибка: {title} — пропущен", 3000
            )
            self._download_worker = None
            self._download_album_tracks(
                tracks, index + 1, source_title, error_count + 1
            )

    def _on_album_track_error(self, error, tracks: list, index: int,
                              source_title: str, error_count: int):
        """Обработка ошибки загрузки трека альбома/плейлиста."""
        title = tracks[index].get('title', f'#{index+1}') \
            if index < len(tracks) else f'#{index+1}'
        logger.error(f"Ошибка загрузки «{title}»: {error}")
        self.status_bar.showMessage(
            f"Ошибка: {title} — пропущен", 3000
        )
        self._download_worker = None
        self._download_album_tracks(
            tracks, index + 1, source_title, error_count + 1
        )

    def _on_album_track_cancelled(self, tracks, index, source_title):
        """Отмена загрузки альбома/плейлиста."""
        self.progress_label.setText(f"{source_title}: отменено")
        self.progress_bar.setFormat("✗ Отменено")
        self.cancel_btn.hide()
        self.status_bar.showMessage(f"{source_title}: отменено", 3000)
        self._download_worker = None
    
    def _download_playlist_by_id(self, user_id: Optional[str], playlist_id: str):
        """Загрузка плейлиста."""
        if not self._client or not self._client.is_authenticated:
            self.status_bar.showMessage("Требуется авторизация", 3000)
            self.cancel_btn.hide()
            return

        playlist_data = self._client.get_playlist(user_id, playlist_id)
        if not playlist_data:
            self.status_bar.showMessage("Плейлист не найден", 3000)
            self.cancel_btn.hide()
            return

        tracks = playlist_data.get('tracks', [])
        if not tracks:
            self.status_bar.showMessage("Плейлист пуст", 3000)
            self.cancel_btn.hide()
            return

        title = playlist_data.get('title', 'Плейлист')
        self.status_bar.showMessage(
            f"Плейлист «{title}»: {len(tracks)} треков", 5000
        )
        self._download_album_tracks(tracks, 0, source_title=title)
    
    def _start_download(self, track_data):
        """Начать загрузку трека."""
        self.progress_label.setText(f"Загрузка: {track_data.get('title', 'Трек')}")
        self.progress_bar.setFormat("Загрузка...")
        self.cancel_btn.show()
        self.progress_icon.setPixmap(get_pixmap('download', 20, '#9ece6a'))

        try:
            track_data = self._prepare_track_for_download(track_data)
        except DownloadError as e:
            self._on_download_error(str(e))
            return

        if self._download_worker:
            try:
                running = self._download_worker.isRunning()
            except RuntimeError:
                running = False
            if running:
                self._download_worker.cancel()
                try:
                    self._download_worker.wait(2000)
                except RuntimeError:
                    pass
        self._download_worker = None

        self._download_worker = DownloadWorker(
            self._downloader, self._client, track_data, self._config.music_path
        )
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.cancelled.connect(self._on_download_cancelled)
        self._download_worker.start()

    def _on_download_progress(self, title: str, downloaded: int, total: int):
        """Обработка прогресса загрузки."""
        if total > 0:
            percent = int(downloaded * 100 / total)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"Загрузка... {percent}%")
            elapsed = time.time() - self._download_start_time
            if downloaded > 0:
                speed = downloaded / elapsed if elapsed > 0 else 0
                eta = (total - downloaded) / speed if speed > 0 else 0
                self.eta_label.setText(
                    f"ETA: {int(eta // 60)}:{int(eta % 60):02d}"
                )
                self.eta_label.show()
            self.progress_status.setText(
                f"{downloaded // 1024} КБ / {total // 1024} КБ"
            )
    
    def _show_about(self):
        """Показ окна о программе."""
        QMessageBox.about(
            self, "О программе",
            "<h2 style='color: #7aa2f7;'>Yandex Music Downloader</h2>"
            "<p style='font-size: 14px;'>Версия: 1.0.0</p>"
            "<p style='font-size: 13px; color: #a9b1d6;'>"
            "Приложение для скачивания музыки из Яндекс.Музыки.</p>"
            "<p style='font-size: 12px; color: #565f89; margin-top: 16px;'>"
            "Использование должно соответствовать Условиям использования "
            "Яндекс.Музыки и законам об авторском праве."
            "</p>"
        )
    
    def logout(self):
        """Выход из аккаунта."""
        reply = QMessageBox.question(
            self, "Выход из аккаунта",
            "Вы уверены, что хотите выйти?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Отменяем активные операции
        for worker in (self._search_worker, self._download_worker):
            if worker:
                try:
                    running = worker.isRunning()
                except RuntimeError:
                    running = False
                if running:
                    worker.cancel()

        self._config.clear_token()
        self._config.save()
        self._client = None
        self._token = None

        # Сбрасываем UI в начальное состояние
        self._clear_results()
        self._show_empty_state("Введите поисковый запрос для начала")
        self.progress_label.setText("Готов к работе")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ожидание...")
        self.progress_status.setText("")
        self.eta_label.hide()
        self.cancel_btn.hide()
        self.search_input.clear()
        self.search_input.setEnabled(True)
        self.search_btn.setEnabled(True)
        self.settings_btn.setEnabled(True)
        self.search_type_combo.setEnabled(True)

        self.user_label.setText("Не авторизован")
        self.user_label.setObjectName("statusLabel")
        # Переустановка stylesheet, чтобы новый objectName применился
        self._setup_styles()
        self.user_label.style().unpolish(self.user_label)
        self.user_label.style().polish(self.user_label)
        self.user_label.update()

        self.status_bar.showMessage("Выход из аккаунта...", 3000)
        self._show_auth_dialog()
    
    def _show_skeleton_loading(self):
        """Показ skeleton loading вместо результатов."""
        self._clear_results()

        # Создаём skeleton виджет
        self.skeleton_widget = SkeletonLoadingWidget(count=5)
        try:
            self.results_layout.addWidget(self.skeleton_widget)
        except RuntimeError:
            # Layout мог быть уже удалён
            self.skeleton_widget = None

    def _update_stats_display(self):
        """Обновление отображения статистики."""
        self.stats_downloads_label.setText(f"Всего: {self._statistics.get_total_downloads()}")
        self.stats_size_label.setText(f"{self._statistics.format_size(self._statistics.get_total_size())}")
        self.stats_today_label.setText(f"Сегодня: {self._statistics.get_today_downloads()}")

    def _setup_shortcuts(self):
        """Настройка горячих клавиш."""
        # Ctrl+F - фокус на поле поиска
        search_focus = QAction(self)
        search_focus.setShortcut(QKeySequence("Ctrl+F"))
        search_focus.triggered.connect(self._safe_focus_search)
        self.addAction(search_focus)

        # Ctrl+S - выполнить поиск
        search_action = QAction(self)
        search_action.setShortcut(QKeySequence("Ctrl+S"))
        search_action.triggered.connect(self._safe_search)
        self.addAction(search_action)

        # Ctrl+L - очистить поле поиска
        clear_action = QAction(self)
        clear_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_action.triggered.connect(self._safe_clear_search)
        self.addAction(clear_action)

        # Escape - отмена текущей операции (только вне модальных диалогов)
        cancel_action = QAction(self)
        cancel_action.setShortcut(QKeySequence("Escape"))
        cancel_action.triggered.connect(self._on_cancel)
        self.addAction(cancel_action)

        # F5 - обновить (повторный поиск)
        refresh_action = QAction(self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self._safe_search)
        self.addAction(refresh_action)

    def _safe_focus_search(self):
        if self.activeModalWidget() is None:
            self.search_input.setFocus()

    def _safe_search(self):
        if self.activeModalWidget() is None:
            self._on_search()

    def _safe_clear_search(self):
        if self.activeModalWidget() is None:
            self.search_input.clear()

    def closeEvent(self, event):
        """Обработка закрытия окна."""
        logger.info("Приложение закрывается")

        for worker in (self._search_worker, self._download_worker):
            if worker:
                try:
                    running = worker.isRunning()
                except RuntimeError:
                    running = False
                if running:
                    worker.cancel()
                    try:
                        if not worker.wait(3000):
                            logger.warning(
                                f"Поток {type(worker).__name__} не завершился за 3с"
                            )
                    except RuntimeError:
                        pass

        self._search_worker = None
        self._download_worker = None

        if self._tray_icon is not None:
            self._tray_icon.hide()
            self._tray_icon = None

        self._downloader.close()

        event.accept()
