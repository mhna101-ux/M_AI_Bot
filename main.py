import os
import logging
import traceback
import asyncio
from aiohttp import web
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.handlers import start, help_command, handle_message
from bot.agent import _initialize_agent

# Setup basic logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def run_dummy_server():
    """Runs a dummy aiohttp web server to satisfy Render health checks."""
    app = web.Application()
    
    async def handle(request):
        return web.Response(text="M.AI Bot is running!")
        
    app.router.add_get('/', handle)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Dummy HTTP server listening on port {port}...")
    
    try:
        # Keep the web server running indefinitely
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Web server shutting down...")
        await runner.cleanup()
        raise

async def run_telegram_bot():
    """Initializes and runs the Telegram bot using PTB's asyncio interface."""
    app = None
    try:
        print("Starting main program execution...")
        load_dotenv()
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        allowed_user_id = os.getenv("ALLOWED_USER_ID")
        
        if not bot_token or not allowed_user_id:
            logger.error("Error: Missing TELEGRAM_BOT_TOKEN or ALLOWED_USER_ID in .env file.")
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

        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        print("\nSuccess! M.AI is now polling for messages.")
        
        try:
            # Keep the bot task running indefinitely
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("Telegram bot shutting down...")
            if app:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
            raise
            
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print("\n=== FATAL ERROR CAUGHT ===")
        print(f"Error text: {e}")
        traceback.print_exc()
        print("==========================")

async def main():
    """Runs BOTH the dummy aiohttp web server and the Telegram bot concurrenty."""
    # Use asyncio.gather to run tasks in the same main asyncio event loop
    server_task = asyncio.create_task(run_dummy_server())
    bot_task = asyncio.create_task(run_telegram_bot())
    
    try:
        await asyncio.gather(server_task, bot_task)
    except asyncio.CancelledError:
        # Cancel tasks on shutdown
        server_task.cancel()
        bot_task.cancel()
        await asyncio.gather(server_task, bot_task, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Successfully shut down M.AI Bot.")
