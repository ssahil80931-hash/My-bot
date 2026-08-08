import os
import logging
import threading
import sqlite3
import random
import requests
from io import BytesIO
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo
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
    logger.error("MASTER_TOKEN not set!")
    exit(1)

master_bot = telebot.TeleBot(MASTER_TOKEN, parse_mode='Markdown')
admin_video_states = {}
admin_wel_states = {}
admin_qr_states = {}

# ===================== QR Themes =====================
QR_THEMES = [
    {"fill": "#000000", "back": "#FFFFFF"},
    {"fill": "#FFFFFF", "back": "#000000"},
    {"fill": "#0A66C2", "back": "#FFFFFF"},
    {"fill": "#00C853", "back": "#FFFFFF"},
    {"fill": "#D50000", "back": "#FFFFFF"},
    {"fill": "#6A1B9A", "back": "#FFFFFF"},
    {"fill": "#FF6D00", "back": "#FFFFFF"},
    {"fill": "#00BCD4", "back": "#FFFFFF"},
    {"fill": "#E91E63", "back": "#FFFFFF"},
    {"fill": "#1A237E", "back": "#E8EAF6"},
    {"fill": "#004D40", "back": "#E0F2F1"},
    {"fill": "#BF360C", "back": "#FBE9E7"},
    {"fill": "#4A148C", "back": "#F3E5F5"},
    {"fill": "#01579B", "back": "#E1F5FE"},
    {"fill": "#1B5E20", "back": "#E8F5E9"},
    {"fill": "#B71C1C", "back": "#FFEBEE"},
    {"fill": "#263238", "back": "#ECEFF1"},
    {"fill": "#3E2723", "back": "#EFEBE9"},
    {"fill": "#880E4F", "back": "#FCE4EC"},
    {"fill": "#006064", "back": "#E0F7FA"},
    {"fill": "#311B92", "back": "#EDE7F6"},
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
    try:
        files = {"fileToUpload": (filename, file_bytes)}
        data = {"reqtype": "fileupload"}
        r = requests.post("https://catbox.moe/user/api.php", data=data, files=files, timeout=60)
        if r.status_code == 200 and r.text.startswith("https://"):
            return r.text.strip()
        return None
    except Exception as e:
        logger.error(f"Catbox error: {e}")
        return None

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS bots (
        id INTEGER PRIMARY KEY AUTOINCREMENT, bot_token TEXT UNIQUE NOT NULL,
        bot_username TEXT, is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE NOT NULL,
        username TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER UNIQUE NOT NULL,
        bot_id INTEGER, first_name TEXT, username TEXT, is_blocked INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER DEFAULT 0,
        name TEXT NOT NULL, price REAL NOT NULL, days INTEGER DEFAULT 30,
        description TEXT, is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS category_videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL,
        video_url TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT UNIQUE NOT NULL,
        user_chat_id INTEGER NOT NULL, category_id INTEGER NOT NULL,
        amount REAL NOT NULL, status TEXT DEFAULT 'pending',
        screenshot_file_id TEXT, admin_message_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT, channel_id TEXT UNIQUE NOT NULL,
        channel_name TEXT, invite_link TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS settings (
        setting_key TEXT PRIMARY KEY, setting_value TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS custom_qrs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, qr_url TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute("""INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES 
        ('upi_id', 'Q691189350@ybl'),
        ('support_link', 'https://t.me/YourUsername'),
        ('start_caption', '✨ *Welcome* ✨\\n\\nChoose a category:'),
        ('welcome_photo_url', '')""")
    conn.commit()
    cursor.close()
    conn.close()

def is_admin(user_id):
    if SUPER_ADMIN_ID and user_id == SUPER_ADMIN_ID:
        return True
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return res is not None

def get_setting(key, default=""):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT setting_value FROM settings WHERE setting_key=?", (key,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row['setting_value'] if row else default

# ===================== MASTER PANEL =====================
@master_bot.message_handler(commands=['start'])
def master_start(message):
    if not is_admin(message.from_user.id):
        master_bot.send_message(message.chat.id, "❌ Unauthorized")
        return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🤖 Add Bot", callback_data="m_add_bot", style="primary"),
        InlineKeyboardButton("📋 Manage Bots", callback_data="m_list_bots"),
        InlineKeyboardButton("📦 Products", callback_data="m_products", style="primary"),
        InlineKeyboardButton("🎬 Add Demo Videos", callback_data="m_add_videos", style="success"),
        InlineKeyboardButton("🖼️ Welcome Photo", callback_data="m_wel_pc", style="primary"),
        InlineKeyboardButton("💳 UPI / Payment", callback_data="m_payment"),
        InlineKeyboardButton("🖼️ Custom QR Images", callback_data="m_custom_qr", style="success"),
        InlineKeyboardButton("🔗 Support Link", callback_data="m_changelink"),
        InlineKeyboardButton("📢 Channels", callback_data="m_channels"),
        InlineKeyboardButton("📊 Analytics", callback_data="m_analytics"),
        InlineKeyboardButton("📢 Broadcast", callback_data="m_broadcast", style="danger"),
        InlineKeyboardButton("👥 Users", callback_data="m_users"),
    )
    master_bot.send_message(message.chat.id, "👑 *MASTER CONTROL PANEL*", reply_markup=markup)

@master_bot.callback_query_handler(func=lambda call: call.data.startswith('m_'))
def master_callbacks(call):
    if not is_admin(call.from_user.id):
        master_bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return
    action = call.data[2:]
    chat_id = call.message.chat.id

    if action == "main_menu":
        try: master_bot.delete_message(chat_id, call.message.message_id)
        except: pass
        master_start(call.message)
        return

    if action == "add_bot":
        msg = master_bot.send_message(chat_id, "🤖 New Bot Token भेजो:")
        master_bot.register_next_step_handler(msg, save_new_bot)

    elif action == "list_bots":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bots")
        bots = cursor.fetchall()
        cursor.close()
        conn.close()
        text = "🤖 *Bots:*\n\n"
        for b in bots:
            text += f"• @{b['bot_username']} {'🟢' if b['is_active'] else '🔴'}\n"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back", callback_data="m_main_menu"))
        master_bot.edit_message_text(text or "No bots", chat_id, call.message.message_id, reply_markup=markup)

    elif action == "products":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories")
        prods = cursor.fetchall()
        cursor.close()
        conn.close()
        text = "📦 *Products:*\n\n"
        for p in prods:
            text += f"`{p['id']}` | {p['name']} - ₹{p['price']}\n"
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("➕ Add Product", callback_data="m_add_prod", style="success"),
                   InlineKeyboardButton("🔙 Back", callback_data="m_main_menu"))
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == "add_prod":
        msg = master_bot.send_message(chat_id, "Format: `Name | Price | Days | Description`")
        master_bot.register_next_step_handler(msg, save_new_product)

    elif action == "add_videos":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories")
        prods = cursor.fetchall()
        cursor.close()
        conn.close()
        if not prods:
            master_bot.answer_callback_query(call.id, "Pehle product add karo!", show_alert=True)
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for p in prods:
            markup.add(InlineKeyboardButton(p['name'], callback_data=f"addv_{p['id']}"))
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="m_main_menu"))
        master_bot.edit_message_text("🎬 Product चुनो:", chat_id, call.message.message_id, reply_markup=markup)

    elif action == "wel_pc":
        msg = master_bot.send_message(chat_id, "📝 Welcome Caption भेजो (या skip):")
        master_bot.register_next_step_handler(msg, get_welcome_caption_step)

    elif action == "payment":
        msg = master_bot.send_message(chat_id, "💳 नया UPI ID भेजो:")
        master_bot.register_next_step_handler(msg, save_upi_setting)

    elif action == "custom_qr":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM custom_qrs")
        cnt = cursor.fetchone()['cnt']
        cursor.close()
        conn.close()
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ Add Custom QR Images", callback_data="m_add_custom_qr", style="success"),
            InlineKeyboardButton(f"🗑️ Clear All ({cnt})", callback_data="m_clear_qr", style="danger"),
            InlineKeyboardButton("🔙 Back", callback_data="m_main_menu")
        )
        master_bot.edit_message_text(f"🖼️ *Custom QR Images*\n\nCurrently saved: {cnt}\n\nअपने QR अपलोड करो, पेमेंट पर रैंडम आएंगे।", chat_id, call.message.message_id, reply_markup=markup)

    elif action == "add_custom_qr":
        admin_qr_states[chat_id] = []
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Done", callback_data="save_custom_qrs", style="success"))
        master_bot.send_message(chat_id, "🖼️ अपने QR Images भेजो (एक या ज्यादा)।\nजब हो जाए तो Done दबाओ।", reply_markup=markup)

    elif action == "clear_qr":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM custom_qrs")
        conn.commit()
        cursor.close()
        conn.close()
        master_bot.answer_callback_query(call.id, "सभी Custom QR डिलीट हो गए!")
        master_bot.edit_message_text("🖼️ Custom QR क्लियर हो गए।", chat_id, call.message.message_id)

    elif action == "changelink":
        msg = master_bot.send_message(chat_id, "🔗 Support Link भेजो:")
        master_bot.register_next_step_handler(msg, save_support_link)

    elif action == "channels":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("➕ Add Channel", callback_data="m_add_chan", style="success"),
                   InlineKeyboardButton("🔙 Back", callback_data="m_main_menu"))
        master_bot.edit_message_text("📢 Channels", chat_id, call.message.message_id, reply_markup=markup)

    elif action == "add_chan":
        msg = master_bot.send_message(chat_id, "`ChannelID | Name | InviteLink`")
        master_bot.register_next_step_handler(msg, save_new_channel)

    elif action == "analytics":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM users")
        users = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM orders")
        orders = cursor.fetchone()['c']
        cursor.execute("SELECT SUM(amount) as r FROM orders WHERE status='approved'")
        rev = cursor.fetchone()['r'] or 0
        cursor.close()
        conn.close()
        text = f"📊 *Stats*\n\nUsers: {users}\nOrders: {orders}\nRevenue: ₹{rev}"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back", callback_data="m_main_menu"))
        master_bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif action == "broadcast":
        msg = master_bot.send_message(chat_id, "📢 Broadcast message भेजो (text/photo/video):")
        master_bot.register_next_step_handler(msg, execute_broadcast)

    elif action == "users":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM users")
        cnt = cursor.fetchone()['c']
        cursor.close()
        conn.close()
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back", callback_data="m_main_menu"))
        master_bot.edit_message_text(f"👥 Total Users: {cnt}", chat_id, call.message.message_id, reply_markup=markup)

    master_bot.answer_callback_query(call.id)

