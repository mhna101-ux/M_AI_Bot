import os
import asyncio
from langchain_groq import ChatGroq
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

from bot.memory_manager import get_chroma_store
from tools.math_tool import get_math_tool
from tools.system_tool import get_system_tool

_agent_executor = None
_chroma_store = None
_retriever = None

def _initialize_agent():
    global _agent_executor, _chroma_store, _retriever
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
    
    # Initialize the LLM via Groq API
    llm = ChatGroq(
        api_key=groq_api_key,
        model_name=groq_model,
        temperature=0.1
    )
    
    # Initialize Persistent Vector Memory natively without legacy wrappers
    _chroma_store = get_chroma_store()
    _retriever = _chroma_store.as_retriever(search_kwargs=dict(k=5))
    
    # Load Python native tools
    tools = [
        get_math_tool(),
        get_system_tool()
    ]
    
    # Pure offline ReAct Chat prompt to maintain 100% local nature
    template = '''You are M.AI, a highly intelligent local AI assistant.

You have access to the following tools:

{tools}

To use a tool, you MUST use the exact following format:

```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
```

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

```
Thought: Do I need to use a tool? No
Final Answer: [your response here]
```

Begin!

Relevant past context (recalled from Vector Memory):
{chat_history}

New Input: {input}
{agent_scratchpad}'''

    prompt = PromptTemplate.from_template(template)
    
    # Create the core reasoning agent (no built-in memory required)
    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    
    # Initialize the executor that handles the standard ReAct loops
    _agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )

async def get_agent_response(user_input: str) -> str:
    global _agent_executor, _retriever, _chroma_store
    
    if _agent_executor is None:
        _initialize_agent()
        
    assert _agent_executor is not None
    assert _retriever is not None
    assert _chroma_store is not None
    
    # 1. Retrieve highly relevant past interactions using native ChromaDB Search
    past_docs = _retriever.invoke(user_input)
    
    if past_docs:
        chat_history_str = "\n---\n".join([doc.page_content for doc in past_docs])
    else:
        chat_history_str = "No relevant past context found."
        
    # 2. Invoke the agent manually injecting the Chat History into the template prompt string
    response = await _agent_executor.ainvoke({
        "input": user_input,
        "chat_history": chat_history_str
    })
    
    output_text = response["output"]
    
    # 3. Permanently save this new interaction into the Chroma VectorStore
    new_memory = f"Human: {user_input}\nM.AI Assistant: {output_text}"
    _chroma_store.add_documents([Document(page_content=new_memory)])
    
    return output_text
