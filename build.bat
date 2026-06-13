@echo off
echo ========================================
echo   Yandex Music Downloader - Build
echo ========================================
echo.

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        echo Try manually: pip install pyinstaller
        pause
        exit /b 1
    )
    echo PyInstaller installed.
    echo.
)

echo Starting build...
python -m PyInstaller --clean yandexdownloader.spec

echo.
if exist "dist\YandexMusicDownloader.exe" (
    echo BUILD SUCCESS!
    echo File: dist\YandexMusicDownloader.exe
    echo.
    echo To create installer:
    echo   1. Download Inno Setup: https://jrsoftware.org/isdl.php
    echo   2. Open installer_setup.iss
    echo   3. Click Build - Compile
) else (
    echo BUILD FAILED! Check output above.
)

echo.
pause
