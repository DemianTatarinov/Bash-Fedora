#!/bin/bash

# 1. Автоматически определяем папку, где лежит сам скрипт
TARGET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$TARGET_DIR"

echo "Расположение скрипта: $TARGET_DIR"
echo "Ищем HEIC файлы для конвертации..."

# Включаем регистронезависимость для поиска
shopt -s nocaseglob

# Максимальный размер файла в байтах (4.5 МБ = 4.5 * 1024 * 1024)
MAX_SIZE=4718592

# Счетчик обработанных файлов
count=0

for f in *.heic; do
    # Проверяем, существует ли файл (на случай, если папка пуста)
    [ -e "$f" ] || continue
    
    basename="${f%.*}"
    output_jpg="${basename}.jpg"
    
    echo "----------------------------------------"
    echo "Обработка: $f"
    
    # 2. Конвертируем HEIC в JPG с максимальным качеством (100)
    if heif-convert -q 100 "$f" "$output_jpg"; then
        
        # 3. Проверяем размер получившегося JPEG
        file_size=$(stat -c%s "$output_jpg")
        
        if [ "$file_size" -gt "$MAX_SIZE" ]; then
            echo "Файл слишком большой ($(bc <<< "scale=2; $file_size/1024/1024") МБ). Сжимаем до 4.5 МБ..."
            
            # Подбираем качество с помощью ImageMagick, пока размер не станет меньше 4.5 МБ
            quality=95
            while [ "$file_size" -gt "$MAX_SIZE" ] && [ "$quality" -gt 10 ]; do
                mogrify -quality "$quality" "$output_jpg"
                file_size=$(stat -c%s "$output_jpg")
                quality=$((quality - 5))
            done
            echo "Итоговый размер после сжатия: $(bc <<< "scale=2; $file_size/1024/1024") МБ (Качество: $((quality + 5))%)"
        else
            echo "Размер в норме: $(bc <<< "scale=2; $file_size/1024/1024") МБ"
        fi
        
        # 4. Удаляем оригинал только если всё прошло успешно
        rm "$f"
        echo "Оригинал $f успешно удален."
        ((count++))
    else
        echo "Ошибка при конвертации файла: $f. Оригинал сохранен."
    fi
done

# Выключаем регистронезависимость обратно
shopt -u nocaseglob

echo "----------------------------------------"
echo "Готово! Обработано файлов: $count"

