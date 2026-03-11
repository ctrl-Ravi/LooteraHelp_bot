import os
import time
import threading
import requests
import logging
from flask import Flask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    # Render assigns a random port through the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def ping_self():
    url = os.environ.get("RENDER_EXTERNAL_URL")

    # If the URL isn't set, just skip no crash, no fuss
    if not url:
        logger.info("KeepAlive: no URL found, skipping")
        return

    logger.info(f"KeepAlive: pinging {url} every 5 minutes...")

    while True:
        try:
            requests.get(url, timeout=10)
            logger.info("KeepAlive: ping sent ✓")
        except Exception as e:
            logger.error(f"KeepAlive: something went wrong — {e}")

        time.sleep(300)  # sleep for 5 minutes, then repeat

def keep_alive():
    # Start the Flask web server (Required by Render to bind the port)
    t_flask = threading.Thread(target=run_flask, daemon=True)
    t_flask.start()
    
    # Start the self-pinging loop (The code you provided)
    t_ping = threading.Thread(target=ping_self, daemon=True)
    t_ping.start()
