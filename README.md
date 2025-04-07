# 🤖 MemeNoKamiBot

<p align="center">
  <img src="images/botInAction.png" alt="Main Features Showcase" width="48%" />
  &nbsp;
  <img src="images/botInAction2.png" alt="Bot in Action" width="48%" />
</p>

**MemeNoKamiBot** is a Telegram bot that fetches top memes from popular Reddit subreddits and automatically posts them to a designated Telegram group topic. It's built with Python using `python-telegram-bot`, `PRAW`, and `dotenv`.

---

## 🚀 Features

- 🔥 **Auto Meme Drops**: Posts memes from subreddits like `r/memes`, `r/ProgrammerHumor`, `r/funny`, and more every hour.
- ✋ **Admin-Triggered Drops**: Group admins can manually drop memes via `/dropmemes` or inline button.
- 🕓 **Delay Logic**: Manual drops delay the next scheduled drop by 1 hour to avoid spamming.
- ❌ **Duplicate Filtering**: Skips reposts by tracking previously posted Reddit IDs.
- 🎥 **Media Support**: Handles images, videos, `.gif`, `.gifv`, and `.mp4` formats.
- 📦 **Persistent Storage**: Saves posted IDs to Firebase Realtime Database for durability.
- 📊 **Status Dashboard**: `/status` command shows stats, uptime, and upcoming drop time.
- 🔐 **Credential Security**: Uses `.env` for API credentials, including Firebase service account JSON.
- ♻️ **Daily Reset**: Clears duplicate tracker daily to allow fresh content.

---

## 💬 Bot Commands

**MemeNoKamiBot** responds to the following slash `/` commands in your Telegram group:

### 📥 `/dropmemes`

Fetches and posts **top trending memes** from Reddit right into your Telegram group topic.

- 🌐 **Sources**: Pulls memes from `r/memes`, `r/ProgrammerHumor`, `r/AImemes`, and more.
- 🔁 **No Reposts**: Uses Reddit post IDs to avoid duplicates.
- 📺 **Video & GIF Support**: Handles Reddit-hosted media effortlessly.
- ⏰ **Resets Timer**: Using this command delays the next auto-drop by 1 hour to prevent spam.

📌 **Example Output:**
```markdown
🔥 Here comes your daily dose of memes!
📄 r/ProgrammerHumor | 👍 13.2k | 💬 290 Comments
🖼️ [Image or Video Meme]
```
---

### 📊 `/status` Command

Returns the current configuration and stats of the MemeNoKamiBot:

```bash
📊 MemeNoKamiBot Status:

• 🤖 Bot Username: @MemeNoKamiBot
• 🕒 Next Auto Drop In: 45 minutes
• 🔄 Last Meme Drop: 15 minutes ago
• 📁 Subreddits Tracked: r/memes, r/ProgrammerHumor, r/dankmemes
• 🚫 Duplicates Filtered: 98
• 📦 Total Memes Sent: 264
• 💾 Data Persistence: Enabled
• 🎛️ Admin Override Mode: Off
```

> ⚡ Tip: `/dropmemes` is **admin-only**. Normal users can enjoy the memes passively!



## 📦 Installation & Setup

> 💡 Make sure you have Python 3.10+ installed.

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/MemeNoKamiBot.git
cd MemeNoKamiBot
```

### 2. Set Up a Virtual Environment
python -m venv env
### 3. Activate the environment:
- On macOS/Linux: source env/bin/activate
- On Windows: env\Scripts\activate

### 4. Install Dependencies
pip install -r requirements.txt

## 🔐 Configuration
### 5. Create a .env File
```ini
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=MemeBot/0.1 by your_reddit_username

TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_GROUP_ID=-1001234567890
TELEGRAM_TOPIC_ID=143

FIREBASE_DATABASE_URL=https://reddittotelegrammemebot-default-rtdb.asia-southeast1.firebasedatabase.app/
FIREBASE_KEY_JSON={"type":"service_account","project_id":"your-project-id", ... }

```
> 🔐 Important Notes: 
- "You no longer need a firebase_key.json file!"
- "Copy your Firebase service account JSON, minify it to a single line, and paste it into FIREBASE_KEY_JSON."
- "Minify tool: https://jsonformatter.org/json-minify"
- Remove ``.example`` from ``.env.example`` file and Replace the placeholders inside it with your actual credentials.


## 🚀 Running the Bot
### 6. Run the bot using:
```bash
python meme_no_kami.py
```
<em>Once running:</em>
- Memes will start posting every hour.
- Admins can use /dropmemes to post memes instantly.
- Use /status to check the next drop time, uptime, and stats.

## 🧠 Use Cases
- Keep Telegram group chats active with automated, curated memes.
- Ideal for AI/ML, dev, or tech communities.
- Low maintenance, high engagement tool.
- Filters duplicates and manages meme frequency automatically.

## 📜 License
This project is licensed under the MIT License. Feel free to use, modify, and share.

## 🛠️ Built With

- [**PRAW** (Python Reddit API Wrapper)](https://praw.readthedocs.io/en/latest/) — for accessing Reddit posts.
- [**python-telegram-bot**](https://docs.python-telegram-bot.org/) — to interact with Telegram’s Bot API.
- [**python-dotenv**](https://saurabh-kumar.com/python-dotenv/) — for securely loading environment variables from a `.env` file.

> **Made with ❤️ by meme enjoyers, for meme enjoyers.**

---