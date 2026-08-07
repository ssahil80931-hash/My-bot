import os
import logging
import threading
import mysql.connector
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

MASTER_TOKEN = os.getenv("8892594189:AAFXnHg7gLw3izYwwb8XzgRqYv-KS2r_6bw")
SUPER_ADMIN_ID = int(os.getenv("8999416691", 0))

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("MASTER_BOT_DB", "master_bot_db")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

master_bot = telebot.TeleBot(MASTER_TOKEN, parse_mode='Markdown')

def get_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, charset='utf8mb4'
    )

def is_admin(user_id):
    if user_id == SUPER_ADMIN_ID:
        return True
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admins WHERE user_id = %s", (user_id,))
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return res is not None

# ==================== MASTER PANEL ====================
@master_bot.message_handler(commands=['start'])
def master_start(message):
    if not is_admin(message.from_user.id):
        master_bot.send_message(message.chat.id, "❌ Unauthorized Access.")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ Add New Bot", callback_data="m_add_bot"),
        InlineKeyboardButton("🤖 Manage Bots", callback_data="m_list_bots"),
        InlineKeyboardButton("📦 Add Category & Videos", callback_data="m_add_cat"),
        InlineKeyboardButton("💳 Payment Settings", callback_data="m_payment"),
        InlineKeyboardButton("📊 Earnings & Analytics", callback_data="m_analytics"),
        InlineKeyboardButton("📢 Broadcast", callback_data="m_broadcast")
    )
    master_bot.send_message(message.chat.id, "👑 *MASTER CONTROL PANEL*\n\nManage your bots, categories, videos, and payments seamlessly:", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('m_'))
def master_callbacks(call):
    if not is_admin(call.from_user.id):
        return
    
    action = call.data[2:]
    chat_id = call.message.chat.id

    if action == 'add_bot':
        msg = master_bot.send_message(chat_id, "🤖 Send the new Bot Token from @BotFather:")
        master_bot.register_next_step_handler(msg, save_new_bot)
    elif action == 'list_bots':
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bots")
        bots = cursor.fetchall()
        cursor.close()
        conn.close()

        text = "🤖 *Active Connected Bots:*\n\n"
        for b in bots:
            text += f"• `{b['bot_username']}` (Token: `{b['bot_token'][:10]}...`)\n"
        master_bot.edit_message_text(text, chat_id, call.message.message_id)

    elif action == 'payment':
        msg = master_bot.send_message(chat_id, "💳 Send new UPI ID:")
        master_bot.register_next_step_handler(msg, save_upi_setting)

def save_new_bot(message):
    token = message.text.strip()
    try:
        temp_bot = telebot.TeleBot(token)
        bot_info = temp_bot.get_me()
        bot_username = bot_info.username

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bots (bot_token, bot_username) VALUES (%s, %s)", (token, bot_username))
        conn.commit()
        cursor.close()
        conn.close()

        master_bot.send_message(message.chat.id, f"✅ Bot `@{bot_username}` successfully added and started!")
        # Start running this bot dynamically in a thread
        threading.Thread(target=run_client_bot, args=(token,)).start()
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ Failed to add bot: {e}")

def save_upi_setting(message):
    upi = message.text.strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO settings (setting_key, setting_value) VALUES ('upi_id', %s) ON DUPLICATE KEY UPDATE setting_value=%s", (upi, upi))
    conn.commit()
    cursor.close()
    conn.close()
    master_bot.send_message(message.chat.id, f"✅ UPI ID updated to: `{upi}`")


