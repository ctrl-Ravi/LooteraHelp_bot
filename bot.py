import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import re
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
from pymongo import MongoClient

# Load environment variables from .env file (for local development)
load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
# Read Bot Token and Admin Chat ID from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID')
MONGO_URI = os.environ.get('MONGO_URI')

if not BOT_TOKEN or not ADMIN_CHAT_ID or not MONGO_URI:
    print("CRITICAL ERROR: BOT_TOKEN, ADMIN_CHAT_ID, or MONGO_URI is missing from environment variables!")
    exit(1)

# Initialize MongoDB connection
client = MongoClient(MONGO_URI)
db = client['lootera_bot_db']
users_collection = db['users']
banned_collection = db['banned_users']
# ==========================================

bot = telebot.TeleBot(BOT_TOKEN)

# Menu Options
OPT_PROFIT = "💰 Share Profit/Cashback"
OPT_OFFER = "🎁 Submit New Offer"
OPT_DOUBT = "❓ Ask Question/Doubt"
OPT_FEEDBACK = "📝 Report Issue/Feedback"
OPT_CANCEL = "❌ Cancel"

# Dictionary to store user state (what option they selected)
user_states = {}

def get_main_menu():
    """Create the main keyboard menu for users."""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton(OPT_PROFIT),
        KeyboardButton(OPT_OFFER),
        KeyboardButton(OPT_DOUBT),
        KeyboardButton(OPT_FEEDBACK)
    )
    return markup

def save_user_id(user_id):
    """Save user ID to database if it doesn't already exist."""
    user_id_str = str(user_id)
    if not users_collection.find_one({'user_id': user_id_str}):
        users_collection.insert_one({'user_id': user_id_str})

def get_all_users():
    """Retrieve all saved user IDs from database."""
    return [doc['user_id'] for doc in users_collection.find()]

def is_user_banned(user_id):
    """Check if a user is in the banned collection."""
    return banned_collection.find_one({'user_id': str(user_id)}) is not None

def ban_user(user_id):
    """Add user ID to banned database collection."""
    user_id_str = str(user_id)
    if not is_user_banned(user_id_str):
        banned_collection.insert_one({'user_id': user_id_str})

def unban_user(user_id):
    """Remove user ID from banned database collection."""
    banned_collection.delete_one({'user_id': str(user_id)})

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handle /start and /help commands."""
    
    if is_user_banned(message.chat.id):
        return
    
    # Save user ID when they start the bot
    save_user_id(message.chat.id)
    
    welcome_text = (
        "Welcome to the *Lootera Shopper Bot*! 🛍️\n\n"
        "How can we help you today?\n"
        "Please choose an option from the menu below:"
    )
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        reply_markup=get_main_menu(),
        parse_mode='Markdown'
    )
    user_states[message.chat.id] = None

@bot.message_handler(func=lambda message: message.text in [OPT_PROFIT, OPT_OFFER, OPT_DOUBT, OPT_FEEDBACK])
def handle_menu_selection(message):
    """Handle when user taps on a menu button."""
    if is_user_banned(message.chat.id):
        return
    user_states[message.chat.id] = message.text
    
    if message.text == OPT_PROFIT:
        response = "Awesome! Please send us a *screenshot* of your loot, cashback, or profit. 💰"
    elif message.text == OPT_OFFER:
        response = "Found a great deal? Send the *offer details and links* here! 🎁"
    elif message.text == OPT_DOUBT:
        response = "What's your doubt or question? Please type it below. ❓"
    elif message.text == OPT_FEEDBACK:
        response = "Please describe your issue or share your feedback with us. 📝"
        
    # Provide a Cancel button in case they change their mind
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton(OPT_CANCEL))
    
    bot.send_message(
        message.chat.id, 
        response, 
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == OPT_CANCEL)
def cancel_action(message):
    """Handle the cancel button."""
    user_states[message.chat.id] = None
    bot.send_message(
        message.chat.id, 
        "Action cancelled. Returning to main menu.", 
        reply_markup=get_main_menu()
    )

@bot.message_handler(func=lambda message: str(message.chat.id) == str(ADMIN_CHAT_ID) and message.reply_to_message is not None, content_types=['text', 'photo', 'video', 'document'])
def handle_admin_reply(message):
    """Handle when the admin replies to a user's message."""
    original_user_id = None
    
    # Check the text or caption of the message the admin replied to
    reply_target_content = message.reply_to_message.text or message.reply_to_message.caption
    
    if reply_target_content:
        # Extract the user ID from the (ID: 12345) format we injected earlier
        match = re.search(r'\(ID:\s*[^0-9]*(\d+)', reply_target_content)
        if match:
            original_user_id = match.group(1)
            
    if original_user_id:
        try:
            # Send the admin's reply back to the user
            if message.text:
                bot.send_message(original_user_id, message.text)
            else:
                # If admin sent a photo/video/file, copy it to the user
                bot.copy_message(original_user_id, message.chat.id, message.message_id)
                bot.send_message(original_user_id, "*(↑ Admin sent the above message)*", parse_mode='Markdown')
                
            # Set the user to a permanent chat state without requiring the menu
            user_id_int = int(original_user_id)
            if user_states.get(user_id_int) != "💬 Chatting with Admin" and user_states.get(original_user_id) != "💬 Chatting with Admin":
                markup = ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(KeyboardButton(OPT_CANCEL))
                bot.send_message(
                    original_user_id, 
                    "_You are now connected to the admin. You can continue sending messages directly. Press Cancel to end._", 
                    reply_markup=markup, 
                    parse_mode='Markdown'
                )
                # Save both int and str to be safe against Telegram API ID types
                user_states[user_id_int] = "💬 Chatting with Admin"
                user_states[str(original_user_id)] = "💬 Chatting with Admin"
            
            bot.reply_to(message, "✅ Reply sent successfully to the user!")
        except Exception as e:
            bot.reply_to(message, f"⚠️ Failed to send reply. The user might have blocked the bot. Error: {e}")
    else:
        bot.reply_to(
            message, 
            "⚠️ Couldn't figure out who to reply to. Ensure you are replying to a user submission message that contains their `(ID: 12345)` tag."
        )

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    """Handle the /broadcast command (Admin only)."""
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return  # Ignore if not admin

    # Extract the message to broadcast
    try:
        command, broadcast_text = message.text.split(maxsplit=1)
    except ValueError:
        bot.reply_to(message, "⚠️ Usage: `/broadcast Your message here`", parse_mode='Markdown')
        return

    users = get_all_users()
    if not users:
        bot.reply_to(message, "⚠️ No users found to broadcast to.")
        return

    success_count = 0
    fail_count = 0
    
    bot.reply_to(message, f"📢 Broadcasting message to {len(users)} users...")

    # Escape HTML to prevent crash on the broadcast text, unless they want to use raw HTML
    safe_broadcast_text = broadcast_text.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')

    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 <b>Important Update from Admin:</b>\n\n{safe_broadcast_text}", parse_mode='HTML')
            success_count += 1
        except Exception as e:
            # User might have blocked the bot or deleted their account
            fail_count += 1
            print(f"Failed to send to {user_id}: {e}")

    bot.send_message(
        ADMIN_CHAT_ID, 
        f"✅ <b>Broadcast Complete!</b>\nSuccessfully sent to: {success_count}\nFailed to send: {fail_count}",
        parse_mode='HTML'
    )

