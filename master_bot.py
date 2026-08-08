import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# अपना बॉट टोकन यहाँ डालें
TOKEN = "8892594189:AAFPZ6J6l5xzD_gAuP2DzUKvqOWGxBJYzXI"

# तेरी GitHub Pages वाली Mini App का लिंक
MINI_APP_URL = "https://ssahil80931-hash.github.io/my-miniapp/"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = "नीचे दिए गए बटन पर क्लिक करें (इसके अंदर के बटन स्काई-ब्लू होंगे):"
    
    # यहाँ URL की जगह 'web_app' का इस्तेमाल करना ज़रूरी है
    keyboard = [
        [InlineKeyboardButton("🌐 Open Plans Menu", web_app=WebAppInfo(url=MINI_APP_URL))]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot is running...")
    app.run_polling()
    