# ---------- Custom QR collect ----------
@master_bot.message_handler(content_types=['photo'], func=lambda m: m.chat.id in admin_qr_states)
def collect_custom_qr(message):
    chat_id = message.chat.id
    try:
        file_id = message.photo[-1].file_id
        file_info = master_bot.get_file(file_id)
        downloaded = master_bot.download_file(file_info.file_path)
        url = upload_to_catbox(downloaded, "qr.png")
        if url:
            admin_qr_states[chat_id].append(url)
            master_bot.reply_to(message, f"✅ QR #{len(admin_qr_states[chat_id])} saved!")
        else:
            master_bot.reply_to(message, "❌ Upload fail")
    except Exception as e:
        master_bot.reply_to(message, f"Error: {e}")

@master_bot.callback_query_handler(func=lambda call: call.data == "save_custom_qrs")
def save_custom_qrs(call):
    chat_id = call.message.chat.id
    urls = admin_qr_states.get(chat_id, [])
    if not urls:
        master_bot.answer_callback_query(call.id, "कोई QR नहीं भेजा!", show_alert=True)
        return
    conn = get_db()
    cursor = conn.cursor()
    for u in urls:
        cursor.execute("INSERT INTO custom_qrs (qr_url) VALUES (?)", (u,))
    conn.commit()
    cursor.close()
    conn.close()
    del admin_qr_states[chat_id]
    master_bot.send_message(chat_id, f"✅ {len(urls)} Custom QR permanent save हो गए!")
    master_bot.answer_callback_query(call.id)

