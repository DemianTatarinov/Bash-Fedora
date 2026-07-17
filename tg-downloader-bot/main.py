#!/usr/bin/env python3
"""
Telegram Media Saver Bot
Compatible with Hugging Face Spaces (Docker), iOS players (H.264/AAC),
and Telegram Forum Topics (message_thread_id support).
"""

import os
import re
import asyncio
import logging
import uuid
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramAPIError
from aiohttp import web
import yt_dlp

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MediaSaverBot")

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Воссоздаем cookies.txt из секретов Hugging Face, если его нет на диске
COOKIES_FILE = "cookies.txt"
cookies_content = os.getenv("COOKIES_CONTENT")

if cookies_content:
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        f.write(cookies_content)
    logger.info("Created cookies.txt from Hugging Face Secret.")

has_cookies = os.path.exists(COOKIES_FILE)


def download_media_sync(url: str, output_path: str) -> dict:
    """
    Скачивание видео и принудительное транскодирование в совместимый с iOS формат.
    """
    ydl_opts = {
        'format': 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        # Жестко пережимаем видео в H.264 YUV420p и звук в AAC для стабильного воспроизведения на iPhone
        'postprocessor_args': {
            'video_convertor': ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level:v', '4.0', '-c:a', 'aac'],
            'merger': ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level:v', '4.0', '-c:a', 'aac']
        },
    }

    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE

    logger.info(f"Starting download sync with yt-dlp for URL: {url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        actual_filename = base + ".mp4"

        if not os.path.exists(actual_filename) and os.path.exists(filename):
            actual_filename = filename

        if not os.path.exists(actual_filename):
            raise FileNotFoundError("Downloaded file could not be located on disk.")

        description = info.get('description') or info.get('title') or ""
        if len(description) > 1000:
            description = description[:997] + "..."

        width = info.get('width')
        height = info.get('height')
        duration = info.get('duration')

        return {
            'filepath': actual_filename,
            'caption': description,
            'width': int(width) if width else None,
            'height': int(height) if height else None,
            'duration': int(duration) if duration else None
        }


async def download_media(url: str) -> dict:
    unique_id = str(uuid.uuid4())
    output_tmpl = f"temp_video_{unique_id}.%(ext)s"
    return await asyncio.to_thread(download_media_sync, url, output_tmpl)


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Регулярка для отслеживания ссылок Instagram и YouTube
LINK_PATTERN = re.compile(
    r'(https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/|v/|embed/|shared\?ci=)|youtu\.be/|instagram\.com/(?:p|reel|reels|tv)/)[^\s]+)',
    re.IGNORECASE
)


async def send_and_delete_error(chat_id: int, text: str, delay: int = 15, message_thread_id: int = None):
    """
    Отправка сообщения об ошибке с автоматическим удалением.
    """
    try:
        err_msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            message_thread_id=message_thread_id
        )
        await asyncio.sleep(delay)
        try:
            await bot.delete_message(chat_id=chat_id, message_id=err_msg.message_id)
        except TelegramAPIError as e:
            logger.warning(f"Failed to delete temporary error message: {e}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send error notification message: {e}")


@dp.channel_post(F.text)
@dp.message(F.text)
async def handle_links(message: types.Message):
    """
    Основной перехватчик сообщений. Поддерживает отправку в конкретные темы (Topics).
    """
    text = message.text or ""
    match = LINK_PATTERN.search(text)
    if not match:
        return

    url = match.group(1)
    chat_id = message.chat.id
    message_id = message.message_id

    # Автоматически считываем ID темы (если это группа с темами, иначе будет None)
    message_thread_id = message.message_thread_id

    logger.info(f"Intercepted URL in chat {chat_id} (Thread: {message_thread_id}): {url}")

    status_msg = None
    try:
        status_msg = await bot.send_message(
            chat_id=chat_id,
            text="⏳ *Processing media, please wait...*",
            parse_mode=ParseMode.MARKDOWN,
            message_thread_id=message_thread_id
        )
    except TelegramAPIError as e:
        logger.warning(f"Could not send processing message: {e}")

    filepath = None
    try:
        meta = await download_media(url)
        filepath = meta['filepath']
        caption = meta['caption']
        width = meta['width']
        height = meta['height']
        duration = meta['duration']

        logger.info(f"Successfully downloaded: {filepath}")

        # Отправляем видео в ту же тему, откуда пришла ссылка
        video_file = FSInputFile(filepath)
        await bot.send_video(
            chat_id=chat_id,
            video=video_file,
            caption=caption,
            width=width,
            height=height,
            duration=duration,
            supports_streaming=True,
            message_thread_id=message_thread_id
        )
        logger.info(f"Successfully uploaded video {filepath} to chat {chat_id}")

        # Удаляем исходную ссылку
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramAPIError as e:
            logger.warning(f"Could not delete original message with link: {e}.")

    except Exception as exc:
        logger.exception(f"Error handling media URL {url}: {exc}")
        asyncio.create_task(
            send_and_delete_error(
                chat_id=chat_id,
                text=f"❌ *Failed to process link:* {url}\n_The error was logged._",
                delay=15,
                message_thread_id=message_thread_id
            )
        )
    finally:
        # Чистим временный статус загрузки
        if status_msg:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
            except TelegramAPIError:
                pass

        # Удаляем локальный файл, чтобы не забивать диск сервера
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Cleaned up temporary file: {filepath}")
            except OSError as e:
                logger.error(f"Error deleting temporary file {filepath}: {e}")


# Веб-сервер для удержания бота в активном состоянии (совместим с Render и Hugging Face)
async def start_dummy_web_server():
    app = web.Application()
    async def index(request):
        return web.Response(text="MediaSaverBot is alive and polling!")
    app.router.add_get('/', index)
    runner = web.AppRunner(app)
    await runner.setup()

    # Читаем порт из переменной окружения Render, по умолчанию ставим 10000
    port = int(os.getenv("PORT", 10000))

    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Dummy web server started on port {port}")


async def main():
    if os.getenv("BOT_TOKEN") is None:
        logger.critical("BOT_TOKEN is not configured!")
        return

    # Запуск сервера-пустышки
    await start_dummy_web_server()

    logger.info("Starting Telegram Bot long polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
