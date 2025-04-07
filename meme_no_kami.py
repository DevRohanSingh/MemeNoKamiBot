# ✅ What’s included:
# /dropmemes (only works for admins): The bot will immediately start posting memes 🎉
# delay the next automatic drop by 1 hour whenever someone uses /dropmemes manually (To avoid meme spam 💥)
# /status: show the next auto meme drop time
# Fetches top 5 memes from each subreddit every hour
# Avoids duplicates even across restarts (using posted_ids stored on the firebase (db))
# Supports images, GIFs, videos, .gifv auto-converted
# Clears old posted_ids every 24 hours to keep memory clean
# Logs errors and operations

import os
import json
import time
import asyncio
import random
import logging
from datetime import datetime, timedelta
import nest_asyncio
import praw
from telegram import Bot, Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.constants import ParseMode
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          ContextTypes)
from telegram.error import TelegramError, RetryAfter
from keep_alive import keep_alive
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db, initialize_app

load_dotenv('.env')
keep_alive()

DATABASE_URL = 'https://reddittotelegrammemebot-default-rtdb.asia-southeast1.firebasedatabase.app/'
# === CONFIG ===
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID"))
TELEGRAM_TOPIC_ID = int(os.getenv("TELEGRAM_TOPIC_ID"))

# SUBREDDITS = [
#     'ProgrammerHumor', 'ProgrammerAnimemes', 'dankmemes', 'funny', 'memes', 'PrequelMemes', 'Wholesomememes'
# ]

# instead of posting from all subreddits every hour, divide them into groups:
# Then pick a different batch each hour (rotate through them), so you're only posting from 1 batch/hour:
SUBREDDIT_BATCHES = [
    ['dankmemes', 'memes'],
    ['ProgrammerHumor', 'PrequelMemes'],
    ['funny', 'Wholesomememes'],
    ['ProgrammerAnimemes']
]


# POSTED_IDS_FILE = 'posted_ids.json'

# === INIT ===
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# === LOAD/SAVE POSTED IDS ===
# def load_posted_ids():
#     if os.path.exists(POSTED_IDS_FILE):
#         try:
#             with open(POSTED_IDS_FILE, 'r') as f:
#                 return set(json.load(f))
#         except json.JSONDecodeError:
#             logging.warning("⚠️ Failed to decode posted_ids.json, starting fresh.")
#             return set()
#     return set()

# def save_posted_ids(ids):
#     with open(POSTED_IDS_FILE, 'w') as f:
#         json.dump(list(ids), f)

# === Firebase Init ===
# Load the JSON key from environment
firebase_key_json = os.getenv("FIREBASE_KEY_JSON")
firebase_creds_dict = json.loads(firebase_key_json)

# Initialize Firebase directly with dict
cred = credentials.Certificate(firebase_creds_dict)
initialize_app(cred, {
    'databaseURL': DATABASE_URL
})

FIREBASE_PATH = '/posted_ids'

# === LOAD FROM FIREBASE ===
def load_posted_ids():
    try:
        ref = db.reference(FIREBASE_PATH)
        data = ref.get()
        if data:
            return set(data)
    except Exception as e:
        logging.warning(f"⚠️ Failed to load from Firebase: {e}")
    return set()

# === SAVE TO FIREBASE ===
def save_posted_ids(ids):
    try:
        ref = db.reference(FIREBASE_PATH)
        ref.set(list(ids))
    except Exception as e:
        logging.error(f"❌ Failed to save to Firebase: {e}")
        
        
posted_ids = load_posted_ids()
last_reset = time.time()
next_auto_drop = time.time()

# === HELPERS ===
def is_supported_media(url):
    return url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.gifv', '.mp4'))

def convert_gifv_to_mp4(url):
    return url.replace('.gifv', '.mp4')

# === GET MEMES ===
def get_unique_memes(subreddit_name, count=5):
    memes = []
    seen = 0
    subreddit = reddit.subreddit(subreddit_name)

    for submission in subreddit.hot(limit=50):
        if seen >= count:
            break
        if submission.stickied or submission.id in posted_ids:
            continue
        if is_supported_media(submission.url) or submission.is_video:
            url = submission.url
            if url.endswith('.gifv'):
                url = convert_gifv_to_mp4(url)
            memes.append({
                'id': submission.id,
                'title': submission.title,
                'url': url,
                'is_video': submission.is_video,
                'subreddit': subreddit_name
            })
            posted_ids.add(submission.id)
            seen += 1

    return memes

