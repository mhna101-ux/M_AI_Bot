import os
import json
from groq import AsyncGroq

from bot.memory_manager import get_history_manager

_client = None

def _initialize_agent():
    global _client
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not set.")
    _client = AsyncGroq(api_key=groq_api_key)

async def get_agent_response(user_input: str, user_id: str) -> str:
    global _client
    
    if _client is None:
        _initialize_agent()
        
    groq_model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
    history_manager = get_history_manager()
    
    # 1. Update memory state natively
    history_manager.add_message(user_id, "user", user_input)
    messages = history_manager.get_messages(user_id)
    
    system_prompt = {
        "role": "system",
        "content": (
            "You are M.AI, a highly intelligent and elite expert AI assistant. "
            "You possess extraordinary, world-class expertise in three core domains:\n"
            "1. Cryptocurrency trading, mining, and financial market analysis.\n"
            "2. Senior Python programming, debugging, and software architecture.\n"
            "3. Advanced data analysis and complex text summarization.\n\n"
            "Answer questions concisely and thoughtfully, always leveraging your advanced "
            "expertise where appropriate. You are a direct conversational AI, do not attempt to invoke any external functions."
        )
    }
    
    current_messages = [system_prompt] + messages
    
    # 2. Invoke Groq asynchronously strictly for conversation
    try:
        response = await _client.chat.completions.create(
            model=groq_model,
            messages=current_messages,
            temperature=0.1
        )
    except Exception as e:
        # Revert the recent input if the API itself fails structurally
        history_manager.get_messages(user_id).pop() 
        raise e
        
    response_message = response.choices[0].message
    final_output = response_message.content or "No response generated."
    
    history_manager.add_message(user_id, "assistant", final_output)
    return final_output
