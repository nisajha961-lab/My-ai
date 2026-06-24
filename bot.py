import logging
import os
import io
import threading
import time
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from PIL import Image

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask('')

@app.route('/')
def home():
    return "Vansh AI Premium is 24/7 Alive!", 200

@app.route('/healthz')
def health_check():
    return "OK", 200

def run_flask():
    # रेलवे का पोर्ट उठाना और डिफ़ॉल्ट 8080 रखना
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Flask server on port {port}")
    # threaded=True करने से हेल्थ चेक कभी फेल नहीं होगा
    app.run(host='0.0.0.0', port=port, threaded=True)

# --- ऑटो-वेकअप अलार्म ---
def keep_alive_ping():
    time.sleep(30)
    while True:
        try:
            requests.get("http://127.0.0.1:8080/")
            logger.info("Ping sent successfully - Keeping Vansh AI awake!")
        except Exception as e:
            logger.error(f"Ping failed: {e}")
        time.sleep(180)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if TELEGRAM_TOKEN and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.error("API Keys missing in environment variables!")

DEFAULT_INSTRUCTION = "You are Vansh AI, an advanced, witty assistant expert in Godot, 3D modeling, and content strategy."

bot_personalities = {}
chat_sessions = {}
MY_TELEGRAM_ID = None 

def is_authorized(update: Update) -> bool:
    global MY_TELEGRAM_ID
    user_id = update.effective_user.id
    if MY_TELEGRAM_ID is None:
        MY_TELEGRAM_ID = user_id
        return True
    return user_id == MY_TELEGRAM_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_id = update.effective_user.id
    bot_personalities[user_id] = DEFAULT_INSTRUCTION
    await update.message.reply_text("👋 नमस्ते बॉस! मैं Vansh AI हूँ। मैं तैयार हूँ!")

