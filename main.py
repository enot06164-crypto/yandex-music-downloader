# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
Главный файл запуска приложения.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

Версия: 0.1.1

================================================================================
ДИСКЛЕЙМЕР
================================================================================

Данное приложение предоставляется "как есть" только для образовательных целей.

Использование этого приложения должно соответствовать:
1. Условиям использования сервиса Яндекс.Музыка (https://yandex.ru/legal/music_termsofuse/)
2. Действующему законодательству об авторском праве
3. Законам вашей страны

Разработчик не несет ответственности за любое неправильное использование
данного программного обеспечения.

Все права на контент Яндекс.Музыки принадлежат их соответствующим владельцам.
================================================================================
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtGui import QFont, QIcon, QFontDatabase

# Импортируем модули приложения
from config import Config, get_config, reset_config
from crypto import TokenCrypto
from ui.main_window import MainWindow
from ui.widgets import get_dark_stylesheet


# =============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================================================================

def setup_logging(log_dir: Path = None, level: int = logging.INFO) -> logging.Logger:
    """
    Настройка системы логирования.
    
    Args:
        log_dir (Path): Директория для логов.
        level (int): Уровень логирования.
        
    Returns:
        logging.Logger: Настроенный логгер.
    """
    if log_dir is None:
        log_dir = Path(__file__).parent / 'logs'
    
    # Создаем директорию для логов
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / 'app.log'
    
    # Настраиваем форматтер
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Rotating File Handler (лог rotates при достижении 5MB)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Логгер приложения
    logger = logging.getLogger('yandex_downloader')
    logger.info("Логирование инициализировано")
    logger.info(f"Лог файл: {log_file}")
    
    return logger


# =============================================================================
# НАСТРОЙКА ПРИЛОЖЕНИЯ
# =============================================================================

def setup_application() -> QApplication:
    """
    Настройка QApplication.
    
    Returns:
        QApplication: Настроенное приложение.
    """
    # Включаем поддержку HiDPI
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # Создаем приложение
    app = QApplication(sys.argv)
    
    # Устанавливаем организацию и имя приложения
    app.setOrganizationName('YandexMusicDownloader')
    app.setApplicationName('Yandex Music Downloader')
    app.setApplicationVersion('0.1.1')
    
    # Устанавливаем темную тему
    app.setStyleSheet(get_dark_stylesheet())
    
    # Устанавливаем шрифт по умолчанию
    font = QFont('Segoe UI', 10)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)
    
    return app


# =============================================================================
# ПРОВЕРКА ЗАВИСИМОСТЕЙ
# =============================================================================

def check_dependencies() -> bool:
    """
    Проверка наличия всех необходимых зависимостей.
    
    Returns:
        bool: True если все зависимости установлены.
    """
    missing = []
    
    # Проверяем основные модули
    try:
        import yandex_music
    except ImportError:
        missing.append('yandex-music')
    
    try:
        import PyQt5
    except ImportError:
        missing.append('PyQt5')
    
    try:
        import cryptography
    except ImportError:
        missing.append('cryptography')
    
    try:
        import mutagen
    except ImportError:
        missing.append('mutagen')
    
    try:
        import requests
    except ImportError:
        missing.append('requests')
    
    try:
        import PIL
    except ImportError:
        missing.append('Pillow')
    
    if missing:
        print("=" * 60)
        print("ОШИБКА: Отсутствуют необходимые зависимости")
        print("=" * 60)
        print(f"Установите отсутствующие пакеты командой:")
        print(f"  pip install {' '.join(missing)}")
        print("=" * 60)
        return False
    
    return True


# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =============================================================================

def main() -> int:
    """
    Главная функция запуска приложения.
    
    Returns:
        int: Код выхода приложения.
    """
    # Проверяем зависимости
    if not check_dependencies():
        return 1
    
    # Настраиваем логирование
    logger = setup_logging()
    logger.info("Запуск приложения Yandex Music Downloader")
    logger.info(f"Python версия: {sys.version}")
    logger.info(f"Платформа: {sys.platform}")
    
    try:
        # Настраиваем QApplication
        app = setup_application()
        
        # Устанавливаем иконку приложения
        icon_path = Path(__file__).parent / 'resources' / 'app.ico'
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        # Загружаем конфигурацию
        config = get_config()
        logger.info(f"Конфигурация загружена из: {config._config_file}")

        # Проверяем наличие токена
        token = None
        encrypted_token = config.encrypted_token
        
        if encrypted_token:
            try:
                from crypto import TokenCrypto
                crypto = TokenCrypto()
                token = crypto.decrypt(encrypted_token)
                logger.info("Токен успешно расшифрован")
                
                # Проверяем работает ли токен
                try:
                    from api_client import YandexMusicClient
                    test_client = YandexMusicClient(token, config)
                    if test_client.is_authenticated:
                        logger.info("✓ Сохранённый токен работает")
                    else:
                        logger.warning("✗ Сохранённый токен не работает, запрашиваем новый")
                        token = None
                        config.clear_token()
                except Exception as e:
                    logger.warning(f"✗ Сохранённый токен не работает: {e}")
                    token = None
                    config.clear_token()
            except Exception as e:
                logger.warning(f"Не удалось расшифровать токен: {e}")
                config.clear_token()
        
        # Если токена нет или он не работает, показываем окно авторизации
        if not token:
            # Используем простой метод авторизации (ручной ввод токена)
            logger.info("Используется авторизация через ручной ввод токена...")
            from ui.auth_dialog import AuthDialog

            token = _prompt_for_token(config, logger)
            if not token:
                logger.warning("✗ Пользователь отменил авторизацию")
                return 1

        # Создаем главное окно
        window = MainWindow(config=config, token=token)
        window.show()
        
        logger.info("Главное окно отображено")
        
        # Запускаем цикл событий
        exit_code = app.exec_()
        
        logger.info(f"Приложение завершено с кодом: {exit_code}")
        
        return exit_code
        
    except Exception as e:
        logger.exception(f"Критическая ошибка при запуске: {e}")
        
        # Показываем ошибку пользователю
        from PyQt5.QtWidgets import QMessageBox
        
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle("Ошибка запуска")
        error_box.setText("Произошла критическая ошибка при запуске приложения")
        error_box.setDetailedText(str(e))
        error_box.exec_()
        
        return 1


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def _prompt_for_token(config: Config, logger: logging.Logger) -> Optional[str]:
    """
    Цикл запроса токена у пользователя.
    Позволяет повторять попытку, пока пользователь не введёт валидный токен
    или не закроет приложение. Возвращает None, если пользователь отказался.
    """
    from ui.auth_dialog import AuthDialog

    while True:
        auth_dialog = AuthDialog()
        auth_dialog.show()
        auth_dialog.raise_()
        auth_dialog.activateWindow()

        if auth_dialog.exec_() != AuthDialog.Accepted:
            return None

        token = auth_dialog.get_token()
        if not token:
            continue

        # Сохраняем токен
        try:
            from crypto import TokenCrypto
            crypto = TokenCrypto()
            encrypted = crypto.encrypt(token)
            config.encrypted_token = encrypted
            config.save()
            logger.info("✓ Токен сохранён")
            return token
        except Exception as e:
            logger.error(f"✗ Ошибка сохранения токена: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                None, "Ошибка",
                f"Не удалось сохранить токен: {e}"
            )
            # продолжаем цикл — пусть попробует снова


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

if __name__ == '__main__':
    sys.exit(main())
