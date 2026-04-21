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

# ইউজারের সব ডেটা স্টোর করার ডিকশনারি
user_data = {}

# --- Bottom Menu Bar (Colorful Emojis for Aesthetic) ---
def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("✨ New Pro Mail"), KeyboardButton("🏠 Dashboard"))
    markup.add(KeyboardButton("👤 Profile"), KeyboardButton("🗑️ Delete Active"))
    markup.add(KeyboardButton("⚡ About Bot"))
    return markup

# --- Smart Extractor (Code Box & Verify Links) ---
def extract_and_format(subject, body):
    subject_text = subject if subject else "No Subject"
    body_text = body if body else ""
    
    clean_body = re.sub(r'<[^>]+>', '', body_text).strip()
    if not clean_body:
        clean_body = subject_text 
        
    full_text = f"{subject_text} {clean_body}"
    escaped_body = html.escape(clean_body)
    
    # 1. Extract 4-8 digit Code and put in a beautiful Blockquote Box
    otp_match = re.search(r'\b(\d{4,8})\b', full_text)
    otp_section = f"<blockquote>🔑 <b>Verification Code:</b>\n👉 <code>{otp_match.group(1)}</code> 👈</blockquote>\n\n" if otp_match else ""
    
    # 2. Extract Verification Links (http/https)
    link_match = re.search(r'(https?://[^\s]+)', full_text)
    extracted_link = link_match.group(1) if link_match else None
    
    # Format inline codes in body
    formatted_body = re.sub(r'\b(\d{4,8})\b', r'<code>\1</code>', escaped_body)
    
    return otp_section, formatted_body, extracted_link

# --- Auto Checker Engine ---
def auto_check_mail():
    while True:
        try:
            for chat_id, data in list(user_data.items()):
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
                            otp_section, smart_body, verify_link = extract_and_format(full_msg.subject, full_msg.text_body)
                            
                            mail_alert = (
                                f"🔔 <b>New Message in</b> <code>{account['email']}</code>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"{otp_section}"
                                f"📌 <b>Subject:</b> {html.escape(full_msg.subject or 'No Subject')}\n\n"
                                f"💬 <b>Message:</b>\n{smart_body}\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                            )
                            
                            # লিংকের জন্য সুন্দর বাটন তৈরি
                            markup = InlineKeyboardMarkup()
                            if verify_link:
                                markup.add(InlineKeyboardButton("🔗 Click to Verify / Open Link", url=verify_link))
                            
                            # মেসেজ পাঠিয়ে তার ID সেভ করা (পরে ডিলিট করার জন্য)
                            sent_msg = bot.send_message(chat_id, mail_alert, reply_markup=markup, disable_web_page_preview=True)
                            account['msg_ids'].append(sent_msg.message_id)
                            
        except Exception:
            pass
        time.sleep(4)

threading.Thread(target=auto_check_mail, daemon=True).start()

# --- Initialize User ---
def init_user(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {'accounts': [], 'active_index': -1, 'total_generated': 0}

# --- Bot Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    init_user(message.chat.id)
    welcome_text = "👋 <b>Welcome to Premium Mail Bot!</b>\n\nনিচের বাটনগুলো ব্যবহার করে মেইল জেনারেট করুন এবং ইনবক্স ম্যানেজ করুন।"
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text
    init_user(chat_id)

    if text == "✨ New Pro Mail":
        anim_msg = bot.send_message(chat_id, "<i>[■□□□] Initializing secure servers...</i>")
        time.sleep(0.4)
        bot.edit_message_text("<i>[■■■□] Generating unique address...</i>", chat_id, anim_msg.message_id)
        
        try:
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            domains = mail_client.accounts.list_domains()
            domain_name = domains[0].domain if hasattr(domains[0], 'domain') else domains[0]
            email_address = f"{username}@{domain_name}"
            
            account = mail_client.accounts.create(email_address, password="propassword123")
            
            # ডেটা স্টোর
            user_data[chat_id]['accounts'].append({
                'account_id': account.id,
                'email': account.address,
                'seen_msgs': set(),
                'msg_ids': [anim_msg.message_id] # ড্যাশবোর্ডের মেসেজটাও ডিলিট করার জন্য সেভ রাখলাম
            })
            user_data[chat_id]['active_index'] = len(user_data[chat_id]['accounts']) - 1
            user_data[chat_id]['total_generated'] += 1
            
            dashboard_text = (
                f"🎉 <b>New Mail Generated!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📧 <b>Address:</b>\n"
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
            bot.send_message(chat_id, "⚠️ আপনার কোনো মেইল নেই।")
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
            
            # মেইল ডিলিট হওয়ার সাথে সাথে ওই মেইলের সব মেসেজ ডিলিট করা
            deleted_count = 0
            for msg_id in del_mail['msg_ids']:
                try:
                    bot.delete_message(chat_id, msg_id)
                    deleted_count += 1
                except:
                    pass
            
            if user_data[chat_id]['accounts']:
                user_data[chat_id]['active_index'] = 0
            else:
                user_data[chat_id]['active_index'] = -1
                
            bot.send_message(chat_id, f"🗑️ মেইল <code>{del_mail['email']}</code> এবং এর <b>{deleted_count}</b> টি মেসেজ চ্যাট থেকে ডিলিট করা হয়েছে!")
        else:
            bot.send_message(chat_id, "⚠️ ডিলেট করার মতো কোনো অ্যাক্টিভ মেইল নেই।")

    elif text == "👤 Profile":
        user_info = message.from_user
        first_name = user_info.first_name if user_info.first_name else "Unknown"
        username = f"@{user_info.username}" if user_info.username else "No Username"
        total_mails = user_data[chat_id]['total_generated']
        active_mails_count = len(user_data[chat_id]['accounts'])
        
        profile_text = (
            f"👤 <b>User Profile Information</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📛 <b>Name:</b> {first_name}\n"
            f"🔗 <b>Username:</b> {username}\n"
            f"🆔 <b>User ID:</b> <code>{chat_id}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Total Mails Created:</b> {total_mails}\n"
            f"🟢 <b>Current Active Mails:</b> {active_mails_count}"
        )
        bot.send_message(chat_id, profile_text)

    elif text == "⚡ About Bot":
        about_text = (
            "🚀 <b>Premium Temp Mail Bot v3.0</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "• API: Mail.td Pro\n"
            "• Features: Smart OTP Box & Link Button\n"
            "• Developer: <a href='https://t.me/Ad_Walid'>Md Walid</a> (ExamPro Admin)\n"
            "━━━━━━━━━━━━━━━━━━\n"
        )
        bot.send_message(chat_id, about_text, disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('switch_'))
def handle_switch(call):
    chat_id = call.message.chat.id
    idx = int(call.data.split('_')[1])
    
    if idx < len(user_data.get(chat_id, {}).get('accounts', [])):
        user_data[chat_id]['active_index'] = idx
        active_email = user_data[chat_id]['accounts'][idx]['email']
        bot.answer_callback_query(call.id, f"Switched to {active_email}")
        bot.edit_message_text(f"✅ <b>Switched to:</b>\n<code>{active_email}</code>", chat_id, call.message.message_id)

print("Pro Bot V3 is running...")
bot.polling(none_stop=True)
