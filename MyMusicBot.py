from telegram import Update, Bot, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Налаштування логування
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Налаштування
TOKEN = os.getenv("TELEGRAM_TOKEN", "8185836155:AAG9-wUl7nYqkVPlNgcjmxL3Zs4akSEGiI0")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1001358165457")
DEFAULT_LINK_TEXT = " <a href='https://t.me/blastmusics'>BlastMusic</a>"

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Отримано команду /start від {update.message.chat_id}")
    if 'link_text' not in context.bot_data:
        context.user_data['awaiting_text'] = True
        await update.message.reply_text(
            "Введіть текст і URL для постів (наприклад: Слухати на Spotify https://spotify.com/track123):"
        )
    else:
        current_text = context.bot_data.get('link_text', DEFAULT_LINK_TEXT)
        await update.message.reply_text(
            f"Поточний текст: {current_text}\n"
            "Надішли аудіофайл, і я опублікую його в канал.\n"
            "Щоб змінити текст, використовуй: /settext [текст] [URL]",
            parse_mode=ParseMode.HTML
        )

# Команда /settext
async def set_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Отримано команду /settext від {update.message.chat_id}")
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Введіть текст і URL, наприклад: /settext Слухати на YouTube https://youtube.com/link"
        )
        return
    url = args[-1]
    text = " ".join(args[:-1])
    link_text = f"<a href='{url}'>{text}</a>"
    context.bot_data['link_text'] = link_text
    context.user_data['awaiting_text'] = False
    await update.message.reply_text(
        f"Текст для постів оновлено: {link_text}",
        parse_mode=ParseMode.HTML
    )

# Обробка текстових повідомлень
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_text', False):
        logger.info(f"Отримано текст від {update.message.chat_id}")
        text_input = update.message.text.split()
        if len(text_input) < 2:
            await update.message.reply_text(
                "Введіть текст і URL, наприклад: Слухати на Spotify https://spotify.com/track123"
            )
            return
        url = text_input[-1]
        text = " ".join(text_input[:-1])
        link_text = f"<a href='{url}'>{text}</a>"
        context.bot_data['link_text'] = link_text
        context.user_data['awaiting_text'] = False
        await update.message.reply_text(
            f"Текст для постів встановлено: {link_text}\n"
            "Тепер надсилай аудіофайл!",
            parse_mode=ParseMode.HTML
        )

# Обробка аудіофайлів
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Отримано аудіофайл від {update.message.chat_id}")
    audio = update.message.audio
    caption = context.bot_data.get('link_text', DEFAULT_LINK_TEXT)
    try:
        await context.bot.send_audio(
            chat_id=CHANNEL_ID,
            audio=audio.file_id,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        await update.message.reply_text("Музика опублікована в канал!")
    except Exception as e:
        logger.error(f"Помилка при публікації: {str(e)}")
        await update.message.reply_text(f"Помилка при публікації: {str(e)}")

# Фейковий HTTP-сервер для Render Web Service
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_http_server():
    port = int(os.getenv("PORT", 8080))  # Render передає порт через змінну PORT
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    logger.info(f"Запуск HTTP-сервера на порту {port}...")
    httpd.serve_forever()

# Telegram-бот
def run_telegram_bot():
    logger.info("Запуск Telegram-бота...")
    try:
        app = Application.builder().token(TOKEN).build()
        bot = Bot(TOKEN)
        bot.set_my_commands([
            BotCommand("start", "Запустити бота і задати текст із посиланням"),
            BotCommand("settext", "Змінити текст і URL для постів")
        ])
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("settext", set_text))
        app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Помилка запуску Telegram-бота: {str(e)}")

# Головна функція
def main():
    # Запускаємо HTTP-сервер у окремому потоці
    http_thread = threading.Thread(target=run_http_server)
    http_thread.daemon = True  # Завершується, коли основна програма завершується
    http_thread.start()

    # Запускаємо Telegram-бот у головному потоці
    run_telegram_bot()

if __name__ == "__main__":
    main()