from collections import deque, defaultdict
import logging
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

MAX_HISTORY_LENGTH = 10

class ConversationHistory:
    def __init__(self):
        self.history = defaultdict(lambda: deque(maxlen=MAX_HISTORY_LENGTH))

    def add_message(self, user_id, role, content):
        self.history[user_id].append({"role": role, "content": content})
        logger.debug(f"Added message for user {user_id}: {role} - {content[:50]}...")

    def get_history(self, user_id):
        logger.debug(f"Retrieving conversation history for user {user_id}")
        return list(self.history[user_id])

    def clear_history(self, user_id):
        self.history[user_id].clear()
        logger.debug(f"Cleared conversation history for user {user_id}")

conversation_history = ConversationHistory()

def is_duplicate_message(message_queue, sender_id, message_text, timestamp):
    message_id = f"{sender_id}:{message_text}:{timestamp}"
    if message_id in message_queue:
        logger.debug(f"Duplicate message detected: {message_id}")
        return True
    message_queue.append(message_id)
    logger.debug(f"New message added to queue: {message_id}")
    return False

def detect_language(text):
    try:
        lang = detect(text)
        if lang == 'ru':
            logger.debug("Detected language: Russian")
            return 'russian'
        elif lang == 'kk':
            logger.debug("Detected language: Kazakh")
            return 'kazakh'
        else:
            logger.debug(f"Detected language: {lang}")
            return 'english'  # Default to English for other languages
    except LangDetectException:
        logger.warning("Language detection failed, defaulting to English")
        return 'english'