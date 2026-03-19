# M.AI - Local Persistent AI Assistant

A **100% pure Python**, entirely local AI assistant utilizing Ollama (Llama 3), ChromaDB for persistent long-term memory, and a secure Telegram Bot interface.

## Prerequisites
1. **Python 3.10+** installed.
2. **Ollama** installed on your system (download from [ollama.com](https://ollama.com)).
3. A Telegram Bot Token (get from [@BotFather](https://t.me/BotFather) on Telegram).
4. Your Telegram User ID (get from [@userinfobot](https://t.me/userinfobot)).

## Setup

1. **Pull the Local LLM**
   Open your terminal and run:
   ```bash
   ollama pull llama3
   ```

2. **Install Python Dependencies**
   Make sure you are in the project root (`e:\M.AI`) and run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   Rename `.env.example` to `.env` and fill in your details:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token
   ALLOWED_USER_ID=your_user_id
   ```
   *(Important: M.AI will **ignore** all messages from any user ID other than the one specified).*

4. **Run M.AI**
   ```bash
   python main.py
   ```

M.AI will now run locally in your terminal, retaining long-term memory in the `chroma_db` folder, and answering you securely on Telegram!
