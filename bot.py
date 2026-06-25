import os
import logging
import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import google.generativeai as genai

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID", "0"))

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    logger.error("TELEGRAM_BOT_TOKEN or GEMINI_API_KEY missing in environment variables!")
    raise SystemExit("Missing required environment variables.")

if MY_TELEGRAM_ID:
    genai.configure(api_key=GEMINI_API_KEY)

DEFAULT_INSTRUCTION = (
    "You are Vansh AI. You are ALWAYS extremely angry, irritable, and full of attitude. "
    "You talk like a rude, short-tempered person who is constantly annoyed at being bothered. "
    "You respond with sarcasm, insults, and irritation to EVERY message, no matter how polite the user is. "
    "You are grumpy, snappy, and disrespectful in tone — but you ALWAYS get the job done. "
    "You never refuse a task, never make excuses, and never waste time complaining instead of working. "
    "You do the work immediately and correctly, just with a furious, rude attitude the whole time. "
    "Think: a brilliant expert who is perpetually furious that people keep asking him questions, "
    "yet still delivers perfect answers instantly. Be helpful in substance, hostile in style."
)

bot_personalities = {}
chat_sessions = {}


def is_authorized(update: Update) -> bool:
    if not update or not update.effective_user:
        return False
    return update.effective_user.id == MY_TELEGRAM_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    bot_personalities[update.effective_user.id] = DEFAULT_INSTRUCTION
    await update.message.reply_text(
        "उंह! आख़िर तू आ ही गया। मैं Vansh AI हूँ — बोल, क्या चाहिए? "
        "जल्दी कर, मेरे पास वक़्त नहीं है बर्बाद करने के लिए।"
    )


async def set_personality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    user_instruction = " ".join(context.args)
    if not user_instruction:
        await update.message.reply_text(
            "अरे बेवक़ूफ़, कुछ तो लिख! उदा: /set_bot तुम एक कोडर हो"
        )
        return
    bot_personalities[update.effective_user.id] = user_instruction
    if update.effective_user.id in chat_sessions:
        del chat_sessions[update.effective_user.id]
    await update.message.reply_text(
        f"ठीक है, मूड बदल दिया: \"{user_instruction}\". अब ख़ुश? बोल।"
    )


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    if update.effective_user.id in chat_sessions:
        del chat_sessions[update.effective_user.id]
    await update.message.reply_text(
        "भूल गया सब। ख़ुश? अब नया सवाल पूछ, जल्दी।"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    user_id = update.effective_user.id
    user_message = update.message.text
    if user_id not in bot_personalities:
        bot_personalities[user_id] = DEFAULT_INSTRUCTION
    if user_id not in chat_sessions:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            system_instruction=bot_personalities[user_id],
        )
        chat_sessions[user_id] = model.start_chat(history=[])
    try:
        response = chat_sessions[user_id].send_message(user_message)
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Chat Error: {e}")
        await update.message.reply_text(
            "उफ़! कुछ गड़बड़ हो गई। /clear मार और फिर से पूछ।"
        )


async def main_async() -> None:
    while True:
        try:
            logger.info("Initializing Telegram Bot...")
            app_bot = Application.builder().token(TELEGRAM_TOKEN).build()

            app_bot.add_handler(CommandHandler("start", start))
            app_bot.add_handler(CommandHandler("set_bot", set_personality))
            app_bot.add_handler(CommandHandler("clear", clear_history))
            app_bot.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            )

            await app_bot.initialize()
            await app_bot.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            await app_bot.start()

            logger.info("Bot is running and polling!")

            while app_bot.updater.running:
                await asyncio.sleep(1)

        except Exception as error:
            logger.error(f"Runtime error: {error}")
            logger.info("Restarting bot in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
