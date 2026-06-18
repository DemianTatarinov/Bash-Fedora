#!/bin/bash
set -uo pipefail

count=0

# 1. Раскладываем файлы по персональным папкам
for file in *; do
    [ -f "$file" ] || continue
    [ "$file" != "$(basename "$0")" ] || continue

    filename="${file%.*}"
    mkdir -p "$filename"
    mv "$file" "$filename/"
    ((count++))
done

if [ "$count" -eq 0 ]; then
    echo "Новых файлов для переноса нет, проверяем отправку..."
fi

# 2. Индексация и коммит
git add .
# Коммитим только если есть что коммитить, чтобы не было ошибок
git diff-index --quiet HEAD -- || git commit -m "Авто-пуш: файлы разложены по папкам ($count шт.)"

echo "--> Синхронизация с GitHub (скачивание изменений)..."
# Подтягиваем изменения с сайта, если они там появились, автоматически объединяя
git pull origin main --allow-unrelated-histories --no-rebase -X ours --quiet

echo "--> Отправка на GitHub..."
if git push; then
    echo "🚀 Всё готово! Файлы успешно улетели на Git."
else
    echo "⚠️ Обычный push не прошел. Пробуем принудительное обновление..."
    git push -u origin main --force
    echo "🚀 Пробито силой! Проверяй сайт."
fi
