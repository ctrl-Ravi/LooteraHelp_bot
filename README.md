# Lootera Shopper Telegram Bot 🛍️

A smart and efficient Telegram Bot designed to help users instantly share deals, profit screenshots, ask questions, and report feedback directly to a channel administrator.

## Features

- **Four Primary Actions:** 
  - 💰 Share Profit/Cashback
  - 🎁 Submit New Offer
  - ❓ Ask Question/Doubt
  - 📝 Report Issue/Feedback
- **Seamless Admin Forwarding:** User submissions (text, photos, documents) are instantly forwarded to the Admin with their Telegram ID attached cleanly as a caption or combined text snippet.
- **Direct Admin Replies:** The admin can effortlessly reply directly to any forwarded user message, and the bot will instantly relay the answer back to the user privately.
- **Admin Broadcasting:** Exclusive `/broadcast <message>` command allows the admin to send an important announcement to all users who have registered with the bot.
- **Spam Control:** The admin can instantly ban or unban users by replying to their messages with `/ban` or `/unban` (or by using `/ban [user_id]`).

## Deployment on Render (24/7 Uptime)

This bot is fully configured to run natively on Render's Free Tier architecture.

### 1. The Keep-Alive Strategy

Because Render shuts down "Free Web Services" if they don't receive web traffic for 15 minutes, this repository includes:
* **Flask Server (`keep_alive.py`)**: A lightweight background server that satisfies Render's requirement to bind active web services to the `$PORT` variable.
* **Auto-Pinger**: The background server continuously pings its own `RENDER_EXTERNAL_URL` every 5 minutes, tricking Render into keeping the bot awake 24/7 forever without the need for external chron-job pingers.

### 2. Environment Variables (.env)

Critical variables have been stripped from the source code and must be provided via the Render Dashboard.

In your Render Dashboard (**Environment** section), add these two Secret Variables:
- `BOT_TOKEN`: The API token provided by `@BotFather` on Telegram.
- `ADMIN_CHAT_ID`: Your personal Telegram User ID (e.g. `12345678`), where you want submissions forwarded to.

*(If testing locally, clone the repo and create a `.env` file in the root directory with these same variables).*

### 3. Build & Start Commands

*   **Build Command:** `pip install -r requirements.txt`
*   **Start Command:** `python bot.py` (Or utilize the included `Procfile` by setting it as `web: python bot.py`).

## Tech Stack
* Python 3
* `pyTelegramBotAPI` (Telegram wrapper)
* `Flask` & `requests` (Render Keep-Alive architecture)
* `python-dotenv` (Secure variable management)