def get_current_subreddit_batch():
    index = int((time.time() // 3600) % len(SUBREDDIT_BATCHES))
    return SUBREDDIT_BATCHES[index]

# === POST TO TELEGRAM ===
# ✅ Reduced meme count per subreddit
# ✅ Delay between each post
# ✅ Staggered delay between subreddits
# ✅ Optional: Subreddit batching (for advanced rotation)
# ✅ Flood control retry handling
async def post_memes():
    logging.info("🚀 Starting meme run...")
    # Use rotating batches
    subreddits_to_post = get_current_subreddit_batch()
    for subreddit in subreddits_to_post:
        memes = get_unique_memes(subreddit, count=2)
        if not memes:
            logging.warning(f"⚠️ No memes found for r/{subreddit}")
            continue

        for meme in memes:
            try:
                caption = f"*{meme['title']}*\nFrom r/{meme['subreddit']}"
                if meme['url'].endswith('.gif'):
                    await bot.send_animation(
                        chat_id=TELEGRAM_GROUP_ID,
                        animation=meme['url'],
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        message_thread_id=TELEGRAM_TOPIC_ID
                    )
                elif meme['is_video'] or meme['url'].endswith('.mp4'):
                    await bot.send_video(
                        chat_id=TELEGRAM_GROUP_ID,
                        video=meme['url'],
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        message_thread_id=TELEGRAM_TOPIC_ID
                    )
                else:
                    await bot.send_photo(
                        chat_id=TELEGRAM_GROUP_ID,
                        photo=meme['url'],
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        message_thread_id=TELEGRAM_TOPIC_ID
                    )
                logging.info(f"✅ Posted from r/{meme['subreddit']}")
                await asyncio.sleep(random.randint(4, 6))  # Delay between posts
                
            except RetryAfter as e:
                logging.warning(f"⏳ Rate limit hit. Retrying in {e.retry_after} seconds.")
                await asyncio.sleep(e.retry_after)
            except TelegramError as e:
                logging.error(f"❌ Telegram error: {e}")
            except Exception as e:
                logging.error(f"❗ General error: {e}")
        # Delay Between subreddits
        await asyncio.sleep(random.randint(10, 20)) 

# === HANDLERS ===
async def drop_memes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    admin_ids = [admin.user.id for admin in admins]

    if user_id not in admin_ids:
        await update.message.reply_text("🚫 You must be an admin to use this.")
        return

    global next_auto_drop
    next_auto_drop = time.time() + 3600
    await update.message.reply_text("🔥 Dropping memes now...")
    await post_memes()
    await update.message.reply_text("✅ Memes posted!")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    next_in = int(next_auto_drop - now)
    next_time = datetime.fromtimestamp(next_auto_drop).strftime('%Y-%m-%d %H:%M:%S')
    since_reset = timedelta(seconds=int(now - last_reset))
    unique_posts = len(posted_ids)

    text = (
        f"📊 *MemeNoKamiBot Status*\n\n"
        f"🕐 *Next Auto Drop:* {next_time} (in {next_in // 60} min)\n"
        f"📦 *Unique Posts Today:* {unique_posts}\n"
        f"🕓 *Uptime Since Last Reset:* {since_reset}\n"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Drop Memes Now", callback_data="drop_now")]
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query: CallbackQuery = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat.id
    admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [admin.user.id for admin in admins]

    if query.data == "drop_now":
        if user_id not in admin_ids:
            await query.edit_message_text("🚫 Only admins can trigger meme drops.")
            return
        global next_auto_drop
        next_auto_drop = time.time() + 3600
        await query.edit_message_text("🔥 Dropping memes now...")
        await post_memes()
        await context.bot.send_message(chat_id, "✅ Memes posted manually!")

# === BACKGROUND TASK ===
async def hourly_loop():
    global posted_ids, last_reset, next_auto_drop
    while True:
        now = time.time()
        if now >= next_auto_drop:
            if now - last_reset >= 86400:
                db.reference(FIREBASE_PATH).delete()
                # posted_ids.clear()
                last_reset = now
                logging.info("🧹 Cleared posted IDs for new day.")

            await post_memes()
            save_posted_ids(posted_ids)
            next_auto_drop = time.time() + 3600
            logging.info("🛌 Scheduled next drop in 1 hour.")
        else:
            wait_time = next_auto_drop - now
            logging.info(f"⏳ Waiting {int(wait_time)}s for next drop...")
            await asyncio.sleep(min(wait_time, 60))

# === MAIN ===
async def post_init(app: Application):
    app.create_task(hourly_loop())

async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("dropmemes", drop_memes_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    await app.run_polling()

if __name__ == "__main__":
    try:
        nest_asyncio.apply()
        asyncio.run(main())
    except KeyboardInterrupt:
        save_posted_ids(posted_ids)
        logging.info("🛑 Bot stopped manually. Saved posted IDs.")
