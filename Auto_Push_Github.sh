#!/bin/bash
set -euo pipefail

# 1. Показываем красивое окно KDE для ввода имени папки
USER_FOLDER=$(kdialog --inputbox "Введите имя папки для сохранения в Git:" "iphone_backup")

# Если нажали "Отмена" или закрыли окно — выходим
[ -z "$USER_FOLDER" ] && exit 0

# Имя папки (если стерли всё, будет дата)
FOLDER_NAME="${USER_FOLDER:-"archive_$(date +%F)"}"

# 2. Создаем папку
mkdir -p "$FOLDER_NAME"

# 3. Переносим файлы (кроме самого скрипта и скрытых)
find . -maxdepth 1 -type f ! -name "$(basename "$0")" ! -name ".*" -exec mv {} "$FOLDER_NAME/" \;

# 4. Отправляем в Git
git add .
git commit -m "Файлы перемещены в папку: $FOLDER_NAME"
git push

# 5. Уведомление об успешном завершении
kdialog --passivepopup "🚀 Все файлы успешно отправлены в Git-папку '$FOLDER_NAME'!" 5
