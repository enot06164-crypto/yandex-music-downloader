# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
Модуль загрузки аудиофайлов с встраиванием метаданных.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TDRC, TCON, APIC, USLT
from mutagen.mp3 import MP3
from PIL import Image
import io

from config import Config, get_config

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Исключение, возникающее при ошибке загрузки."""
    pass


class TagError(Exception):
    """Исключение, возникающее при ошибке записи тегов."""
    pass


class AudioDownloader:
    """
    Класс для загрузки аудиофайлов с Яндекс.Музыки.
    Обрабатывает скачивание, встраивание ID3 тегов и обложек.
    """
    
    # Размер чанка для загрузки (байты)
    CHUNK_SIZE = 8192
    
    # Максимальный размер обложки (пиксели)
    MAX_COVER_SIZE = 600
    
    # Форматы обложек
    COVER_FORMAT = 'JPEG'
    COVER_QUALITY = 90
    
    def __init__(self, config: Optional[Config] = None):
        """
        Инициализация загрузчика.
        
        Args:
            config (Optional[Config]): Конфигурация приложения.
        """
        self._config = config or get_config()
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        
        # Статистика загрузки
        self._total_downloaded = 0
        self._total_size = 0
    
    def download_track(self, url: str, file_path: Path,
                       track_info: Optional[Dict[str, Any]] = None,
                       progress_callback: Optional[Callable[[int, int], None]] = None
                       ) -> Path:
        """
        Загрузка трека по URL.

        Args:
            url (str): URL для скачивания.
            file_path (Path): Путь для сохранения файла.
            track_info (Optional[Dict[str, Any]]): Информация о треке для тегов.
            progress_callback (Optional[Callable]): Функция обратного вызова для прогресса.

        Returns:
            Path: Путь к сохраненному файлу.

        Raises:
            DownloadError: Ошибка загрузки.
        """
        timeout = self._config.request_timeout
        response = None
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Загрузка трека: {url}")

            response = self._session.get(
                url,
                stream=True,
                timeout=timeout
            )
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            # Локальные счётчики, чтобы не ломать _total_* при повторных вызовах
            downloaded = 0

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            self._total_size = total_size
            self._total_downloaded = downloaded

            if response is not None:
                response.close()

            # Проверка: файл не должен быть пустым
            if downloaded == 0:
                self._safe_remove(file_path)
                raise DownloadError("Сервер вернул пустой файл")

            logger.info(f"Трек загружен: {file_path}")

            # Встраиваем метаданные (только если файл валидный)
            if track_info:
                try:
                    self._embed_metadata(file_path, track_info)
                except TagError as e:
                    # Ошибка тегирования не должна удалять уже скачанный файл
                    logger.warning(f"Не удалось встроить метаданные: {e}")

            return file_path

        except requests.RequestException as e:
            self._safe_remove(file_path)
            if response is not None:
                response.close()
            logger.error(f"Ошибка загрузки {url}: {e}")
            raise DownloadError(f"Не удалось загрузить трек: {e}")
        except (IOError, OSError) as e:
            self._safe_remove(file_path)
            if response is not None:
                response.close()
            logger.error(f"Ошибка записи файла {file_path}: {e}")
            raise DownloadError(f"Не удалось сохранить файл: {e}")
        except DownloadError:
            self._safe_remove(file_path)
            if response is not None:
                response.close()
            raise
        except Exception:
            self._safe_remove(file_path)
            if response is not None:
                response.close()
            raise

    @staticmethod
    def _safe_remove(file_path: Path) -> None:
        """Удаление partial-файла без падения, если он не существует."""
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError as e:
            logger.warning(f"Не удалось удалить {file_path}: {e}")
    
    def download_tracks_batch(self, tracks: List[Dict[str, Any]], 
                              base_path: Optional[Path] = None,
                              progress_callback: Optional[Callable[[str, int, int], None]] = None
                              ) -> List[Tuple[Path, Optional[str]]]:
        """
        Пакетная загрузка нескольких треков.
        
        Args:
            tracks (List[Dict[str, Any]]): Список треков для загрузки.
            base_path (Optional[Path]): Базовый путь для сохранения.
            progress_callback (Optional[Callable]): Callback для прогресса.
            
        Returns:
            List[Tuple[Path, Optional[str]]]: Список кортежей (путь, ошибка).
        """
        base_path = base_path or self._config.music_path
        results = []
        
        total_tracks = len(tracks)
        
        for index, track in enumerate(tracks):
            try:
                if progress_callback:
                    progress_callback(track.get('title', 'Unknown'), index + 1, total_tracks)
                
                # Получаем URL для скачивания
                url = track.get('download_url')
                if not url:
                    raise DownloadError("URL для скачивания не предоставлен")
                
                # Формируем путь к файлу
                file_path = self._generate_file_path(track, base_path)
                
                # Скачиваем трек
                self.download_track(
                    url, 
                    file_path, 
                    track_info=track,
                    progress_callback=None  # Используем общий прогресс для батча
                )
                
                results.append((file_path, None))
                
            except Exception as e:
                logger.error(f"Ошибка загрузки трека {track.get('title', 'Unknown')}: {e}")
                results.append((Path(), str(e)))
            
            # Небольшая задержка между загрузками
            time.sleep(0.5)
        
        return results
    
    def _generate_file_path(self, track_info: Dict[str, Any],
                           base_path: Path) -> Path:
        """
        Генерация пути к файлу на основе метаданных.

        Структура: Music/Artist/Track.mp3

        Args:
            track_info (Dict[str, Any]): Информация о треке.
            base_path (Path): Базовая директория.

        Returns:
            Path: Полный путь к файлу.
        """
        # Получаем и очищаем названия
        artist = self._sanitize_filename(track_info.get('artist', 'Unknown Artist'))
        title = self._sanitize_filename(track_info.get('title', 'Unknown Title'))

        # Ограничение длины пути Windows — 260 символов.
        # base/artist/title.mp3 → резервируем место под base + artist.
        max_total = 250
        base_prefix_len = len(str(base_path)) + len(artist) + 2  # два разделителя
        max_title_len = max_total - base_prefix_len - 4  # '.mp3'
        if max_title_len < 1:
            max_title_len = 1
        if len(title) > max_title_len:
            title = title[:max_title_len]

        return base_path / artist / f"{title}.mp3"
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Очистка названия файла от недопустимых символов.

        Args:
            filename (str): Исходное название.

        Returns:
            str: Очищенное название.
        """
        # Удаляем ", " в начале (проблема с именами артистов)
        if filename.startswith(', '):
            filename = filename[2:]

        # Удаляем лишние тире и дефисы в начале/конце
        filename = filename.strip('-').strip()

        # Запрещенные символы в Windows: < > : " / \ | ? *
        forbidden_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(forbidden_chars, '_', filename)

        # Удаляем начальные/конечные пробелы и точки
        sanitized = sanitized.strip(' .')

        # Заменяем множественные пробелы на один
        sanitized = re.sub(r'\s+', ' ', sanitized)

        # Если после очистки строка пустая, используем fallback
        if not sanitized:
            sanitized = 'unknown_track'

        return sanitized[:100]  # Ограничиваем длину
    
    def _embed_metadata(self, file_path: Path, track_info: Dict[str, Any]) -> None:
        """
        Встраивание ID3 тегов в аудиофайл.
        
        Args:
            file_path (Path): Путь к файлу.
            track_info (Dict[str, Any]): Информация о треке.
            
        Raises:
            TagError: Ошибка записи тегов.
        """
        try:
            # Загружаем файл
            audio = MP3(str(file_path))
            
            # Пытаемся загрузить существующие теги
            try:
                tags = ID3(str(file_path))
            except ID3NoHeaderError:
                tags = ID3()
            
            # Title (название трека)
            tags['TIT2'] = TIT2(encoding=3, text=track_info.get('title', ''))
            
            # Artist (исполнитель)
            tags['TPE1'] = TPE1(encoding=3, text=track_info.get('artist', ''))
            
            # Album (альбом)
            album_info = track_info.get('album', {})
            if album_info:
                tags['TALB'] = TALB(encoding=3, text=album_info.get('title', ''))
                
                # Year (год)
                year = album_info.get('year')
                if year:
                    tags['TDRC'] = TDRC(encoding=3, text=str(year))
            
            # Genre (жанр) - если доступен
            if 'genre' in track_info:
                tags['TCON'] = TCON(encoding=3, text=track_info['genre'])
            
            # Обложка
            if self._config.get('embed_cover', True):
                cover_url = track_info.get('cover_url')
                if cover_url:
                    cover_data = self._download_cover(cover_url)
                    if cover_data:
                        tags['APIC'] = APIC(
                            encoding=3,
                            mime='image/jpeg',
                            type=3,  # Front cover
                            desc='Cover',
                            data=cover_data
                        )

            # Текст песни (если доступен и включён)
            if self._config.get('embed_lyrics', False):
                lyrics = track_info.get('lyrics')
                if lyrics:
                    tags['USLT'] = USLT(
                        encoding=3,
                        lang='rus',
                        desc='Lyrics',
                        text=lyrics
                    )
            
            # Сохраняем теги
            tags.save(str(file_path))
            
            logger.info(f"Метаданные встроены в {file_path}")
            
        except Exception as e:
            logger.error(f"Ошибка встраивания метаданных в {file_path}: {e}")
            raise TagError(f"Не удалось встроить метаданные: {e}")
    
    def _download_cover(self, cover_url: str) -> Optional[bytes]:
        """
        Загрузка и обработка обложки альбома.
        
        Args:
            cover_url (str): URL обложки.
            
        Returns:
            Optional[bytes]: Данные обложки в формате JPEG или None.
        """
        response = None
        try:
            # Увеличиваем качество обложки (заменяем %% на размер)
            if '%%' in cover_url:
                cover_url = cover_url.replace('%%', '600x600')

            response = self._session.get(cover_url, timeout=10)
            response.raise_for_status()

            # Открываем изображение
            image = Image.open(io.BytesIO(response.content))
            
            # Конвертируем в RGB если нужно (для PNG с прозрачностью)
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # Изменяем размер если нужно
            max_size = self.MAX_COVER_SIZE
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Сохраняем в JPEG
            output = io.BytesIO()
            image.save(output, format=self.COVER_FORMAT, quality=self.COVER_QUALITY)
            
            return output.getvalue()

        except Exception as e:
            logger.warning(f"Не удалось загрузить обложку {cover_url}: {e}")
            return None
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
    
    def get_progress(self) -> Tuple[int, int]:
        """
        Получение прогресса текущей загрузки.
        
        Returns:
            Tuple[int, int]: Кортеж (загружено байт, всего байт).
        """
        return (self._total_downloaded, self._total_size)
    
    def reset_progress(self) -> None:
        """
        Сброс прогресса.
        """
        self._total_downloaded = 0
        self._total_size = 0
    
    def calculate_eta(self, downloaded: int, total: int, 
                      elapsed_time: float) -> Optional[float]:
        """
        Расчет предполагаемого времени до завершения загрузки.
        
        Args:
            downloaded (int): Загружено байт.
            total (int): Всего байт.
            elapsed_time (float): Прошло времени в секундах.
            
        Returns:
            Optional[float]: ETA в секундах или None.
        """
        if elapsed_time <= 0 or downloaded <= 0:
            return None
        
        speed = downloaded / elapsed_time  # байт/сек
        remaining = total - downloaded
        
        if speed <= 0:
            return None
        
        return remaining / speed
    
    def format_size(self, size_bytes: int) -> str:
        """
        Форматирование размера в человекочитаемый вид.
        
        Args:
            size_bytes (int): Размер в байтах.
            
        Returns:
            str: Форматированный размер.
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.1f} TB"
    
    def format_time(self, seconds: float) -> str:
        """
        Форматирование времени в человекочитаемый вид.
        
        Args:
            seconds (float): Время в секундах.
            
        Returns:
            str: Форматированное время (MM:SS или HH:MM:SS).
        """
        if seconds < 0:
            return "--:--"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def close(self) -> None:
        """
        Закрытие сессии и очистка ресурсов.
        """
        self._session.close()
