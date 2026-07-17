#!/bin/bash

# Папка, куда ваш браузер или система сохраняет PDF-скриншоты
# Поменяйте путь, если они падают в другую папку
SCREENSHOT_DIR="$HOME/Загрузки"

# Находим самый свежий PDF-файл в этой папке
LATEST_PDF=$(ls -t "$SCREENSHOT_DIR"/*.pdf 2>/dev/null | head -n 1)

if [ -z "$LATEST_PDF" ]; then
    echo "PDF файлы не найдены в $SCREENSHOT_DIR"
    exit 1
fi

echo "Обрабатываю файл: $LATEST_PDF"

# Конвертируем с помощью MarkItDown во временный файл
markitdown "$LATEST_PDF" > /tmp/converted_screen.md

# Копируем результат в буфер обмена Wayland (в Fedora 43 за это отвечает wl-copy)
if command -v wl-copy &> /dev/null; then
    cat /tmp/converted_screen.md | wl-copy
    echo "Успешно! Текст скопирован в буфер обмена. Нажмите Ctrl+V в браузере."
else
    echo "Ошибка: утилита wl-copy не найдена. Установите её: sudo dnf install wl-clipboard"
fi
