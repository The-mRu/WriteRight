# bot.py
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
# FUNCTION: Wrap corrected text in Telegram code block
# ================================================================
def wrap_corrected_text_block(output: str) -> str:
    """
    Detects the '✅ CORRECTED TEXT:' section and wraps ONLY the corrected text
    inside a Telegram Markdown code block (```), enabling a copy button.
    """
    marker = "✅ CORRECTED TEXT:"
    if marker not in output:
        return output

    parts = output.split(marker, 1)
    before = parts[0]
    after = parts[1].lstrip()

    # Identify corrected text (the first line after the marker)
    lines = after.split("\n", 1)
    corrected_line = lines[0].strip()

    # Build a wrapped version
    wrapped = f"```\n{corrected_line}\n```"

    # Replace only the first corrected line
    if len(lines) > 1:
        new_after = wrapped + "\n" + lines[1]
    else:
        new_after = wrapped

    return before + marker + "\n" + new_after


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
    await update.message.reply_text(
        "📘 *WriteRight Commands*\n\n"
        "/start – Show welcome message\n"
        "/help – List all commands\n"
        "/check – Analyze grammar\n"
        "/rewrite – Rewrite your text\n"
        "/explain – Explain grammar rules\n"
        "/improve – Improve clarity and style\n"
        "/clear – Reset conversation\n"
    )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "check"
    await update.message.reply_text("📝 Mode set to *Grammar Check*. Send the text you want analyzed.")


async def rewrite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "rewrite"
    await update.message.reply_text("✍️ Mode set to *Rewrite*. Send the text you want rewritten.")


async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "explain"
    await update.message.reply_text("📘 Mode set to *Explain*. Send the sentence you want explained.")


async def improve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "improve"
    await update.message.reply_text("💡 Mode set to *Improve*. Send the text you want enhanced.")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "check"
    await update.message.reply_text("🔄 Conversation reset. Default mode: Grammar Check.")


# ================================================================
# MAIN GRAMMAR PROCESSING
# ================================================================
async def analyze_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
    mode = context.user_data.get("mode", "check")

    status_msg = await update.message.reply_text("Analyzing… 🔍")

    # Task selection
    if mode == "check":
        task = "Analyze grammar and correctness."
    elif mode == "rewrite":
        task = "Rewrite this text clearly and naturally."
    elif mode == "explain":
        task = "Explain grammar rules."
    elif mode == "improve":
        task = "Suggest improvements."
    else:
        task = "Analyze grammar."

    # Build prompt
    prompt = f"""
You are WriteRight, an English writing tutor.

Task: {task}

Follow the structure below:

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
        output = response.text.strip()

        # Clean any stray backticks
        output = output.replace("```", "")

        # Wrap ONLY corrected text
        output = wrap_corrected_text_block(output)

        # Send safely
        if len(output) <= 4000:
            await status_msg.edit_text(output, parse_mode="Markdown")
        else:
            await status_msg.delete()
            for i in range(0, len(output), 4000):
                await update.message.reply_text(output[i:i+4000], parse_mode="Markdown")

    except Exception as e:
        logger.error(f"ERROR: {e}")
        await status_msg.edit_text("⚠️ Something went wrong. Please try again.")


# ================================================================
# MAIN FUNCTION
# ================================================================
def main():
    # Start Flask keep-alive
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start Telegram bot
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