# ---------- Demo Videos ----------
@master_bot.callback_query_handler(func=lambda call: call.data.startswith('addv_'))
def select_product_for_video(call):
    if not is_admin(call.from_user.id): return
    cat_id = int(call.data.split('_')[1])
    admin_video_states[call.message.chat.id] = {'cat_id': cat_id, 'videos': []}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Done", callback_data="save_batch_videos", style="success"))
    master_bot.send_message(call.message.chat.id, "🎬 Videos भेजो। Done दबाओ जब खत्म हो।", reply_markup=markup)
    master_bot.answer_callback_query(call.id)

@master_bot.message_handler(content_types=['video', 'document'], func=lambda m: m.chat.id in admin_video_states)
def collect_batch_videos(message):
    chat_id = message.chat.id
    file_id = message.video.file_id if message.video else message.document.file_id
    try:
        file_info = master_bot.get_file(file_id)
        downloaded = master_bot.download_file(file_info.file_path)
        url = upload_to_catbox(downloaded, "video.mp4")
        if url:
            admin_video_states[chat_id]['videos'].append(url)
            master_bot.reply_to(message, f"📥 Video #{len(admin_video_states[chat_id]['videos'])} saved!")
        else:
            master_bot.reply_to(message, "❌ Fail")
    except Exception as e:
        master_bot.reply_to(message, f"Error: {e}")

