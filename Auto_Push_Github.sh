#!/bin/bash
set -uo pipefail
SCRIPT_NAME=$(basename "$0")

# Проверяем наличие изменений в git (включая подпапки)
# Смотрим и на новые файлы и на изменённые и на удалённые
git_changes=$(git status --porcelain | grep -v "^?? $SCRIPT_NAME" | wc -l)
untracked=$(git status --porcelain | grep "^??" | grep -v "$SCRIPT_NAME" | wc -l)
total_changes=$((git_changes + untracked))

if [ "$total_changes" -eq 0 ]; then
    kdialog --passivepopup "Нет изменений для отправки на GitHub." 3
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
    # Перемещаем только файлы из корня папки (не подпапки)
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
    echo "* Все файлы упакованы в папку \`$MAIN_FOLDER\`" >> "$CHOSEN_README_PATH"
else
    echo "* Файлы загружены напрямую или распределены по подпапкам." >> "$CHOSEN_README_PATH"
fi

# Добавляем список изменённых файлов в README
echo -e "\n### 📄 Изменённые файлы:" >> "$CHOSEN_README_PATH"
git status --porcelain | grep -v "^?? $SCRIPT_NAME" >> "$CHOSEN_README_PATH"

# ==========================================
# ШАГ 3: ОТПРАВКА В GIT
# ==========================================
echo "--> Индексация всех изменений включая подпапки..."
git add -A

# Убираем сам скрипт из коммита
git rm --cached "$SCRIPT_NAME" &> /dev/null || true

COMMIT_MSG="Авто-пуш: бэкап $(date '+%Y-%m-%d %H:%M')"
[ -n "$MAIN_FOLDER" ] && COMMIT_MSG="Авто-пуш: создана папка $MAIN_FOLDER"

git diff-index --quiet HEAD -- || git commit -m "$COMMIT_MSG"

echo "--> Синхронизация с GitHub..."
git pull origin main --allow-unrelated-histories --no-rebase -X ours --quiet

echo "--> Отправка на GitHub..."
if git push; then
    kdialog --passivepopup "🚀 Готово! Изменения отправлены на GitHub." 5
else
    echo "⚠️ Обычный push отклонён. Пробиваем через Force..."
    git push -u origin main --force
    kdialog --passivepopup "🚀 Отправлено через Force! Проверяй GitHub." 5
fi
