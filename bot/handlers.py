import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.agent import get_agent_response

logger = logging.getLogger(__name__)

def is_allowed(update: Update) -> bool:
    allowed_user_id = os.getenv("ALLOWED_USER_ID")
    if not allowed_user_id:
        # If not set, deny all for security
        return False
    # Validate user ID
    user_id = str(update.effective_user.id)
    return user_id == allowed_user_id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        logger.warning(f"Unauthorized access attempt by user {update.effective_user.id}")
        return
        
    await update.message.reply_text("Hello! I am M.AI, your local, secure AI assistant. How can I help you today?")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
        
    help_text = (
        "I am M.AI. I operate 100% locally on your machine.\n"
        "Capabilities:\n"
        "- Reason via local Ollama LLM.\n"
        "- Remember past context with persistent memory.\n"
        "- Execute local tools like Math and System commands."
    )
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
        
    user_text = update.message.text
    if not user_text:
        return
        
    # Send a typing action while the local LLM generates a response
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        user_id = str(update.effective_user.id)
        response = await get_agent_response(user_text, user_id)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        await update.message.reply_text("I encountered a local processing error. Check the terminal logs.")
