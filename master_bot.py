import os
import random
from io import BytesIO
import qrcode
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo

# ====== CONFIGURATION ======
TOKEN = "852802558:AAEuL_8BiS2QbJjGBzzAkbedYN0N9-tw4NU"
UPI_ID = "Q691189350@ybl"
ADMIN_ID = 8999416691 
BANNER_URL = "https://pic-link-bot.lovable.app/i/telegram-1779454035738-e9821961.jpg"
PREMIUM_LINK = "https://t.me/+bQ4zD8v0JpIxZTgx"
BOT_USERNAME = "YourBotUsername" # यहाँ अपने बोट का यूजरनेम लिख ले (बिना @ के)

bot = telebot.TeleBot(TOKEN)

# कैटेगरीज और उनके दाम और वीडियोज़
CATEGORIES = {
    "desi": {"name": "💦 Real Ind!an Dēsi P0rn 🫦", "price": 69, "days": "Lifetime", "count": "50,000+", "videos": ["https://files.catbox.moe/lbqulg.mp4", "https://files.catbox.moe/7sdo4a.mp4"]},
    "allinone": {"name": "🔥 All IN ONE 100+ Category", "price": 169, "days": "Lifetime", "count": "1,00,000+", "videos": ["https://files.catbox.moe/lbqulg.mp4", "https://files.catbox.moe/7sdo4a.mp4"]},
    "channels": {"name": "🚀 100+ Channel Access", "price": 299, "days": "Lifetime", "count": "100+ Channels", "videos": ["https://files.catbox.moe/lbqulg.mp4", "https://files.catbox.moe/7sdo4a.mp4"]},
    "child": {"name": "🌝 ¢𝐡!𝐥𝐝 𝐏𝟎𝐫𝐧 𝐈𝐧𝐝!𝐚𝐧 ⚡️⚡️", "price": 99, "days": "Lifetime", "count": "50,000+", "videos": ["https://files.catbox.moe/1b9zja.mp4", "https://files.catbox.moe/i02d8l.mp4"]},
    "mom": {"name": "🥶 𝐌0𝐦 & 𝐒0𝐧 𝐕¡𝐝𝐞𝐨𝐬 😱", "price": 149, "days": "Lifetime", "count": "50,000+", "videos": ["https://files.catbox.moe/agntne.mp4", "https://files.catbox.moe/y4q779.mp4"]},
    "rape": {"name": "💀 𝐑@𝐩€ 𝐜@𝐬𝐞 𝐢𝐧𝐝¡𝐚𝐧 💢🌚", "price": 199, "days": "Lifetime", "count": "50,000+", "videos": ["https://files.catbox.moe/lr228r.mp4", "https://files.catbox.moe/ht1t5c.mp4"]}
}

