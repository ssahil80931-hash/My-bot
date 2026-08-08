import os
import logging
import threading
import sqlite3
import random
import requests
from io import BytesIO
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import qrcode
from PIL import Image

print("SCRIPT STARTING...", flush=True)

load_dotenv()

MASTER_TOKEN = os.getenv("MASTER_TOKEN")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID") or "0")

DB_FILE = "bot_database.db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if not MASTER_TOKEN:
    logger.error("MASTER_TOKEN environment variable not set!")
    exit(1)

master_bot = telebot.TeleBot(MASTER_TOKEN, parse_mode='Markdown')
admin_video_states = {}
admin_wel_states = {}

# ===================== QR Themes (20+) =====================
QR_THEMES = [
    {"fill": "#000000", "back": "#FFFFFF", "name": "Classic"},
    {"fill": "#FFFFFF", "back": "#000000", "name": "Dark"},
    {"fill": "#0A66C2", "back": "#FFFFFF", "name": "Blue"},
    {"fill": "#00C853", "back": "#FFFFFF", "name": "Green"},
    {"fill": "#D50000", "back": "#FFFFFF", "name": "Red"},
    {"fill": "#6A1B9A", "back": "#FFFFFF", "name": "Purple"},
    {"fill": "#FF6D00", "back": "#FFFFFF", "name": "Orange"},
    {"fill": "#00BCD4", "back": "#FFFFFF", "name": "Cyan"},
    {"fill": "#E91E63", "back": "#FFFFFF", "name": "Pink"},
    {"fill": "#212121", "back": "#FFF8E1", "name": "Cream"},
    {"fill": "#1A237E", "back": "#E8EAF6", "name": "Indigo"},
    {"fill": "#004D40", "back": "#E0F2F1", "name": "Teal"},
    {"fill": "#BF360C", "back": "#FBE9E7", "name": "Deep Orange"},
    {"fill": "#4A148C", "back": "#F3E5F5", "name": "Deep Purple"},
    {"fill": "#01579B", "back": "#E1F5FE", "name": "Light Blue"},
    {"fill": "#1B5E20", "back": "#E8F5E9", "name": "Forest"},
    {"fill": "#B71C1C", "back": "#FFEBEE", "name": "Crimson"},
    {"fill": "#263238", "back": "#ECEFF1", "name": "Blue Grey"},
    {"fill": "#3E2723", "back": "#EFEBE9", "name": "Brown"},
    {"fill": "#880E4F", "back": "#FCE4EC", "name": "Magenta"},
    {"fill": "#006064", "back": "#E0F7FA", "name": "Dark Cyan"},
    {"fill": "#311B92", "back": "#EDE7F6", "name": "Deep Indigo"},
]

def generate_random_qr(upi_id: str, amount: float) -> BytesIO:
    theme = random.choice(QR_THEMES)
    upi_link = f"upi://pay?pa={upi_id}&am={amount}&cu=INR"
    
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=3)
    qr.add_data(upi_link)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color=theme["fill"], back_color=theme["back"]).convert("RGB")
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

def upload_to_catbox(file_bytes: bytes, filename: str = "file.jpg") -> str | None:
    """Upload media to catbox.moe and return permanent URL"""
    try:
        files = {"fileToUpload": (filename, file_bytes)}
        data = {"reqtype": "fileupload"}
        r = requests.post("https://catbox.moe/user/api.php", data=data, files=files, timeout=60)
        if r.status_code == 200 and r.text.startswith("https://"):
            return r.text.strip()
        logger.error(f"Catbox upload failed: {r.text}")
        return None
    except Exception as e:
        logger.error(f"Catbox error: {e}")
        return None

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
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
                video_url TEXT NOT NULL,
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
            ('upi_id', 'Q691189350@ybl'),
            ('support_link', 'https://t.me/YourUsername'),
            ('start_caption', '✨ *Welcome to Viral Mms Bot* ✨\\n\\nGet exclusive access to premium content\\nAffordable plans starting at just ₹39\\n\\nChoose a category below:'),
            ('welcome_photo_url', '')
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
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
    if not is_admin(message.from_user.id):
        master_bot.send_message(message.chat.id, "❌ *Unauthorized Access.*")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🤖 Add New Bot", callback_data="m_add_bot", style="primary"),
        InlineKeyboardButton("📋 Manage Bots", callback_data="m_list_bots"),
        InlineKeyboardButton("📦 Products", callback_data="m_products", style="primary"),
        InlineKeyboardButton("🎬 Add Demo Videos", callback_data="m_add_videos", style="success"),
        InlineKeyboardButton("🖼️ Set Welcome Photo & Caption", callback_data="m_wel_pc", style="primary"),
        InlineKeyboardButton("📢 Channels", callback_data="m_channels"),
        InlineKeyboardButton("💳 Payment & UPI", callback_data="m_payment"),
        InlineKeyboardButton("🔗 Change Support Link", callback_data="m_changelink"),
        InlineKeyboardButton("📊 Stats & Revenue", callback_data="m_analytics"),
        InlineKeyboardButton("📢 Broadcast", callback_data="m_broadcast", style="danger"),
        InlineKeyboardButton("👥 Users", callback_data="m_users")
    )
    master_bot.send_message(message.chat.id, "👑 *MASTER CONTROL PANEL*\n\nSelect an option below:", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('m_'))
