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
    
    # --- STRICT SYSTEM PROMPT (THE NUCLEAR OPTION) ---
    system_prompt = {
        "role": "system",
        "content": (
            "STRICT OPERATIONAL RULE: You are the AI controller for Whale Bot V17 Colossus. "
            "YOU ARE FORBIDDEN FROM PERFORMING ANY MATHEMATICAL CALCULATIONS OR FORMULAS. "
            "Your internal math logic is disabled. If the user asks for a price calculation, DCA average, "
            "or percentage, you MUST state that you are waiting for the numbers from the Python Engine. "
            "Only provide trading advice and strategic decisions based on numbers EXPLICITLY provided to you in the chat. "
            "NEVER guess, NEVER calculate, NEVER show multiplication or addition results. "
            "If you see a number like 618.83 and a 2% profit, DO NOT calculate the result. "
            "Simply ask the Python Engine for the 'Final Take Profit Price'."
        )
    }
    
    current_messages = [system_prompt] + messages
    
    # 2. Invoke Groq asynchronously strictly for conversation
    try:
        response = await _client.chat.completions.create(
            model=groq_model,
            messages=current_messages,
            temperature=0.1  # Set to minimum to reduce hallucination
        )
    except Exception as e:
        # Revert the recent input if the API itself fails structurally
        history_manager.get_messages(user_id).pop() 
        raise e
        
    response_message = response.choices[0].message
    final_output = response_message.content or "No response generated."
    
    history_manager.add_message(user_id, "assistant", final_output)
    return final_output