user_states = {}
active_users = set()

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    active_users.add(chat_id)
    
    welcome_text = (
        "🎉 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐭𝐨 😋\n\n"
        "✨ 𝐆𝐞𝐭 𝐞𝐱𝐜𝐥𝐮𝐬𝐢𝐯𝐞 𝐚𝐜𝐜𝐞𝐬𝐬 𝐭𝐨 𝐩𝐫𝐞𝐦𝐢𝐮𝐦 𝐜𝐨𝐧𝐭𝐞𝐧𝐭\n"
        "💰 𝐀𝐟𝐟𝐨𝐫𝐝𝐚𝐛𝐥𝐞 𝐩𝐥𝐚𝐧𝐬 𝐬𝐭𝐚𝐫𝐭𝐢𝐧𝐠 𝐚𝐭 𝐣𝐮𝐬𝐭 ₹6𝟗\n\n"
        "🥵 𝐀𝐋𝐋 𝐓𝐘𝐏𝐄 𝐏𝐎𝐑𝐍 𝐕𝐈𝐃𝐄𝐎𝐒 𝐀𝐕𝐀𝐈𝐋𝐀𝐁𝐋𝐄 🥵\n\n"
        "💦 𝐑𝐞𝐚𝐥 𝐈𝐧𝐝!𝐚𝐧 𝐃ē𝐬𝐢 𝐏𝟎𝐫𝐧 🫦 𝟓𝟎𝟎𝟎𝟎+ 𝐕!𝐝𝐞𝐨𝐬\n"
        "🌝 ¢𝐡!𝐥𝐝 𝐏𝟎𝐫𝐧 𝐈𝐧𝐝!𝐚𝐧 ⚡️⚡️   𝟓𝟎𝟎𝟎𝟎+ 𝐕!𝐝𝐞𝐨𝐬💥\n"
        "🥶 𝐌0𝐦 & 𝐒0𝐧 𝐕¡𝐝𝐞𝐨𝐬 😱    𝟓𝟎𝟎𝟎𝟎+ 𝐕!𝐝𝐞𝐨𝐬\n"
        "💀 𝐑@𝐩€ 𝐜@𝐬𝐞 𝐢𝐧𝐝¡𝐚𝐧 💢🌚   𝟓𝟎𝟎𝟎𝟎+ 𝐕!𝐝𝐞𝐨𝐬\n\n"
        "🚀 𝐓𝐨𝐭𝐚𝐥 𝟏𝟎𝟎𝟎𝟎𝟎𝟎 𝐕!𝐝𝐞𝐨𝐬 𝐒𝐭0𝐜𝐤 ✅\n"
        "🚀 𝐕𝐚𝐥𝐢𝐝𝐢𝐭𝐲 :- 𝐋𝐢𝐟𝐞𝐭𝐢𝐦𝐞 ✅\n\n"
        "👇 𝐂𝐇𝐎𝐎𝐒𝐄 𝐀 𝐏𝐋𝐀𝐍 👇"
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    # सारे प्लान वाले बटन नीले (style="primary") रंग के
    for key, cat in CATEGORIES.items():
        markup.add(InlineKeyboardButton(f"{cat['name']} — ₹{cat['price']} / {cat['days']}", callback_data=f"buy_{key}", style="primary"))
    
    markup.add(
        InlineKeyboardButton("📖 How to Use", callback_data="how_to", style="primary"),
        InlineKeyboardButton("🚨 Report Issue", callback_data="report", style="primary")
    )
    
    bot.send_photo(chat_id, photo=BANNER_URL, caption=welcome_text, reply_markup=markup)

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(message.chat.id, "📢 ब्रॉडकास्ट के लिए अपना मैसेज भेजो (नीचे नीला Buy Now बटन लग जाएगा):")
    bot.register_next_step_handler(msg, send_broadcast_to_all)

def send_broadcast_to_all(message):
    success = 0
    fail = 0
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔥 Buy Now / Open Bot", url=f"https://t.me/{BOT_USERNAME}", style="primary"))

    for chat_id in active_users:
        try:
            if message.content_type == 'text':
                bot.send_message(chat_id, message.text, reply_markup=markup)
            elif message.content_type == 'photo':
                bot.send_photo(chat_id, message.photo[-1].file_id, caption=message.caption, reply_markup=markup)
            elif message.content_type == 'video':
                bot.send_video(chat_id, message.video.file_id, caption=message.caption, reply_markup=markup)
            success += 1
        except:
            fail += 1

    bot.send_message(ADMIN_ID, f"📢 Broadcast Complete!\n\n✅ Success: {success}\n❌ Failed: {fail}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data_id = call.data

    if data_id.startswith("buy_"):
        key = data_id.split("_")[1]
        data = CATEGORIES[key]
        
        videos = data['videos']
        if videos:
            try:
                if len(videos) == 1:
                    bot.send_video(chat_id, video=videos[0])
                else:
                    media_group = [InputMediaVideo(v) for v in videos[:10]]
                    bot.send_media_group(chat_id, media_group)
            except Exception as e:
                for v in videos:
                    try:
                        bot.send_video(chat_id, video=v)
                    except:
                        pass
            
        qr = qrcode.make(f"upi://pay?pa={UPI_ID}&am={data['price']}&cu=INR")
        bio = BytesIO()
        qr.save(bio, "PNG")
        bio.seek(0)
        
        caption = (
            f"💳 **PAYMENT BILL**\n\n"
            f"📂 Category: {data['name']}\n"
            f"📊 Video Count: {data['count']}\n"
            f"⏳ Validity: {data['days']}\n"
            f"💰 Payable Amount: ₹{data['price']}\n\n"
            "✅ Pay karke 'I Have Paid' dabayein."
        )
        
        markup = InlineKeyboardMarkup()
        # 'I Have Paid' बटन हरा (style="success") रंग का
        markup.add(InlineKeyboardButton("✅ I Have Paid", callback_data="ask_proof", style="success"))
        bot.send_photo(chat_id, photo=bio, caption=caption, reply_markup=markup)

    elif data_id == "report":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "🚨 Report an Issue\n\nPlease describe your issue or send a screenshot.")
    elif data_id == "how_to":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📖 How to use\n\n1. Select category.\n2. Scan QR & pay.\n3. Click 'I Have Paid' & send screenshot.")
    elif data_id == "ask_proof":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📸 Please send your payment screenshot.")
        user_states[chat_id] = True
    elif data_id.startswith(("approve_", "reject_")):
        action, user_id = data_id.split("_")
        user_id = int(user_id)
        if action == "approve":
            bot.send_message(user_id, f"Payment Approved! Link: {PREMIUM_LINK}")
        else:
            bot.send_message(user_id, "Payment Rejected.")
        try:
            bot.edit_message_caption(caption=f"✅ {action.capitalize()}ed", chat_id=chat_id, message_id=call.message.message_id)
        except:
            pass

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    active_users.add(chat_id)
    if user_states.get(chat_id):
        user = message.from_user
        markup = InlineKeyboardMarkup(row_width=2)
        # एडमिन अप्रूव (हरा) और रिजेक्ट (लाल) बटन
        markup.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}", style="success"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}", style="danger")
        )
        bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id, caption=f"Proof from @{user.username or user.first_name} (ID: {user.id})", reply_markup=markup)
        bot.reply_to(message, "✅ Proof sent to admin.")
        user_states[chat_id] = False

if __name__ == "__main__":
    print("Bot is running with Updated Welcome Message & Blue/Green Buttons...")
    bot.infinity_polling(skip_pending=True)
        
