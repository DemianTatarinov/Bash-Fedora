#!/bin/bash
set -euo pipefail

# Автоматически определяем папку, где лежит сам скрипт
TARGET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TARGET_DIR"

echo "Рабочая директория: $TARGET_DIR"
echo "Ищем ZIP-архивы..."

# Функция для генерации уникального имени, если файл/папка уже существует
get_unique_name() {
    local path="$1"
    local dir
    local base
    local ext
    local counter=1

    if [ ! -e "$path" ]; then
        echo "$path"
        return
    fi

    dir=$(dirname "$path")
    base=$(basename "$path")
    ext="${base##*.}"
    base="${base%.*}"

    # Если расширения нет (это папка)
    if [ "$base" = "$ext" ]; then
        while [ -e "$dir/${base}_$counter" ]; do
            ((counter++))
        done
        echo "$dir/${base}_$counter"
    else
        while [ -e "$dir/${base}_$counter.$ext" ]; do
            ((counter++))
        done
        echo "$dir/${base}_$counter.$ext"
    fi
}

# Включаем регистронезависимость
shopt -s nocaseglob

count=0

for archive in *.zip; do
    # Проверяем, существуют ли файлы
    [ -e "$archive" ] || continue

    # Получаем базовое имя папки
    base_dirname="${archive%.*}"

    # Проверяем коллизии имён
    dirname=$(get_unique_name "$base_dirname")

    echo "----------------------------------------"
    if [ "$base_dirname" != "$dirname" ]; then
        echo "Папка $base_dirname уже существует. Изменено на: $(basename "$dirname")"
    fi
    echo "Распаковка: $archive -> папка: $(basename "$dirname")"

    # Распаковываем в одноименную папку
    if unzip -q "$archive" -d "$dirname"; then
        echo "Успешно распаковано. Удаляем архив..."
        rm -f "$archive"
        ((count++))
    else
        echo "Ошибка при распаковке $archive! Архив сохранен."
    fi
done

shopt -u nocaseglob

echo "----------------------------------------"
echo "Готово! Успешно обработано архивов: $count"
