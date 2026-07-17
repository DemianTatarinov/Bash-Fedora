<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Инструкция: Universal GitHub Auto-Push CLI</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #2d3748;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            background-color: #f7fafc;
        }
        .container {
            background: #ffffff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        h1 {
            color: #1a365d;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        h2 {
            color: #2b6cb0;
            margin-top: 30px;
            border-bottom: 1px solid #edf2f7;
            padding-bottom: 8px;
        }
        h3 {
            color: #4a5568;
        }
        code {
            background-color: #edf2f7;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 0.9em;
        }
        pre {
            background-color: #2d3748;
            color: #f7fafc;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
        }
        pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
        }
        ul, ol {
            padding-left: 20px;
        }
        li {
            margin-bottom: 8px;
        }
        .info-box {
            background-color: #ebf8ff;
            border-left: 4px solid #3182ce;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 4px 4px 0;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 Universal GitHub Auto-Push CLI</h1>
    <p>Универсальный Bash-скрипт для автоматической и интерактивной выгрузки файлов и целых проектов из любой локальной папки в ваши публичные репозитории GitHub прямо из файлового менеджера или терминала Linux.</p>
    <p>Скрипт автоматически находит абсолютно новые или измененные файлы во всех вложенных директориях, сравнивает их по хэш-сумме и размеру с версией на GitHub (защита от дубликатов), запрашивает целевой репозиторий, предоставляет встроенный блокнот для редактирования <code>README.md</code> и наглядно показывает процесс работы через графический индикатор загрузки.</p>

    <h2>✨ Основные возможности</h2>
    <ul>
        <li><strong>Интерактивный выбор репозитория</strong>: Динамически загружает список всех ваших публичных репозиториев через официальный GitHub API.</li>
        <li><strong>Глубокий рекурсивный поиск любых файлов</strong>: Находит абсолютно все файлы во всех вложенных папках, автоматически игнорируя скрытые системные папки (например, <code>.git</code>), чтобы не засорять репозиторий.</li>
        <li><strong>Умная защита от дубликатов</strong>: Сравнивает не просто имена, а реальные контрольные суммы файлов (<code>git diff</code> по хэш-суммам). Если файл не изменялся, скрипт не будет тратить время на его отправку.</li>
        <li><strong>Встроенный блокнот для README.md</strong>: Скрипт сам открывает удобное текстовое поле <code>kdialog</code> с текущим содержимым вашей документации. Вы можете быстро отредактировать описание проекта прямо перед отправкой.</li>
        <li><strong>Наглядный прогресс-бар</strong>: Встроенная графическая шкала прогресса (<code>kdialog --progressbar</code>) отображает текущие шаги выполнения (клонирование, сверка, пуш) и позволяет безопасно отменить операцию в один клик.</li>
        <li><strong>Абсолютная безопасность</strong>: Скрипт гарантированно игнорирует сам себя при копировании и отправке, даже если вы случайно закинули его копию во вложенную папку с исходниками.</li>
    </ul>

    <h2>📋 Системные требования</h2>
    <p>Скрипт разработан для <strong>Fedora Linux</strong> (окружение KDE Plasma), но будет работать на любом дистрибутиве при наличии следующих пакетов:</p>
    <ol>
        <li><code>git</code> (контроль версий)</li>
        <li><code>kdialog</code> (для отрисовки графических окон)</li>
        <li><code>gh</code> (официальный консольный клиент GitHub CLI)</li>
    </ol>

    <h2>🛠️ Инсталляция и настройка</h2>
    <h3>Шаг 1: Установка зависимостей</h3>
    <p>Откройте терминал и выполните команду:</p>
    <pre><code>sudo dnf install git gh kdialog -y</code></pre>

    <h3>Шаг 2: Одноразовая авторизация в GitHub CLI</h3>
    <ol>
        <li>Запустите в терминале команду:
            <pre><code>gh auth login</code></pre>
        </li>
        <li>Ответьте на вопросы в терминале:
            <ul>
                <li>Where do you use GitHub? -> <strong>GitHub.com</strong></li>
                <li>What is your preferred protocol for Git operations? -> <strong>HTTPS</strong></li>
                <li>Authenticate Git with your GitHub credentials? -> <strong>Yes</strong></li>
                <li>How would you like to authenticate GitHub CLI? -> <strong>Login with a web browser</strong></li>
            </ul>
        </li>
        <li>Терминал покажет <strong>8-значный одноразовый код</strong>. Скопируйте его.</li>
        <li>Нажмите <em>Enter</em>. В браузере откроется страница авторизации GitHub. Вставьте туда код и нажмите <strong>Authorize github</strong>.</li>
    </ol>

    <h2>🚀 Инструкция по использованию</h2>
    <ol>
        <li>Поместите скрипт <code>Auto_Push_Github.sh</code> в любую рабочую папку.</li>
        <li>Сделайте его исполняемым (один раз):
            <pre><code>chmod +x Auto_Push_Github.sh</code></pre>
        </li>
        <li>Перенесите файлы вашего проекта или целые папки в ту же директорию, где лежит скрипт.</li>
        <li>Запустите скрипт через терминал: <code>./Auto_Push_Github.sh</code> или двойным кликом в файловом менеджере.</li>
    </ol>
    <div class="info-box">
        <strong>💡 Как проходит процесс:</strong> Выберите репозиторий в меню -> Скрипт проверит дубликаты -> Напишите описание в открывшемся блокноте -> Нажмите ОК, и изменения улетят на GitHub!
    </div>
</div>
</body>
</html>