@master_bot.callback_query_handler(func=lambda call: call.data == "save_batch_videos")
def save_all_collected_videos(call):
    chat_id = call.message.chat.id
    state = admin_video_states.get(chat_id)
    if not state or not state['videos']:
        master_bot.answer_callback_query(call.id, "No videos!", show_alert=True)
        return
    conn = get_db()
    cursor = conn.cursor()
    for url in state['videos']:
        cursor.execute("INSERT INTO category_videos (category_id, video_url) VALUES (?, ?)", (state['cat_id'], url))
    conn.commit()
    cursor.close()
    conn.close()
    del admin_video_states[chat_id]
    master_bot.send_message(chat_id, f"✅ {len(state['videos'])} videos save हो गईं!")
    master_bot.answer_callback_query(call.id)

# ---------- Welcome ----------
def get_welcome_caption_step(message):
    chat_id = message.chat.id
    admin_wel_states[chat_id] = message.text.strip() if message.text.lower() != "skip" else None
    msg = master_bot.send_message(chat_id, "🖼️ Welcome Photo भेजो:")
    master_bot.register_next_step_handler(msg, save_welcome_photo_final)

def save_welcome_photo_final(message):
    chat_id = message.chat.id
    if not message.photo:
        master_bot.send_message(chat_id, "❌ Photo भेजो")
        return
    try:
        file_id = message.photo[-1].file_id
        file_info = master_bot.get_file(file_id)
        downloaded = master_bot.download_file(file_info.file_path)
        url = upload_to_catbox(downloaded, "welcome.jpg")
        if not url:
            master_bot.send_message(chat_id, "❌ Upload fail")
            return
        caption = admin_wel_states.get(chat_id) or message.caption or "✨ Welcome ✨"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('welcome_photo_url', ?)", (url,))
        cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('start_caption', ?)", (caption,))
        conn.commit()
        cursor.close()
        conn.close()
        if chat_id in admin_wel_states: del admin_wel_states[chat_id]
        master_bot.send_message(chat_id, f"✅ Welcome set!\n{url}")
    except Exception as e:
        master_bot.send_message(chat_id, f"Error: {e}")

# ---------- Save helpers ----------
def save_new_bot(message):
    token = message.text.strip()
    try:
        temp = telebot.TeleBot(token)
        info = temp.get_me()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bots (bot_token, bot_username) VALUES (?, ?)", (token, info.username))
        conn.commit()
        cursor.close()
        conn.close()
        master_bot.send_message(message.chat.id, f"✅ @{info.username} added!")
        threading.Thread(target=run_client_bot, args=(token,), daemon=True).start()
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ {e}")

def save_new_product(message):
    try:
        parts = [p.strip() for p in message.text.split("|")]
        name, price, days = parts[0], float(parts[1]), int(parts[2])
        desc = parts[3] if len(parts) > 3 else ""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name, price, days, description) VALUES (?,?,?,?)", (name, price, days, desc))
        conn.commit()
        cursor.close()
        conn.close()
        master_bot.send_message(message.chat.id, f"✅ {name} added!")
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ {e}")

def save_new_channel(message):
    try:
        parts = [p.strip() for p in message.text.split("|")]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO channels (channel_id, channel_name, invite_link) VALUES (?,?,?)", (parts[0], parts[1], parts[2] if len(parts)>2 else ""))
        conn.commit()
        cursor.close()
        conn.close()
        master_bot.send_message(message.chat.id, "✅ Channel added!")
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ {e}")