async def set_personality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_instruction = " ".join(context.args)
    if not user_instruction:
        await update.message.reply_text("निर्देश लिखें (उदा: /set_bot तुम एक कोडर हो)")
        return
    bot_personalities[update.effective_user.id] = user_instruction
    if update.effective_user.id in chat_sessions: del chat_sessions[update.effective_user.id]
    await update.message.reply_text(f"🎯 Vansh का मूड बदल गया: \"{user_instruction}\"")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_prompt = " ".join(context.args)
    if not user_prompt:
        await update.message.reply_text("🎨 प्रॉम्ट लिखें।")
        return
    await update.message.reply_text("⏳ Vansh इमेज बना रहा है...")
    try:
        model = genai.ImageGenerationModel("imagen-3.0-generate-002")
        result = model.generate_images(prompt=user_prompt, number_of_images=1, aspect_ratio="1:1")
        for generated_image in result.generated_images:
            image = Image.open(io.BytesIO(generated_image.image.image_bytes))
            bio = io.BytesIO()
            bio.name = 'vansh_image.png'
            image.save(bio, 'PNG')
            bio.seek(0)
            await update.message.reply_photo(photo=bio, caption=f"✨ Vansh की कलाकृति: '{user_prompt}'")
    except Exception as e:
        await update.message.reply_text("❌ इमेज बनाने में एरर आया।")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    if update.effective_user.id in chat_sessions: del chat_sessions[update.effective_user.id]
    await update.message.reply_text("🔄 याददाश्त साफ कर दी गई है।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_id = update.effective_user.id
    user_message = update.message.text
    if user_id not in bot_personalities: bot_personalities[user_id] = DEFAULT_INSTRUCTION
    if user_id not in chat_sessions:
        model = genai.GenerativeModel(model_name="gemini-1.5-pro", system_instruction=bot_personalities[user_id])
        chat_sessions[user_id] = model.start_chat(history=[])
    try:
        response = chat_sessions[user_id].send_message(user_message)
        await update.message.reply_text(response.text, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ एरर! /clear करें।")

def main() -> None:
    # टेलीग्राम बोट शुरू होने से पहले ही Flask को चला देना ताकि रेलवे को तुरंत रिप्लाई मिले
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    
    app_bot = Application.builder().token(TELEGRAM_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("set_bot", set_personality))
    app_bot.add_handler(CommandHandler("generate_image", generate_image))
    app_bot.add_handler(CommandHandler("clear", clear_history))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Starting Telegram Bot Polling...")
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if TELEGRAM_TOKEN and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.error("API Keys missing in environment variables!")

DEFAULT_INSTRUCTION = "You are Vansh AI, an advanced, witty assistant expert in Godot, 3D modeling, and content strategy."

bot_personalities = {}
chat_sessions = {}
MY_TELEGRAM_ID = None 

def is_authorized(update: Update) -> bool:
    global MY_TELEGRAM_ID
    user_id = update.effective_user.id
    if MY_TELEGRAM_ID is None:
        MY_TELEGRAM_ID = user_id
        return True
    return user_id == MY_TELEGRAM_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_id = update.effective_user.id
    bot_personalities[user_id] = DEFAULT_INSTRUCTION
    await update.message.reply_text("👋 नमस्ते बॉस! मैं Vansh AI हूँ। मैं तैयार हूँ!")

async def set_personality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_instruction = " ".join(context.args)
    if not user_instruction:
        await update.message.reply_text("निर्देश लिखें (उदा: /set_bot तुम एक कोडर हो)")
        return
    bot_personalities[update.effective_user.id] = user_instruction
    if update.effective_user.id in chat_sessions: del chat_sessions[update.effective_user.id]
    await update.message.reply_text(f"🎯 Vansh का मूड बदल गया: \"{user_instruction}\"")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_prompt = " ".join(context.args)
    if not user_prompt:
        await update.message.reply_text("🎨 प्रॉम्ट लिखें।")
        return
    await update.message.reply_text("⏳ Vansh इमेज बना रहा है...")
    try:
        model = genai.ImageGenerationModel("imagen-3.0-generate-002")
        result = model.generate_images(prompt=user_prompt, number_of_images=1, aspect_ratio="1:1")
        time.sleep(180) # हर 3 मिनट (180 सेकंड) में पिंग करेगा

TELEGRAM_TOKEN = os.getenv("8289048381:AAEK1nlS30WcwMquRzQm9nOZ9bHWuXqtzCk
")
GEMINI_API_KEY = os.getenv("AQ.Ab8RN6LVVLGdIB-Z1YtLPzEWlJ8rp2w0hR2CgWh9Ak9j8-zdBQ")

if TELEGRAM_TOKEN and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.error("API Keys missing in environment variables!")

DEFAULT_INSTRUCTION = "You are Vansh AI, an advanced, witty assistant expert in Godot, 3D modeling, and content strategy."

bot_personalities = {}
chat_sessions = {}
MY_TELEGRAM_ID = None 

def is_authorized(update: Update) -> bool:
    global MY_TELEGRAM_ID
    user_id = update.effective_user.id
    if MY_TELEGRAM_ID is None:
        MY_TELEGRAM_ID = user_id
        return True
    return user_id == MY_TELEGRAM_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_id = update.effective_user.id
    bot_personalities[user_id] = DEFAULT_INSTRUCTION
    await update.message.reply_text("👋 नमस्ते बॉस! मैं Vansh AI हूँ। मैं तैयार हूँ!")

async def set_personality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_instruction = " ".join(context.args)
    if not user_instruction:
        await update.message.reply_text("निर्देश लिखें (उदा: /set_bot तुम एक कोडर हो)")
        return
    bot_personalities[update.effective_user.id] = user_instruction
    if update.effective_user.id in chat_sessions: del chat_sessions[update.effective_user.id]
    await update.message.reply_text(f"🎯 Vansh का मूड बदल गया: \"{user_instruction}\"")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_prompt = " ".join(context.args)
    if not user_prompt:
        await update.message.reply_text("🎨 प्रॉम्ट लिखें।")
        return
    await update.message.reply_text("⏳ Vansh इमेज बना रहा है...")
    try:
        model = genai.ImageGenerationModel("imagen-3.0-generate-002")
        result = model.generate_images(prompt=user_prompt, number_of_images=1, aspect_ratio="1:1")
        for generated_image in result.generated_images:
            image = Image.open(io.BytesIO(generated_image.image.image_bytes))
            bio = io.BytesIO()
            bio.name = 'vansh_image.png'
            image.save(bio, 'PNG')
            bio.seek(0)
            await update.message.reply_photo(photo=bio, caption=f"✨ Vansh की कलाकृति: '{user_prompt}'")
    except Exception as e:
        await update.message.reply_text("❌ इमेज बनाने में एरर आया।")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    if update.effective_user.id in chat_sessions: del chat_sessions[update.effective_user.id]
    await update.message.reply_text("🔄 याददाश्त साफ कर दी गई है।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_id = update.effective_user.id
    user_message = update.message.text
    if user_id not in bot_personalities: bot_personalities[user_id] = DEFAULT_INSTRUCTION
    if user_id not in chat_sessions:
        model = genai.GenerativeModel(model_name="gemini-1.5-pro", system_instruction=bot_personalities[user_id])
        chat_sessions[user_id] = model.start_chat(history=[])
    try:
        response = chat_sessions[user_id].send_message(user_message)
        await update.message.reply_text(response.text, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ एरर! /clear करें।")

def main() -> None:
    threading.Thread(target=run_flask, daemon=True).start()
    # ऑटो-वेकअप थ्रेड को बैकग्राउंड में शुरू करना
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    
    app_bot = Application.builder().token(TELEGRAM_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("set_bot", set_personality))
    app_bot.add_handler(CommandHandler("generate_image", generate_image))
    app_bot.add_handler(CommandHandler("clear", clear_history))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()        time.sleep(180) # हर 3 मिनट (180 सेकंड) में पिंग करेगा

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if TELEGRAM_TOKEN and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.error("API Keys missing in environment variables!")

DEFAULT_INSTRUCTION = "You are Vansh AI, an advanced, witty assistant expert in Godot, 3D modeling, and content strategy."

bot_personalities = {}
chat_sessions = {}
MY_TELEGRAM_ID = None 

def is_authorized(update: Update) -> bool:
    global MY_TELEGRAM_ID
    user_id = update.effective_user.id
    if MY_TELEGRAM_ID is None:
        MY_TELEGRAM_ID = user_id
        return True
    return user_id == MY_TELEGRAM_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_id = update.effective_user.id
    bot_personalities[user_id] = DEFAULT_INSTRUCTION
    await update.message.reply_text("👋 नमस्ते बॉस! मैं Vansh AI हूँ। मैं तैयार हूँ!")

async def set_personality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_instruction = " ".join(context.args)
    if not user_instruction:
        await update.message.reply_text("निर्देश लिखें (उदा: /set_bot तुम एक कोडर हो)")
        return
    bot_personalities[update.effective_user.id] = user_instruction
    if update.effective_user.id in chat_sessions: del chat_sessions[update.effective_user.id]
    await update.message.reply_text(f"🎯 Vansh का मूड बदल गया: \"{user_instruction}\"")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_prompt = " ".join(context.args)
    if not user_prompt:
        await update.message.reply_text("🎨 प्रॉम्ट लिखें।")
        return
    await update.message.reply_text("⏳ Vansh इमेज बना रहा है...")
    try:
        model = genai.ImageGenerationModel("imagen-3.0-generate-002")
        result = model.generate_images(prompt=user_prompt, number_of_images=1, aspect_ratio="1:1")
        for generated_image in result.generated_images:
            image = Image.open(io.BytesIO(generated_image.image.image_bytes))
            bio = io.BytesIO()
            bio.name = 'vansh_image.png'
            image.save(bio, 'PNG')
            bio.seek(0)
            await update.message.reply_photo(photo=bio, caption=f"✨ Vansh की कलाकृति: '{user_prompt}'")
    except Exception as e:
        await update.message.reply_text("❌ इमेज बनाने में एरर आया।")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    if update.effective_user.id in chat_sessions: del chat_sessions[update.effective_user.id]
    await update.message.reply_text("🔄 याददाश्त साफ कर दी गई है।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update): return
    user_id = update.effective_user.id
    user_message = update.message.text
    if user_id not in bot_personalities: bot_personalities[user_id] = DEFAULT_INSTRUCTION
    if user_id not in chat_sessions:
        model = genai.GenerativeModel(model_name="gemini-1.5-pro", system_instruction=bot_personalities[user_id])
        chat_sessions[user_id] = model.start_chat(history=[])
    try:
        response = chat_sessions[user_id].send_message(user_message)
        await update.message.reply_text(response.text, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ एरर! /clear करें।")

def main() -> None:
    threading.Thread(target=run_flask, daemon=True).start()
    # ऑटो-वेकअप थ्रेड को बैकग्राउंड में शुरू करना
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    
    app_bot = Application.builder().token(TELEGRAM_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("set_bot", set_personality))
    app_bot.add_handler(CommandHandler("generate_image", generate_image))
    app_bot.add_handler(CommandHandler("clear", clear_history))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