def master_callbacks(call):
    if not is_admin(call.from_user.id):
        master_bot.answer_callback_query(call.id, "❌ Unauthorized!", show_alert=True)
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
            text += f"• `@{b['bot_username']}` | Status: {status}\n\n"
        
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

        text = "📦 *Product Management (Categories):*\n\n"
        for p in prods:
            text += f"🆔 ID: `{p['id']}` | *{p['name']}* - ₹{p['price']} ({p['days']} Days)\n"
        
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ Add New Product", callback_data="m_add_prod", style="success"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu")
        )
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'add_prod':
        msg = master_bot.send_message(chat_id, "📦 *Enter Product Details in format:*\n`Name | Price | Days | Description`")
        master_bot.register_next_step_handler(msg, save_new_product)

    elif action == 'add_videos':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories")
        prods = cursor.fetchall()
        cursor.close()
        conn.close()

        if not prods:
            master_bot.edit_message_text("❌ *Pehle koi product add karein!*", chat_id, call.message.message_id)
            return

        markup = InlineKeyboardMarkup(row_width=1)
        for p in prods:
            markup.add(InlineKeyboardButton(f"🎬 {p['name']}", callback_data=f"addv_{p['id']}"))
        markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu"))
        master_bot.edit_message_text("🎬 *Select a Product to add Demo Videos:*", chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'wel_pc':
        msg = master_bot.send_message(chat_id, "📝 **Step 1/2:** Pehle apna naya **Welcome Caption** text bhejo (या 'skip' लिखें):")
        master_bot.register_next_step_handler(msg, get_welcome_caption_step)

    elif action == 'channels':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM channels")
        channels = cursor.fetchall()
        cursor.close()
        conn.close()

        text = "📢 *Channel Management:*\n\n"
        if not channels:
            text += "No channels added yet."
        for c in channels:
            text += f"• *{c['channel_name']}* (`{c['channel_id']}`)\n"
        
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ Add Channel", callback_data="m_add_chan", style="success"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu")
        )
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'add_chan':
        msg = master_bot.send_message(chat_id, "📢 *Enter Channel Details:*\n`ChannelID | ChannelName | InviteLink`")
        master_bot.register_next_step_handler(msg, save_new_channel)

    elif action == 'payment':
        msg = master_bot.send_message(chat_id, "💳 *Send new UPI ID:*")
        master_bot.register_next_step_handler(msg, save_upi_setting)

    elif action == 'changelink':
        msg = master_bot.send_message(chat_id, "🔗 *Send the new Support / DM Telegram Link:*")
        master_bot.register_next_step_handler(msg, save_support_link)

    elif action == 'analytics':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM orders")
        total_orders = cursor.fetchone()['cnt']
        cursor.execute("SELECT SUM(amount) as rev FROM orders WHERE status='approved'")
        total_rev = cursor.fetchone()['rev'] or 0
        cursor.close()
        conn.close()

        text = f"📊 *Analytics*\n\n👥 Total Users: `{total_users}`\n📦 Total Orders: `{total_orders}`\n💰 Total Revenue: `₹{total_rev}`"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu"))
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'broadcast':
        msg = master_bot.send_message(chat_id, "📢 *Send the broadcast message (text/photo/video):*")
        master_bot.register_next_step_handler(msg, execute_broadcast)

    elif action == 'users':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        count = cursor.fetchone()['cnt']
        cursor.close()
        conn.close()
        text = f"👥 *Users*\n\nTotal Users: `{count}`"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu"))
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'main_menu':
        try:
            master_bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass
        master_start(call.message)
        master_bot.answer_callback_query(call.id)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('addv_'))
