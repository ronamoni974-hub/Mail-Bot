import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from mailtd import MailTD
import time
import threading
import re
import random
import string
import html

TOKEN = '8572418006:AAEQBCXBPxa35yBiSWeaVWVvLP9N326fJos'
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

MAILTD_TOKEN = 'td_18c938ad445ea882ebc1110b22723e1ca1ddef7911dde89e80a095f3c2120119'
mail_client = MailTD(MAILTD_TOKEN)

# ইউজারদের ডেটা স্টোর (একাধিক মেইল সেভ রাখার জন্য)
user_data = {}

# --- Bottom Menu Bar ---
def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("✨ New Pro Mail"), KeyboardButton("🏠 Dashboard"))
    markup.add(KeyboardButton("🗑️ Delete Active"), KeyboardButton("⚡ About Bot"))
    return markup

# --- Smart Extractor (Fix for empty body & OTP in subject) ---
def extract_and_format(subject, body):
    subject_text = subject if subject else "No Subject"
    body_text = body if body else ""
    
    # HTML ট্যাগ রিমুভ করা
    clean_body = re.sub(r'<[^>]+>', '', body_text).strip()
    if not clean_body:
        clean_body = subject_text  # বডি ফাঁকা থাকলে সাবজেক্টকেই বডি হিসেবে ধরবে
        
    escaped_body = html.escape(clean_body)
    full_text = f"{subject_text} {escaped_body}"
    
    # 4-8 ডিজিটের কোড স্ক্যান করা
    otp_match = re.search(r'\b(\d{4,8})\b', full_text)
    otp_section = f"🔑 <b>Auto-Extracted Code:</b> <code>{otp_match.group(1)}</code>\n" if otp_match else ""
    
    # বডির ভেতরের কোডগুলোকেও ক্লিকেবল করা
    formatted_body = re.sub(r'\b(\d{4,8})\b', r'<code>\1</code>', escaped_body)
    
    return otp_section, formatted_body

# --- Auto Checker Engine ---
def auto_check_mail():
    while True:
        try:
            for chat_id, data in list(user_data.items()):
                # শুধুমাত্র ইউজারের অ্যাক্টিভ মেইল চেক করবে ফাস্ট পারফরম্যান্সের জন্য
                active_index = data.get('active_index', -1)
                if active_index >= 0 and data['accounts']:
                    account = data['accounts'][active_index]
                    account_id = account['account_id']
                    
                    messages, _ = mail_client.messages.list(account_id)
                    for msg_preview in messages:
                        msg_id = msg_preview.id
                        if msg_id not in account['seen_msgs']:
                            account['seen_msgs'].add(msg_id)
                            
                            full_msg = mail_client.messages.get(account_id, msg_id)
                            otp_section, smart_body = extract_and_format(full_msg.subject, full_msg.text_body)
                            
                            mail_alert = (
                                f"🔔 <b>New Message in </b><code>{account['email']}</code>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"{otp_section}"
                                f"📌 <b>Subject:</b> {html.escape(full_msg.subject or 'No Subject')}\n\n"
                                f"💬 <b>Message:</b>\n{smart_body}\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"<i>⚡ Live tracking is active...</i>"
                            )
                            bot.send_message(chat_id, mail_alert, reply_markup=get_main_menu())
        except Exception:
            pass
        time.sleep(4)

threading.Thread(target=auto_check_mail, daemon=True).start()

