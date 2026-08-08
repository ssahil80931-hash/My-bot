import os
import logging
import threading
import sqlite3
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

print("SCRIPT STARTING...", flush=True)

load_dotenv()

MASTER_TOKEN = os.getenv("MASTER_TOKEN")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID") or "0")

DB_FILE = "bot_database.db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if not MASTER_TOKEN:
    logger.error("MASTER_TOKEN environment variable not set in Railway variables!")
    exit(1)

master_bot = telebot.TeleBot(MASTER_TOKEN, parse_mode='Markdown')
admin_video_states = {}
admin_wel_states = {}

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
            ('upi_id', 'Q691189350@ybl'),
            ('qr_file_id', ''),
            ('support_link', 'https://t.me/YourUsername'),
            ('start_caption', '✨ *Welcome to Viral Mms Bot* ✨\n\nGet exclusive access to premium content\nAffordable plans starting at just ₹39\n\nChoose a category below:'),
            ('welcome_photo_id', '')
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
        InlineKeyboardButton("🤖 Add New Bot", callback_data="m_add_bot"),
        InlineKeyboardButton("📋 Manage Bots", callback_data="m_list_bots"),
        InlineKeyboardButton("📦 Products", callback_data="m_products"),
        InlineKeyboardButton("🎬 Add Demo Videos", callback_data="m_add_videos"),
        InlineKeyboardButton("🖼️ Set Welcome Photo & Caption", callback_data="m_wel_pc"),
        InlineKeyboardButton("📢 Channels", callback_data="m_channels"),
        InlineKeyboardButton("💳 Payment & UPI", callback_data="m_payment"),
        InlineKeyboardButton("🖼️ Set QR Code", callback_data="m_setqr"),
        InlineKeyboardButton("🔗 Change Support Link", callback_data="m_changelink"),
        InlineKeyboardButton("📊 Stats & Revenue", callback_data="m_analytics"),
        InlineKeyboardButton("📢 Broadcast", callback_data="m_broadcast"),
        InlineKeyboardButton("👥 Users", callback_data="m_users")
    )
    master_bot.send_message(message.chat.id, "👑 *MASTER CONTROL PANEL*\n\nSelect an option below to manage your system seamlessly:", reply_markup=markup)

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
            InlineKeyboardButton("➕ Add New Product", callback_data="m_add_prod"),
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
            master_bot.edit_message_text("❌ *Pehle koi product add karein tab videos jod payenge!*", chat_id, call.message.message_id)
            return

        markup = InlineKeyboardMarkup(row_width=1)
        for p in prods:
            markup.add(InlineKeyboardButton(f"🎬 {p['name']}", callback_data=f"addv_{p['id']}"))
        markup.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="m_main_menu"))
        master_bot.edit_message_text("🎬 *Select a Product to add Demo Videos:*", chat_id, call.message.message_id, reply_markup=markup)

    elif action == 'wel_pc':
        msg = master_bot.send_message(chat_id, "📝 **Step 1/2:** Pehle apna naya **Welcome Caption** text bhejें (या 'skip' लिखें अगर पुराना रखना है):")
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

    elif action == 'setqr':
        msg = master_bot.send_message(chat_id, "🖼️ *Send or Forward the QR Code Photo now:*")
        master_bot.register_next_step_handler(msg, save_qr_photo)

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
        msg = master_bot.send_message(chat_id, "📢 *Send the broadcast message:*")
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
    markup.add(InlineKeyboardButton("✅ Done (Save All Videos)", callback_data="save_batch_videos"))
    master_bot.send_message(
        call.message.chat.id, 
        "🎬 **Product Selected!**\n\nAb aap **ek sath ya ek-ek karke 5 videos** (ya jitni marzi) mujhe bhejte/forward karte jao.\n\nJab saari videos bhej lo, toh niche diye gaye **'✅ Done (Save All Videos)'** button par click kar dena!",
        reply_markup=markup
    )
    master_bot.answer_callback_query(call.id)

