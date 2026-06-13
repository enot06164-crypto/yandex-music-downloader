# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
Модуль конфигурации приложения.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

import json
import logging
import os
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# Пути по умолчанию
DEFAULT_MUSIC_PATH = Path.home() / 'Music'
CONFIG_DIR = Path(__file__).parent / '.config'
CONFIG_FILE = CONFIG_DIR / 'config.json'

# Настройки по умолчанию
DEFAULT_CONFIG = {
    # Путь для сохранения музыки
    'music_path': str(DEFAULT_MUSIC_PATH),
    
    # Качество аудио: 'best', 'high', 'medium', 'low'
    'audio_quality': 'best',
    
    # Задержка между запросами к API (секунды)
    'api_delay': 0.5,
    
    # Таймаут запросов (секунды)
    'request_timeout': 30,
    
    # Тема оформления: 'dark', 'light'
    'theme': 'dark',
    
    # Язык интерфейса
    'language': 'ru',
    
    # Автоматическая проверка обновлений
    'check_updates': True,
    
    # Показывать уведомления о завершении
    'show_notifications': True,
    
    # Встраивать обложку в файл
    'embed_cover': True,
    
    # Встраивать текст песни (если доступен)
    'embed_lyrics': False,
    
    # Формат названия папки альбома: '{album}' или '{year} - {album}'
    'album_format': '{album}',
    
    # Зашифрованный токен (хранится отдельно)
    'encrypted_token': None,
}


class Config:
    """
    Класс для управления конфигурацией приложения.
    Отвечает за загрузку, сохранение и доступ к настройкам.
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Инициализация конфигурации.
        
        Args:
            config_file (Optional[Path]): Путь к файлу конфигурации.
        """
        self._config_file = config_file or CONFIG_FILE
        self._config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self._load()
    
    def _ensure_config_dir(self) -> None:
        """
        Создание директории конфигурации, если она не существует.
        """
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load(self) -> None:
        """
        Загрузка конфигурации из файла.
        Если файл не существует или поврежден, используются настройки по умолчанию.
        """
        if not self._config_file.exists():
            return
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            # Объединяем с настройками по умолчанию
            for key, value in loaded_config.items():
                if key in self._config:
                    self._config[key] = value
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Не удалось загрузить конфигурацию: {e}")
    
    def save(self) -> None:
        """
        Сохранение конфигурации в файл.
        """
        self._ensure_config_dir()
        
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Не удалось сохранить конфигурацию: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получение значения настройки.
        
        Args:
            key (str): Ключ настройки.
            default (Any): Значение по умолчанию, если ключ не найден.
            
        Returns:
            Any: Значение настройки.
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Установка значения настройки.

        Args:
            key (str): Ключ настройки.
            value (Any): Значение настройки.
        """
        if key in self._config:
            self._config[key] = value
        else:
            # Молча игнорировать опечатку в имени ключа — путь к
            # «настройки не сохраняются» без следов. Логируем.
            logger.warning(
                f"Config.set: неизвестный ключ '{key}' (нет в DEFAULT_CONFIG)"
            )
    
    def reset(self, key: Optional[str] = None) -> None:
        """
        Сброс настроек к значениям по умолчанию.
        
        Args:
            key (Optional[str]): Ключ настройки для сброса. 
                                Если None, сбрасываются все настройки.
        """
        if key is None:
            self._config = DEFAULT_CONFIG.copy()
        elif key in DEFAULT_CONFIG:
            self._config[key] = DEFAULT_CONFIG[key]
    
    @property
    def music_path(self) -> Path:
        """
        Получение пути для сохранения музыки.
        
        Returns:
            Path: Путь к директории музыки.
        """
        return Path(self._config.get('music_path', str(DEFAULT_MUSIC_PATH)))
    
    @music_path.setter
    def music_path(self, path: Path) -> None:
        """
        Установка пути для сохранения музыки.
        
        Args:
            path (Path): Путь к директории музыки.
        """
        self._config['music_path'] = str(path)
    
    @property
    def audio_quality(self) -> str:
        """
        Получение качества аудио.
        
        Returns:
            str: Качество аудио.
        """
        return self._config.get('audio_quality', 'best')
    
    @audio_quality.setter
    def audio_quality(self, quality: str) -> None:
        """
        Установка качества аудио.
        
        Args:
            quality (str): Качество ('best', 'high', 'medium', 'low').
        """
        if quality in ('best', 'high', 'medium', 'low'):
            self._config['audio_quality'] = quality
    
    @property
    def encrypted_token(self) -> Optional[str]:
        """
        Получение зашифрованного токена.
        
        Returns:
            Optional[str]: Зашифрованный токен или None.
        """
        return self._config.get('encrypted_token')
    
    @encrypted_token.setter
    def encrypted_token(self, token: str) -> None:
        """
        Установка зашифрованного токена.
        
        Args:
            token (str): Зашифрованный токен.
        """
        self._config['encrypted_token'] = token
    
    @property
    def theme(self) -> str:
        """
        Получение темы оформления.
        
        Returns:
            str: Тема ('dark', 'light').
        """
        return self._config.get('theme', 'dark')
    
    @theme.setter
    def theme(self, theme: str) -> None:
        """
        Установка темы оформления.
        
        Args:
            theme (str): Тема ('dark', 'light').
        """
        if theme in ('dark', 'light'):
            self._config['theme'] = theme
    
    @property
    def api_delay(self) -> float:
        """
        Получение задержки между запросами к API.
        
        Returns:
            float: Задержка в секундах.
        """
        return self._config.get('api_delay', 0.5)
    
    @api_delay.setter
    def api_delay(self, delay: float) -> None:
        """
        Установка задержки между запросами к API.

        Args:
            delay (float): Задержка в секундах.
        """
        if delay >= 0:
            self._config['api_delay'] = delay

    @property
    def request_timeout(self) -> int:
        """
        Получение таймаута HTTP-запросов (секунды).

        Returns:
            int: Таймаут в секундах.
        """
        try:
            return int(self._config.get('request_timeout', 30))
        except (TypeError, ValueError):
            return 30

    @request_timeout.setter
    def request_timeout(self, value: int) -> None:
        """
        Установка таймаута HTTP-запросов.

        Args:
            value (int): Таймаут в секундах.
        """
        if value > 0:
            self._config['request_timeout'] = int(value)
    
    def has_token(self) -> bool:
        """
        Проверка наличия сохраненного токена.
        
        Returns:
            bool: True если токен сохранен.
        """
        return self.encrypted_token is not None
    
    def clear_token(self) -> None:
        """
        Очистка сохраненного токена.
        """
        self._config['encrypted_token'] = None


# Глобальный экземпляр конфигурации
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Получение глобального экземпляра конфигурации.
    
    Returns:
        Config: Экземпляр конфигурации.
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """
    Сброс глобального экземпляра конфигурации.
    Используется при тестировании.
    """
    global _config
    _config = None
