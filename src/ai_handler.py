import aiohttp
import os
import re
from dotenv import load_dotenv
from utils import detect_language, conversation_history
import logging
import json
import random
from database_handler import save_or_update_client_data

logger = logging.getLogger(__name__)

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    logger.error("ANTHROPIC_API_KEY is not set in the environment variables")

def get_missing_info(user_data):
    required_fields = ['name', 'email', 'telegram_username', 'phone_number', 'city_country', 'interests', 'final_decision', 'paid']
    return [field for field in required_fields if field not in user_data]

def generate_info_summary(user_data):
    summary = "Here's a summary of the information I have:\n"
    if 'name' in user_data:
        summary += f"Name: {user_data['name']}\n"
    if 'email' in user_data:
        summary += f"Email: {user_data['email']}\n"
    if 'telegram_username' in user_data:
        summary += f"Telegram: {user_data['telegram_username']}\n"
    if 'phone_number' in user_data:
        summary += f"Phone: {user_data['phone_number']}\n"
    if 'city_country' in user_data:
        summary += f"Location: {user_data['city_country']}\n"
    if 'interests' in user_data:
        summary += f"Interests: {user_data['interests']}\n"
    if 'final_decision' in user_data:
        summary += f"Course Decision: {user_data['final_decision']}\n"
    if 'paid' in user_data:
        summary += f"Payment Status: {'Paid' if user_data['paid'] else 'Not Paid'}\n"
    return summary

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
                base_context = file.read()
        except FileNotFoundError:
            base_context = "You are an AI assistant named Dias for an Instagram consultant service."
        
        context = f"{base_context}\n\nYour task is to engage in a natural conversation with the user and gather the following information step by step: name, email, Telegram username, phone number, location (city and country), interests in Instagram growth or social media marketing, decision to use our service, and payment status. Don't ask for this information all at once or in a list format. Instead, weave these questions naturally into the conversation. After each response from the user, the system will automatically save any new information provided."

    history = conversation_history.get_history(user_id)
    messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]
    
    # Get user data from conversation history
    user_data = {}
    for msg in history:
        if msg["role"] == "user":
            user_data.update(extract_client_info(msg["content"]))
    
    missing_info = get_missing_info(user_data)
    if missing_info:
        context += f"\n\nThe following information is still missing: {', '.join(missing_info)}. Focus on obtaining this information naturally in the conversation."
    else:
        info_summary = generate_info_summary(user_data)
        context += f"\n\nAll required information has been collected. Here's a summary:\n{info_summary}\nAsk the user if this information is correct and if they have any questions about our Instagram consultant service."

    if 'final_decision' in user_data:
        if user_data['final_decision'] == 'Uncertain':
            context += "\nThe user is uncertain about using our service. Address their specific concerns, provide more detailed information about our services, and highlight the unique benefits we offer. Ask open-ended questions to understand their hesitations better."
        elif user_data['final_decision'] == 'Leaning Towards Yes':
            context += "\nThe user is leaning towards using our service. Reinforce their positive inclination by summarizing the key benefits and addressing any remaining doubts they might have. Offer to guide them through the next steps."
        elif user_data['final_decision'] == 'Leaning Towards No':
            context += "\nThe user is leaning towards not using our service. Try to understand their reasons without being pushy. Offer additional information or alternatives that might better suit their needs. Keep the conversation open for future possibilities."
        elif user_data['final_decision'] == 'Not Interested':
            context += "\nThe user has indicated they're not interested in our service. Respectfully acknowledge their decision, thank them for their time, and keep the door open for future engagement. You might offer to keep them updated on new services or promotions if they're interested."

    if 'paid' in user_data:
        if user_data['paid']:
            context += "\nThe user has paid for the service. Express gratitude for their payment and commitment. Offer immediate next steps or information on how to get started with the service."
        else:
            context += "\nThe user hasn't paid for the service yet. If they've decided to join, gently remind them about the payment process, offer assistance if needed, and provide clear instructions on how to complete the payment."

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
        
        emojis = ['👋', '😊', '💡', '🚀', '🌟', '🔥', '💪', '📈']
        if not any(emoji in ai_response for emoji in emojis):
            ai_response += f" {random.choice(emojis)}"
        
        conversation_history.add_message(user_id, "user", input_text)
        conversation_history.add_message(user_id, "assistant", ai_response)
        
        # Extract and save client info after each message
        new_info = extract_client_info(input_text)
        if new_info:
            await update_client_info(user_id, new_info)
        
        return ai_response
    except aiohttp.ClientError as e:
        logger.error(f"Network error when calling Anthropic API: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response from Anthropic API: {e}")
    except KeyError as e:
        logger.error(f"Unexpected response structure from Anthropic API: {e}")
    except Exception as e:
        logger.error(f"Unexpected error generating AI response: {e}")
    
    return "I apologize, but I'm experiencing some technical difficulties. Could you please try asking your question again? I'm here to help with any inquiries about our Instagram consultant service. 😊"

def extract_client_info(message):
    info = {}
    message_lower = message.lower()
    
    # Name (don't overwrite existing name)
    name_match = re.search(r'(?:my name is|i\'m|i am|call me)\s+([A-Za-z\s]+)', message_lower)
    if name_match and 'name' not in info:
        info['name'] = name_match.group(1).strip().title()
    
    # Email
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message)
    if email_match:
        info['email'] = email_match.group()
    
    # Telegram username
    telegram_match = re.search(r'@(\w+)', message)
    if telegram_match:
        info['telegram_username'] = telegram_match.group()
    
    # Phone number (including country code)
    phone_match = re.search(r'\+?\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,9}[-.\s]?\d{1,9}', message)
    if phone_match:
        info['phone_number'] = phone_match.group()
    
    # Location
    location_match = re.search(r'(?:i\'m from|i am from|i live in|my location is)\s+([A-Za-z\s,]+)', message_lower)
    if location_match:
        info['city_country'] = location_match.group(1).strip().title()
    
    # Interests
    interests_match = re.search(r'(?:interested in|passion for|excited about)\s+(.+?)(?:\.|$)', message_lower)
    if interests_match:
        info['interests'] = interests_match.group(1).strip()
    
    # Decision to join (expanded with more variations)
    if re.search(r'\b(definitely join|absolutely|sign me up|ready to start|let\'s do this)\b', message_lower):
        info['final_decision'] = "Joined"
    elif re.search(r'\b(considering|leaning towards yes|probably will|sounds good|interested)\b', message_lower):
        info['final_decision'] = "Leaning Towards Yes"
    elif re.search(r'\b(not sure|maybe|thinking about it|need more time|uncertain|on the fence)\b', message_lower):
        info['final_decision'] = "Uncertain"
    elif re.search(r'\b(probably not|leaning towards no|not convinced|hesitant)\b', message_lower):
        info['final_decision'] = "Leaning Towards No"
    elif re.search(r'\b(not interested|don\'t want|no thanks|not for me)\b', message_lower):
        info['final_decision'] = "Not Interested"
    
    # Payment status
    if re.search(r'\b(paid|completed payment|payment sent|transaction done)\b', message_lower):
        info['paid'] = True
    elif re.search(r'\b(haven\'t paid|not paid|pending payment|still need to pay)\b', message_lower):
        info['paid'] = False
    
    return info

async def update_client_info(user_id, new_info):
    try:
        await save_or_update_client_data(user_id, new_info)
        logger.info(f"Updated client info for user {user_id}: {new_info}")
    except Exception as e:
        logger.error(f"Error updating client info for user {user_id}: {str(e)}")