@master_bot.message_handler(content_types=['video', 'document'], func=lambda message: message.chat.id in admin_video_states)
def collect_batch_videos(message):
    chat_id = message.chat.id
    v_id = message.video.file_id if message.video else (message.document.file_id if message.document else None)
    
    if v_id:
        admin_video_states[chat_id]['videos'].append(v_id)
        count = len(admin_video_states[chat_id]['videos'])
        master_bot.reply_to(message, f"📥 Video #{count} successfully queue me add ho gayi! Aur bhejo ya niche button dabao.")

@master_bot.callback_query_handler(func=lambda call: call.data == 'save_batch_videos')
def save_all_collected_videos(call):
    chat_id = call.message.chat.id
    state = admin_video_states.get(chat_id)
    
    if not state or not state['videos']:
        master_bot.answer_callback_query(call.id, "❌ Ek bhi video nahi bheji aapne!", show_alert=True)
        return
    
    cat_id = state['cat_id']
    videos = state['videos']
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        for vid in videos:
            cursor.execute("INSERT INTO category_videos (category_id, video_file_id) VALUES (?, ?)", (cat_id, vid))
        conn.commit()
        cursor.close()
        conn.close()
        
        total_saved = len(videos)
        master_bot.send_message(chat_id, f"🔥 **100% SUCCESS!**\n\nProduct ID `{cat_id}` ke liye कुल **{total_saved}** demo videos permanent save ho chuki hain!")
        del admin_video_states[chat_id]
    except Exception as e:
        master_bot.send_message(chat_id, f"❌ Error saving: `{e}`")
    
    master_bot.answer_callback_query(call.id)

def get_welcome_caption_step(message):
    chat_id = message.chat.id
    text = message.text.strip()
    admin_wel_states[chat_id] = text if text.lower() != 'skip' else None
    
    msg = master_bot.send_message(chat_id, "🖼️ **Step 2/2:** Ab apni **Welcome Photo** bhejें (caption ke sath ya bina caption ke):")
    master_bot.register_next_step_handler(msg, save_welcome_photo_final)

def save_welcome_photo_final(message):
    chat_id = message.chat.id
    if not message.photo:
        master_bot.send_message(chat_id, "❌ Kripya valid photo bhejiye! Process cancel ho gaya, dobara try karein.")
        if chat_id in admin_wel_states:
            del admin_wel_states[chat_id]
        return
    
    photo_file_id = message.photo[-1].file_id
    caption_text = admin_wel_states.get(chat_id)
    if not caption_text and message.caption:
        caption_text = message.caption
    if not caption_text:
        caption_text = "✨ *Welcome to Bot* ✨"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('welcome_photo_id', ?)", (photo_file_id,))
    cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('start_caption', ?)", (caption_text,))
    conn.commit()
    cursor.close()
    conn.close()

    if chat_id in admin_wel_states:
        del admin_wel_states[chat_id]

    master_bot.send_message(chat_id, "✅ **100% SUCCESS!**\n\nNaya Welcome Photo aur Caption permanently update ho chuka hai!")

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

        master_bot.send_message(message.chat.id, f"✅ *Bot `@{bot_username}` added successfully!*")
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

        master_bot.send_message(message.chat.id, f"✅ *Product '{name}' added successfully!*")
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ *Error format:* `{e}`")

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

        master_bot.send_message(message.chat.id, f"✅ *Channel added successfully!*")
    except Exception as e:
        master_bot.send_message(message.chat.id, f"❌ *Error format:* `{e}`")

def save_upi_setting(message):
    upi = message.text.strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('upi_id', ?)", (upi,))
    conn.commit()
    cursor.close()
    conn.close()
    master_bot.send_message(message.chat.id, f"✅ *UPI ID updated to:* `{upi}`")

