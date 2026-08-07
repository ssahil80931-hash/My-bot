import os
import logging
import threading
import mysql.connector
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

MASTER_TOKEN = "8892594189:AAGtMzvMCVqVdMkdwSY1R0Tu86rVCWlVXPc"
SUPER_ADMIN_ID = 8999416691

DB_HOST = os.getenv("DB_HOST", "mysql.railway.internal")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "railway")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

master_bot = telebot.TeleBot(MASTER_TOKEN, parse_mode='Markdown')

def get_db():
    db_port = int(os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or 3306)
    return mysql.connector.connect(
        host=DB_HOST, 
        user=DB_USER, 
        password=DB_PASSWORD, 
        database=DB_NAME, 
        port=db_port, 
        charset='utf8mb4'
    )

def init_db():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bot_token VARCHAR(255) UNIQUE NOT NULL,
                bot_username VARCHAR(100),
                is_active TINYINT DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                chat_id BIGINT UNIQUE NOT NULL,
                bot_id INT,
                first_name VARCHAR(255),
                username VARCHAR(100),
                is_blocked TINYINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bot_id INT DEFAULT 0,
                name VARCHAR(255) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                days INT DEFAULT 30,
                description TEXT,
                is_active TINYINT DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_videos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category_id INT NOT NULL,
                video_file_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id VARCHAR(50) UNIQUE NOT NULL,
                user_chat_id BIGINT NOT NULL,
                category_id INT NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                screenshot_file_id VARCHAR(255),
                admin_message_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INT AUTO_INCREMENT PRIMARY KEY,
                channel_id VARCHAR(100) UNIQUE NOT NULL,
                channel_name VARCHAR(255),
                invite_link TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                setting_key VARCHAR(100) PRIMARY KEY,
                setting_value TEXT
            )
        """)
        cursor.execute("""
            INSERT IGNORE INTO settings (setting_key, setting_value) VALUES 
            ('upi_id', 'merchant@upi'),
            ('qr_file_id', ''),
            ('start_caption', '✨ *Welcome to Premium Store* ✨\n\nChoose a category below to explore:')
        """)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database tables initialized successfully!")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

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

@master_bot.message_handler(commands=['start'])
def master_start(message):
    if not is_admin(message.from_user.id):
        master_bot.send_message(message.chat.id, "❌ *Unauthorized Access.*")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🤖 Add New Bot", callback_data="m_add_bot"),
        InlineKeyboardButton("📋 Manage Bots", callback_data="m_list_bots"),
        InlineKeyboardButton("📦 Add/Manage Products", callback_data="m_products"),
        InlineKeyboardButton("💳 Payment Settings", callback_data="m_payment"),
        InlineKeyboardButton("📊 Analytics & Stats", callback_data="m_analytics"),
        InlineKeyboardButton("📢 Broadcast", callback_data="m_broadcast"),
        InlineKeyboardButton("👥 User Management", callback_data="m_users"),
        InlineKeyboardButton("⚙️ General Settings", callback_data="m_settings")
    )
    master_bot.send_message(message.chat.id, "👑 *MASTER CONTROL PANEL*\n\nSelect an option below to manage your system seamlessly:", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('m_'))
def master_callbacks(call):
    if not is_admin(call.from_user.id):
        return
    
    action = call.data[2:]
    chat_id = call.message.chat.id

    if action == 'add_bot':
        msg = master_bot.send_message(chat_id, "🤖 *Send the new Bot Token from @BotFather:*")
        master_bot.register_next_step_handler(msg, save_new_bot)
        
    elif action == 'list_bots':
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bots")
        bots = cursor.fetchall()
        cursor.close()
        conn.close()

        text = "🤖 *Active Connected Bots:*\n\n"
        if not bots:
            text += "No bots added yet."
        for b in bots:
            status = "🟢 Active" if b['is_active'] else "🔴 Inactive"
            text += f"• `@{b['bot_username']}` | Status: {status}\n  Token: `{b['bot_token'][:10]}...`\n\n"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu"))
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'products':
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories")
        prods = cursor.fetchall()
        cursor.close()
        conn.close()

        text = "📦 *Product Management:*\n\n"
        for p in prods:
            text += f"🆔 ID: {p['id']} | *{p['name']}* - ₹{p['price']} ({p['days']} Days)\n"
        
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ Add New Product", callback_data="m_add_prod"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu")
        )
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'add_prod':
        msg = master_bot.send_message(chat_id, "📦 *Enter Product Details in format:*\n`Name | Price | Days | Description`")
        master_bot.register_next_step_handler(msg, save_new_product)

    elif action == 'payment':
        msg = master_bot.send_message(chat_id, "💳 *Send new UPI ID:*")
        master_bot.register_next_step_handler(msg, save_upi_setting)

    elif action == 'analytics':
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM orders")
        total_orders = cursor.fetchone()['cnt']
        cursor.execute("SELECT SUM(amount) as rev FROM orders WHERE status='approved'")
        total_rev = cursor.fetchone()['rev'] or 0
        cursor.close()
        conn.close()

        text = f"📊 *Earnings & Analytics Summary*\n\n" \
               f"👥 Total Users: `{total_users}`\n" \
               f"📦 Total Orders: `{total_orders}`\n" \
               f"💰 Total Revenue: `₹{total_rev}`"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu"))
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'broadcast':
        msg = master_bot.send_message(chat_id, "📢 *Send the broadcast message (Text, Photo, or Video with caption):*")
        master_bot.register_next_step_handler(msg, execute_broadcast)

    elif action == 'users':
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        count = cursor.fetchone()['cnt']
        cursor.close()
        conn.close()

        text = f"👥 *User Management*\n\nTotal Registered Users across bots: `{count}`"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu"))
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'settings':
        text = "⚙️ *General System Settings*\nConfigure system parameters via database values."
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu"))
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'main_menu':
        master_start(call.message)

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

        master_bot.send_message(message.chat.id, f"✅ *Bot `@{bot_username}` successfully added and started!*")
        threading.Thread(target=run_client_bot, args=(token,)).start()
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ *Failed to add bot:* `{e}`")

def save_new_product(message):
    try:
        parts = message.text.split('|')
        name = parts[0].strip()
        price = float(parts[1].strip())
        days = int(parts[2].strip())
        desc = parts[3].strip() if len(parts) > 3 else ""

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name, price, days, description) VALUES (%s, %s, %s, %s)", (name, price, days, desc))
        conn.commit()
        cursor.close()
        conn.close()

        master_bot.send_message(message.chat.id, f"✅ *Product '{name}' added successfully!*")
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ *Invalid format or error:* `{e}`")

def save_upi_setting(message):
    upi = message.text.strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO settings (setting_key, setting_value) VALUES ('upi_id', %s) ON DUPLICATE KEY UPDATE setting_value=%s", (upi, upi))
    conn.commit()
    cursor.close()
    conn.close()
    master_bot.send_message(message.chat.id, f"✅ *UPI ID updated to:* `{upi}`")

def execute_broadcast(message):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT chat_id FROM users WHERE is_blocked = 0")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    success, failed = 0, 0
    for u in users:
        try:
            if message.content_type == 'text':
                master_bot.send_message(u['chat_id'], message.text, parse_mode='Markdown')
            elif message.content_type == 'photo':
                master_bot.send_photo(u['chat_id'], message.photo[-1].file_id, caption=message.caption, parse_mode='Markdown')
            elif message.content_type == 'video':
                master_bot.send_video(u['chat_id'], message.video.file_id, caption=message.caption, parse_mode='Markdown')
            success += 1
        except Exception:
            failed += 1

    master_bot.send_message(message.chat.id, f"📢 *Broadcast Completed!*\n\n✅ Sent: {success}\n❌ Failed: {failed}")

def run_client_bot(token):
    client_bot = telebot.TeleBot(token, parse_mode='Markdown')

    @client_bot.message_handler(commands=['start'])
    def client_start(message):
        chat_id = message.chat.id
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("INSERT INTO users (chat_id, first_name, username) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE first_name=%s", 
                       (chat_id, message.from_user.first_name, message.from_user.username, message.from_user.first_name))
        conn.commit()

        cursor.execute("SELECT * FROM categories WHERE is_active = 1")
        categories = cursor.fetchall()
        
        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='start_caption'")
        cap_res = cursor.fetchone()
        caption = cap_res['setting_value'] if cap_res else "✨ *Welcome to Store* ✨\n\nChoose a category below:"
        
        cursor.close()
        conn.close()

        markup = InlineKeyboardMarkup(row_width=1)
        for cat in categories:
            markup.add(InlineKeyboardButton(f"🛒 {cat['name']} - ₹{cat['price']}", callback_data=f"cat_{cat['id']}"))

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
            client_bot.answer_callback_query(call.id, "❌ Category not found!")
            return

        client_bot.send_message(chat_id, f"📂 *Product:* {category['name']}\n💰 *Price:* ₹{category['price']}\n⏳ *Validity:* {category['days']} Days\n\n📝 {category['description']}")
        
        for v in videos:
            try:
                client_bot.send_video(chat_id, v['video_file_id'])
            except Exception:
                pass

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

        pay_text = f"💳 *PAYMENT REQUIRED*\n\n" \
                   f"📦 Item: {category['name']}\n" \
                   f"💰 Amount: ₹{category['price']}\n" \
                   f"🆔 Order ID: `#{order_id}`\n\n" \
                   f"UPI ID: `{upi_id}`\n\n" \
                   f"👉 Please make payment and click below to upload screenshot:"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📸 Send Payment Screenshot", callback_data=f"pay_ss_{order_id}"))

        if qr_id:
            client_bot.send_photo(chat_id, qr_id, caption=pay_text, reply_markup=markup)
        else:
            client_bot.send_message(chat_id, pay_text, reply_markup=markup)

    @client_bot.callback_query_handler(func=lambda call: call.data.startswith('pay_ss_'))
    def ask_for_screenshot(call):
        order_id = call.data.split('_')[2]
        msg = client_bot.send_message(call.message.chat.id, f"📸 *Send payment screenshot photo for Order `#{order_id}` now:*")
        client_bot.register_next_step_handler(msg, receive_screenshot, order_id)

    def receive_screenshot(message, order_id):
        chat_id = message.chat.id
        if not message.photo:
            client_bot.send_message(chat_id, "❌ *Please send a valid photo screenshot.*")
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

        client_bot.send_message(chat_id, "✅ *Screenshot received successfully! Admin will verify and approve soon.*")

        if SUPER_ADMIN_ID:
            admin_txt = f"🔔 *NEW PAYMENT PROOF!*\n\nOrder: `#{order_id}`\nUser: `{chat_id}`\nProduct: {order['name']}\nAmount: ₹{order['amount']}"
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"app_{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{order_id}")
            )
            master_bot.send_photo(SUPER_ADMIN_ID, file_id, caption=admin_txt, reply_markup=markup)

    client_bot.infinity_polling(skip_pending=True)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def handle_order_approval(call):
    if not is_admin(call.from_user.id):
        return

    action, order_id = call.data.split('_', 1)
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        cursor.close()
        conn.close()
        master_bot.answer_callback_query(call.id, "❌ Order not found!")
        return

    user_chat_id = order['user_chat_id']

    if action == 'app':
        cursor.execute("UPDATE orders SET status = 'approved' WHERE order_id = %s", (order_id,))
        conn.commit()
        cursor.close()
        conn.close()

        master_bot.edit_message_caption(f"✅ *Order #{order_id} Approved Successfully!*", call.message.chat.id, call.message.message_id)
        try:
            master_bot.send_message(user_chat_id, f"🎉 *Payment Approved!*\n\nYour order `#{order_id}` has been verified successfully. Enjoy your premium access!")
        except Exception:
            pass
    else:
        cursor.execute("UPDATE orders SET status = 'rejected' WHERE order_id = %s", (order_id,))
        conn.commit()
        cursor.close()
        conn.close()

        master_bot.edit_message_caption(f"❌ 
