import os
import logging
from dotenv import load_dotenv
from flask import Flask
import threading

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

import google.generativeai as genai

# --------------------------
# FLASK SERVER (Render keep-alive)
# --------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ WriteRight Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


# --------------------------
# LOGGING CONFIG
# --------------------------
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --------------------------
# ENVIRONMENT VARIABLES
# --------------------------
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not GOOGLE_API_KEY or not TELEGRAM_TOKEN:
    raise ValueError("Missing GOOGLE_API_KEY or TELEGRAM_TOKEN in .env")

# Gemini configuration
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")


# ================================================================
# COMMAND HANDLERS
# ================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "check"
    await update.message.reply_text(
        "👋 Hello! I'm WriteRight.\n\n"
        "Send me any sentence and I'll analyze it.\n"
        "Use /help to see all available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📘 *WriteRight Commands*\n\n"
        "/start – Start the bot and show welcome message\n"
        "/help – Show full command list\n"
        "/check – Analyze grammar & correctness\n"
        "/rewrite – Rewrite your text clearly & naturally\n"
        "/explain – Explain grammar rules in your sentence\n"
        "/improve – Suggest improvements to make writing better\n"
        "/clear – Reset conversation\n\n"
        "Just send any text after selecting a mode."
    )
    await update.message.reply_text(help_text)


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "check"
    await update.message.reply_text("📝 Mode set to *Grammar Check*. Send the text you want me to analyze.")


async def rewrite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "rewrite"
    await update.message.reply_text("✍️ Mode set to *Rewrite*. Send the text you want rewritten.")


async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "explain"
    await update.message.reply_text("📘 Mode set to *Grammar Explain*. Send the sentence you want explained.")


async def improve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "improve"
    await update.message.reply_text("💡 Mode set to *Improve Writing*. Send the text you want improved.")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "check"
    await update.message.reply_text("🔄 Conversation reset. Default mode: Grammar Check.")


# ================================================================
# MAIN TEXT HANDLER (Gemini Processing)
# ================================================================
async def analyze_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
    mode = context.user_data.get("mode", "check")

    status_msg = await update.message.reply_text("Analyzing… 🔍")

    # Select task by mode
    if mode == "check":
        task = "Analyze grammar and correctness."
    elif mode == "rewrite":
        task = "Rewrite this text clearly and naturally."
    elif mode == "explain":
        task = "Explain the grammar rules used in this sentence."
    elif mode == "improve":
        task = "Suggest improvements to make this writing better."
    else:
        task = "Analyze grammar and correctness."

    # Prompt for Gemini
    prompt = f"""
You are WriteRight, an English writing tutor.

Task: {task}

Provide results using the following structure:

📝 REVIEW:
[Correct / Partially Correct / Incorrect]

🔍 ERRORS FOUND:
• Type: [type]
• Original: [text]
• Correction: [text]
• Rule: [rule]
• Explanation: [explanation]

💡 SUGGESTIONS:
• [Suggestion 1]
• [Suggestion 2]

✅ CORRECTED TEXT:
[text]

User text: {user_text}
"""

    try:
        response = model.generate_content(prompt)
        output = response.text.strip().replace("```", "")

        # Telegram length safety
        if len(output) <= 4000:
            await status_msg.edit_text(output)
        else:
            await status_msg.delete()
            for i in range(0, len(output), 4000):
                await update.message.reply_text(output[i:i+4000])

    except Exception as e:
        logger.error(f"ERROR: {e}")
        await status_msg.edit_text("⚠️ Something went wrong. Please try again.")



def main():
    # Start Flask server for Render uptime
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Telegram bot
    tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register commands
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("help", help_command))
    tg_app.add_handler(CommandHandler("check", check_command))
    tg_app.add_handler(CommandHandler("rewrite", rewrite_command))
    tg_app.add_handler(CommandHandler("explain", explain_command))
    tg_app.add_handler(CommandHandler("improve", improve_command))
    tg_app.add_handler(CommandHandler("clear", clear_command))

    # Text handler
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_text))

    logger.info("🚀 WriteRight Bot is running...")
    tg_app.run_polling()


if __name__ == "__main__":
    main()
