import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# अपना बॉट टोकन यहाँ डालें
TOKEN = "8892594189:AAFPZ6J6l5xzD_gAuP2DzUKvqOWGxBJYzXI"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "नीचे दिए गए लिंक बटन टेलीग्राम में स्काई-ब्लू/नीले रंग में दिखाई देंगे:"
    
    # URL वाले बटन (टेलीग्राम ऐप इन्हें स्काई-ब्लू/नीला दिखाता है)
    keyboard = [
        [InlineKeyboardButton("🌐 Main Website", url="https://google.com")],
        [InlineKeyboardButton("📢 Join Channel", url="https://t.me/telegram")],
        [InlineKeyboardButton("💬 Official Support", url="https://t.me/telegram")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot is running...")
    app.run_polling()
    
