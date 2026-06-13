; Yandex Music Downloader - Скрипт установщика Inno Setup
; Скачать Inno Setup: https://jrsoftware.org/isdl.php

#define MyAppName "Yandex Music Downloader"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Yandex Music Downloader"
#define MyAppExeName "YandexMusicDownloader.exe"
#define MyAppURL "https://github.com/"

[Setup]
; Уникальный ID приложения
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Пути установки
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; Выходной файл
OutputDir=installer_output
OutputBaseFilename=YandexMusicDownloader_Setup_1.0.0
VersionInfoVersion=1.0.0
VersionInfoCompany=Yandex Music Downloader
VersionInfoDescription=Yandex Music Downloader Installer
VersionInfoProductName=Yandex Music Downloader
VersionInfoProductVersion=1.0.0

; Иконка установщика
SetupIconFile=resources\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Сжатие
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Внешний вид
WizardStyle=modern
WizardSizePercent=100,100

; Требования
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Основной exe файл
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Если есть дополнительные файлы (не упакованы в exe):
; Source: "resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Главное меню
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Рабочий стол
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Запуск после установки
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Удаление созданных папок при деинсталляции
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\.config"
