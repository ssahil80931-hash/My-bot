import os
import logging
import threading
import sqlite3
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

print("SCRIPT STARTING...", flush=True)

load_dotenv()

MASTER_TOKEN = os.getenv("MASTER_TOKEN")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID") or "0")

DB_FILE = "bot_database.db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print(f"Loaded MASTER_TOKEN length: {len(MASTER_TOKEN) if MASTER_TOKEN else 0}", flush=True)
print(f"Loaded SUPER_ADMIN_ID: {SUPER_ADMIN_ID}", flush=True)

if not MASTER_TOKEN:
    logger.error("MASTER_TOKEN environment variable not set in Railway variables!")
    print("CRITICAL ERROR: MASTER_TOKEN missing!", flush=True)
    exit(1)

master_bot = telebot.TeleBot(MASTER_TOKEN, parse_mode='Markdown')

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        print("Initializing SQLite Database...", flush=True)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_token TEXT UNIQUE NOT NULL,
                bot_username TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                bot_id INTEGER,
                first_name TEXT,
                username TEXT,
                is_blocked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER DEFAULT 0,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                days INTEGER DEFAULT 30,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                video_file_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                user_chat_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                screenshot_file_id TEXT,
                admin_message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT,
                invite_link TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT
            )
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES 
            ('upi_id', 'merchant@upi'),
            ('qr_file_id', ''),
            ('start_caption', '✨ *Welcome to Premium Store* ✨\n\nChoose a category below to explore:')
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("SQLite Database tables initialized successfully!", flush=True)
    except Exception as e:
        print(f"Database initialization failed: {e}", flush=True)
        logger.error(f"Database initialization failed: {e}")

def is_admin(user_id):
    if SUPER_ADMIN_ID and user_id == SUPER_ADMIN_ID:
        return True
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return res is not None

@master_bot.message_handler(commands=['start'])
def master_start(message):
    print(f"Received /start from user: {message.from_user.id}", flush=True)
    if not is_admin(message.from_user.id):
        master_bot.send_message(message.chat.id, "❌ *Unauthorized Access.*")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🤖 Add New Bot", callback_data="m_add_bot"),
        InlineKeyboardButton("📋 Manage Bots", callback_data="m_list_bots"),
        InlineKeyboardButton("📦 Products", callback_data="m_products"),
        InlineKeyboardButton("📢 Channels", callback_data="m_channels"),
        InlineKeyboardButton("💳 Payment Settings", callback_data="m_payment"),
        InlineKeyboardButton("📊 Stats & Revenue", callback_data="m_analytics"),
        InlineKeyboardButton("📢 Broadcast", callback_data="m_broadcast"),
        InlineKeyboardButton("👥 Users", callback_data="m_users"),
        InlineKeyboardButton("⚙️ Settings", callback_data="m_settings")
    )
    master_bot.send_message(message.chat.id, "👑 *MASTER CONTROL PANEL*\n\nSelect an option below to manage your system seamlessly:", reply_markup=markup)

