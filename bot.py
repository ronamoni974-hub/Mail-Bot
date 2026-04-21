import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from mailtd import MailTD
import time
import threading
import re
import random
import string
import html
from flask import Flask # হোস্টিং এ বট সচল রাখার জন্য

# --- Bot Setup ---
TOKEN = '8572418006:AAEQBCXBPxa35yBiSWeaVWVvLP9N326fJos'
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

MAILTD_TOKEN = 'td_18c938ad445ea882ebc1110b22723e1ca1ddef7911dde89e80a095f3c2120119'
mail_client = MailTD(MAILTD_TOKEN)

user_sessions = {}

# --- Flask Server for 24/7 Hosting ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Alive!"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# --- Code Extractor ---
def format_email_body(text):
    escaped_text = html.escape(text)
    formatted_text = re.sub(r'\b(\d{4,8})\b', r'<code>\1</code>', escaped_text)
    return formatted_text

# --- Auto Checker Engine ---
def auto_check_mail():
    while True:
        try:
            for chat_id, data in list(user_sessions.items()):
                account_id = data.get('account_id')
                if account_id:
                    messages, _ = mail_client.messages.list(account_id)
                    for msg_preview in messages:
                        msg_id = msg_preview.id
                        if msg_id not in data['seen_msgs']:
                            data['seen_msgs'].add(msg_id)
                            full_msg = mail_client.messages.get(account_id, msg_id)
                            
                            smart_body = format_email_body(full_msg.text_body if full_msg.text_body else "No Content")
                            
                            mail_alert = (
                                f"🔔 <b>New Pro Mail Received!</b>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"📌 <b>Subject:</b> {html.escape(full_msg.subject or 'No Subject')}\n\n"
                                f"💬 <b>Message:</b>\n{smart_body}\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"<i>💡 Note: Tap on any code to copy it!</i>"
                            )
                            bot.send_message(chat_id, mail_alert)
        except Exception:
            pass
        time.sleep(5)

# --- Bot Handlers ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    btn = InlineKeyboardButton("✨ Generate Pro Mail", callback_data="generate_mail")
    markup.add(btn)
    bot.send_message(message.chat.id, "👋 <b>Welcome to Pro Temp Mail Bot!</b>\n\nনিচের বাটনে ক্লিক করে মেইল তৈরি করুন।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "generate_mail":
        chat_id = call.message.chat.id
        anim_msg = bot.edit_message_text("<i>⏳ Connecting to Mail.td...</i>", chat_id, call.message.message_id)
        
        try:
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            domains = mail_client.accounts.list_domains()
            domain_name = domains[0].domain if hasattr(domains[0], 'domain') else domains[0]
            email_address = f"{username}@{domain_name}"
            
            account = mail_client.accounts.create(email_address, password="propassword123")
            user_sessions[chat_id] = {'account_id': account.id, 'email': account.address, 'seen_msgs': set()}
            
            dashboard_text = (
                f"🎉 <b>Your Pro Mail is Ready!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📧 <b>Email Address:</b>\n"
                f"<code>{account.address}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🟢 <i>Status: Online & Listening...</i>"
            )
            bot.edit_message_text(dashboard_text, chat_id, anim_msg.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔄 New Mail", callback_data="generate_mail")))
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {str(e)}", chat_id, anim_msg.message_id)

# --- Execution ---
if __name__ == "__main__":
    # ১. ওয়েব সার্ভার চালু করা (২৪/৭ রাখার জন্য)
    threading.Thread(target=run_web_server, daemon=True).start()
    # ২. অটো মেইল চেকার চালু করা
    threading.Thread(target=auto_check_mail, daemon=True).start()
    
    print("Bot is running...")
    # ৩. বটের মেইন লুপ (ক্র্যাশ করলেও রিস্টার্ট হবে)
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            time.sleep(5)
