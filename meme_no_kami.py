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
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError, RetryAfter
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

load_dotenv('.env')

# Configuration
DATABASE_URL = 'https://reddittotelegrammemebot-default-rtdb.asia-southeast1.firebasedatabase.app/'
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID"))
TELEGRAM_TOPIC_ID = int(os.getenv("TELEGRAM_TOPIC_ID"))

SUBREDDIT_BATCHES = [
    ['dankmemes', 'memes', 'ProgrammerHumor', 'ProgrammerAnimemes', 'funny', 'Animemes', 'anime']
]
    # ['Wholesomememes', 'Unexpected', 'ContagiousLaughter'],
    # ['nextfuckinglevel', 'MadeMeSmile', 'HumansBeingBros'],
    # ['BeAmazed', 'toptalent', 'maybemaybemaybe', 'KidsAreFuckingStupid', 'oddlysatisfying', ],
    # ['interestingasfuck', 'mildlyinteresting', 'Damnthatsinteresting', 'todayilearned', 'Satisfyingasfuck', 'aww']

POSTED_IDS_FILE = 'posted_ids.json'

# === SETUP LOGGING ===
log_format = '[%(asctime)s] %(levelname)s - %(message)s'
file_handler = RotatingFileHandler(
    "meme.log",
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=3,
    encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter(log_format))
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(log_format))
logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])

# === INIT SERVICES ===
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# === LOAD/SAVE POSTED IDS ===
def load_posted_ids():
    logging.info("🔄 Loading posted_ids from file...")
    if os.path.exists(POSTED_IDS_FILE):
        try:
            with open(POSTED_IDS_FILE, 'r') as f:
                ids = set(json.load(f))
                logging.info(f"✅ Loaded {len(ids)} posted IDs.")
                return ids
        except json.JSONDecodeError:
            logging.warning("⚠️ Failed to decode posted_ids.json, starting fresh.")
            return set()
    logging.info("📁 posted_ids.json not found, starting fresh.")
    return set()

def save_posted_ids(ids):
    logging.info("💾 Saving posted_ids to file...")
    with open(POSTED_IDS_FILE, 'w') as f:
        json.dump(list(ids), f)
    logging.info("✅ posted_ids saved.")

posted_ids = load_posted_ids()
last_reset = time.time()
next_auto_drop = time.time()

# === HELPERS ===
def is_supported_media(url):
    return url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.gifv', '.mp4'))

def convert_gifv_to_mp4(url):
    return url.replace('.gifv', '.mp4')

# === GET MEMES ===
def get_unique_memes(subreddit_name, count=25):
    logging.info(f"📥 Fetching memes from r/{subreddit_name}...")
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
            seen += 1
    logging.info(f"✅ Fetched {len(memes)} new memes from r/{subreddit_name}")
    return memes

def get_current_subreddit_batch():
    # index = int((time.time() // 3600) % len(SUBREDDIT_BATCHES))
    index = 0
    logging.info(f"🎯 Using subreddit batch index: {index}")
    return SUBREDDIT_BATCHES[index]

# === SEND MEME WITH RETRY LOGIC ===
async def send_meme(meme):
    max_retries = 5
    delay = 1  # start with 1 second delay
    caption = f"*{meme['title']}*\nFrom r/{meme['subreddit']}"
    for attempt in range(1, max_retries + 1):
        try:
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
            logging.info(f"✅ Posted meme from r/{meme['subreddit']}")
            # If post is successful, return True (caller will add the meme ID)
            return True
        except RetryAfter as e:
            logging.warning(f"⏳ Rate limit hit on attempt {attempt}. Retrying in {e.retry_after} seconds.")
            await asyncio.sleep(e.retry_after)
        except TelegramError as e:
            logging.error(f"❌ Telegram error on attempt {attempt}: {e}")
            # For network-related errors, we can retry.
            await asyncio.sleep(delay)
        except Exception as e:
            logging.error(f"❗ General error on attempt {attempt}: {e}")
            await asyncio.sleep(delay)
        delay *= 2  # exponential backoff
    logging.error(f"❌ Failed to post meme from r/{meme['subreddit']} after {max_retries} attempts.")
    return False

# === POST TO TELEGRAM ===
async def post_memes():
    logging.info("🚀 Starting meme run...")
    subreddits_to_post = get_current_subreddit_batch()
    for subreddit in subreddits_to_post:
        memes = get_unique_memes(subreddit, count=5)
        if not memes:
            logging.warning(f"⚠️ No memes found for r/{subreddit}")
            continue
        for meme in memes:
            success = await send_meme(meme)
            if success:
                # Record the post only if sending succeeded
                posted_ids.add(meme['id'])
            # Wait a short random duration between posts (even after failed attempt)
            await asyncio.sleep(random.randint(4, 6))
        await asyncio.sleep(random.randint(10, 20))

# === HANDLERS ===
async def drop_memes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    admin_ids = [admin.user.id for admin in admins]

    if user_id not in admin_ids:
        await update.message.reply_text("🚫 You must be an admin to use this.")
        logging.info(f"👮 Unauthorized /dropmemes attempt by user {user_id}")
        return

    global next_auto_drop
    next_auto_drop = time.time() + 3600
    logging.info(f"📢 /dropmemes triggered by admin {user_id}")
    await update.message.reply_text("🔥 Dropping memes now...")
    await post_memes()
    await update.message.reply_text("✅ Memes posted!")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    next_in = int(next_auto_drop - now)
    next_time = datetime.fromtimestamp(next_auto_drop).strftime('%Y-%m-%d %H:%M:%S')
    since_reset = timedelta(seconds=int(now - last_reset))
    unique_posts = len(posted_ids)

    logging.info(f"📊 /status requested by {update.effective_user.id}")
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
            logging.info(f"❌ Non-admin {user_id} tried to use drop_now")
            return
        global next_auto_drop
        next_auto_drop = time.time() + 3600
        logging.info(f"🖲️ Inline button meme drop triggered by {user_id}")
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
                posted_ids.clear()
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
    logging.info("📦 Starting background hourly loop...")
    app.create_task(hourly_loop())

async def main():
    logging.info("🤖 Starting MemeNoKamiBot...")
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
