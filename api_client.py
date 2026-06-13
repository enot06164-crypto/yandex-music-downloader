# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
Клиент для работы с API Яндекс.Музыки.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from yandex_music import Client, Track, Album, Artist, Playlist
from yandex_music.exceptions import YandexMusicError, UnauthorizedError

from config import Config, get_config

logger = logging.getLogger(__name__)


class YandexMusicClient:
    """
    Клиент для взаимодействия с API Яндекс.Музыки.
    Обеспечивает поиск, получение информации о треках, альбомах, исполнителях.
    """
    
    # Типы поиска
    SEARCH_TYPE_TRACK = 'track'
    SEARCH_TYPE_ALBUM = 'album'
    SEARCH_TYPE_ARTIST = 'artist'
    SEARCH_TYPE_PLAYLIST = 'playlist'
    
    # Качество аудио (диапазоны битрейта, kbps)
    QUALITY_RANGES = {
        'best':   (320, float('inf')),  # Лучшее доступное
        'high':   (320, float('inf')),  # 320 кбит/с
        'medium': (192, 319),           # 192 кбит/с
        'low':    (128, 191),           # 128 кбит/с
    }

    def __init__(self, token: Optional[str] = None, config: Optional[Config] = None):
        """
        Инициализация клиента API.
        
        Args:
            token (Optional[str]): OAuth-токен Яндекс.Музыки.
            config (Optional[Config]): Конфигурация приложения.
        """
        self._config = config or get_config()
        self._token = token
        self._client: Optional[Client] = None
        self._last_request_time: float = 0
        
        if token:
            self._init_client()
    
    def _init_client(self) -> None:
        """
        Инициализация клиента Yandex Music.
        """
        if not self._token:
            logger.warning("Токен не предоставлен, клиент не инициализирован")
            return

        try:
            self._client = Client(self._token).init()
            logger.info("Клиент API успешно инициализирован")
        except UnauthorizedError:
            logger.error("Неверный токен авторизации")
            raise
        except YandexMusicError as e:
            logger.error(f"Ошибка инициализации клиента: {e}")
            raise
    
    def _apply_rate_limit(self) -> None:
        """
        Применение rate limiting для запросов к API.
        Добавляет задержку между запросами для избежания блокировки.
        """
        delay = self._config.api_delay
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < delay:
            sleep_time = delay - elapsed
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    @property
    def is_authenticated(self) -> bool:
        """
        Проверка аутентификации клиента.
        
        Returns:
            bool: True если клиент аутентифицирован.
        """
        return self._client is not None
    
    @property
    def token(self) -> Optional[str]:
        """
        Получение текущего токена.
        
        Returns:
            Optional[str]: Токен или None.
        """
        return self._token
    
    def set_token(self, token: str) -> None:
        """
        Установка токена и инициализация клиента.
        
        Args:
            token (str): OAuth-токен Яндекс.Музыки.
            
        Raises:
            UnauthorizedError: Если токен недействителен.
        """
        self._token = token
        self._init_client()
    
    def clear_token(self) -> None:
        """
        Очистка токена и клиента.
        """
        self._token = None
        self._client = None
    
    def search(self, query: str, search_type: str = SEARCH_TYPE_TRACK,
               page: int = 0, limit: int = 20) -> Dict[str, Any]:
        """
        Поиск по Яндекс.Музыке.

        Args:
            query (str): Поисковый запрос.
            search_type (str): Тип поиска (track, album, artist, playlist).
            page (int): Номер страницы результатов.
            limit (int): Количество результатов на странице.

        Returns:
            Dict[str, Any]: Результаты поиска.

        Raises:
            YandexMusicError: Ошибка API.
        """
        if not self.is_authenticated:
            raise UnauthorizedError("Требуется авторизация для поиска")

        self._apply_rate_limit()

        try:
            logger.info(
                f"Поиск: query={query!r}, type={search_type}, "
                f"page={page}, limit={limit}"
            )
            results = self._client.search(
                text=query,
                type_=search_type,
                page=page
            )

            if results is None:
                logger.warning("Результат поиска None")
                return {'total': 0, 'items': [], 'page': page, 'limit': limit}

            items: List[Dict[str, Any]] = []
            total = 0

            if search_type == self.SEARCH_TYPE_TRACK and results.tracks:
                for track in results.tracks.results:
                    items.append(self._track_to_dict(track))
                total = results.tracks.total or len(items)

            elif search_type == self.SEARCH_TYPE_ALBUM and results.albums:
                for album in results.albums.results:
                    items.append(self._album_to_dict(album))
                total = results.albums.total or len(items)

            elif search_type == self.SEARCH_TYPE_ARTIST and results.artists:
                for artist in results.artists.results:
                    items.append(self._artist_to_dict(artist))
                total = results.artists.total or len(items)

            elif search_type == self.SEARCH_TYPE_PLAYLIST and results.playlists:
                for playlist in results.playlists.results:
                    items.append(self._playlist_to_dict(playlist))
                total = results.playlists.total or len(items)

            # Реальное ограничение количества возвращаемых элементов
            if limit and len(items) > limit:
                items = items[:limit]

            logger.info(
                f"Поиск завершён: получено {len(items)} из {total}"
            )

            return {
                'total': total,
                'items': items,
                'page': page,
                'limit': limit,
            }

        except YandexMusicError as e:
            logger.error(f"Ошибка поиска: {e}")
            raise
    
    def _paginated(self, raw: Dict[str, Any], page: int, limit: int) -> Dict[str, Any]:
        """
        Нормализация результата `search` для удобства пагинации:
        добавляет items, has_more, page, limit, total.
        """
        items = raw.get('items', [])
        total = raw.get('total', 0)
        return {
            'items': items,
            'total': total,
            'page': page,
            'limit': limit,
            'has_more': (page + 1) * limit < total,
        }

    def search_tracks(self, query: str, limit: int = 20,
                      page: int = 0) -> Dict[str, Any]:
        """
        Поиск треков.

        Args:
            query (str): Поисковый запрос.
            limit (int): Количество результатов на странице.
            page (int): Номер страницы (0-based).

        Returns:
            Dict с полями items, has_more, total, page, limit.
        """
        results = self.search(query, self.SEARCH_TYPE_TRACK,
                              page=page, limit=limit)
        return self._paginated(results, page, limit)

    def search_albums(self, query: str, limit: int = 20,
                      page: int = 0) -> Dict[str, Any]:
        """
        Поиск альбомов.

        Args:
            query (str): Поисковый запрос.
            limit (int): Количество результатов на странице.
            page (int): Номер страницы (0-based).

        Returns:
            Dict с полями items, has_more, total, page, limit.
        """
        results = self.search(query, self.SEARCH_TYPE_ALBUM,
                              page=page, limit=limit)
        return self._paginated(results, page, limit)

    def search_artists(self, query: str, limit: int = 20,
                       page: int = 0) -> Dict[str, Any]:
        """
        Поиск исполнителей.

        Args:
            query (str): Поисковый запрос.
            limit (int): Количество результатов на странице.
            page (int): Номер страницы (0-based).

        Returns:
            Dict с полями items, has_more, total, page, limit.
        """
        results = self.search(query, self.SEARCH_TYPE_ARTIST,
                              page=page, limit=limit)
        return self._paginated(results, page, limit)
    
    def get_track(self, track_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Получение информации о треке по ID.
        
        Args:
            track_id (Union[str, int]): ID трека.
            
        Returns:
            Optional[Dict[str, Any]]: Информация о треке или None.
        """
        if not self.is_authenticated:
            return None
        
        self._apply_rate_limit()
        
        try:
            track = self._client.tracks([track_id])
            if track and len(track) > 0:
                return self._track_to_dict(track[0])
        except YandexMusicError as e:
            logger.error(f"Ошибка получения трека {track_id}: {e}")
        
        return None
    
    def get_album(self, album_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Получение информации об альбоме по ID.

        Args:
            album_id (Union[str, int]): ID альбома.

        Returns:
            Optional[Dict[str, Any]]: Информация об альбоме или None.
        """
        if not self.is_authenticated:
            return None

        self._apply_rate_limit()

        try:
            albums = self._client.albums([album_id])
            if albums and len(albums) > 0:
                return self._album_to_dict(albums[0])
        except YandexMusicError as e:
            logger.error(f"Ошибка получения альбома {album_id}: {e}")

        return None
    
    def get_artist(self, artist_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Получение информации об исполнителе по ID.

        Args:
            artist_id (Union[str, int]): ID исполнителя.

        Returns:
            Optional[Dict[str, Any]]: Информация об исполнителе или None.
        """
        if not self.is_authenticated:
            return None

        self._apply_rate_limit()

        try:
            artists = self._client.artists([artist_id])
            if artists and len(artists) > 0:
                return self._artist_to_dict(artists[0])
        except YandexMusicError as e:
            logger.error(f"Ошибка получения исполнителя {artist_id}: {e}")

        return None

    def get_artist_tracks(self, artist_id: Union[str, int],
                          page: int = 0, limit: int = 20
                          ) -> Dict[str, Any]:
        """
        Получение треков исполнителя по ID (с пагинацией).

        Args:
            artist_id (Union[str, int]): ID исполнителя.
            page (int): Номер страницы (0-based).
            limit (int): Количество треков на странице.

        Returns:
            Dict[str, Any]: {
                'items': List[Dict],
                'total': int,
                'page': int,
                'limit': int,
                'has_more': bool,
                'artist_id': str|int,
            }
        """
        empty = {
            'items': [], 'total': 0, 'page': page, 'limit': limit,
            'has_more': False, 'artist_id': artist_id,
        }
        if not self.is_authenticated:
            return empty

        try:
            self._apply_rate_limit()
            artist_tracks = self._client.artists_tracks(
                artist_id, page=page, page_size=limit
            )

            if artist_tracks is None:
                return empty

            raw_tracks = list(artist_tracks) if artist_tracks else []
            items = [self._track_to_dict(t) for t in raw_tracks]

            pager = getattr(artist_tracks, 'pager', None)
            if pager is not None:
                total = getattr(pager, 'total', None) or len(items)
                per_page = getattr(pager, 'per_page', None) or limit
            else:
                total = len(items)
                per_page = limit

            return {
                'items': items,
                'total': total,
                'page': page,
                'limit': per_page,
                'has_more': (page + 1) * per_page < total,
                'artist_id': artist_id,
            }
        except YandexMusicError as e:
            logger.error(
                f"Ошибка получения треков исполнителя {artist_id}: {e}"
            )
            return empty
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка get_artist_tracks({artist_id}): {e}"
            )
            return empty
    
    def get_playlist(self, user_id: Union[str, int], 
                     playlist_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Получение информации о плейлисте.
        
        Args:
            user_id (Union[str, int]): ID пользователя.
            playlist_id (Union[str, int]): ID плейлиста.
            
        Returns:
            Optional[Dict[str, Any]]: Информация о плейлисте или None.
        """
        if not self.is_authenticated:
            return None
        
        self._apply_rate_limit()
        
        try:
            playlist = self._client.users_playlists(user_id, [playlist_id])
            if playlist and len(playlist) > 0:
                return self._playlist_to_dict(playlist[0])
        except YandexMusicError as e:
            logger.error(f"Ошибка получения плейлиста {playlist_id}: {e}")
        
        return None
    
    def get_track_lyrics(self, track_id: Union[str, int],
                         track_obj: Optional[Any] = None) -> Optional[str]:
        """
        Получение текста песни.

        Вызывается отдельно (не при поиске), чтобы не делать лишних
        API-запросов на каждый трек в результатах.

        Args:
            track_id: ID трека.
            track_obj: Уже загруженный объект Track (если есть) —
                позволяет избежать лишнего запроса tracks().

        Returns:
            Optional[str]: Текст песни или None.
        """
        if not self.is_authenticated:
            return None

        self._apply_rate_limit()

        try:
            if track_obj is None:
                fetched = self._client.tracks([track_id])
                if not fetched or len(fetched) == 0:
                    return None
                track_obj = fetched[0]

            lyrics_info = getattr(track_obj, 'lyrics_info', None)
            if not lyrics_info or not getattr(lyrics_info, 'id', None):
                return None
            lyrics_obj = self._client.lyrics(lyrics_info.id)
            if lyrics_obj and getattr(lyrics_obj, 'text', None):
                return lyrics_obj.text
        except YandexMusicError as e:
            logger.warning(f"Не удалось получить текст трека {track_id}: {e}")
        except Exception as e:
            logger.warning(f"Неожиданная ошибка при получении текста {track_id}: {e}")
        return None

    def get_track_download_url(self, track_id: Union[str, int],
                               version: Optional[str] = None) -> Optional[str]:
        """
        Получение URL для скачивания трека.
        
        Args:
            track_id (Union[str, int]): ID трека.
            version (Optional[str]): Версия трека (хеш файла).
            
        Returns:
            Optional[str]: URL для скачивания или None.
        """
        if not self.is_authenticated:
            return None
        
        self._apply_rate_limit()
        
        try:
            # Получаем информацию о треке
            track = self._client.tracks([track_id])
            if not track or len(track) == 0:
                return None
            
            track_obj = track[0]
            
            # Проверяем доступность трека
            if not track_obj.available:
                logger.warning(f"Трек {track_id} недоступен")
                return None
            
            # Получаем информацию для скачивания БЕЗ прямых ссылок
            download_info_list = track_obj.get_download_info(get_direct_links=False)

            if not download_info_list:
                return None

            # Сортируем по битрейту (лучшее качество первым)
            download_info_list.sort(key=lambda x: x.bitrate_in_kbps, reverse=True)

            quality = self._config.audio_quality

            # Диапазоны битрейта для конкретных настроек качества
            # 'best' / 'high'  -> >= 320
            # 'medium'         -> 192..319
            # 'low'            -> 128..191
            quality_ranges = {
                'best':   (320, float('inf')),
                'high':   (320, float('inf')),
                'medium': (192, 319),
                'low':    (128, 191),
            }
            low, high = quality_ranges.get(quality, (320, float('inf')))

            # 1) Ищем трек в нужном диапазоне (без превью)
            for info in download_info_list:
                if info.preview:
                    continue
                if low <= info.bitrate_in_kbps <= high:
                    return info.get_direct_link()

            # 2) Если в нужном диапазоне ничего нет — берём лучшее доступное без превью
            for info in download_info_list:
                if not info.preview:
                    return info.get_direct_link()

            # 3) Совсем ничего — отдаём превью (лучшее из них)
            if download_info_list:
                logger.warning(f"Для трека {track_id} доступны только превью")
                return download_info_list[0].get_direct_link()

            return None
            
        except YandexMusicError as e:
            logger.error(f"Ошибка получения URL скачивания для {track_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении URL для {track_id}: {e}")
            return None
    
    def _track_to_dict(self, track: Track) -> Dict[str, Any]:
        """
        Преобразование объекта Track в словарь.

        Args:
            track (Track): Объект трека.

        Returns:
            Dict[str, Any]: Словарь с информацией о треке.
        """
        # Получаем информацию об альбоме
        album_info = {}
        if track.albums and len(track.albums) > 0:
            album = track.albums[0]
            album_info = {
                'id': album.id,
                'title': album.title or 'Без названия',
                'year': album.year,
            }

        # Получаем обложку
        cover_url = None
        if track.albums and len(track.albums) > 0:
            cover = track.albums[0].cover_uri
            if cover:
                cover_url = self._normalize_cover_url(cover)

        artists = []
        if track.artists:
            for artist in track.artists:
                if artist.name:
                    artists.append(artist.name)

        if not artists:
            major = getattr(track, 'major', None)
            if major and getattr(major, 'name', None):
                artists.append(major.name)

        artists = [a.strip().rstrip('-').strip() for a in artists if a.strip()]

        return {
            'type': 'track',
            'id': track.id,
            'title': track.title or 'Без названия',
            'artists': artists,
            'artist': ', '.join(artists) if artists else 'Неизвестный исполнитель',
            'album': album_info,
            'duration_ms': track.duration_ms or 0,
            'cover_url': cover_url,
            'available': track.available,
            'version': track.version,
        }
    
    def _album_to_dict(self, album: Album) -> Dict[str, Any]:
        """
        Преобразование объекта Album в словарь.

        Args:
            album (Album): Объект альбома.

        Returns:
            Dict[str, Any]: Словарь с информацией об альбоме.
        """
        cover_url = None
        if album.cover_uri:
            cover_url = self._normalize_cover_url(album.cover_uri)

        # Получаем исполнителей
        artists = []
        if album.artists:
            for artist in album.artists:
                if artist.name:
                    artists.append(artist.name)
        
        # Получаем список треков
        tracks = []
        if album.volumes:
            for volume in album.volumes:
                for track in volume:
                    tracks.append({
                        'id': track.id,
                        'title': track.title or 'Без названия',
                        'duration_ms': track.duration_ms or 0,
                        'version': track.version,
                    })
        
        return {
            'type': 'album',
            'id': album.id,
            'title': album.title or 'Без названия',
            'artists': artists,
            'artist': ', '.join(artists) if artists else 'Неизвестный исполнитель',
            'year': album.year,
            'cover_url': cover_url,
            'track_count': len(tracks),
            'tracks': tracks,
            'available': album.available,
        }
    
    def _artist_to_dict(self, artist: Artist) -> Dict[str, Any]:
        """
        Преобразование объекта Artist в словарь.

        Args:
            artist (Artist): Объект исполнителя.

        Returns:
            Dict[str, Any]: Словарь с информацией об исполнителе.
        """
        cover_url = self._extract_cover_url(getattr(artist, 'cover', None))
        # Fallback: в некоторых версиях обложка лежит прямо в cover_uri
        if not cover_url and getattr(artist, 'cover_uri', None):
            cover_url = self._normalize_cover_url(artist.cover_uri)

        return {
            'type': 'artist',
            'id': artist.id,
            'name': artist.name or 'Без имени',
            'cover_url': cover_url,
            'genres': artist.genres or [],
        }
    
    @staticmethod
    def _normalize_cover_url(cover: str) -> str:
        """
        Приведение URL обложки к https://. Без downgrade до http.
        """
        if not cover:
            return ''
        if cover.startswith('//'):
            return 'https:' + cover
        if not cover.startswith('http'):
            return 'https://' + cover.lstrip('/')
        return cover

    @staticmethod
    def _extract_cover_url(cover) -> Optional[str]:
        """
        Универсальное извлечение URL обложки из разных представлений
        (dict, объект Cover с .big/.medium/.small, объект с .uri).
        """
        if not cover:
            return None
        try:
            # Словарь (старые версии API)
            if isinstance(cover, dict):
                url = (cover.get('big') or cover.get('medium')
                       or cover.get('small') or cover.get('uri'))
                return YandexMusicClient._normalize_cover_url(url) if url else None

            # Объект с .big/.medium/.small (некоторые версии)
            for attr in ('big', 'medium', 'small'):
                if hasattr(cover, attr):
                    val = getattr(cover, attr, None)
                    if val:
                        return YandexMusicClient._normalize_cover_url(val)

            # Объект Cover с .uri (актуальные версии)
            uri = getattr(cover, 'uri', None)
            if uri:
                return YandexMusicClient._normalize_cover_url(uri)
        except Exception:
            return None
        return None

    def _playlist_to_dict(self, playlist: Playlist) -> Dict[str, Any]:
        """
        Преобразование объекта Playlist в словарь.

        Args:
            playlist (Playlist): Объект плейлиста.

        Returns:
            Dict[str, Any]: Словарь с информацией о плейлисте.
        """
        cover_url = self._extract_cover_url(getattr(playlist, 'cover', None))
        if not cover_url and getattr(playlist, 'cover_uri', None):
            cover_url = self._normalize_cover_url(playlist.cover_uri)

        tracks = []
        if playlist.tracks:
            for track_short in playlist.tracks:
                track = getattr(track_short, 'track', None)
                if not track:
                    continue
                # Обложка и альбом — из привязанного альбома трека,
                # иначе метаданные файла будут пустыми
                track_album = {}
                track_cover = None
                track_albums = getattr(track, 'albums', None)
                if track_albums:
                    album_obj = track_albums[0]
                    track_album = {
                        'id': getattr(album_obj, 'id', None),
                        'title': getattr(album_obj, 'title', None) or 'Без названия',
                        'year': getattr(album_obj, 'year', None),
                    }
                    cover_uri = getattr(album_obj, 'cover_uri', None)
                    if cover_uri:
                        track_cover = self._normalize_cover_url(cover_uri)
                tracks.append({
                    'id': track.id,
                    'title': track.title or 'Без названия',
                    'artists': [a.name for a in track.artists
                                if getattr(a, 'name', None)] if track.artists else [],
                    'duration_ms': track.duration_ms or 0,
                    'cover_url': track_cover,
                    'album': track_album,
                })

        return {
            'type': 'playlist',
            'id': playlist.kind,
            'user_id': playlist.owner_account.uid if playlist.owner_account else None,
            'title': playlist.title or 'Без названия',
            'description': playlist.description or '',
            'cover_url': cover_url,
            'track_count': len(tracks),
            'tracks': tracks,
            'is_public': playlist.is_public,
        }
    
    def parse_link(self, link: str) -> Optional[Dict[str, Any]]:
        """
        Парсинг ссылки Яндекс.Музыки.

        Args:
            link (str): Ссылка на трек, альбом, исполнителя или плейлист.

        Returns:
            Optional[Dict[str, Any]]: Информация о типе и ID или None.
        """
        import re
        from urllib.parse import urlparse

        if not link or 'music.yandex.' not in link:
            return None

        # Нормализуем URL: убираем query/fragment, приводим к https://
        text = link.strip()
        # Схема
        if not text.startswith(('http://', 'https://', '//')):
            text = 'https://' + text
        parsed_url = urlparse(text)
        path = parsed_url.path.rstrip('/')

        if not path:
            return None

        patterns = {
            'track':    r'^/album/[\d]+/track/(?P<id>\d+)$',
            'album':    r'^/album/(?P<id>\d+)$',
            'artist':   r'^/artist/(?P<id>\d+)$',
            'playlist': r'^(?:/users/(?P<user>[^/]+))?/playlists/(?P<id>[^/]+)$',
        }

        for type_, pattern in patterns.items():
            match = re.match(pattern, path)
            if match:
                groups = match.groupdict()
                result = {'type': type_, 'id': groups['id']}
                if type_ == 'playlist' and groups.get('user'):
                    result['user_id'] = groups['user']
                return result

        return None
