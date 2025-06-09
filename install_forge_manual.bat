@echo off
title Ручная установка Forge для сервера

echo === Ручная установка Forge ===
echo.

REM Переходим в директорию сервера
cd /d "C:\Users\Sharp\Desktop\open\Сервер Где Стас"

echo Текущая директория: %cd%
echo.

REM Проверяем наличие installer
if not exist "forge-installer.jar" (
    echo ❌ forge-installer.jar не найден!
    echo Сначала скачайте Forge installer
    pause
    exit /b 1
)

echo Найден forge-installer.jar
echo.

REM Проверяем Java
java -version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Java не установлена!
    pause
    exit /b 1
)

echo ✓ Java найдена
echo.

echo Запускаем установку Forge...
echo ВАЖНО: Выберите "Install server" в окне установщика!
echo.
pause

REM Запускаем GUI установщик
java -jar forge-installer.jar

echo.
echo Установка завершена. Проверяем результат...
echo.

REM Проверяем, появился ли основной JAR
set FORGE_INSTALLED=0
for %%f in (forge-*.jar) do (
    echo Найден: %%f
    echo %%f | findstr /i "installer" >nul
    if errorlevel 1 (
        echo ✅ Основной Forge JAR создан: %%f
        set FORGE_INSTALLED=1
    )
)

if %FORGE_INSTALLED%==0 (
    echo.
    echo ❌ Основной Forge JAR не найден!
    echo Возможно установка не завершена или произошла ошибка.
    echo.
    echo Попробуйте:
    echo 1. Запустить установку еще раз
    echo 2. Проверить подключение к интернету
    echo 3. Убедиться что выбрали "Install server"
) else (
    echo.
    echo ✅ Forge установлен успешно!
    echo Теперь можно запускать сервер через start_server.bat
)

echo.
pause