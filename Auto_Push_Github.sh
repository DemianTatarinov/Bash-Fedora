#!/bin/bash
set -uo pipefail

# Считаем количество обычных файлов на текущем уровне (исключая сам скрипт)
file_count=$(find . -maxdepth 1 -type f ! -name "$(basename "$0")" ! -name ".*" | wc -l)

if [ "$file_count" -eq 0 ]; then
    echo "Новых файлов для переноса нет."
    exit 0
fi

# Инициализируем имя целевой папки
FOLDER_NAME=""

if [ "$file_count" -gt 1 ]; then
    # Если файлов больше одного — запрашиваем имя ОДИН раз через графическое окно KDE
    USER_INPUT=$(kdialog --inputbox "Найдено файлов: $file_count. Введите общее имя для папки:" "iphone_backup")
    # Если нажали "Отмена" — выходим
    [ -z "$USER_INPUT" ] && exit 0
    FOLDER_NAME="${USER_INPUT}"
else
    # Если файл всего один — берем его имя без расширения (автоматически)
    single_file=$(find . -maxdepth 1 -type f ! -name "$(basename "$0")" ! -name ".*" -printf "%f\n" -quit)
    FOLDER_NAME="${single_file%.*}"
fi

# Создаем папку
mkdir -p "$FOLDER_NAME"

# Генерируем красивый README.md ДО переноса файлов, чтобы знать их список
README_PATH="$FOLDER_NAME/README.md"
echo "# Набор файлов: $FOLDER_NAME" > "$README_PATH"
echo "Данные автоматически упакованы и отправлены с Fedora Linux (KDE Plasma 6)." >> "$README_PATH"
echo -e "\n### 📦 Список перенесенных файлов (Дата: $(date '+%Y-%m-%d %H:%M')):" >> "$README_PATH"

# Переносим файлы и одновременно пишем их имена в создаваемый README
for file in *; do
    [ -f "$file" ] || continue
    [ "$file" != "$(basename "$0")" ] || continue
    [ "$file" != "$FOLDER_NAME" ] || continue

    echo "* \`$file\`" >> "$README_PATH"
    mv "$file" "$FOLDER_NAME/"
done

echo "--> Папка '$FOLDER_NAME' с README.md сформирована локально."

# --- Блок работы с Git ---
git add .
git diff-index --quiet HEAD -- || git commit -m "Авто-пуш: файлы упакованы в папку $FOLDER_NAME (+ README.md)"

echo "--> Синхронизация с GitHub..."
git pull origin main --allow-unrelated-histories --no-rebase -X ours --quiet

echo "--> Отправка на GitHub..."
if git push; then
    kdialog --passivepopup "🚀 Всё готово! Папка '$FOLDER_NAME' и README успешно улетели на Git." 5
else
    echo "⚠️ Обычный push отклонен сервером. Пробиваем через Force..."
    git push -u origin main --force
    kdialog --passivepopup "🚀 Пробито силой! Проверяй репозиторий Bash-Fedora." 5
fi
