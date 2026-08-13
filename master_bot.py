import os
import random
from io import BytesIO
import qrcode
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo

# ====== CONFIGURATION ======
TOKEN = "8715411517:AAECPXrzK4FHqzkmyrgsChtHylvm3GYS8IM"
UPI_ID = "Q691189350@ybl"
ADMIN_ID = 8999416691 
BANNER_URL = "https://pic-link-bot.lovable.app/i/telegram-1779454035738-e9821961.jpg"
PREMIUM_LINK = "https://t.me/+WdmuQrQCWHgxNjdh"
BOT_USERNAME = "VIDEO_GROUP_PURCHASE"

bot = telebot.TeleBot(TOKEN)

# सभी कैटेगरीज के 100% वर्किंग यूनिक वीडियो लिंक्स
CATEGORIES = {
    "desi": {
        "name": "💦 Real Indian Desi P*rn", 
        "price": 69, 
        "days": "Lifetime Access", 
        "count": "50,000+ Videos", 
        "videos": [
            "https://files.catbox.moe/7sdo4a.mp4",
            "https://files.catbox.moe/1b9zja.mp4",
            "https://files.catbox.moe/i02d8l.mp4",
            "https://files.catbox.moe/lbqulg.mp4"
        ]
    },
    "allinone": {
        "name": "🔥 All IN ONE 100+ Category", 
        "price": 169, 
        "days": "Lifetime Access", 
        "count": "1,00,000+ Videos", 
        "videos": [
            "https://files.catbox.moe/7sdo4a.mp4",
            "https://files.catbox.moe/lr228r.mp4",
            "https://files.catbox.moe/lbqulg.mp4",
            "https://files.catbox.moe/1b9zja.mp4"
        ]
    },
    "channels": {
        "name": "🚀 100+ Channel Access", 
        "price": 299, 
        "days": "Lifetime Access", 
        "count": "100+ VIP Channels", 
        "videos": [
            "https://files.catbox.moe/lr228r.mp4",
            "https://files.catbox.moe/i02d8l.mp4",
            "https://files.catbox.moe/7sdo4a.mp4",
            "https://files.catbox.moe/lbqulg.mp4"
        ]
    },
    "child": {
        "name": "🌝 ¢𝐡!𝐥𝐝 𝐏𝟎𝐫𝐧 𝐈𝐧𝐝!𝐚𝐧 ⚡️⚡️", 
        "price": 99, 
        "days": "Lifetime Access", 
        "count": "50,000+ Videos", 
        "videos": [
            "https://files.catbox.moe/1b9zja.mp4", 
            "https://files.catbox.moe/i02d8l.mp4",
            "https://files.catbox.moe/lbqulg.mp4",
            "https://files.catbox.moe/7sdo4a.mp4"
        ]
    },
    "mom": {
        "name": "🥶 𝐌0𝐦 & 𝐒0𝐧 𝐕¡𝐝𝐞𝐨𝐬 😱", 
        "price": 149, 
        "days": "Lifetime Access", 
        "count": "50,000+ Videos", 
        "videos": [
            "https://files.catbox.moe/i02d8l.mp4",
            "https://files.catbox.moe/lbqulg.mp4",
            "https://files.catbox.moe/lr228r.mp4",
            "https://files.catbox.moe/1b9zja.mp4"
        ]
    },
    "rape": {
        "name": "💀 𝐑@𝐩€ 𝐜@𝐬𝐞 𝐢𝐧𝐝¡𝐚𝐧 💢🌚", 
        "price": 199, 
        "days": "Lifetime Access", 
        "count": "50,000+ Videos", 
        "videos": [
            "https://files.catbox.moe/lr228r.mp4",
            "https://files.catbox.moe/7sdo4a.mp4",
            "https://files.catbox.moe/i02d8l.mp4",
            "https://files.catbox.moe/lbqulg.mp4"
        ]
    }
}