# --- Bot Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {'accounts': [], 'active_index': -1}
        
    welcome_text = (
        "👋 <b>Welcome to Premium Mail Bot!</b>\n\n"
        "নিচের বাটনগুলো ব্যবহার করে মেইল জেনারেট করুন এবং ইনবক্স ম্যানেজ করুন।"
    )
    bot.send_message(chat_id, welcome_text, reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text
    
    if chat_id not in user_data:
        user_data[chat_id] = {'accounts': [], 'active_index': -1}

    if text == "✨ New Pro Mail":
        # Dynamic Loading Animation
        anim_msg = bot.send_message(chat_id, "<i>[■□□□] Initializing secure servers...</i>")
        time.sleep(0.4)
        bot.edit_message_text("<i>[■■□□] Bypassing security protocols...</i>", chat_id, anim_msg.message_id)
        time.sleep(0.4)
        bot.edit_message_text("<i>[■■■□] Generating unique address...</i>", chat_id, anim_msg.message_id)
        
        try:
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            domains = mail_client.accounts.list_domains()
            domain_name = domains[0].domain if hasattr(domains[0], 'domain') else domains[0]
            email_address = f"{username}@{domain_name}"
            
            account = mail_client.accounts.create(email_address, password="propassword123")
            
            # নতুন মেইল স্টোর করা
            user_data[chat_id]['accounts'].append({
                'account_id': account.id,
                'email': account.address,
                'seen_msgs': set()
            })
            user_data[chat_id]['active_index'] = len(user_data[chat_id]['accounts']) - 1
            
            bot.edit_message_text("<i>[■■■■] Setup Complete!</i>", chat_id, anim_msg.message_id)
            time.sleep(0.3)
            
            dashboard_text = (
                f"🎉 <b>New Mail Generated Successfully!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📧 <b>Active Address:</b>\n"
                f"<code>{account.address}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🟢 <i>Live listening... Waiting for emails!</i>"
            )
            bot.edit_message_text(dashboard_text, chat_id, anim_msg.message_id)
            
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", chat_id, anim_msg.message_id)

    elif text == "🏠 Dashboard":
        accounts = user_data[chat_id]['accounts']
        if not accounts:
            bot.send_message(chat_id, "⚠️ আপনার কোনো মেইল নেই। আগে নতুন মেইল জেনারেট করুন।")
            return
            
        dash_text = "🗂️ <b>Your Mail Dashboard</b>\n\n"
        markup = InlineKeyboardMarkup(row_width=1)
        
        for i, acc in enumerate(accounts):
            status = "🟢 Active" if i == user_data[chat_id]['active_index'] else "⚪ Standby"
            dash_text += f"{i+1}. <code>{acc['email']}</code> [{status}]\n"
            markup.add(InlineKeyboardButton(f"Switch to Mail {i+1}", callback_data=f"switch_{i}"))
            
        bot.send_message(chat_id, dash_text, reply_markup=markup)

    elif text == "🗑️ Delete Active":
        if user_data[chat_id]['accounts']:
            active_idx = user_data[chat_id]['active_index']
            del_mail = user_data[chat_id]['accounts'].pop(active_idx)
            
            if user_data[chat_id]['accounts']:
                user_data[chat_id]['active_index'] = 0 # প্রথমটিতে শিফট করবে
            else:
                user_data[chat_id]['active_index'] = -1
                
            bot.send_message(chat_id, f"🗑️ মেইল <code>{del_mail['email']}</code> ডিলেট করা হয়েছে!")
        else:
            bot.send_message(chat_id, "⚠️ ডিলেট করার মতো কোনো অ্যাক্টিভ মেইল নেই।")

    elif text == "⚡ About Bot":
        about_text = (
            "🚀 <b>Premium Temp Mail Bot v2.0</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• API: Mail.td Pro\n"
            "• Speed: Ultra Fast (4s Ping)\n"
            "• Auto OTP Extractor: ✅ Enabled\n"
            "• Developer: Md Walid (ExamPro Admin)\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "<i>Designed with modern Glassmorphism-inspired chat dynamics.</i>"
        )
        bot.send_message(chat_id, about_text)

@bot.callback_query_handler(func=lambda call: call.data.startswith('switch_'))
def handle_switch(call):
    chat_id = call.message.chat.id
    idx = int(call.data.split('_')[1])
    
    if idx < len(user_data.get(chat_id, {}).get('accounts', [])):
        user_data[chat_id]['active_index'] = idx
        active_email = user_data[chat_id]['accounts'][idx]['email']
        bot.answer_callback_query(call.id, f"Switched to {active_email}")
        bot.edit_message_text(f"✅ <b>Successfully switched to:</b>\n<code>{active_email}</code>\n\n🟢 <i>Live listening activated for this mail.</i>", chat_id, call.message.message_id)

print("Pro Bot V2 is live with Dashboard...")
bot.polling(none_stop=True)