def save_upi_setting(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('upi_id', ?)", (message.text.strip(),))
    conn.commit()
    cursor.close()
    conn.close()
    master_bot.send_message(message.chat.id, "✅ UPI updated!")

def save_support_link(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('support_link', ?)", (message.text.strip(),))
    conn.commit()
    cursor.close()
    conn.close()
    master_bot.send_message(message.chat.id, "✅ Link updated!")

def execute_broadcast(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM users WHERE is_blocked=0")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    success = 0
    for u in users:
        try:
            if message.content_type == "text":
                master_bot.send_message(u['chat_id'], message.text)
            elif message.content_type == "photo":
                master_bot.send_photo(u['chat_id'], message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == "video":
                master_bot.send_video(u['chat_id'], message.video.file_id, caption=message.caption)
            success += 1
        except: pass
    master_bot.send_message(message.chat.id, f"📢 Sent to {success} users")

# ===================== CLIENT BOT =====================
def run_client_bot(token):
    client_bot = telebot.TeleBot(token, parse_mode='Markdown')

    @client_bot.message_handler(commands=['start'])
    def client_start(message):
        chat_id = message.chat.id
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO users (chat_id, first_name, username) VALUES (?,?,?)
            ON CONFLICT(chat_id) DO UPDATE SET first_name=excluded.first_name, username=excluded.username""",
            (chat_id, message.from_user.first_name, message.from_user.username))
        conn.commit()
        cursor.execute("SELECT * FROM categories WHERE is_active=1")
        categories = cursor.fetchall()
        caption = get_setting("start_caption", "✨ Welcome ✨")
        welcome_photo = get_setting("welcome_photo_url")
        cursor.close()
        conn.close()

        markup = InlineKeyboardMarkup(row_width=1)
        for cat in categories:
            markup.add(InlineKeyboardButton(f"💙 {cat['name']} - ₹{cat['price']}", callback_data=f"cat_{cat['id']}", style="primary"))

        if welcome_photo:
            try:
                client_bot.send_photo(chat_id, welcome_photo, caption=caption, reply_markup=markup)
                return
            except: pass
        client_bot.send_message(chat_id, caption, reply_markup=markup)

    @client_bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
    def handle_category(call):
        chat_id = call.message.chat.id
        cat_id = call.data.split("_")[1]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id=?", (cat_id,))
        category = cursor.fetchone()
        cursor.execute("SELECT video_url FROM category_videos WHERE category_id=?", (cat_id,))
        videos = [r['video_url'] for r in cursor.fetchall()]
        upi_id = get_setting("upi_id", "Q691189350@ybl")
        support = get_setting("support_link", "https://t.me/")
        cursor.close()
        conn.close()

        if not category:
            client_bot.answer_callback_query(call.id, "Not found")
            return

        # Send all videos together
        if videos:
            try:
                if len(videos) == 1:
                    client_bot.send_video(chat_id, videos[0])
                else:
                    media = [InputMediaVideo(v) for v in videos[:10]]  # max 10
                    client_bot.send_media_group(chat_id, media)
            except Exception as e:
                logger.error(f"Video send error: {e}")
                for v in videos:
                    try: client_bot.send_video(chat_id, v)
                    except: pass
        else:
            client_bot.send_message(chat_id, "ℹ️ No demo videos yet.")

        order_id = f"ORD{call.message.date}{random.randint(100,999)}"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (order_id, user_chat_id, category_id, amount, status) VALUES (?,?,?,?,'pending')",
                       (order_id, chat_id, cat_id, category['price']))
        conn.commit()
        cursor.close()
        conn.close()

        # QR: custom or generated
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT qr_url FROM custom_qrs")
        custom_qrs = [r['qr_url'] for r in cursor.fetchall()]
        cursor.close()
        conn.close()

        pay_text = f"💳 *PAYMENT BILL*\n\n📂 {category['name']}\n💰 ₹{category['price']}\n🆔 `{order_id}`\n\nUPI: `{upi_id}`\n\n✅ Pay करके Screenshot भेजो"

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📸 I Have Paid", callback_data=f"pay_ss_{order_id}", style="success"),
            InlineKeyboardButton("💬 Contact Admin", url=support)
        )

        if custom_qrs:
            qr_url = random.choice(custom_qrs)
            client_bot.send_photo(chat_id, qr_url, caption=pay_text, reply_markup=markup)
        else:
            qr_bio = generate_random_qr(upi_id, category['price'])
            client_bot.send_photo(chat_id, qr_bio, caption=pay_text, reply_markup=markup)

    @client_bot.callback_query_handler(func=lambda call: call.data.startswith("pay_ss_"))
    def ask_screenshot(call):
        order_id = call.data.split("_")[2]
        msg = client_bot.send_message(call.message.chat.id, f"📸 Order `{order_id}` का Screenshot भेजो:")
        client_bot.register_next_step_handler(msg, receive_screenshot, order_id)

    def receive_screenshot(message, order_id):
        if not message.photo:
            client_bot.send_message(message.chat.id, "❌ Photo भेजो")
            return
        try:
            file_id = message.photo[-1].file_id
            file_info = client_bot.get_file(file_id)
            downloaded = client_bot.download_file(file_info.file_path)
            ss_url = upload_to_catbox(downloaded, "ss.jpg")
            if not ss_url:
                client_bot.send_message(message.chat.id, "❌ Upload fail, dobara bhejo")
                return

            user = message.from_user
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET screenshot_file_id=? WHERE order_id=?", (ss_url, order_id))
            cursor.execute("""SELECT o.*, c.name FROM orders o JOIN categories c ON o.category_id=c.id WHERE o.order_id=?""", (order_id,))
            order = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            client_bot.send_message(message.chat.id, "✅ Screenshot मिल गया! Admin चेक करेगा।")

            if SUPER_ADMIN_ID and order:
                admin_txt = f"🔔 *NEW PAYMENT*\n\n🆔 `{order_id}`\n👤 {user.first_name} (@{user.username or 'N/A'})\n📦 {order['name']}\n💰 ₹{order['amount']}"
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    InlineKeyboardButton("✅ Approve", callback_data=f"app_{order_id}", style="success"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"rej_{order_id}", style="danger")
                )
                master_bot.send_photo(SUPER_ADMIN_ID, ss_url, caption=admin_txt, reply_markup=markup)
        except Exception as e:
            logger.error(e)
            client_bot.send_message(message.chat.id, "❌ Error, dobara try करो")

    client_bot.infinity_polling(skip_pending=True)

# ===================== APPROVE / REJECT =====================
@master_bot.callback_query_handler(func=lambda call: call.data.startswith(("app_", "rej_")))
def handle_approval(call):
    if not is_admin(call.from_user.id):
        master_bot.answer_callback_query(call.id, "Unauthorized", show_alert=True)
        return
    action, order_id = call.data.split("_", 1)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""SELECT o.*, c.name FROM orders o JOIN categories c ON o.category_id=c.id WHERE o.order_id=?""", (order_id,))
    order = cursor.fetchone()
    if not order:
        master_bot.answer_callback_query(call.id, "Order not found")
        return
    cursor.execute("SELECT invite_link FROM channels LIMIT 1")
    chan = cursor.fetchone()
    if action == "app":
        cursor.execute("UPDATE orders SET status='approved' WHERE order_id=?", (order_id,))
        conn.commit()
        try: master_bot.edit_message_caption(f"✅ Approved #{order_id}", call.message.chat.id, call.message.message_id)
        except: pass
        try:
            msg = f"🎉 Payment Approved!\nOrder `{order_id}` - {order['name']}"
            if chan and chan['invite_link']:
                msg += f"\n\n🔗 {chan['invite_link']}"
            master_bot.send_message(order['user_chat_id'], msg)
        except: pass
    else:
        cursor.execute("UPDATE orders SET status='rejected' WHERE order_id=?", (order_id,))
        conn.commit()
        try: master_bot.edit_message_caption(f"❌ Rejected #{order_id}", call.message.chat.id, call.message.message_id)
        except: pass
        try: master_bot.send_message(order['user_chat_id'], f"❌ Payment Rejected for `{order_id}`")
        except: pass
    cursor.close()
    conn.close()
    master_bot.answer_callback_query(call.id)

# ===================== START =====================
init_db()

def load_all_bots():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT bot_token FROM bots WHERE is_active=1")
        for b in cursor.fetchall():
            threading.Thread(target=run_client_bot, args=(b['bot_token'],), daemon=True).start()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(e)

load_all_bots()
master_bot.infinity_polling(skip_pending=True)