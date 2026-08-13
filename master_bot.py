import os
import random
from io import BytesIO
import qrcode
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo

# ====== CONFIGURATION ======
TOKEN = "8715411517:AAFDDmJb0G_lMbfwY_27WSuE4drIBgHsOU4"
UPI_ID = "Q691189350@ybl"
ADMIN_ID = 8999416691 
BANNER_URL = "https://pic-link-bot.lovable.app/i/telegram-1779454035738-e9821961.jpg"
PREMIUM_LINK = "https://t.me/+WdmuQrQCWHgxNjdh"
BOT_USERNAME = "Premiumpaiddd_bot" # यहाँ अपने बोट का यूजरनेम बिना @ के लिख ले

bot = telebot.TeleBot(TOKEN)

# हर कैटेगरी में 5-5 वीडियोज़ के लिंक सेट कर दिए हैं
CATEGORIES = {
    "desi": {
        "name": "💦 Real Indian Desi P*rn", 
        "price": 69, 
        "days": "Lifetime", 
        "count": "50,000+", 
        "videos": [
            "BAACAgQAAxkDAAEFVTFqen6mTwMyZOrLjtNUvtiRrEi2bgACoh8AAko-kFCP9Xf978FAmD0E", 
            "BAACAgQAAxkDAAEFVTdqen64cP20Ku8jSElgrDARcQvgTwACoR8AAko-kFA4tbSkJ9IbaT0E-kFCP9",
            "BAACAgQAAxkDAAEFVTZqen64DmrCN-sMHPdm1IT87FQQgwACoB8AAko-kFApU7E1sNA1Bz0E",
            "BAACAgQAAxkDAAEFVTBqen6mxug9_GX_SlaKDcm-nmbCOgACnx8AAko-kFALHKTzteWDKT0E",
            "https://files.catbox.moe/lbqulg.mp4"
        ]
    },
    "allinone": {
        "name": "🔥 All IN ONE 100+ Category", 
        "price": 169, 
        "days": "Lifetime", 
        "count": "1,00,000+", 
        "videos": [
            "https://files.catbox.moe/lbqulg.mp4", 
            "https://files.catbox.moe/7sdo4a.mp4",
            "https://files.catbox.moe/lbqulg.mp4",
            "https://files.catbox.moe/7sdo4a.mp4",
            "https://files.catbox.moe/lbqulg.mp4"
        ]
    },
    "channels": {
        "name": "🚀 100+ Channel Access", 
        "price": 299, 
        "days": "Lifetime", 
        "count": "100+ Channels", 
        "videos": [
            "https://files.catbox.moe/lbqulg.mp4", 
            "https://files.catbox.moe/7sdo4a.mp4",
            "https://files.catbox.moe/lbqulg.mp4",
            "https://files.catbox.moe/7sdo4a.mp4",
            "https://files.catbox.moe/lbqulg.mp4"
        ]
    },
    "child": {
        "name": "🌝 ¢𝐡!𝐥𝐝 𝐏𝟎𝐫𝐧 𝐈𝐧𝐝!𝐚𝐧 ⚡️⚡️", 
        "price": 99, 
        "days": "Lifetime", 
        "count": "50,000+", 
        "videos": [
            "https://files.catbox.moe/1b9zja.mp4", 
            "https://files.catbox.moe/i02d8l.mp4",
            "https://files.catbox.moe/1b9zja.mp4",
            "https://files.catbox.moe/i02d8l.mp4",
            "https://files.catbox.moe/1b9zja.mp4"
        ]
    },
    "mom": {
        "name": "🥶 𝐌0𝐦 & 𝐒0𝐧 𝐕¡𝐝𝐞𝐨𝐬 😱", 
        "price": 149, 
        "days": "Lifetime", 
        "count": "50,000+", 
        "videos": [
            "BAACAgQAAxkDAAEFVVlqeoIp_rkRc9UUjurz7r85g_7seAACqSIAAg0yGVF2LnKy2PAO9z0E, 
            "BAACAgQAAxkDAAEFVVhqeoIpgns2eGjJSFPKbF10uSo5VAACqCIAAg0yGVHSZim8ffp3vz0E",
            "BAACAgQAAxkDAAEFVVdqeoIpGh-Mh400Hts4d4ShbdDk2gACpyIAAg0yGVHAcQTi_7yyRD0E",
            "BAACAgQAAxkDAAEFVVZqeoIpOifbiZ39vmc6NK3F660u8wACpiIAAg0yGVHjNAJTvt76Uj0E",
            "BAACAgQAAxkDAAEFVVVqeoIpVO3Pk5km7x33Z1dhZOGPFAACpSIAAg0yGVGuHYqDRTwsDD0E"
        ]
    },
    "rape": {
        "name": "💀 𝐑@𝐩€ 𝐜@𝐬𝐞 𝐢nd¡𝐚𝐧 💢🌚", 
        "price": 199, 
        "days": "Lifetime", 
        "count": "50,000+", 
        "videos": [
            "BAACAgQAAxkDAAEFVT9qen7LRQHrvRZ1UL73ENgl--q-TAACqB8AAko-kFChaCYQRCAvzj0E", 
            "BAACAgQAAxkDAAEFVT5qen7LQHnYttDLYCo4OCzSyGaDbwACpx8AAko-kFCf_n6hGIrrwT0E--q-TAACqB8AAko-kFChaCYQRCAvzj0E",
            "BAACAgQAAxkDAAEFVT1qen7LRmCchl0YUXpua_y5RX13IAACph8AAko-kFAeHkh3hTXnOj0E",
            "BAACAgQAAxkDAAEFVTxqen7L4BEnfc-1tAUtSIUwMwLy-QACpR8AAko-kFA6nzWNRilfbz0E",
            "https://files.catbox.moe/lr228r.mp4"
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
        "🔥━━━━━━━━━━━━━━━━━━━🔥\n"
        "      🎉 **𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐇𝐔𝐁** 🎉\n"
        "🔥━━━━━━━━━━━━━━━━━━━🔥\n\n"
        "✨ **Get 100% Exclusive & Uncensored Private Access!**\n"
        "💎 *Super Affordable Plans Starting at Just ₹69 Only!*\n\n"
        "🚀 **AVAILABLE CATEGORIES & STOCK:**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💦 **Real Indian Desi Videos** — ₹69 (Lifetime)\n"
        "🔥 **All In One 100+ Categories** — ₹169 (Lifetime)\n"
        "🚀 **100+ Private Channels** — ₹299 (Lifetime)\n"
        "🌝 **Indian Special Content** — ₹99 (Lifetime)\n"
        "🥶 **Mom & Son Collection** — ₹149 (Lifetime)\n"
        "💀 **Rape / Heavy Desi Cases** — ₹199 (Lifetime)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ **Total Stock:** 10,00,000+ Videos ✅\n"
        "⏳ **Validity:** Lifetime Access (No Extra Charges) ✅\n\n"
        "🔗 **CHECK DEMO HERE:**\n"
        "👉 https://telegra.ph/New-Collection-Sipi-07-10\n\n"
        "👇 **CHOOSE YOUR PLAN BELOW TO START** 👇"
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    for key, cat in CATEGORIES.items():
        markup.add(InlineKeyboardButton(f"{cat['name']} — ₹{cat['price']} / {cat['days']}", callback_data=f"buy_{key}", style="primary"))
    
    markup.add(
        InlineKeyboardButton("📖 How to Use", callback_data="how_to", style="primary"),
        InlineKeyboardButton("🚨 Report Issue", callback_data="report", style="primary")
    )
    
    bot.send_photo(chat_id, photo=BANNER_URL, caption=welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(message.chat.id, "📢 ब्रॉडकास्ट मैसेज भेजें:")
    bot.register_next_step_handler(msg, send_broadcast_to_all)

def send_broadcast_to_all(message):
    success, fail = 0, 0
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔥 Buy Now / Open Bot", url=f"https://t.me/{BOT_USERNAME}", style="primary"))
    for chat_id in active_users:
        try:
            if message.content_type == 'text': bot.send_message(chat_id, message.text, reply_markup=markup)
            elif message.content_type == 'photo': bot.send_photo(chat_id, message.photo[-1].file_id, caption=message.caption, reply_markup=markup)
            success += 1
        except: fail += 1
    bot.send_message(ADMIN_ID, f"📢 Broadcast Done!\n✅ Success: {success}\n❌ Failed: {fail}")

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
                media_group = [InputMediaVideo(v) for v in videos[:10]]
                bot.send_media_group(chat_id, media_group)
            except:
                pass
                
        qr = qrcode.make(f"upi://pay?pa={UPI_ID}&am={data['price']}&cu=INR")
        bio = BytesIO(); qr.save(bio, "PNG"); bio.seek(0)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ I Have Paid", callback_data="ask_proof", style="success"))
        bot.send_photo(chat_id, photo=bio, caption=f"💳 **PAYMENT BILL**\n\n📂 Category: {data['name']}\n💰 Amount: ₹{data['price']}\n\n✅ Pay करके नीचे 'I Have Paid' बटन दबाएं और स्क्रीनशॉट भेजें।", reply_markup=markup, parse_mode="Markdown")
        
    elif data_id == "ask_proof":
        bot.send_message(chat_id, "📸 कृपया अपना पेमेंट स्क्रीनशॉट यहाँ भेजें ताकि एडमिन अप्रूव कर सके।")
        user_states[chat_id] = True
    elif data_id == "report":
        bot.send_message(chat_id, "🚨 कोई समस्या है? कृपया अपनी समस्या लिखकर या स्क्रीनशॉट भेजकर बताएं।")
    elif data_id == "how_to":
        bot.send_message(chat_id, "📖 इस्तेमाल कैसे करें:\n\n1. पसंद की कैटेगरी चुनें।\n2. QR कोड स्कैन करके पेमेंट करें।\n3. 'I Have Paid' दबाएं और स्क्रीनशॉट भेजें।")
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
        markup.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}", style="success"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}", style="danger")
        )
        bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id, caption=f"👤 User Proof from @{user.username or user.first_name} (ID: {user.id})", reply_markup=markup)
        bot.reply_to(message, "✅ आपका पेमेंट प्रूफ एडमिन के पास भेज दिया गया है। कृपया इंतज़ार करें।")
        user_states[chat_id] = False

if __name__ == "__main__":
    print("Bot is running with 5 videos per category...")
    bot.infinity_polling(skip_pending=True)
    
