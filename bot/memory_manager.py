class HistoryManager:
    def __init__(self):
        self._history = {}
        # Enforce rolling window per-user so we don't blow up token windows
        self.max_messages = 30

    def get_messages(self, user_id: str) -> list:
        if user_id not in self._history:
            self._history[user_id] = []
        return self._history[user_id]

    def add_message(self, user_id: str, role: str, content: str):
        if user_id not in self._history:
            self._history[user_id] = []
        
        self._history[user_id].append({"role": role, "content": content})
        
        # Apply sliding window logic: pop oldest interactions beyond threshold
        if len(self._history[user_id]) > self.max_messages:
            self._history[user_id] = self._history[user_id][-self.max_messages:]

# Singleton initialization
_manager = HistoryManager()

def get_history_manager() -> HistoryManager:
    return _manager
