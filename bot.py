# bot.py
import os
import logging
from dotenv import load_dotenv

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
# LOGGING (All errors here)
# --------------------------
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in .env")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")


# --------------------------
# START COMMAND
# --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a sentence.")


# --------------------------
# ANALYZE TEXT
# --------------------------
async def analyze_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
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
- If multiple errors exist, repeat the "🔍 ERRORS FOUND" section for each.
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
                await update.message.reply_text(output_text[i:i + MAX_LEN])

    except Exception as e:
        # Log error only in terminal
        logger.error("Error while processing text:", exc_info=True)

        # User-friendly message
        await status_msg.edit_text("⚠️ Sorry, something went wrong. Please try again.")
        

# --------------------------
# MAIN
# --------------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_text))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
