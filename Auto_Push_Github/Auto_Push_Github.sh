#!/bin/bash
set -uo pipefail

# Определяем абсолютный путь к запущенному скрипту, чтобы игнорировать только его
SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_NAME=$(basename "$SCRIPT_PATH")
# Папка, где лежит сам скрипт и новые .sh файлы
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Проверяем, установлен ли GitHub CLI
if ! command -v gh &> /dev/null; then
    kdialog --error "Для работы скрипта требуется GitHub CLI (gh).\nУстановите его командой: sudo dnf install gh"
    exit 1
fi

# Проверяем авторизацию в GitHub
if ! gh auth status &>/dev/null; then
    kdialog --error "Вы не авторизованы в GitHub CLI.\nЗапустите в терминале 'gh auth login' для авторизации."
    exit 1
fi

echo "=== Получение списка репозиториев ==="
# Получаем список публичных репозиториев
repo_list=$(gh repo list --limit 100 --visibility public --json nameWithOwner -q '.[] | .nameWithOwner')

if [ -z "$repo_list" ]; then
    kdialog --error "Не удалось найти публичные репозитории на вашем аккаунте."
    exit 1
fi

# Форматируем список для kdialog
dialog_args=()
while IFS= read -r repo; do
    dialog_args+=("$repo" "$repo")
done <<< "$repo_list"

# Выводим меню выбора репозитория
CHOSEN_REPO=$(kdialog --menu "Выберите публичный репозиторий для выгрузки:" "${dialog_args[@]}")

if [ -z "$CHOSEN_REPO" ]; then
    kdialog --error "Репозиторий не выбран. Выход."
    exit 1
fi

# Ищем .sh файлы во всех папках
sh_files=()
while IFS= read -r -d '' file; do
    # Получаем абсолютный путь к проверяемому файлу
    abs_file_path=$(readlink -f "$file")

    # Игнорируем строго сам запущенный скрипт по его физическому пути
    if [ "$abs_file_path" = "$SCRIPT_PATH" ]; then
        continue
    fi

    clean_file="${file#$SOURCE_DIR/}"
    sh_files+=("$clean_file")
done < <(find "$SOURCE_DIR" -type f -name "*.sh" -print0)

if [ ${#sh_files[@]} -eq 0 ]; then
    kdialog --error "В папке со скриптом нет .sh файлов для отправки."
    exit 0
fi

# Создаем временную папку для работы с репозиторием
TEMP_DIR=$(mktemp -d -t git-push-XXXXXX)
trap 'rm -rf "$TEMP_DIR"' EXIT # Гарантируем удаление временной папки при выходе

echo "--> Клонирование репозитория во временную папку..."
gh repo clone "$CHOSEN_REPO" "$TEMP_DIR" -- --depth 1 --quiet

# Переходим во временную папку репозитория
cd "$TEMP_DIR"

# Копируем новые файлы для проверки
for file in "${sh_files[@]}"; do
    mkdir -p "$(dirname "$file")"
    cp "$SOURCE_DIR/$file" "$file"
done

# Проверяем на дубликаты (содержимое, хэш, размер)
files_to_add=()
duplicates=()

for file in "${sh_files[@]}"; do
    if git show "HEAD:$file" &>/dev/null; then
        # Сравниваем содержимое
        if git diff --quiet "HEAD:$file" -- "$file"; then
            duplicates+=("$file")
        else
            files_to_add+=("$file")
        fi
    else
        files_to_add+=("$file")
    fi
done

# Показываем дубликаты, если они есть
if [ ${#duplicates[@]} -gt 0 ]; then
    dup_list=$(printf "* %s\n" "${duplicates[@]}")
    kdialog --msgbox "В репозитории $CHOSEN_REPO уже есть точно такие же файлы:\n\n$dup_list\n\nОни не будут отправлены повторно."
fi

if [ ${#files_to_add[@]} -eq 0 ]; then
    kdialog --passivepopup "Нет новых или измененных файлов для отправки." 5
    exit 0
fi

# Уведомление-пауза для редактирования README.md
kdialog --yesno "Файлы подготовлены. \n\nВы можете открыть и отредактировать README.md во временной папке:\n$TEMP_DIR/README.md\n\nКогда закончите, нажмите 'Да' для отправки изменений на GitHub." --title "Пауза для README"
if [ $? -ne 0 ]; then
    echo "Отмена операции."
    exit 0
fi

# Индексируем изменения
git add README.md 2>/dev/null || true
for file in "${files_to_add[@]}"; do
    git add "$file"
done

COMMIT_MSG="Авто-пуш: добавлены/обновлены скрипты Bash $(date '+%Y-%m-%d %H:%M')"

if git diff-index --quiet HEAD --; then
    kdialog --passivepopup "Изменений для коммита не обнаружено." 5
    exit 0
fi

git commit -m "$COMMIT_MSG"

echo "--> Синхронизация и отправка..."
git pull origin main --allow-unrelated-histories --no-rebase -X ours --quiet 2>/dev/null || true

if git push origin main; then
    kdialog --passivepopup "🚀 Всё готово! Изменения улетели в репозиторий $CHOSEN_REPO." 5
else
    echo "⚠️ Обычный push отклонен. Пробуем Force..."
    git push origin main --force
    kdialog --passivepopup "🚀 Пробито силой в $CHOSEN_REPO!" 5
fi
