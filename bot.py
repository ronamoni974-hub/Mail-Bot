import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from mailtd import MailTD
import time
import threading
import re
import random
import string
import html
from datetime import datetime

TOKEN = '8572418006:AAEQBCXBPxa35yBiSWeaVWVvLP9N326fJos'
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

MAILTD_TOKEN = 'td_18c938ad445ea882ebc1110b22723e1ca1ddef7911dde89e80a095f3c2120119'
mail_client = MailTD(MAILTD_TOKEN)

# --- Global Storage ---
ADMIN_ID = "6670461311"
user_data = {}
banned_users = set()
bot_stats = {'total_mails_generated': 0}
system_data = {'notice': None, 'active_promos': {}}

# --- Bottom Menu Builder ---
def get_main_menu(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("✨ New Pro Mail"), KeyboardButton("🏠 Dashboard"))
    markup.add(KeyboardButton("👤 Profile"), KeyboardButton("🗑️ Delete Active"))
    
    if system_data['notice']:
        markup.add(KeyboardButton("📌 Notice Board"), KeyboardButton("⚡ About Bot"))
    else:
        markup.add(KeyboardButton("⚡ About Bot"))
        
    if str(chat_id) == ADMIN_ID:
        markup.add(KeyboardButton("⚙️ Admin Panel"))
    return markup

# --- Admin Inline Menu ---
def get_admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("👥 User List", callback_data="admin_users"),
               InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"))
    markup.add(InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
               InlineKeyboardButton("✅ Unban User", callback_data="admin_unban"))
    markup.add(InlineKeyboardButton("📢 Set Notice", callback_data="admin_set_notice"),
               InlineKeyboardButton("🗑️ Del Notice", callback_data="admin_del_notice"))
    markup.add(InlineKeyboardButton("🚀 Send Promo", callback_data="admin_send_promo"),
               InlineKeyboardButton("🗑️ Del Promo", callback_data="admin_del_promo"))
    return markup

# --- Ban Checker Middleware ---
def is_banned(chat_id):
    if str(chat_id) in banned_users:
        bot.send_message(chat_id, "🚫 <b>Account Banned!</b>\n\nআপনি এই বটটি ব্যবহার করার নিয়ম ভঙ্গ করেছেন তাই আপনাকে ব্যান করা হয়েছে।\n\nযেকোনো সাহায্যের জন্য Admin এর সাথে যোগাযোগ করুন: <a href='https://t.me/Ad_Walid'>@Ad_Walid</a>", disable_web_page_preview=True)
        return True
    return False

# --- Smart Extractor (Large & Clickable Code Box) ---
def extract_and_format(subject, body):
    subject_text = subject if subject else "No Subject"
    body_text = body if body else ""
    
    clean_body = re.sub(r'<[^>]+>', '', body_text).strip()
    if not clean_body:
        clean_body = subject_text 
        
    full_text = f"{subject_text} {clean_body}"
    escaped_body = html.escape(clean_body)
    
    # 4-8 Digit Code Box
    otp_match = re.search(r'\b(\d{4,8})\b', full_text)
    otp_section = ""
    if otp_match:
        otp_section = (
            f"<blockquote>🔐 <b>Verification Code:</b>\n"
            f"👉 <code>{otp_match.group(1)}</code> 👈\n"
            f"<i>(Click the code to copy instantly)</i></blockquote>\n\n"
        )
    
    link_match = re.search(r'(https?://[^\s]+)', full_text)
    extracted_link = link_match.group(1) if link_match else None
    
    formatted_body = re.sub(r'\b(\d{4,8})\b', r'<code>\1</code>', escaped_body)
    
    return otp_section, formatted_body, extracted_link

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
                            
                            mail_alert = (
                                f"📥 <b>INBOX UPDATE | NEW MAIL RECEIVED</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"📧 <b>To:</b> <code>{account['email']}</code>\n"
                                f"📌 <b>Subject:</b> {html.escape(full_msg.subject or 'No Subject')}\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                f"{otp_section}"
                                f"💬 <b>Message Content:</b>\n"
                                f"<code>{smart_body[:1000]}</code>{'...' if len(smart_body)>1000 else ''}\n\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"⚡ <i>Live synchronization active...</i>"
                            )
                            
                            markup = InlineKeyboardMarkup()
                            if verify_link:
                                markup.add(InlineKeyboardButton("🔗 Secure Verify / Open Link", url=verify_link))
                            
                            sent_msg = bot.send_message(chat_id, mail_alert, reply_markup=markup, disable_web_page_preview=True)
                            account['msg_ids'].append(sent_msg.message_id)
        except Exception:
            pass
        time.sleep(3)

