import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from mailtd import MailTD
import time
import threading
import re
import random
import string
import html
import os
from flask import Flask
from datetime import datetime

# --- Configuration ---
TOKEN = '8572418006:AAEQBCXBPxa35yBiSWeaVWVvLP9N326fJos'
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

MAILTD_TOKEN = 'td_18c938ad445ea882ebc1110b22723e1ca1ddef7911dde89e80a095f3c2120119'
mail_client = MailTD(MAILTD_TOKEN)

ADMIN_ID = "6670461311"

# --- Global Storage ---
user_data = {}
banned_users = set()
bot_stats = {'total_mails_generated': 0}
system_data = {'active_promos': {}}

# --- Web Server (24/7 Hosting) ---
app = Flask('')
@app.route('/')
def home(): return "Pro Mail Bot is Running 24/7!"
def run_web_server(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- Menu Builders ---
def get_main_menu(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("✨ New Pro Mail"), KeyboardButton("✏️ Custom Mail"))
    markup.add(KeyboardButton("🏠 Dashboard"), KeyboardButton("🗑️ Delete Active"))
    markup.add(KeyboardButton("👤 Profile"), KeyboardButton("⚡ About Bot"))
    if str(chat_id) == ADMIN_ID:
        markup.add(KeyboardButton("⚙️ Admin Panel"))
    return markup

def get_admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("👥 User List", callback_data="admin_users"),
               InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"))
    markup.add(InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
               InlineKeyboardButton("✅ Unban User", callback_data="admin_unban"))
    markup.add(InlineKeyboardButton("📢 Send Notice/Promo", callback_data="admin_send_promo"),
               InlineKeyboardButton("🗑️ Del Promo", callback_data="admin_del_promo"))
    return markup

def get_back_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Back to Panel", callback_data="admin_back"))
    return markup

def is_banned(chat_id):
    if str(chat_id) in banned_users:
        bot.send_message(chat_id, "🚫 <b>Account Banned!</b>\n\nআপনি বট ব্যবহারের নিয়ম ভঙ্গ করেছেন।\nযোগাযোগ করুন: <a href='https://t.me/Ad_Walid'>@Ad_Walid</a>", disable_web_page_preview=True)
        return True
    return False

# --- Service Logo Detector ---
def get_service_logo(sender):
    sender_lower = str(sender).lower()
    if 'facebook' in sender_lower or 'fb' in sender_lower: return '📘 Facebook'
    if 'instagram' in sender_lower or 'ig' in sender_lower: return '📸 Instagram'
    if 'youtube' in sender_lower or 'yt' in sender_lower: return '▶️ YouTube'
    if 'twitter' in sender_lower or 'x.com' in sender_lower: return '🕢 X (Twitter)'
    if 'google' in sender_lower or 'gmail' in sender_lower: return '🇬 Google'
    if 'tiktok' in sender_lower: return '🎵 TikTok'
    if 'netflix' in sender_lower: return '🎬 Netflix'
    if 'amazon' in sender_lower: return '🛒 Amazon'
    if 'apple' in sender_lower: return '🍎 Apple'
    if 'microsoft' in sender_lower: return '🪟 Microsoft'
    if 'spotify' in sender_lower: return '🎧 Spotify'
    if 'discord' in sender_lower: return '👾 Discord'
    if 'steam' in sender_lower: return '🎮 Steam'
    return '🌐 Web Service'

# --- Smart Extractor ---
def extract_and_format(subject, body):
    subject_text = subject if subject else "No Subject"
    body_text = body if body else ""
    
    clean_body = re.sub(r'<[^>]+>', '', body_text).strip()
    if not clean_body:
        clean_body = subject_text 
        
    full_text = f"{subject_text} {clean_body}"
    escaped_body = html.escape(clean_body)
    
    otp_match = re.search(r'\b(\d{4,8})\b', full_text)
    otp_section = ""
    if otp_match:
        otp_section = (
            f"🔑 <b>Verification Code :</b>\n"
            f"<code>{otp_match.group(1)}</code>\n\n"
        )
    
    link_match = re.search(r'(https?://[^\s]+)', full_text)
    extracted_link = link_match.group(1) if link_match else None
    
    formatted_body = re.sub(r'\b(\d{4,8})\b', r'<code>\1</code>', escaped_body)
    return otp_section, formatted_body, extracted_link

# --- Clean Layout Generators ---
def generate_mail_layout(email_address):
    layout = (
        f"✅ <b>Mail Assigned Successfully !</b>\n\n"
        f"📧 <b>Address :</b> <code>{email_address}</code>\n\n"
        f"📡 <b>Status :</b> Live Sync Active\n\n"
        f"<blockquote>•  Waiting for new messages ⬇️</blockquote>"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🔄 Switch Mail", callback_data="quick_switch"),
               InlineKeyboardButton("🔄 Force Fetch", callback_data="force_fetch"))
    return layout, markup

# --- Non-Blocking Auto Checker Engine ---
def auto_check_mail():
    while True:
        try:
            for chat_id, data in list(user_data.items()):
                if str(chat_id) in banned_users: continue
                
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
                            
                            sender_info = getattr(full_msg, 'from_address', getattr(full_msg, 'sender', 'Unknown Sender'))
                            service_logo = get_service_logo(sender_info)
                            
                            mail_alert = (
                                f"✅ <b>New Message Received !</b>\n\n"
                                f"🏢 <b>From :</b> {service_logo} <i>({html.escape(sender_info)})</i>\n\n"
                                f"📧 <b>To :</b> <code>{account['email']}</code>\n\n"
                                f"📌 <b>Subject :</b> {html.escape(full_msg.subject or 'No Subject')}\n\n"
                                f"{otp_section}"
                                f"<blockquote>💬 <b>Message :</b>\n"
                                f"{smart_body[:1000]}{'...' if len(smart_body)>1000 else ''}</blockquote>"
                            )
                            
                            markup = InlineKeyboardMarkup()
                            if verify_link:
                                markup.add(InlineKeyboardButton("🔗 Secure Verify / Open Link", url=verify_link))
                            
                            sent_msg = bot.send_message(chat_id, mail_alert, reply_markup=markup, disable_web_page_preview=True)
                            account['msg_ids'].append(sent_msg.message_id)
        except Exception:
            pass
        time.sleep(3)

# --- Initialize User ---
def init_user(message):
    chat_id = str(message.chat.id)
    if chat_id not in user_data:
        user_data[chat_id] = {
            'accounts': [], 
            'active_index': -1, 
            'total_generated': 0,
            'name': message.from_user.first_name or "Unknown",
            'username': f"@{message.from_user.username}" if message.from_user.username else "N/A",
            'joined': datetime.now().strftime("%Y-%m-%d")
        }

# --- Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    init_user(message)
    if is_banned(message.chat.id): return
    
    welcome_text = (
        "🌟 <b>Welcome to Pro Mail Assistant!</b>\n\n"
        "আপনার পার্সোনাল ইনবক্সকে স্প্যাম থেকে সুরক্ষিত রাখুন। "
        "যেকোনো ওয়েবসাইটের ভেরিফিকেশন কোড (OTP) বা লিংক রিসিভ করুন মাত্র কয়েক সেকেন্ডে!\n\n"
        "✨ <i>মডার্ন UI এবং ডায়নামিক ইনবক্স ম্যানেজমেন্টের অভিজ্ঞতা নিতে নিচের বাটনগুলো ব্যবহার করুন।</i>"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu(str(message.chat.id)))

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = str(message.chat.id)
    text = message.text
    init_user(message)
    if is_banned(chat_id): return

    if text == "✨ New Pro Mail":
        anim_msg = bot.send_message(chat_id, "<i>⏳ Initializing Protocol...</i>")
        
        try:
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            domains = mail_client.accounts.list_domains()
            domain_name = domains[0].domain if hasattr(domains[0], 'domain') else domains[0]
            email_address = f"{username}@{domain_name}"
            
            account = mail_client.accounts.create(email_address, password="propassword123")
            
            user_data[chat_id]['accounts'].append({'account_id': account.id, 'email': account.address, 'seen_msgs': set(), 'msg_ids': [anim_msg.message_id]})
            user_data[chat_id]['active_index'] = len(user_data[chat_id]['accounts']) - 1
            user_data[chat_id]['total_generated'] += 1
            bot_stats['total_mails_generated'] += 1
            
            layout, markup = generate_mail_layout(account.address)
            bot.edit_message_text(layout, chat_id, anim_msg.message_id, reply_markup=markup)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", chat_id, anim_msg.message_id)

    elif text == "✏️ Custom Mail":
        msg = bot.send_message(chat_id, "✏️ <b>Custom Mail Creation</b>\n\nআপনি মেইলের শুরুতে কী নাম দিতে চান তা লিখুন (যেমন: <code>walid</code>):", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Cancel", callback_data="cancel_custom")))
        bot.register_next_step_handler(msg, process_custom_mail)

    elif text == "🏠 Dashboard":
        accounts = user_data[chat_id]['accounts']
        if not accounts:
            bot.send_message(chat_id, "⚠️ আপনার কোনো অ্যাক্টিভ মেইল নেই।")
            return
            
        dash_text = "🗂️ <b>Your Mail Dashboard</b>\n\n"
        markup = InlineKeyboardMarkup(row_width=1)
        for i, acc in enumerate(accounts):
            status = "🟢 Active" if i == user_data[chat_id]['active_index'] else "⚪ Standby"
            dash_text += f"{i+1}. <code>{acc['email']}</code> [{status}]\n\n"
            markup.add(InlineKeyboardButton(f"🔄 Switch to Mail {i+1}", callback_data=f"switch_{i}"))
            
        bot.send_message(chat_id, dash_text, reply_markup=markup)

    elif text == "🗑️ Delete Active":
        if user_data[chat_id]['accounts']:
            active_idx = user_data[chat_id]['active_index']
            del_mail = user_data[chat_id]['accounts'].pop(active_idx)
            deleted_count = 0
            for msg_id in del_mail['msg_ids']:
                try: bot.delete_message(chat_id, msg_id); deleted_count += 1
                except: pass
            
            user_data[chat_id]['active_index'] = 0 if user_data[chat_id]['accounts'] else -1
            bot.send_message(chat_id, f"✅ <b>Deleted !</b>\n\nমেইল <code>{del_mail['email']}</code> চ্যাট থেকে মুছে ফেলা হয়েছে।")
        else:
            bot.send_message(chat_id, "⚠️ ডিলেট করার মতো কোনো অ্যাক্টিভ মেইল নেই।")

    elif text == "👤 Profile":
        user_info = user_data[chat_id]
        profile_text = (
            f"👤 <b>User Profile</b>\n\n"
            f"📛 <b>Name :</b> {user_info['name']}\n\n"
            f"🆔 <b>User ID :</b> <code>{chat_id}</code>\n\n"
            f"📊 <b>Total Generated :</b> {user_info['total_generated']} Mails\n\n"
            f"🟢 <b>Current Active :</b> {len(user_info['accounts'])} Mails"
        )
        bot.send_message(chat_id, profile_text)

    elif text == "⚡ About Bot":
        about_text = (
            "🚀 <b>Premium Temp Mail Bot</b>\n\n"
            "• Engine: Mail.td Pro API\n"
            "• Performance: Zero-Lag Sync\n"
            "• Designed by: <a href='https://t.me/Ad_Walid'>Md Walid</a>\n\n"
            "<i>Crafted with modern interface aesthetics.</i>"
        )
        bot.send_message(chat_id, about_text, disable_web_page_preview=True)

    elif text == "⚙️ Admin Panel" and chat_id == ADMIN_ID:
        bot.send_message(chat_id, "⚙️ <b>Admin Control Panel</b>\n\nবেছে নিন আপনি কী করতে চান:", reply_markup=get_admin_menu())

# --- Custom Mail Processing ---
def process_custom_mail(message):
    chat_id = str(message.chat.id)
    if message.text.startswith('/'): return
        
    requested_name = message.text.lower().strip()
    clean_name = re.sub(r'[^a-z0-9]', '', requested_name)
    
    if len(clean_name) < 3:
        bot.send_message(chat_id, "⚠️ নাম কমপক্ষে ৩ অক্ষরের হতে হবে। আবার চেষ্টা করুন।")
        return
        
    anim_msg = bot.send_message(chat_id, "<i>⏳ Checking availability...</i>")
    
    try:
        domains = mail_client.accounts.list_domains()
        domain_name = domains[0].domain if hasattr(domains[0], 'domain') else domains[0]
        email_address = f"{clean_name}@{domain_name}"
        
        account = mail_client.accounts.create(email_address, password="propassword123")
        
        user_data[chat_id]['accounts'].append({'account_id': account.id, 'email': account.address, 'seen_msgs': set(), 'msg_ids': [anim_msg.message_id]})
        user_data[chat_id]['active_index'] = len(user_data[chat_id]['accounts']) - 1
        user_data[chat_id]['total_generated'] += 1
        bot_stats['total_mails_generated'] += 1
        
        layout, markup = generate_mail_layout(account.address)
        bot.edit_message_text(layout, chat_id, anim_msg.message_id, reply_markup=markup)
        
    except Exception as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "taken" in error_msg.lower() or "400" in error_msg.lower():
            bot.edit_message_text(f"❌ <b>দুঃখিত!</b> <code>{clean_name}</code> নামটি আগে থেকেই কেউ নিয়ে নিয়েছে। অন্য নাম দিন।", chat_id, anim_msg.message_id)
        else:
            bot.edit_message_text(f"❌ Error: {error_msg}", chat_id, anim_msg.message_id)

# --- Callbacks & Dynamic Admin Menu ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = str(call.message.chat.id)
    if is_banned(chat_id): return
    
    if call.data == "cancel_custom":
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        bot.edit_message_text("❌ Custom Mail creation cancelled.", chat_id, call.message.message_id)

    elif call.data == "force_fetch":
        bot.answer_callback_query(call.id, "🔄 Fetching new emails from server...")

    elif call.data == "quick_switch":
        accounts = user_data.get(chat_id, {}).get('accounts', [])
        if len(accounts) > 1:
            bot.answer_callback_query(call.id, "Please use Dashboard to switch mails.")
        else:
            bot.answer_callback_query(call.id, "You only have one active mail.")

    elif call.data.startswith('switch_'):
        idx = int(call.data.split('_')[1])
        if idx < len(user_data.get(chat_id, {}).get('accounts', [])):
            user_data[chat_id]['active_index'] = idx
            active_email = user_data[chat_id]['accounts'][idx]['email']
            bot.answer_callback_query(call.id, "Switched successfully!")
            
            layout, markup = generate_mail_layout(active_email)
            bot.edit_message_text(layout, chat_id, call.message.message_id, reply_markup=markup)
            
    elif chat_id == ADMIN_ID:
        if call.data == "admin_back":
            bot.edit_message_text("⚙️ <b>Admin Control Panel</b>\n\nবেছে নিন আপনি কী করতে চান:", chat_id, call.message.message_id, reply_markup=get_admin_menu())
            
        elif call.data == "admin_stats":
            total_users = len(user_data)
            active_accounts = sum(len(d['accounts']) for d in user_data.values())
            stats = (
                f"📊 <b>Bot Live Statistics</b>\n\n"
                f"👥 Total Users: <b>{total_users}</b>\n\n"
                f"🚫 Banned Users: <b>{len(banned_users)}</b>\n\n"
                f"📧 Total Mails Gen: <b>{bot_stats['total_mails_generated']}</b>\n\n"
                f"🟢 Current Active Mails: <b>{active_accounts}</b>"
            )
            bot.edit_message_text(stats, chat_id, call.message.message_id, reply_markup=get_back_button())
            
        elif call.data == "admin_users":
            user_list = "👥 <b>Recent Users List:</b>\n\n"
            for uid, data in list(user_data.items())[-20:]:
                user_list += f"• {data['name']} (<code>{uid}</code>)\n"
            bot.edit_message_text(user_list, chat_id, call.message.message_id, reply_markup=get_back_button())
            
        elif call.data == "admin_ban":
            bot.edit_message_text("✍️ <b>Ban User:</b>\n\nযাকে ব্যান করতে চান তার User ID টাইপ করে সেন্ড করুন:", chat_id, call.message.message_id, reply_markup=get_back_button())
            bot.register_next_step_handler(call.message, process_ban)
            
        elif call.data == "admin_unban":
            bot.edit_message_text("✍️ <b>Unban User:</b>\n\nযাকে আনব্যান করতে চান তার User ID সেন্ড করুন:", chat_id, call.message.message_id, reply_markup=get_back_button())
            bot.register_next_step_handler(call.message, process_unban)
            
        elif call.data == "admin_send_promo":
            bot.edit_message_text("📢 <b>Broadcast Message:</b>\n\nনোটিশ বা প্রোমোশনাল পোস্টের টেক্সট লিখে সেন্ড করুন (HTML):", chat_id, call.message.message_id, reply_markup=get_back_button())
            bot.register_next_step_handler(call.message, process_promo_text)
            
        elif call.data == "admin_del_promo":
            deleted = 0
            for uid, msg_id in system_data['active_promos'].items():
                try: bot.delete_message(uid, msg_id); deleted += 1
                except: pass
            system_data['active_promos'].clear()
            bot.edit_message_text(f"✅ <b>Promo Deleted!</b>\n\n{deleted} জন ইউজারের ইনবক্স থেকে সর্বশেষ মেসেজ মুছে ফেলা হয়েছে।", chat_id, call.message.message_id, reply_markup=get_back_button())

# --- Admin Processing Functions ---
def process_ban(message):
    if not message.text.isdigit(): return
    banned_users.add(message.text.strip())
    bot.send_message(message.chat.id, f"✅ <b>{message.text}</b> কে ব্যান করা হয়েছে!")

def process_unban(message):
    if not message.text.isdigit(): return
    banned_users.discard(message.text.strip())
    bot.send_message(message.chat.id, f"✅ <b>{message.text}</b> কে আনব্যান করা হয়েছে!")

def process_promo_text(message):
    if not message.text: return
    promo_text = message.text
    msg = bot.send_message(message.chat.id, "🔗 লিংকের জন্য বাটন দিতে চাইলে লিংক দিন। না দিতে চাইলে 'no' লিখুন:")
    bot.register_next_step_handler(msg, lambda m: broadcast_promo(m, promo_text))

def broadcast_promo(message, promo_text):
    link = message.text.strip()
    markup = InlineKeyboardMarkup()
    if link.lower() != 'no' and link.startswith('http'):
        markup.add(InlineKeyboardButton("🌟 View Details", url=link))
        
    bot.send_message(message.chat.id, "🚀 ব্রডকাস্ট শুরু হয়েছে... এটি ব্যাকগ্রাউন্ডে চলবে।")
    
    def send_to_all():
        system_data['active_promos'].clear()
        for uid in list(user_data.keys()):
            try:
                sent = bot.send_message(uid, f"📢 <b>Official Update</b>\n\n{promo_text}", reply_markup=markup if markup.keyboard else None)
                system_data['active_promos'][uid] = sent.message_id
            except: pass
            time.sleep(0.05)
    
    threading.Thread(target=send_to_all, daemon=True).start()

# --- App Execution ---
if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    threading.Thread(target=auto_check_mail, daemon=True).start()
    print("Clean UI Bot is Live...")
    while True:
        try: bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception: time.sleep(5)