def save_qr_photo(message):
    if not message.photo:
        master_bot.send_message(message.chat.id, "❌ *Please send a valid QR code photo.*")
        return
    qr_file_id = message.photo[-1].file_id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (setting_key, setting_value) VALUES ('qr_file_id', ?)", (qr_file_id,))
    conn.commit()
    cursor.close()
    conn.close()
    master_bot.send_message(message.chat.id, f"✅ *QR Code updated permanently!*")

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

        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='welcome_photo_id'")
        photo_res = cursor.fetchone()
        welcome_photo = photo_res['setting_value'] if photo_res else ""
        
        cursor.close()
        conn.close()

        markup = InlineKeyboardMarkup(row_width=1)
        for cat in categories:
            # यहाँ बटन को चौड़ा और स्टाइल लुक देने के लिए डिक्शनरी या कस्टमाइज्ड फॉर्मेट का उपयोग किया गया है
            btn = InlineKeyboardButton(f"💙 {cat['name']} - ₹{cat['price']} ({cat['days']} days)", callback_data=f"cat_{cat['id']}")
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

        cursor.execute("SELECT video_file_id FROM category_videos WHERE category_id = ?", (cat_id,))
        videos = cursor.fetchall()

        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='upi_id'")
        upi_res = cursor.fetchone()
        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='qr_file_id'")
        qr_res = cursor.fetchone()
        cursor.execute("SELECT setting_value FROM settings WHERE setting_key='support_link'")
        supp_res = cursor.fetchone()
        cursor.close()
        conn.close()

        if not category:
            client_bot.answer_callback_query(call.id, "❌ Category not found!")
            return

        if videos:
            client_bot.send_message(chat_id, "🎬 *Here are the Permanent Demo Videos for this pack:*")
            for v in videos:
                try:
                    client_bot.send_video(chat_id, v['video_file_id'])
                except Exception as e:
                    logger.error(f"Error sending video: {e}")
        else:
            client_bot.send_message(chat_id, "ℹ️ *No demo videos uploaded for this category yet. Admin can upload them from Master Panel.*")

        order_id = f"ORD{call.message.date}"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (order_id, user_chat_id, category_id, amount, status) VALUES (?, ?, ?, ?, 'pending')",
                       (order_id, chat_id, cat_id, category['price']))
        conn.commit()
        cursor.close()
        conn.close()

        upi_id = upi_res['setting_value'] if upi_res else "Q691189350@ybl"
        qr_id = qr_res['setting_value'] if qr_res else ""
        support_url = supp_res['setting_value'] if supp_res else "https://t.me/YourUsername"

        pay_text = f"💳 *PAYMENT BILL*\n\n" \
                   f"📂 Category: {category['name']}\n" \
                   f"📊 Validity / Details: {category['days']} Days Access\n" \
                   f"💰 Payable Amount: ₹{category['price']}\n" \
                   f"🆔 Order ID: `#{order_id}`\n\n" \
                   f"🌐 UPI ID: `{upi_id}`\n\n" \
                   f"✅ Pay karke niche 'I Have Paid' dabayein:"

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📸 I Have Paid (Send Screenshot)", callback_data=f"pay_ss_{order_id}"),
            InlineKeyboardButton("💬 Contact / DM Admin", url=support_url)
        )

        if qr_id:
            try:
                client_bot.send_photo(chat_id, qr_id, caption=pay_text, reply_markup=markup)
            except Exception:
                client_bot.send_message(chat_id, pay_text, reply_markup=markup)
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

        client_bot.send_message(chat_id, "✅ *Screenshot received! Admin will verify soon.*")

        if SUPER_ADMIN_ID:
            admin_txt = f"🔔 *NEW PAYMENT PROOF!*\n\n" \
                        f"🆔 Order ID: `#{order_id}`\n" \
                        f"👤 User: {user.first_name} ({username_str})\n" \
                        f"📦 Product: {order['name']}\n" \
                        f"💰 Amount: ₹{order['amount']}"
            
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"app_{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{order_id}"),
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
            success_msg = f"🎉 *Payment Approved!*\n\nYour order `#{order_id}` for *{order['name']}* is approved."
            if chan and chan['invite_link']:
                success_msg += f"\n\n🔗 *Channel Link:* {chan['invite_link']}"
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
            master_bot.send_message(user_chat_id, f"❌ *Payment Rejected for order #{order_id}.*")
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