@bot.message_handler(commands=['ban', 'unban'])
def handle_ban_unban(message):
    """Handle /ban and /unban commands (Admin only)."""
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return

    command = message.text.split()[0].lower()
    target_user_id = None
    
    # 1. Check if admin replied to a user's forwarded message
    if message.reply_to_message:
        reply_target_content = message.reply_to_message.text or message.reply_to_message.caption
        if reply_target_content:
            match = re.search(r'\(ID:\s*[^0-9]*(\d+)', reply_target_content)
            if match:
                target_user_id = match.group(1)
                
    # 2. Check if admin provided ID in the command directly (e.g., /ban 12345)
    if not target_user_id:
        try:
            target_user_id = message.text.split()[1]
        except IndexError:
            bot.reply_to(
                message, 
                f"⚠️ Usage: Reply to a user's message with `{command}`, or type `{command} USER_ID`",
                parse_mode='Markdown'
            )
            return

    if command == '/ban':
        if str(target_user_id) == str(ADMIN_CHAT_ID):
            bot.reply_to(message, "⚠️ You cannot ban yourself!")
            return
        ban_user(target_user_id)
        bot.reply_to(message, f"🚫 User `{target_user_id}` has been **BANNED**.", parse_mode='Markdown')
    elif command == '/unban':
        unban_user(target_user_id)
        bot.reply_to(message, f"✅ User `{target_user_id}` has been **UNBANNED**.", parse_mode='Markdown')

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_user_submission(message):
    """Handle the actual message/screenshot sent by the user."""
    # Ignore if this is from admin doing a broadcast or something else (handled by other functions)
    if str(message.chat.id) == str(ADMIN_CHAT_ID):
        return

    if is_user_banned(message.chat.id):
        return

    chat_id = message.chat.id
    state = user_states.get(chat_id)
    
    # If they haven't selected an option but send something
    if not state:
        bot.send_message(
            chat_id, 
            "Please select an option from the menu first.", 
            reply_markup=get_main_menu()
        )
        return

    try:
        # Prepare info about the user context
        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        # Escape HTML chars to prevent parsing errors
        username = username.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
        
        info_text = (
            f"📩 <b>{state}</b>\n"
            f"👤 <b>From:</b> {username} (ID: <code>{message.from_user.id}</code>)"
        )
        
        # Determine the best way to send it as a SINGLE message
        if message.content_type == 'text':
            # For plain text, combine info and text
            full_text = f"{info_text}\n\n<b>Message:</b>\n{message.text}"
            bot.send_message(ADMIN_CHAT_ID, full_text, parse_mode='HTML')
            
        else:
            # For media (photo, video, document), copy it and use the info as the caption
            original_caption = message.caption if message.caption else ""
            if original_caption:
                original_caption = original_caption.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
                full_caption = f"{info_text}\n\n<b>Caption:</b>\n{original_caption}"
            else:
                full_caption = info_text
                
            bot.copy_message(
                ADMIN_CHAT_ID, 
                chat_id, 
                message.message_id, 
                caption=full_caption,
                parse_mode='HTML'
            )
        
        # Confirm success to the user
        if state == "💬 Chatting with Admin":
            # Short confirmation so we don't spam the conversation
            bot.send_message(
                chat_id, 
                "✅ *Sent.*", 
                parse_mode='Markdown'
            )
        else:
            bot.send_message(
                chat_id, 
                "✅ *Thank you!* Your message has been sent to our team.", 
                reply_markup=get_main_menu(),
                parse_mode='Markdown'
            )
            # Reset state so they can use the menu again
            user_states[chat_id] = None
        
    except Exception as e:
        error_msg = f"⚠️ Sorry, there was an error sending your message.\n\nError details: {e}\n\nPlease check ADMIN_CHAT_ID."
        bot.send_message(
            chat_id, 
            error_msg, 
            reply_markup=get_main_menu()
        )
        print(f"Error forwarding message: {e}")

if __name__ == "__main__":
    keep_alive()
    print("Bot is running! Press Ctrl+C to stop.")
    bot.infinity_polling()
