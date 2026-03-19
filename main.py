import os
import logging
import traceback
import threading
from dotenv import load_dotenv
import http.server
import socketserver

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from bot.handlers import start, help_command, handle_message
from bot.agent import _initialize_agent

# Setup basic logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DummyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"M.AI Bot is running!")
        
    def log_message(self, format, *args):
        # Suppress logging for every request
        pass

class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def run_dummy_server():
    port = int(os.environ.get('PORT', 8080))
    with ReuseTCPServer(("0.0.0.0", port), DummyHandler) as httpd:
        logger.info(f"Dummy HTTP server listening on port {port}...")
        httpd.serve_forever()

def run_telegram_bot():
    try:
        print("Starting main program execution...")
        load_dotenv()
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        allowed_user_id = os.getenv("ALLOWED_USER_ID")
        
        if not bot_token or not allowed_user_id:
            print("Error: Missing TELEGRAM_BOT_TOKEN or ALLOWED_USER_ID in .env file.")
            return

        print("1. Initializing setup...")
        print("2. Setting up Memory...")
        print("3. Initializing LangChain Agent...")
        
        _initialize_agent()
        print("LangChain Agent initialized successfully!")

        print("4. Starting Telegram Application...")
        app = ApplicationBuilder().token(bot_token).build()

        # Handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        
        # Any text message that isn't a command
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        print("\nSuccess! M.AI is now polling for messages.")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print("\n=== FATAL ERROR CAUGHT ===")
        print(f"Error text: {e}")
        traceback.print_exc()
        print("==========================")

def main():
    # Start bot in a background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # Start dummy HTTP server in a separate thread for Render health checks
    server_thread = threading.Thread(target=run_dummy_server, daemon=True)
    server_thread.start()

    # Keep the main thread alive to allow background threads to run
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == '__main__':
    main()
