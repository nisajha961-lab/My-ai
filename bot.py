import logging
import io
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
from PIL import Image

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Tokens (hardcoded) ---
TELEGRAM_TOKEN = "8864000200:AAETXZ9l0VUwtZw8RHKm35eP5ONR5Met5L0"
GEMINI_API_KEY = "AQ.Ab8RN6LVVLGdIB-Z1YtLPzEWlJ8rp2w0hR2CgWh9Ak9j8-zdBQ"
MY_TELEGRAM_ID = 8587752591

genai.configure(api_key=GEMINI_API_KEY)

DEFAULT_INSTRUCTION = (
    "You are Vansh AI, an advanced, witty assistant expert in Godot, "
    "3D modeling, and content strategy."
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
    user_id = update.effective_user.id
    bot_personalities[user_id] = DEFAULT_INSTRUCTION
    await update.message.reply_text("👋 नमस्ते बॉस! मैं Vansh AI हूँ। मैं तैयार हूँ!")


async def set_personality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    user_instruction = " ".join(context.args)
    if not user_instruction:
        await update.message.reply_text("निर्देश लिखें (उदा: /set_bot तुम एक कोडर हो)")
        return
    bot_personalities[update.effective_user.id] = user_instruction
    if update.effective_user.id in chat_sessions:
        del chat_sessions[update.effective_user.id]
    await update.message.reply_text(f"🎯 Vansh का मूड बदल गया: \"{user_instruction}\"")


async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    user_prompt = " ".join(context.args)
    if not user_prompt:
        await update.message.reply_text("🎨 प्रॉम्ट लिखें।")
        return
    await update.message.reply_text("⏳ Vansh इमेज बना रहा है...")
    try:
        model = genai.ImageGenerationModel("imagen-3.0-generate-002")
        result = model.generate_images(
            prompt=user_prompt, number_of_images=1, aspect_ratio="1:1"
        )
        for generated_image in result.generated_images:
            image = Image.open(io.BytesIO(generated_image.image.image_bytes))
            bio = io.BytesIO()
            bio.name = "vansh_image.png"
            image.save(bio, "PNG")
            bio.seek(0)
            await update.message.reply_photo(
                photo=bio, caption=f"✨ Vansh की कलाकृति: '{user_prompt}'"
            )
    except Exception as e:
        logger.error(f"Image Generation Error: {e}")
        await update.message.reply_text("❌ इमेज बनाने में एरर आया।")


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    if update.effective_user.id in chat_sessions:
        del chat_sessions[update.effective_user.id]
    await update.message.reply_text("🔄 याददाश्त साफ कर दी गई है।")


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
        await update.message.reply_text(response.text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Chat Error: {e}")
        await update.message.reply_text("❌ एरर! /clear करें।")


async def main_async() -> None:
    while True:
        try:
            logger.info("Initializing Telegram Bot (Async Worker Mode)...")
            app_bot = Application.builder().token(TELEGRAM_TOKEN).build()

            app_bot.add_handler(CommandHandler("start", start))
            app_bot.add_handler(CommandHandler("set_bot", set_personality))
            app_bot.add_handler(CommandHandler("generate_image", generate_image))
            app_bot.add_handler(CommandHandler("clear", clear_history))
            app_bot.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            )

            await app_bot.initialize()
            await app_bot.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            await app_bot.start()

            logger.info("Bot is successfully running and polling!")

            while app_bot.updater.running:
                await asyncio.sleep(1)

        except Exception as error:
            logger.error(f"Encountered connection or runtime error: {error}")
            logger.info("Attempting to restart bot in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
