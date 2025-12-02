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
# LOGGING (errors visible only in terminal)
# --------------------------
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load env variables (works locally, ignored on Railway)
load_dotenv()
# debug presence only — safe: does NOT print secret values
present = {k: (k in os.environ) for k in ("GOOGLE_API_KEY", "TELEGRAM_TOKEN")}
logger.info("Env presence check: %s", present)


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --------------------------
# Validate environment variables
# --------------------------
if not GOOGLE_API_KEY or not TELEGRAM_TOKEN:
    raise ValueError(
        "Missing environment variables. "
        "Make sure GOOGLE_API_KEY and TELEGRAM_TOKEN are set in Railway → Variables."
    )

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")


# --------------------------
# /start command
# --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a sentence to analyze.")


# --------------------------
# Grammar analysis handler
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
        logger.error("Error while processing text:", exc_info=True)
        await status_msg.edit_text("⚠️ Sorry, something went wrong. Please try again.")


# --------------------------
# Main entry point
# --------------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_text))

    print("✅ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
