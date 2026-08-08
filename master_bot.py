import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("8892594189:AAFPZ6J6l5xzD_gAuP2DzUKvqOWGxBJYzXI")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("हरा बटन (Success)", callback_data="green", style="success"),
            InlineKeyboardButton("नीला बटन (Primary)", callback_data="blue", style="primary"),
        ],
        [
            InlineKeyboardButton("लाल बटन (Danger)", callback_data="red", style="danger"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "बटन्स टेस्ट करो भाई। हरा, नीला और लाल कलर दिखना चाहिए।",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"तुमने दबाया: {query.data}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