threading.Thread(target=auto_check_mail, daemon=True).start()

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
        "🌟 <b>Welcome to the Ultimate Premium Mail Bot!</b>\n\n"
        "সবচেয়ে ফাস্ট এবং সিকিউর টেম্পোরারি মেইল সার্ভিস। যেকোনো OTP এবং Verification Link সাথে সাথে পেয়ে যাবেন।\n\n"
        "👇 <i>নিচের মেনু থেকে আপনার কাজ শুরু করুন:</i>"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu(str(message.chat.id)))

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = str(message.chat.id)
    text = message.text
    init_user(message)
    if is_banned(chat_id): return

    if text == "✨ New Pro Mail":
        anim_msg = bot.send_message(chat_id, "<i>[■□□□] Establishing secure connection...</i>")
        time.sleep(0.3)
        bot.edit_message_text("<i>[■■■□] Registering premium domain...</i>", chat_id, anim_msg.message_id)
        
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
            
            dashboard_text = (
                f"🎉 <b>Premium Mail Generated Successfully!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📥 <b>Your Secure Address:</b>\n"
                f"👉 <code>{account.address}</code> 👈\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🟢 <i>Status: Ultra-Fast Listening Mode ON</i>\n"
                f"যেকোনো সাইটে এই মেইলটি ব্যবহার করুন, ইনবক্স এখানেই শো করবে।"
            )
            bot.edit_message_text(dashboard_text, chat_id, anim_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", chat_id, anim_msg.message_id)

    elif text == "🏠 Dashboard":
        accounts = user_data[chat_id]['accounts']
        if not accounts:
            bot.send_message(chat_id, "⚠️ আপনার কোনো মেইল নেই।")
            return
            
        dash_text = "🗂️ <b>Your Mail Control Panel</b>\n\n"
        markup = InlineKeyboardMarkup(row_width=1)
        for i, acc in enumerate(accounts):
            status = "🟢 Active" if i == user_data[chat_id]['active_index'] else "⚪ Standby"
            dash_text += f"{i+1}. <code>{acc['email']}</code> [{status}]\n"
            markup.add(InlineKeyboardButton(f"🔄 Switch to Mail {i+1}", callback_data=f"switch_{i}"))
            
        bot.send_message(chat_id, dash_text, reply_markup=markup)

    elif text == "🗑️ Delete Active":
        if user_data[chat_id]['accounts']:
            active_idx = user_data[chat_id]['active_index']
            del_mail = user_data[chat_id]['accounts'].pop(active_idx)
            deleted_count = 0
            for msg_id in del_mail['msg_ids']:
                try:
                    bot.delete_message(chat_id, msg_id)
                    deleted_count += 1
                except: pass
            
            user_data[chat_id]['active_index'] = 0 if user_data[chat_id]['accounts'] else -1
            bot.send_message(chat_id, f"🗑️ <b>Deleted!</b>\nমেইল <code>{del_mail['email']}</code> এবং এর <b>{deleted_count}</b> টি মেসেজ চ্যাট থেকে সম্পূর্ণ মুছে ফেলা হয়েছে।")
        else:
            bot.send_message(chat_id, "⚠️ ডিলেট করার মতো কোনো অ্যাক্টিভ মেইল নেই।")

    elif text == "👤 Profile":
        user_info = user_data[chat_id]
        profile_text = (
            f"👤 <b>User Profile & Statistics</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📛 <b>Name:</b> {user_info['name']}\n"
            f"🔗 <b>Username:</b> {user_info['username']}\n"
            f"🆔 <b>User ID:</b> <code>{chat_id}</code>\n"
            f"📅 <b>Joined:</b> {user_info['joined']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Total Generated:</b> {user_info['total_generated']} Mails\n"
            f"🟢 <b>Current Active:</b> {len(user_info['accounts'])} Mails"
        )
        bot.send_message(chat_id, profile_text)

    elif text == "📌 Notice Board" and system_data['notice']:
        bot.send_message(chat_id, f"📌 <b>Official Notice:</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n{system_data['notice']}\n━━━━━━━━━━━━━━━━━━━━━━━━")

    elif text == "⚡ About Bot":
        about_text = (
            "🚀 <b>Premium Temp Mail Bot v4.0</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Engine: Mail.td Pro API\n"
            "• Performance: Zero-Lag Multi-threading\n"
            "• Features: Smart OTP Box, Link Button\n"
            "• Admin: <a href='https://t.me/Ad_Walid'>Md Walid</a>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        bot.send_message(chat_id, about_text, disable_web_page_preview=True)

    elif text == "⚙️ Admin Panel" and chat_id == ADMIN_ID:
        bot.send_message(chat_id, "⚙️ <b>Advanced Admin Control Panel</b>\nবেছে নিন আপনি কী করতে চান:", reply_markup=get_admin_menu())

# --- Admin Callbacks & Functions ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = str(call.message.chat.id)
    if is_banned(chat_id): return
    
    if call.data.startswith('switch_'):
        idx = int(call.data.split('_')[1])
        if idx < len(user_data.get(chat_id, {}).get('accounts', [])):
            user_data[chat_id]['active_index'] = idx
            active_email = user_data[chat_id]['accounts'][idx]['email']
            bot.answer_callback_query(call.id, "Switched successfully!")
            bot.edit_message_text(f"✅ <b>Successfully Switched!</b>\n\n🟢 <b>Active Mail:</b> <code>{active_email}</code>\n<i>Live synchronization active for this mail.</i>", chat_id, call.message.message_id)
            
    elif chat_id == ADMIN_ID:
        if call.data == "admin_stats":
            total_users = len(user_data)
            active_accounts = sum(len(d['accounts']) for d in user_data.values())
            stats = (
                f"📊 <b>Bot Statistics</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👥 Total Users: <b>{total_users}</b>\n"
                f"🚫 Banned Users: <b>{len(banned_users)}</b>\n"
                f"📧 Total Mails Gen: <b>{bot_stats['total_mails_generated']}</b>\n"
                f"🟢 Current Active Mails: <b>{active_accounts}</b>"
            )
            bot.send_message(chat_id, stats)
            
        elif call.data == "admin_users":
            user_list = "👥 <b>Recent Users List:</b>\n"
            for uid, data in list(user_data.items())[-20:]: # Last 20 users
                user_list += f"• {data['name']} (<code>{uid}</code>) - {data['total_generated']} Mails\n"
            bot.send_message(chat_id, user_list)
            
        elif call.data == "admin_ban":
            msg = bot.send_message(chat_id, "✍️ যাকে ব্যান করতে চান তার User ID দিন:")
            bot.register_next_step_handler(msg, process_ban)
            
        elif call.data == "admin_unban":
            msg = bot.send_message(chat_id, "✍️ যাকে আনব্যান করতে চান তার User ID দিন:")
            bot.register_next_step_handler(msg, process_unban)
            
        elif call.data == "admin_set_notice":
            msg = bot.send_message(chat_id, "✍️ নোটিশের টেক্সটটি লিখে সেন্ড করুন:")
            bot.register_next_step_handler(msg, process_set_notice)
            
        elif call.data == "admin_del_notice":
            system_data['notice'] = None
            bot.send_message(chat_id, "🗑️ নোটিশ ডিলিট করা হয়েছে।", reply_markup=get_main_menu(chat_id))
            
        elif call.data == "admin_send_promo":
            msg = bot.send_message(chat_id, "🚀 প্রোমোশনাল পোস্টের <b>টেক্সট</b> লিখুন (HTML সাপোর্টেড):")
            bot.register_next_step_handler(msg, process_promo_text)
            
        elif call.data == "admin_del_promo":
            deleted = 0
            for uid, msg_id in system_data['active_promos'].items():
                try:
                    bot.delete_message(uid, msg_id)
                    deleted += 1
                except: pass
            system_data['active_promos'].clear()
            bot.send_message(chat_id, f"🗑️ <b>Promo Deleted!</b>\n{deleted} জন ইউজারের ইনবক্স থেকে পোস্টটি মুছে ফেলা হয়েছে।")

# --- Admin Process Handlers ---
def process_ban(message):
    banned_users.add(message.text.strip())
    bot.send_message(message.chat.id, f"✅ <b>{message.text}</b> কে ব্যান করা হয়েছে!")

def process_unban(message):
    banned_users.discard(message.text.strip())
    bot.send_message(message.chat.id, f"✅ <b>{message.text}</b> কে আনব্যান করা হয়েছে!")

def process_set_notice(message):
    system_data['notice'] = message.text
    bot.send_message(message.chat.id, "✅ নোটিশ সেট করা হয়েছে।", reply_markup=get_main_menu(message.chat.id))

def process_promo_text(message):
    promo_text = message.text
    msg = bot.send_message(message.chat.id, "🔗 যদি কোনো বাটন লিংক দিতে চান তবে লিংক দিন। না দিতে চাইলে 'no' লিখুন:")
    bot.register_next_step_handler(msg, lambda m: broadcast_promo(m, promo_text))

def broadcast_promo(message, promo_text):
    link = message.text.strip()
    markup = InlineKeyboardMarkup()
    if link.lower() != 'no' and link.startswith('http'):
        markup.add(InlineKeyboardButton("🌟 Click Here", url=link))
        
    bot.send_message(message.chat.id, "🚀 ব্রডকাস্ট শুরু হয়েছে... এটি ব্যাকগ্রাউন্ডে চলবে।")
    
    # Non-blocking broadcast
    def send_to_all():
        system_data['active_promos'].clear()
        for uid in list(user_data.keys()):
            try:
                sent = bot.send_message(uid, f"📢 <b>Promotional Update</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n{promo_text}", reply_markup=markup if markup.keyboard else None)
                system_data['active_promos'][uid] = sent.message_id
            except: pass
            time.sleep(0.05) # Anti-Spam delay
    
    threading.Thread(target=send_to_all, daemon=True).start()

print("Ultimate Pro Bot with Admin Panel is Running...")
bot.polling(none_stop=True)