def select_product_for_video(call):
    if not is_admin(call.from_user.id):
        master_bot.answer_callback_query(call.id, "❌ Unauthorized!", show_alert=True)
        return
    cat_id = int(call.data.split('_')[1])
    admin_video_states[call.message.chat.id] = {
        'cat_id': cat_id,
        'videos': []
    }
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Done (Save All Videos)", callback_data="save_batch_videos", style="success"))
    master_bot.send_message(
        call.message.chat.id, 
        "🎬 **Product Selected!**\n\nAb videos bhejo (ek sath ya ek-ek karke).\nJab ho jaye to **✅ Done** dabao.\n\n(Videos permanent link banakar save hongi)",
        reply_markup=markup
    )
    master_bot.answer_callback_query(call.id)

@master_bot.message_handler(content_types=['video', 'document'], func=lambda message: message.chat.id in admin_video_states)
def collect_batch_videos(message):
    chat_id = message.chat.id
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    
    if file_id:
        try:
            file_info = master_bot.get_file(file_id)
            downloaded = master_bot.download_file(file_info.file_path)
            url = upload_to_catbox(downloaded, "video.mp4")
            if url:
                admin_video_states[chat_id]['videos'].append(url)
                count = len(admin_video_states[chat_id]['videos'])
                master_bot.reply_to(message, f"📥 Video #{count} permanent link ban gaya!\n`{url}`\n\nAur bhejo ya Done dabao.")
            else:
                master_bot.reply_to(message, "❌ Upload fail hua, dobara try karo.")
        except Exception as e:
            master_bot.reply_to(message, f"❌ Error: {e}")

@master_bot.callback_query_handler(func=lambda call: call.data == 'save_batch_videos')
def save_all_collected_videos(call):
    chat_id = call.message.chat.id
    state = admin_video_states.get(chat_id)
    
    if not state or not state['videos']:
        master_bot.answer_callback_query(call.id, "❌ Ek bhi video nahi bheji!", show_alert=True)
        return
    
    cat_id = state['cat_id']
    videos = state['videos']
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        for vid_url in videos:
            cursor.execute("INSERT INTO category_videos (category_id, video_url) VALUES (?, ?)", (cat_id, vid_url))
        conn.commit()
        cursor.close()
        conn.close()
        
        master_bot.send_message(chat_id, f"🔥 **SUCCESS!**\n\nProduct ID `{cat_id}` ke liye **{len(videos)}** demo videos permanent save ho gayi!")
        del admin_video_states[chat_id]
    except Exception as e:
        master_bot.send_message(chat_id, f"❌ Error: `{e}`")
    
    master_bot.answer_callback_query(call.id)

def get_welcome_caption_step(message):
    chat_id = message.chat.id
    text = message.text.strip()
    admin_wel_states[chat_id] = text if text.lower() != 'skip' else None
    
    msg = master_bot.send_message(chat_id, "🖼️ **Step 2/2:** Ab **Welcome Photo** bhejo:")
    master_bot.register_next_step_handler(msg, save_welcome_photo_final)

def save_welcome_photo_final(message):
    chat_id = message.chat.id
    if not message.photo:
        master_bot.send_message(chat_id, "❌ Valid photo bhejo! Process cancel.")
        if chat_id in admin_wel_states:
            del admin_wel_states[chat_id]
        return
    
    try:
        file_id = message.photo[-1].file_id
        file_info = master_bot.get_file(file_id)
        downloaded = master_bot.download_file(file_info.file_path)
        url = upload_to_catbox(downloaded, "welcome.jpg")
        
        if not url:
            master_bot.send_message(chat_id, "❌ Photo upload fail hua.")
            return

        caption_text = admin_wel_states.get(chat_id)
        if not caption_text and message.caption:
            caption_text = message.caption
        if not caption_text:
            caption_text = "✨ *Welcome to Bot* ✨"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('welcome_photo_url', ?)", (url,))
        cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('start_caption', ?)", (caption_text,))
        conn.commit()
        cursor.close()
        conn.close()

        if chat_id in admin_wel_states:
            del admin_wel_states[chat_id]

        master_bot.send_message(chat_id, f"✅ **SUCCESS!**\n\nWelcome Photo permanent save ho gaya!\n`{url}`")
    except Exception as e:
        master_bot.send_message(chat_id, f"❌ Error: {e}")

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

        master_bot.send_message(message.chat.id, f"✅ *Bot `@{bot_username}` added!*")
        threading.Thread(target=run_client_bot, args=(token,)).start()
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ *Failed:* `{e}`")

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

        master_bot.send_message(message.chat.id, f"✅ *Product '{name}' added!*")
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ *Error:* `{e}`")

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

        master_bot.send_message(message.chat.id, f"✅ *Channel added!*")
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ *Error:* `{e}`")