user_states = {}
active_users = set()

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    active_users.add(chat_id)
    
    welcome_text = (
        "🎉 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐭𝐨 𝐕𝐢𝐫𝐚𝐥 𝐌𝐦𝐬 𝐁𝐨𝐭😋\n\n"
        "✨ 𝐆𝐞𝐭 𝐞𝐱𝐜𝐥𝐮𝐬𝐢𝐯𝐞 𝐚𝐜𝐜𝐞𝐬𝐬 𝐭𝐨 𝐩𝐫𝐞𝐦𝐢𝐮𝐦 𝐜𝐨𝐧𝐭𝐞𝐧𝐭\n"
        "💰 𝐀𝐟𝐟𝐨𝐫𝐝𝐚𝐛𝐥𝐞 𝐩𝐥𝐚𝐧𝐬 𝐬𝐭𝐚𝐫𝐭𝐢𝐧𝐠 𝐚𝐭 𝐣𝐮𝐬𝐭 ₹𝟑𝟗\n\n"
        "🥵𝐀𝐋𝐋 𝐓𝐘𝐏𝐄 𝐏𝟎𝐑𝐍 𝐕𝐈𝐃𝐄𝐎𝐒 𝐀𝐕𝐀𝐈𝐋𝐀𝐁𝐋𝐄 🥵\n\n"
        "💦 𝐑𝐞𝐚𝐥 𝐈𝐧𝐝!𝐚𝐧 𝐃ē𝐬𝐢 𝐏𝟎𝐫𝐧 🫦 𝟓𝟎𝟎𝟎𝟎+ 𝐕!𝐝𝐞𝐨𝐬\n\n"
        "🌝 ¢𝐡!𝐥𝐝 𝐏𝟎𝐫𝐧 𝐈𝐧𝐝!𝐚𝐧 ⚡️⚡️   𝟓𝟎𝟎𝟎𝟎+ 𝐕!𝐝𝐞𝐨𝐬\n\n"
        "🥶 𝐌0𝐦 & 𝐒0𝐧 𝐕¡𝐝𝐞𝐨𝐬 😱     𝟓𝟎𝟎𝟎𝟎+ 𝐕!𝐝𝐞𝐨𝐬\n\n"
        "💀 𝐑@𝐩€ 𝐜@𝐬𝐞 𝐢𝐧𝐝¡𝐚𝐧 💢🌚   𝟓𝟎𝟎𝟎𝟎+ 𝐕!𝐝𝐞𝐨𝐬\n\n"
        "🎉 𝟓𝟎𝟎𝟎𝟎+ 𝐕𝐢𝐫𝐚𝐥 𝐕𝐢𝐝𝐞𝐨𝐬 𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞✨\n\n"
        "🎉 𝐈𝐧$𝐭𝐚𝐠𝐫𝐚𝐦 𝐂𝐫𝐞𝐚𝐭𝐨𝐫𝐬 𝐌𝐦$ 𝐋𝐞@𝐤𝐞𝐝 ✨\n\n"
        "🚀 𝐓𝐨𝐭𝐚𝐥 𝟏𝟎𝟎𝟎𝟎𝟎𝟎 𝐕!𝐝𝐞𝐨𝐬 𝐒𝐭0𝐜𝐤 ✅\n\n"
        "🚀 𝗩𝗮𝗹𝗶𝗱𝗶𝘁𝘆 :- 𝗟𝗶𝗳𝗲𝘁𝗶𝗺𝗲 ✅\n\n"
        "👇 **CHOOSE YOUR PLAN BELOW TO START** 👇"
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    for key, cat in CATEGORIES.items():
        markup.add(InlineKeyboardButton(f"{cat['name']} — ₹{cat['price']} / Lifetime", callback_data=f"buy_{key}", style="primary"))
    
    markup.add(
        InlineKeyboardButton("📖 How to Use", callback_data="how_to", style="primary"),
        InlineKeyboardButton("🚨 Report Issue", callback_data="report", style="primary")
    )
    
    bot.send_photo(chat_id, photo=BANNER_URL, caption=welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(message.chat.id, "📢 ब्रॉडकास्ट के लिए अपना मैसेज, फोटो या वीडियो भेजें:")
    bot.register_next_step_handler(msg, send_broadcast_to_all)

def send_broadcast_to_all(message):
    success, fail = 0, 0
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
            
    bot.send_message(ADMIN_ID, f"📢 Broadcast Done!\n✅ Success: {success}\n❌ Failed: {fail}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data_id = call.data
    
    try:
        bot.answer_callback_query(call.id)
    except:
        pass
    
    if data_id.startswith("buy_"):
        key = data_id.split("_")[1]
        data = CATEGORIES[key]
        
        # 1. चारों वीडियो का मीडिया ग्रुप भेजने की कोशिश (अगर कोई दिक्कत हो भी तो try-except से QR नहीं रुकेगा)
        videos = data.get('videos', [])
        if videos:
            try:
                media_group = [InputMediaVideo(v) for v in videos[:4]]
                bot.send_media_group(chat_id, media_group)
            except Exception as e:
                print(f"Media group error: {e}")
                
        # 2. QR कोड और बिल हमेशा 100% भेजा जाएगा
        qr = qrcode.make(f"upi://pay?pa={UPI_ID}&am={data['price']}&cu=INR")
        bio = BytesIO()
        qr.save(bio, "PNG")
        bio.seek(0)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ I Have Paid", callback_data="ask_proof", style="success"))
        
        bill_caption = (
            f"🔥 **VIP MEMBERSHIP BILL & DETAILS** 🔥\n\n"
            f"📂 **Category:** {data['name']}\n"
            f"💰 **Price:** ₹{data['price']} Only\n"
            f"⏳ **Validity:** {data['days']} (जीवन भर का मज़ा)\n"
            f"📦 **Total Stock:** {data['count']}\n\n"
            f"🔹 **UPI ID:** `{UPI_ID}`\n\n"
            f"⚡️ **ऊपर दिए गए QR कोड को स्कैन करके पेमेंट करें। पेमेंट सफल होने के बाद नीचे 'I Have Paid' बटन दबाकर तुरंत स्क्रीनशॉट भेजें!**"
        )
        
        bot.send_photo(
            chat_id, 
            photo=bio, 
            caption=bill_caption, 
            reply_markup=markup, 
            parse_mode="Markdown"
        )
        
    elif data_id == "ask_proof":
        bot.send_message(chat_id, "📸 कृपया अपना पेमेंट स्क्रीनशॉट यहाँ भेजें ताकि एडमिन तुरंत चेक करके अप्रूव कर सके।")
        user_states[chat_id] = True
    elif data_id == "report":
        bot.send_message(chat_id, "🚨 कोई समस्या है? कृपया अपनी समस्या लिखकर या स्क्रीनशॉट भेजकर बताएं।")
    elif data_id == "how_to":
        bot.send_message(chat_id, "📖 इस्तेमाल कैसे करें:\n\n1. पसंद की कैटेगरी चुनें।\n2. चारों डेमो वीडियो देखें।\n3. QR कोड स्कैन करके पेमेंट करें और 'I Have Paid' दबाकर स्क्रीनशॉट भेजें।")
    elif data_id.startswith(("approve_", "reject_")):
        action, user_id = data_id.split("_")
        user_id = int(user_id)
        if action == "approve": 
            bot.send_message(user_id, f"🎉 Payment Approved! Your Lifetime Access Link: {PREMIUM_LINK}")
        else: 
            bot.send_message(user_id, "❌ Payment Rejected. Please contact support.")
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
        markup.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}", style="success"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}", style="danger")
        )
        bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id, caption=f"👤 User Proof from @{user.username or user.first_name} (ID: {user.id})", reply_markup=markup)
        bot.reply_to(message, "✅ आपका पेमेंट प्रूफ एडमिन के पास भेज दिया गया है। कृपया इंतज़ार करें।")
        user_states[chat_id] = False

if __name__ == "__main__":
    print("Bot is running perfectly with all QR codes...")
    try:
        bot.remove_webhook()
    except:
        pass
    bot.infinity_polling(skip_pending=True)
    