@master_bot.message_handler(commands=['getids'])
def get_file_ids(message):
    if not is_admin(message.from_user.id):
        return
    if message.reply_to_message:
        msg = message.reply_to_message
        file_id = ""
        media_type = "Text"
        if msg.photo:
            file_id = msg.photo[-1].file_id
            media_type = "Photo"
        elif msg.video:
            file_id = msg.video.file_id
            media_type = "Video"
        elif msg.document:
            file_id = msg.document.file_id
            media_type = "Document"
        
        master_bot.send_message(message.chat.id, f"📋 *Media File ID ({media_type}):*\n`{file_id}`")
    else:
        master_bot.send_message(message.chat.id, "ℹ️ *Reply to any Photo or Video with `/getids` to get its File ID.*")

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
        cursor = conn.cursor()
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
        cursor = conn.cursor()
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

    elif action == 'channels':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels")
        channels = cursor.fetchall()
        cursor.close()
        conn.close()

        text = "📢 *Channel/Group Management:*\n\n"
        if not channels:
            text += "No channels added yet."
        for c in channels:
            text += f"• *{c['channel_name']}* (`{c['channel_id']}`)\n"
        
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ Add Channel", callback_data="m_add_chan"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu")
        )
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'add_chan':
        msg = master_bot.send_message(chat_id, "📢 *Enter Channel Details in format:*\n`ChannelID | ChannelName | InviteLink`")
        master_bot.register_next_step_handler(msg, save_new_channel)

    elif action == 'payment':
        msg = master_bot.send_message(chat_id, "💳 *Send new UPI ID:*")
        master_bot.register_next_step_handler(msg, save_upi_setting)

    elif action == 'analytics':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM orders")
        total_orders = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM orders WHERE status='pending'")
        pending_orders = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM orders WHERE status='approved'")
        approved_orders = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM orders WHERE status='rejected'")
        rejected_orders = cursor.fetchone()['cnt']
        
        cursor.execute("SELECT SUM(amount) as rev FROM orders WHERE status='approved'")
        total_rev = cursor.fetchone()['rev'] or 0
        
        cursor.execute("SELECT SUM(amount) as rev FROM orders WHERE status='approved' AND date(created_at) = date('now')")
        today_rev = cursor.fetchone()['rev'] or 0

        cursor.execute("SELECT SUM(amount) as rev FROM orders WHERE status='approved' AND created_at >= datetime('now', '-7 days')")
        week_rev = cursor.fetchone()['rev'] or 0

        cursor.execute("SELECT SUM(amount) as rev FROM orders WHERE status='approved' AND created_at >= datetime('now', '-30 days')")
        month_rev = cursor.fetchone()['rev'] or 0

        cursor.close()
        conn.close()

        text = f"📊 *Advanced Earnings & Analytics*\n\n" \
               f"👥 Total Users: `{total_users}`\n" \
               f"📦 Total Orders: `{total_orders}` (Pending: `{pending_orders}`, Approved: `{approved_orders}`, Rejected: `{rejected_orders}`)\n\n" \
               f"💰 Total Revenue: `₹{total_rev}`\n" \
               f"📅 Today's Revenue: `₹{today_rev}`\n" \
               f"📈 Last 7 Days Revenue: `₹{week_rev}`\n" \
               f"🗓️ Last 30 Days Revenue: `₹{month_rev}`"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu"))
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'broadcast':
        msg = master_bot.send_message(chat_id, "📢 *Send the broadcast message (Text, Photo, or Video with caption):*")
        master_bot.register_next_step_handler(msg, execute_broadcast)

    elif action == 'users':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        count = cursor.fetchone()['cnt']
        cursor.close()
        conn.close()

        text = f"👥 *User Management*\n\nTotal Registered Users across all bots: `{count}`"
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
        cursor.execute("INSERT INTO bots (bot_token, bot_username) VALUES (?, ?)", (token, bot_username))
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
        cursor.execute("INSERT INTO categories (name, price, days, description) VALUES (?, ?, ?, ?)", (name, price, days, desc))
        conn.commit()
        cursor.close()
        conn.close()

        master_bot.send_message(message.chat.id, f"✅ *Product '{name}' added successfully!*")
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ *Invalid format or error:* `{e}`")

def save_new_channel(message):
    try:
        parts = message.text.split('|')
        chan_id = parts[0].strip()
        chan_name = parts[1].strip()
        invite = parts[2].strip() if len(parts) > 2 else ""

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO channels (channel_id, channel_name, invite_link) VALUES (?, ?, ?)", (chan_id, chan_name, invite))
        conn.commit()
        cursor.close()
        conn.close()

        master_bot.send_message(message.chat.id, f"✅ *Channel '{chan_name}' added successfully!*")
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ *Invalid format or error:* `{e}`")

def save_upi_setting(message):
    upi = message.text.strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('upi_id', ?)", (upi,))
    conn.commit()
    cursor.close()
    conn.close()
    master_bot.send_message(message.chat.id, f"✅ *UPI ID updated to:* `{upi}`")

def execute_broadcast(message):
    conn = get_db()
    cursor = conn.cursor()
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
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (chat_id, first_name, username) VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET first_name = excluded.first_name, username = excluded.username
        """, (chat_id, message.from_user.first_name, message.from_user.username))
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
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
        category = cursor.fetchone()

        cursor.execute("SELECT video_file_id FROM category_videos WHERE category_id = ?", (cat_id,))
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
        cursor.execute("INSERT INTO orders (order_id, user_chat_id, category_id, amount, status) VALUES (?, ?, ?, ?, 'pending')",
                       (order_id, chat_id, cat_id, category['price']))
        conn.commit()
        cursor.close()
        conn.close()

        upi_id = upi_res['setting_value'] if upi_res else "merchant@upi"
    