def save_upi_setting(message):
    upi = message.text.strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('upi_id', ?)", (upi,))
    conn.commit()
    cursor.close()
    conn.close()
    master_bot.send_message(message.chat.id, f"✅ *UPI ID updated:* `{upi}`")

def save_support_link(message):
    link = message.text.strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('support_link', ?)", (link,))
    conn.commit()
    cursor.close()
    conn.close()
    master_bot.send_message(message.chat.id, f"✅ *Support Link updated!*")

def execute_broadcast(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM users WHERE is_blocked = 0")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    success = 0
    for u in users:
        try:
            if message.content_type == 'text':
                master_bot.send_message(u['chat_id'], message.text, parse_mode='Markdown')
            elif message.content_type == 'photo':
                master_bot.send_photo(u['chat_id'], message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == 'video':
                master_bot.send_video(u['chat_id'], message.video.file_id, caption=message.caption)
            success += 1
        except Exception:
            pass
    master_bot.send_message(message.chat.id, f"📢 *Broadcast Done:* {success} users reached.")

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
        caption = cap_res['setting_value'] if cap_res else "✨ *Welcome* ✨"

        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='welcome_photo_url'")
        photo_res = cursor.fetchone()
        welcome_photo = photo_res['setting_value'] if photo_res else ""
        
        cursor.close()
        conn.close()

        markup = InlineKeyboardMarkup(row_width=1)
        for cat in categories:
            btn = InlineKeyboardButton(
                f"💙 {cat['name']} - ₹{cat['price']} ({cat['days']} days)", 
                callback_data=f"cat_{cat['id']}",
                style="primary"
            )
            markup.add(btn)

        if welcome_photo:
            try:
                client_bot.send_photo(chat_id, welcome_photo, caption=caption, reply_markup=markup)
                return
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
        
        client_bot.send_message(chat_id, caption, reply_markup=markup)

    @client_bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
    def handle_category_click(call):
        chat_id = call.message.chat.id
        cat_id = call.data.split('_')[1]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
        category = cursor.fetchone()

        cursor.execute("SELECT video_url FROM category_videos WHERE category_id = ?", (cat_id,))
        videos = cursor.fetchall()

        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='upi_id'")
        upi_res = cursor.fetchone()
        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='support_link'")
        supp_res = cursor.fetchone()
        cursor.close()
        conn.close()

        if not category:
            client_bot.answer_callback_query(call.id, "❌ Category not found!")
            return

        # Send all demo videos at once
        if videos:
            client_bot.send_message(chat_id, "🎬 *Demo Videos:*")
            for v in videos:
                try:
                    client_bot.send_video(chat_id, v['video_url'])
                except Exception as e:
                    logger.error(f"Error sending video: {e}")
        else:
            client_bot.send_message(chat_id, "ℹ️ *No demo videos for this category yet.*")

        order_id = f"ORD{call.message.date}{random.randint(100,999)}"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (order_id, user_chat_id, category_id, amount, status) VALUES (?, ?, ?, ?, 'pending')",
                       (order_id, chat_id, cat_id, category['price']))
        conn.commit()
        cursor.close()
        conn.close()

        upi_id = upi_res['setting_value'] if upi_res else "Q691189350@ybl"
        support_url = supp_res['setting_value'] if supp_res else "https://t.me/YourUsername"

        # Generate random design QR
        qr_bio = generate_random_qr(upi_id, category['price'])

        pay_text = f"💳 *PAYMENT BILL*\n\n" \
                   f"📂 Category: {category['name']}\n" \
                   f"📊 Validity: {category['days']} Days\n" \
                   f"💰 Amount: ₹{category['price']}\n" \
                   f"🆔 Order ID: `#{order_id}`\n\n" \
                   f"🌐 UPI: `{upi_id}`\n\n" \
                   f"✅ Pay karke 'I Have Paid' dabayein:"

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📸 I Have Paid (Send Screenshot)", callback_data=f"pay_ss_{order_id}", style="success"),
            InlineKeyboardButton("💬 Contact Admin", url=support_url)
        )

        client_bot.send_photo(chat_id, qr_bio, caption=pay_text, reply_markup=markup)

    @client_bot.callback_query_handler(func=lambda call: call.data.startswith('pay_ss_'))
    def ask_for_screenshot(call):
        order_id = call.data.split('_')[2]
        msg = client_bot.send_message(call.message.chat.id, f"📸 *Send payment screenshot for Order `#{order_id}`:*")
        client_bot.register_next_step_handler(msg, receive_screenshot, order_id)

    def receive_screenshot(message, order_id):
        chat_id = message.chat.id
        if not message.photo:
            client_bot.send_message(chat_id, "❌ *Valid photo bhejo.*")
            return

        file_id = message.photo[-1].file_id
        user = message.from_user
        username_str = f"@{user.username}" if user.username else "No Username"

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET screenshot_file_id = ? WHERE order_id = ?", (file_id, order_id))
        
        cursor.execute("""
            SELECT o.*, c.name FROM orders o 
            JOIN categories c ON o.category_id = c.id 
            WHERE o.order_id = ?
        """, (order_id,))
        order = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        client_bot.send_message(chat_id, "✅ *Screenshot received! Admin verify karega.*")

        if SUPER_ADMIN_ID:
            admin_txt = f"🔔 *NEW PAYMENT PROOF!*\n\n" \
                        f"🆔 Order: `#{order_id}`\n" \
                        f"👤 User: {user.first_name} ({username_str})\n" \
                        f"📦 Product: {order['name']}\n" \
                        f"💰 Amount: ₹{order['amount']}"
            
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"app_{order_id}", style="success"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{order_id}", style="danger"),
                InlineKeyboardButton("💬 DM User", url=f"tg://user?id={chat_id}")
            )
            master_bot.send_photo(SUPER_ADMIN_ID, file_id, caption=admin_txt, reply_markup=markup)

    client_bot.infinity_polling(skip_pending=True)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def handle_order_approval(call):
    if not is_admin(call.from_user.id):
        master_bot.answer_callback_query(call.id, "❌ Unauthorized!", show_alert=True)
        return

    action, order_id = call.data.split('_', 1)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.*, c.name FROM orders o 
        JOIN categories c ON o.category_id = c.id 
        WHERE o.order_id = ?
    """, (order_id,))
    order = cursor.fetchone()
    
    if not order:
        cursor.close()
        conn.close()
        master_bot.answer_callback_query(call.id, "❌ Order not found!")
        return

    user_chat_id = order['user_chat_id']
    cursor.execute("SELECT * FROM channels LIMIT 1")
    chan = cursor.fetchone()

    if action == 'app':
        cursor.execute("UPDATE orders SET status = 'approved' WHERE order_id = ?", (order_id,))
        conn.commit()
        cursor.close()
        conn.close()

        try:
            master_bot.edit_message_caption(f"✅ *Order #{order_id} Approved!*", call.message.chat.id, call.message.message_id)
        except Exception:
            pass

        try:
            success_msg = f"🎉 *Payment Approved!*\n\nOrder `#{order_id}` for *{order['name']}* approved."
            if chan and chan['invite_link']:
                success_msg += f"\n\n🔗 *Channel:* {chan['invite_link']}"
            master_bot.send_message(user_chat_id, success_msg)
        except Exception:
            pass
    else:
        cursor.execute("UPDATE orders SET status = 'rejected' WHERE order_id = ?", (order_id,))
        conn.commit()
        cursor.close()
        conn.close()

        try:
            master_bot.edit_message_caption(f"❌ *Order #{order_id} Rejected!*", call.message.chat.id, call.message.message_id)
        except Exception:
            pass

        try:
            master_bot.send_message(user_chat_id, f"❌ *Payment Rejected for #{order_id}.*")
        except Exception:
            pass

init_db()

def load_all_bots():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT bot_token FROM bots WHERE is_active = 1")
        bots = cursor.fetchall()
        cursor.close()
        conn.close()
        for b in bots:
            threading.Thread(target=run_client_bot, args=(b['bot_token'],)).start()
    except Exception as e:
        logger.error(f"Error: {e}")

load_all_bots()
master_bot.infinity_polling(skip_pending=True)