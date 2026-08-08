import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = "8892594189:AAFPZ6J6l5xzD_gAuP2DzUKvqOWGxBJYzXI"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("हरा बटन", callback_data="green", style="success"),
            InlineKeyboardButton("नीला बटन", callback_data="blue", style="primary"),
        ],
        [
            InlineKeyboardButton("लाल बटन", callback_data="red", style="danger"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "टेस्ट करो भाई। हरा और नीला बटन दिखना चाहिए।",
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
    print("Bot start ho gaya...")
    app.run_polling()

if __name__ == "__main__":
    main()
