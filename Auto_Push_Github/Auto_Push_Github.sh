#!/bin/bash
set -uo pipefail

SCRIPT_NAME=$(basename "$0")

# Проверяем наличие файлов (исключая сам скрипт)
file_count=$(find . -maxdepth 1 -type f ! -name "$SCRIPT_NAME" ! -name ".*" | wc -l)
if [ "$file_count" -eq 0 ]; then
    echo "Новых файлов для переноса нет."
    exit 0
fi

# ==========================================
# ШАГ 1: ОПРЕДЕЛЯЕМ СТРУКТУРУ ПАПОК
# ==========================================
MAIN_FOLDER=$(kdialog --inputbox "Шаг 1/3: Если нужно собрать ВСЕ файлы в одну общую папку, введите её имя.\n(Оставьте пустым, если папка не нужна):" "")

TARGET_DIR="."
CHOSEN_README_PATH="./README.md"

if [ -n "$MAIN_FOLDER" ]; then
    mkdir -p "$MAIN_FOLDER"
    TARGET_DIR="$MAIN_FOLDER"
    CHOSEN_README_PATH="$MAIN_FOLDER/README.md"

    for file in *; do
        [ -f "$file" ] || continue
        [ "$file" != "$SCRIPT_NAME" ] || continue
        [ "$file" != "$MAIN_FOLDER" ] || continue
        mv "$file" "$TARGET_DIR/"
    done
else
    kdialog --yesno "Общая папка не создана. Разложить каждый файл в ПЕРСОНАЛЬНУЮ папку по его имени?"
    if [ $? -eq 0 ]; then
        for file in *; do
            [ -f "$file" ] || continue
            [ "$file" != "$SCRIPT_NAME" ] || continue
            filename="${file%.*}"
            mkdir -p "$filename"
            mv "$file" "$filename/"
        done
    fi
fi

# ==========================================
# ШАГ 2: СОЗДАНИЕ И ОПИСАНИЕ README.md
# ==========================================
README_COMMENT=$(kdialog --inputbox "Шаг 2/3: Добавить описание или заметку в README.md?\n(По желанию):" "")

echo "# Обновление репозитория от $(date '+%Y-%m-%d %H:%M')" > "$CHOSEN_README_PATH"
echo "Отправлено автоматически с Fedora Linux (KDE Plasma 6)." >> "$CHOSEN_README_PATH"

if [ -n "$README_COMMENT" ]; then
    echo -e "\n### 📝 Комментарий автора:\n> $README_COMMENT" >> "$CHOSEN_README_PATH"
fi

echo -e "\n### 📦 Структура изменений:" >> "$CHOSEN_README_PATH"
if [ -n "$MAIN_FOLDER" ]; then
    echo "* Все файлы были успешно упакованы в целевую папку \`$MAIN_FOLDER\`" >> "$CHOSEN_README_PATH"
else
    echo "* Файлы загружены напрямую в корень репозитория или распределены персонально." >> "$CHOSEN_README_PATH"
fi

# ==========================================
# ШАГ 3: ОТПРАВКА В GIT (ЗАЩИТА ОТ СЕБЯ)
# ==========================================
echo "--> Индексация..."
git add .

# ЖЕСТКАЯ ЗАЩИТА: Насильно убираем сам скрипт из отправки, если он случайно добавился
git rm --cached "$SCRIPT_NAME" &> /dev/null || true

COMMIT_MSG="Авто-пуш: бэкап $(date '+%Y-%m-%d %H:%M')"
[ -n "$MAIN_FOLDER" ] && COMMIT_MSG="Авто-пуш: создана папка $MAIN_FOLDER"

git diff-index --quiet HEAD -- || git commit -m "$COMMIT_MSG"

echo "--> Синхронизация с GitHub..."
git pull origin main --allow-unrelated-histories --no-rebase -X ours --quiet

echo "--> Отправка на GitHub..."
if git push; then
    kdialog --passivepopup "🚀 Всё готово! Изменения улетели на Git (без самого скрипта)." 5
else
    echo "⚠️ Обычный push отклонен сервером. Пробиваем через Force..."
    git push -u origin main --force
    kdialog --passivepopup "🚀 Пробито силой! Проверяй свой GitHub." 5
fi
