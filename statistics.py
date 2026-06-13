# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
Модуль статистики загрузок.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DownloadStatistics:
    """Класс для отслеживания статистики загрузок."""

    def __init__(self, stats_file: Optional[Path] = None):
        """
        Инициализация статистики.
        
        Args:
            stats_file: Путь к файлу статистики
        """
        self._stats_file = stats_file or Path(__file__).parent / '.config' / 'statistics.json'
        self._stats = self._load_stats()

    def _load_stats(self) -> Dict:
        """Загрузка статистики из файла с защитой от потери данных."""
        defaults = self._default_stats()
        if not self._stats_file.exists():
            return defaults

        for candidate in (self._stats_file, self._stats_file.with_suffix('.bak')):
            if not candidate.exists():
                continue
            try:
                with open(candidate, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise ValueError("корневой объект не dict")
                # Мердж с дефолтами, чтобы новые ключи не вызывали KeyError
                merged = defaults.copy()
                merged.update(loaded)
                return merged
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    f"Не удалось прочитать {candidate.name}: {e}. "
                    f"Пробуем следующий источник."
                )
                continue
            except OSError as e:
                logger.warning(f"Ошибка доступа к {candidate.name}: {e}")
                continue

        # Ни основной, ни бэкап не прочитали — пробуем спасти основной
        # файл переименованием в .corrupt, чтобы пользователь мог
        # восстановить данные вручную.
        try:
            corrupt_path = self._stats_file.with_suffix('.corrupt')
            if self._stats_file.exists() and not corrupt_path.exists():
                self._stats_file.rename(corrupt_path)
                logger.error(
                    f"Статистика повреждена, файл сохранён как {corrupt_path.name}"
                )
        except OSError:
            pass

        return defaults

    def _save_stats(self):
        """Сохранение статистики в файл (атомарно через временный файл)."""
        try:
            self._stats_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._stats_file.with_suffix('.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self._stats, f, indent=4, ensure_ascii=False)
            # Перед заменой сохраняем .bak
            if self._stats_file.exists():
                try:
                    self._stats_file.replace(self._stats_file.with_suffix('.bak'))
                except OSError:
                    pass
            tmp_path.replace(self._stats_file)
        except Exception as e:
            logger.error(f"Не удалось сохранить статистику: {e}")

    def _default_stats(self) -> Dict:
        """Статистика по умолчанию."""
        return {
            'total_downloads': 0,
            'total_size_bytes': 0,
            'total_time_seconds': 0,
            'last_download': None,
            'downloads_by_date': {},
            'recent_downloads': []
        }

    def record_download(self, track_title: str, file_size: int, duration: float, file_path: str):
        """
        Запись информации о загрузке.
        
        Args:
            track_title: Название трека
            file_size: Размер файла в байтах
            duration: Время загрузки в секундах
            file_path: Путь к файлу
        """
        # Обновляем общую статистику
        self._stats['total_downloads'] += 1
        self._stats['total_size_bytes'] += file_size
        self._stats['total_time_seconds'] += duration
        self._stats['last_download'] = datetime.now().isoformat()

        # Обновляем статистику по датам
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self._stats['downloads_by_date']:
            self._stats['downloads_by_date'][today] = {
                'count': 0,
                'size_bytes': 0
            }
        self._stats['downloads_by_date'][today]['count'] += 1
        self._stats['downloads_by_date'][today]['size_bytes'] += file_size

        # Добавляем в недавние загрузки (храним последние 20)
        download_info = {
            'title': track_title,
            'size_bytes': file_size,
            'duration': duration,
            'file_path': file_path,
            'timestamp': datetime.now().isoformat()
        }
        self._stats['recent_downloads'].insert(0, download_info)
        self._stats['recent_downloads'] = self._stats['recent_downloads'][:20]

        # Сохраняем
        self._save_stats()

    def get_total_downloads(self) -> int:
        """Получение общего количества загрузок."""
        return self._stats['total_downloads']

    def get_total_size(self) -> int:
        """Получение общего размера всех загрузок в байтах."""
        return self._stats['total_size_bytes']

    def get_total_time(self) -> float:
        """Получение общего времени загрузок в секундах."""
        return self._stats['total_time_seconds']

    def get_today_downloads(self) -> int:
        """Получение количества загрузок за сегодня."""
        today = datetime.now().strftime('%Y-%m-%d')
        return self._stats['downloads_by_date'].get(today, {}).get('count', 0)

    def get_today_size(self) -> int:
        """Получение размера загрузок за сегодня в байтах."""
        today = datetime.now().strftime('%Y-%m-%d')
        return self._stats['downloads_by_date'].get(today, {}).get('size_bytes', 0)

    def get_recent_downloads(self, limit: int = 10) -> List[Dict]:
        """Получение последних загрузок."""
        return self._stats['recent_downloads'][:limit]

    def get_average_speed(self) -> float:
        """Получение средней скорости загрузки (байт/сек)."""
        if self._stats['total_time_seconds'] == 0:
            return 0
        return self._stats['total_size_bytes'] / self._stats['total_time_seconds']

    def format_size(self, size_bytes: int) -> str:
        """Форматирование размера в человекочитаемый вид."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def format_time(self, seconds: float) -> str:
        """Форматирование времени в человекочитаемый вид."""
        if seconds < 60:
            return f"{seconds:.0f} сек"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} мин"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} ч"

    def get_summary(self) -> Dict:
        """Получение сводной статистики."""
        return {
            'total_downloads': self.get_total_downloads(),
            'total_size': self.format_size(self.get_total_size()),
            'total_time': self.format_time(self.get_total_time()),
            'today_downloads': self.get_today_downloads(),
            'today_size': self.format_size(self.get_today_size()),
            'average_speed': self.format_size(self.get_average_speed()) + '/сек',
            'recent_downloads': self.get_recent_downloads(5)
        }

    def reset_stats(self):
        """Сброс статистики."""
        self._stats = self._default_stats()
        self._save_stats()
