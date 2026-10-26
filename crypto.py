# -*- coding: utf-8 -*-
"""
Yandex Music Downloader
Модуль криптографии для шифрования токена.

Copyright (c) 2026. Использование должно соответствовать Условиям использования Яндекс.Музыки
и законам об авторском праве.

"""

import hashlib
import sys
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os


def get_hwid() -> str:
    """
    Получение уникального идентификатора оборудования (HWID).
    Используется для привязки зашифрованного токена к конкретному компьютеру.

    Returns:
        str: Строка HWID для использования в качестве соли.
    """
    if sys.platform == 'win32':
        # Windows: volume serial number диска C:
        try:
            import ctypes
            import ctypes.wintypes

            drive_type = ctypes.windll.kernel32.GetDriveTypeW('C:\\')
            if drive_type != 0:
                volume_info = ctypes.create_unicode_buffer(512)
                serial_number = ctypes.wintypes.DWORD()
                max_component_length = ctypes.wintypes.DWORD()
                file_system_flags = ctypes.wintypes.DWORD()
                file_system_name = ctypes.create_unicode_buffer(512)

                result = ctypes.windll.kernel32.GetVolumeInformationW(
                    'C:\\',
                    volume_info,
                    len(volume_info),
                    ctypes.byref(serial_number),
                    ctypes.byref(max_component_length),
                    ctypes.byref(file_system_flags),
                    file_system_name,
                    len(file_system_name)
                )

                if result and serial_number.value:
                    return f"win-vol-{serial_number.value}"
        except Exception:
            pass

        # Fallback: MachineGuid из реестра (стабильнее UUID компьютера,
        # не меняется при переустановке/смене диска). `wmic` deprecated
        # в Windows 11 24H2+ — registry надёжнее.
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography"
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
                if value:
                    return f"win-mg-{value}"
        except Exception:
            pass

    elif sys.platform.startswith('linux'):
        try:
            with open('/etc/machine-id') as f:
                return f"linux-mid-{f.read().strip()[:32]}"
        except Exception:
            pass
        try:
            import uuid
            return f"linux-uuid-{str(uuid.getnode())}"
        except Exception:
            pass

    elif sys.platform == 'darwin':
        # macOS: IOPlatformSerialNumber
        import subprocess
        try:
            result = subprocess.run(
                ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'IOPlatformSerialNumber' in line:
                    serial = line.split('=')[-1].strip().strip('"')
                    if serial and serial != '0':
                        return f"mac-{serial}"
        except Exception:
            pass

    # Linux / Docker / WSL: machine-id
    # ВНИМАНИЕ: в контейнерах одинаковый — файл соли (.token_salt)
    # всё равно разный на каждом хосте, что даёт уникальность.
    try:
        if os.path.exists('/etc/machine-id'):
            with open('/etc/machine-id', 'r') as f:
                machine_id = f.read().strip()
                if machine_id:
                    return f"linux-{machine_id}"
    except Exception:
        pass

    # Последний fallback: hostname (не уникален, но стабилен в пределах машины)
    import socket
    try:
        return f"host-{socket.gethostname()}-{os.getuid()}"
    except Exception:
        return f"host-{socket.gethostname()}"


class TokenCrypto:
    """
    Класс для шифрования и дешифрования токена Яндекс.Музыки.
    Использует Fernet симметричное шифрование с ключом, 
    полученным из параметров оборудования.
    """
    
    SALT_FILE = Path(__file__).parent / '.config' / '.token_salt'
    ITERATIONS = 100000  # Количество итераций для PBKDF2

    @classmethod
    def _get_salt(cls) -> bytes:
        """
        Возвращает уникальную соль для KDF.

        Соль генерируется один раз при первом запуске и сохраняется
        в файле `.config/.token_salt`. Это:
        - даёт уникальную соль на каждую установку (не константа);
        - обеспечивает стабильность между запусками (иначе токен
          не расшифруется);
        - не зависит от HWID (HWID уже используется как материал ключа).
        """
        try:
            if cls.SALT_FILE.exists():
                return cls.SALT_FILE.read_bytes()
        except OSError as e:
            # Не падаем молча — если файл существует, но прочитать
            # не можем, перезаписывать соль НЕЛЬЗЯ: токен станет
            # невосстановим. Возвращаем детерминированный fallback
            # (наихудший случай — все установки с одной солью,
            # но токен хоть расшифруется).
            import logging
            logging.getLogger(__name__).warning(
                f"Не удалось прочитать salt-файл {cls.SALT_FILE}: {e}. "
                f"Используем детерминированный fallback."
            )
            return b"yandex-music-downloader-fallback-salt"
        # Генерируем новую соль
        salt = os.urandom(32)
        try:
            cls.SALT_FILE.parent.mkdir(parents=True, exist_ok=True)
            cls.SALT_FILE.write_bytes(salt)
            # Прячем файл на Windows
            if sys.platform == 'win32':
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(
                        str(cls.SALT_FILE), 0x02  # HIDDEN
                    )
                except Exception:
                    pass
        except Exception:
            # Если не удалось сохранить — используем в памяти,
            # но токен не будет расшифрован после перезапуска.
            pass
        return salt
    
    def __init__(self):
        """
        Инициализация криптографического модуля.
        Генерирует ключ шифрования на основе HWID.
        """
        self._hwid = get_hwid()
        self._fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """
        Создание объекта Fernet для шифрования/дешифрования.

        Returns:
            Fernet: Объект для криптографических операций.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._get_salt(),
            iterations=self.ITERATIONS,
        )

        hwid_bytes = self._hwid.encode('utf-8')
        key = kdf.derive(hwid_bytes)

        key_base64 = base64.urlsafe_b64encode(key)

        return Fernet(key_base64)
    
    def encrypt(self, token: str) -> str:
        """
        Шифрование токена.
        
        Args:
            token (str): Токен для шифрования.
            
        Returns:
            str: Зашифрованный токен в base64 кодировке.
            
        Raises:
            ValueError: Если токен пустой.
        """
        if not token:
            raise ValueError("Токен не может быть пустым")
        
        token_bytes = token.encode('utf-8')
        encrypted = self._fernet.encrypt(token_bytes)
        
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, encrypted_token: str) -> str:
        """
        Дешифрование токена.
        
        Args:
            encrypted_token (str): Зашифрованный токен в base64 кодировке.
            
        Returns:
            str: Расшифрованный токен.
            
        Raises:
            InvalidToken: Если токен недействителен или поврежден.
            ValueError: Если зашифрованный токен пустой.
        """
        if not encrypted_token:
            raise ValueError("Зашифрованный токен не может быть пустым")
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode('utf-8'))
            decrypted = self._fernet.decrypt(encrypted_bytes)
            
            return decrypted.decode('utf-8')
        except InvalidToken:
            raise InvalidToken("Не удалось расшифровать токен. "
                             "Возможно, приложение запущено на другом компьютере.")
    
    def verify_hwid(self) -> bool:
        """
        Проверка соответствия текущего HWID тому, с которым был создан ключ.
        В данной реализации всегда возвращает True, так как ключ генерируется
        динамически при каждом запуске.
        
        Returns:
            bool: True если HWID совпадает.
        """
        return True
    
    def get_hwid_display(self) -> str:
        """
        Получение отображаемой версии HWID для пользователя.
        
        Returns:
            str: Первые 8 символов HWID.
        """
        return self._hwid[:8].upper()
