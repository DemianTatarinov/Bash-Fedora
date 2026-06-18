#!/bin/bash
set -euo pipefail

# Автоматически создаем уникальное имя папки по дате и времени
FOLDER_NAME="backup_$(date +%F_%H-%M)"

echo "--> Создается новая папка: $FOLDER_NAME"
mkdir -p "$FOLDER_NAME"

# Переносим все файлы текущего уровня внутрь этой папки (кроме скрипта и скрытых)
find . -maxdepth 1 -type f ! -name "$(basename "$0")" ! -name ".*" -exec mv {} "$FOLDER_NAME/" \;

# Авто-отправка в твой репозиторий Bash-Fedora
echo "--> Индексация файлов в Git..."
git add .

echo "--> Создание коммита..."
git commit -m "Авто-пуш: создана папка $FOLDER_NAME"

echo "--> Отправка на GitHub..."
git push

echo "🚀 Всё готово! Файлы в репозитории Bash-Fedora!"
