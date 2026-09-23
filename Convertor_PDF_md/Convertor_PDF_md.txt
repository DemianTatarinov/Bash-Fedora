#!/bin/bash

TARGET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_PNG="/tmp/fireshot_page"
TEMP_TXT="/tmp/fireshot_text"

echo "=== Запуск железного распознавания в папке: $TARGET_DIR ==="

# Находим самый свежий PDF от FireShot
LATEST_PDF=$(ls -t "$TARGET_DIR"/*.pdf 2>/dev/null | head -n 1)

if [ -z "$LATEST_PDF" ]; then
    echo "❌ Ошибка: В текущей папке не найдено PDF-файлов."
    exit 1
fi

echo "📦 Найдено для обработки: $(basename "$LATEST_PDF")"

# 1. Извлекаем картинку из PDF высокой четкости (150 DPI)
echo "📸 Извлекаю снимок страницы..."
pdftoppm -png -r 150 "$LATEST_PDF" "$TEMP_PNG"

REAL_PNG="${TEMP_PNG}-1.png"

if [ ! -f "$REAL_PNG" ]; then
    echo "❌ Ошибка: Не удалось извлечь изображение из PDF."
    exit 1
fi

# 2. Распознаем текст напрямую через Tesseract (три языка сразу)
echo "🔮 Движок Tesseract распознаёт текст (PL + RU + ENG)..."
tesseract "$REAL_PNG" "$TEMP_TXT" -l pol+rus+eng &>/dev/null

if [ $? -ne 0 ] || [ ! -s "${TEMP_TXT}.txt" ]; then
    echo "❌ Ошибка распознавания. Проверьте, установлены ли языковые пакеты."
    rm -f "$REAL_PNG"
    exit 1
fi

# 3. Копируем готовый текст в буфер обмена Wayland (Fedora 43)
if command -v wl-copy &> /dev/null; then
    cat "${TEMP_TXT}.txt" | wl-copy
    echo "⚡ УСПЕХ! Весь текст со скриншота скопирован в буфер."
    echo "📋 Откройте браузер и нажмите Ctrl+V в чате Gemini."
else
    echo "⚠️ Текст распознан, но утилита 'wl-copy' не найдена (sudo dnf install wl-clipboard)"
fi

# Чистим мусор
rm -f "$REAL_PNG" "${TEMP_TXT}.txt"