# ==================== CLIENT BOT RUNNER & LOGIC ====================
def run_client_bot(token):
    client_bot = telebot.TeleBot(token, parse_mode='Session')

    @client_bot.message_handler(commands=['start'])
    def client_start(message):
        chat_id = message.chat.id
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Save user
        cursor.execute("INSERT INTO users (chat_id, first_name, username) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE first_name=%s", 
                       (chat_id, message.from_user.first_name, message.from_user.username, message.from_user.first_name))
        conn.commit()

        # Fetch categories with price
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        
        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='start_caption'")
        cap_res = cursor.fetchone()
        caption = cap_res['setting_value'] if cap_res else "Welcome! Choose a category below:"
        
        cursor.close()
        conn.close()

        markup = InlineKeyboardMarkup(row_width=1)
        for cat in categories:
            markup.add(InlineKeyboardButton(f"📂 {cat['name']} - ₹{cat['price']}", callback_data=f"cat_{cat['id']}"))

        client_bot.send_message(chat_id, caption, reply_markup=markup)

    @client_bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
    def handle_category_click(call):
        chat_id = call.message.chat.id
        cat_id = call.data.split('_')[1]

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories WHERE id = %s", (cat_id,))
        category = cursor.fetchone()

        cursor.execute("SELECT video_file_id FROM category_videos WHERE category_id = %s", (cat_id,))
        videos = cursor.fetchall()

        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='upi_id'")
        upi_res = cursor.fetchone()
        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='qr_file_id'")
        qr_res = cursor.fetchone()
        cursor.close()
        conn.close()

        if not category:
            client_bot.answer_callback_query(call.id, "Category not found!")
            return

        # Step 1: Send all 5 videos together or sequentially
        client_bot.send_message(chat_id, f"🎬 Here are your videos for *{category['name']}*:")
        for v in videos:
            try:
                client_bot.send_video(chat_id, v['video_file_id'])
            except Exception:
                pass

        # Step 2: Generate Order & QR Code based on Price
        order_id = f"ORD{call.message.date}"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (order_id, user_chat_id, category_id, amount, status) VALUES (%s, %s, %s, %s, 'pending')",
                       (order_id, chat_id, cat_id, category['price']))
        conn.commit()
        cursor.close()
        conn.close()

        upi_id = upi_res['setting_value'] if upi_res else "merchant@upi"
        qr_id = qr_res['setting_value'] if qr_res else ""

        pay_text = f"💳 *Payment Required*\n\n" \
                   f"📦 Category: {category['name']}\n" \
                   f"💰 Price: ₹{category['price']}\n" \
                   f"🆔 Order ID: `#{order_id}`\n\n" \
                   f"UPI ID: `{upi_id}`\n\n" \
                   f"Please pay and send screenshot below:"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📸 Send Payment Screenshot", callback_data=f"pay_ss_{order_id}"))

        if qr_id:
            client_bot.send_photo(chat_id, qr_id, caption=pay_text, reply_markup=markup)
        else:
            client_bot.send_message(chat_id, pay_text, reply_markup=markup)

    @client_bot.callback_query_handler(func=lambda call: call.data.startswith('pay_ss_'))
    def ask_for_screenshot(call):
        order_id = call.data.split('_')[2]
        msg = client_bot.send_message(call.message.chat.id, f"📸 Send payment screenshot for Order `#{order_id}` now:")
        client_bot.register_next_step_handler(msg, receive_screenshot, order_id)

    def receive_screenshot(message, order_id):
        chat_id = message.chat.id
        if not message.photo:
            client_bot.send_message(chat_id, "❌ Please send a valid photo screenshot.")
            return

        file_id = message.photo[-1].file_id

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("UPDATE orders SET screenshot_file_id = %s WHERE order_id = %s", (file_id, order_id))
        cursor.execute("SELECT o.*, c.name FROM orders o JOIN categories c ON o.category_id = c.id WHERE o.order_id = %s", (order_id,))
        order = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        client_bot.send_message(chat_id, "✅ Screenshot received! Admin will verify soon.")

        # Notify Master Admin
        if SUPER_ADMIN_ID:
            admin_txt = f"🔔 *New Payment Proof!*\n\nOrder: `#{order_id}`\nUser: `{chat_id}`\nCategory: {order['name']}\nAmount: ₹{order['amount']}"
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"app_{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{order_id}")
            )
            master_bot.send_photo(SUPER_ADMIN_ID, file_id, caption=admin_txt, reply_markup=markup)

    client_bot.infinity_polling(skip_pending=True)

# Auto-start all registered client bots from database on startup
def load_all_bots():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT bot_token FROM bots WHERE is_active = 1")
    bots = cursor.fetchall()
    cursor.close()
    conn.close()

    for b in bots:
        threading.Thread(target=run_client_bot, args=(b['bot_token'],)).start()

if __name__ == '__main__':
    load_all_bots()
    logger.info("Master Control Bot is running...")
    master_bot.infinity_polling(skip_pending=True)
      
