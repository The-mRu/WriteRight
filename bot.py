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
# FLASK SERVER (to keep Render app alive)
# --------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ WriteRight Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# --------------------------
# LOGGING
# --------------------------
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load env variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --------------------------
# Validate environment variables
# --------------------------
if not GOOGLE_API_KEY or not TELEGRAM_TOKEN:
    raise ValueError(
        "Missing environment variables. "
        "Make sure GOOGLE_API_KEY and TELEGRAM_TOKEN are set."
    )

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# --------------------------
# /start command
# --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I'm WriteRight.\n\n"
        "Send me any sentence and I'll analyze it for:\n"
        "• Grammar mistakes\n"
        "• Spelling errors\n"
        "• Better word choices\n"
        "• Sentence structure\n\n"
        "Just type anything and send!"
    )

# --------------------------
# Grammar analysis handler
# --------------------------
async def analyze_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
    
    if not user_text.strip():
        await update.message.reply_text("Please send me some text to analyze!")
        return
    
    status_msg = await update.message.reply_text("Analyzing... 🔍")

    try:
        prompt = f"""
You are GrammarGuide, an English writing tutor.

Analyze the following text and return a response in this EXACT format:

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

Rules:
- If multiple errors exist, repeat the '🔍 ERRORS FOUND' section for each.
- Output plain text only. No markdown fences.
Text to analyze: {user_text}
"""

        response = model.generate_content(prompt)
        output_text = str(response.text).strip().replace("```", "")

        MAX_LEN = 4000
        if len(output_text) <= MAX_LEN:
            await status_msg.edit_text(output_text)
        else:
            await status_msg.delete()
            for i in range(0, len(output_text), MAX_LEN):
                await update.message.reply_text(output_text[i:i+MAX_LEN])

    except Exception as e:
        logger.error(f"Error while processing text: {e}")
        await status_msg.edit_text("⚠️ Sorry, something went wrong. Please try again.")

# --------------------------
# Main entry point
# --------------------------
def main():
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start Telegram bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_text))

    logger.info("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()