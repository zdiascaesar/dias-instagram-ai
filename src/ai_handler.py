import aiohttp
import os
from dotenv import load_dotenv
from utils import detect_language, conversation_history
import logging
import json
import random

logger = logging.getLogger(__name__)

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    logger.error("ANTHROPIC_API_KEY is not set in the environment variables")

async def generate_ai_response(user_id, input_text, context=None):
    language = detect_language(input_text)
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    if context is None:
        try:
            with open('prompts/instagram_consultant_prompt.txt', 'r') as file:
                context = file.read()
        except FileNotFoundError:
            context = "You are an AI assistant and your name is Dias for a programming course. Provide helpful and engaging responses."
    
    history = conversation_history.get_history(user_id)
    messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]
    messages.append({"role": "user", "content": input_text})
    
    data = {
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 1000,
        "system": context,
        "messages": messages
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=30) as response:
                response.raise_for_status()
                result = await response.json()
                ai_response = result['content'][0]['text']
        
        emojis = ['👋', '😊', '💡', '🚀', '💻', '📚', '🌟', '🔥', '💪', '🎓']
        if not any(emoji in ai_response for emoji in emojis):
            ai_response += f" {random.choice(emojis)}"
        
        conversation_history.add_message(user_id, "user", input_text)
        conversation_history.add_message(user_id, "assistant", ai_response)
        
        return ai_response
    except aiohttp.ClientError as e:
        logger.error(f"Network error when calling Anthropic API: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response from Anthropic API: {e}")
    except KeyError as e:
        logger.error(f"Unexpected response structure from Anthropic API: {e}")
    except Exception as e:
        logger.error(f"Unexpected error generating AI response: {e}")
    
    return "Oops! 😅 I'm having a quick glitch. Mind asking about our AI course again? I'm here to help! 🚀"