import os
import json
from groq import AsyncGroq

from bot.memory_manager import get_history_manager
from tools.math_tool import evaluate_math, get_math_tool_schema
from tools.system_tool import execute_system_command, get_system_tool_schema

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
    
    # Prepend the system directive internally
    system_prompt = {
        "role": "system",
        "content": "You are M.AI, a highly intelligent local AI assistant. You have access to local tools like MathCalculator and SystemTerminal. Answer questions concisely and thoughtfully. When using a tool, you do not need to explain that you are using it; just execute."
    }
    
    current_messages = [system_prompt] + messages
    
    tools = [
        get_math_tool_schema(),
        get_system_tool_schema()
    ]
    
    # 2. Invoke Groq asynchronously allowing for potential tool callbacks
    while True:
        try:
            response = await _client.chat.completions.create(
                model=groq_model,
                messages=current_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1
            )
        except Exception as e:
            # Revert the recent input if the API itself fails structurally
            history_manager.get_messages(user_id).pop() 
            raise e
            
        response_message = response.choices[0].message
        
        # Determine exit condition: Did it return string content and no tools?
        if not response_message.tool_calls:
            final_output = response_message.content or "No response generated."
            history_manager.add_message(user_id, "assistant", final_output)
            return final_output
            
        # Append the native Assistant ToolCall object (required for Groq to maintain context)
        current_messages.append(response_message)
        
        # Fulfill all requested tool executions locally
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            
            try:
                function_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                function_args = {}
                
            tool_response = ""
            if function_name == "MathCalculator":
                tool_response = evaluate_math(function_args.get("expression", ""))
            elif function_name == "SystemTerminal":
                tool_response = execute_system_command(function_args.get("command", ""))
            else:
                tool_response = f"Error: Unknown tool '{function_name}'"
                
            current_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": str(tool_response)
            })
