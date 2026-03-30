import os
import logging
import traceback
import asyncio
from aiohttp import web
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# استدعاء العقل (من مجلد bot)
from bot.handlers import start, help_command, handle_message
from bot.agent import _initialize_agent

# استدعاء العضلات (من مجلد logic)
# ملاحظة: تأكد أن ملفك اسمه CyberWhale_AI.py (بشرطة سفلية)
from logic.CyberWhale_AI import main_trading_loop  

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
        return web.Response(text="CyberWhale Colossus is LIVE and Trading!")
        
    app.router.add_get('/', handle)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Dummy HTTP server listening on port {port}...")
    
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Web server shutting down...")
        await runner.cleanup()
        raise

async def run_telegram_bot():
    """Initializes and runs the Telegram bot."""
    app = None
    try:
        load_dotenv()
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not bot_token:
            logger.error("Error: Missing TELEGRAM_BOT_TOKEN.")
            return

        logger.info("Initializing Agent and Telegram Application...")
        _initialize_agent()
        
        app = ApplicationBuilder().token(bot_token).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        logger.info("Success! Telegram Bot is now polling.")
        
        while True:
            await asyncio.sleep(3600)
            
    except asyncio.CancelledError:
        if app:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
        raise
    except Exception as e:
        logger.error(f"FATAL ERROR in Telegram Bot: {e}")
        traceback.print_exc()

async def run_trading_engine():
    """هذه الدالة تشغل محرك التداول (العضلات) من مجلد logic"""
    try:
        logger.info("Starting CyberWhale Trading Engine...")
        # هنا نقوم بتشغيل الدالة الرئيسية في ملف CyberWhale_AI.py
        await main_trading_loop() 
    except asyncio.CancelledError:
        logger.info("Trading engine shutting down...")
        raise
    except Exception as e:
        logger.error(f"FATAL ERROR in Trading Engine: {e}")
        traceback.print_exc()

async def main():
    """تشغيل الثلاثي المرح: السيرفر، البوت، ومحرك التداول"""
    # إنشاء المهام
    server_task = asyncio.create_task(run_dummy_server())
    bot_task = asyncio.create_task(run_telegram_bot())
    trading_task = asyncio.create_task(run_trading_engine())
    
    try:
        # تشغيل المهام الثلاثة معاً في نفس الوقت
        await asyncio.gather(server_task, bot_task, trading_task)
    except asyncio.CancelledError:
        server_task.cancel()
        bot_task.cancel()
        trading_task.cancel()
        await asyncio.gather(server_task, bot_task, trading_task, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System successfully shut down by CTO.")
