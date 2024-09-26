import aiohttp
import os
import json
from dotenv import load_dotenv
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

INSTAGRAM_TOKEN = os.getenv("INSTAGRAM_TOKEN")

logger.info(f"Debug: INSTAGRAM_TOKEN = {INSTAGRAM_TOKEN}")  # Debug line

def split_message(message, chunk_size=1000):
    return [message[i:i+chunk_size] for i in range(0, len(message), chunk_size)]

async def send_message(recipient_id, message):
    url = f"https://graph.facebook.com/v12.0/me/messages"
    
    message_chunks = split_message(message)
    success = True

    async with aiohttp.ClientSession() as session:
        for chunk in message_chunks:
            payload = {
                'recipient': {'id': recipient_id},
                'message': {'text': chunk},
                'access_token': INSTAGRAM_TOKEN
            }
            
            try:
                async with session.post(url, json=payload) as response:
                    await response.text()
                    response.raise_for_status()
                logger.info(f"Successfully sent message chunk to {recipient_id}")
            except aiohttp.ClientError as e:
                logger.error(f"Failed to send message chunk. Error: {e}")
                if response.text:
                    try:
                        error_data = json.loads(await response.text())
                        logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
                    except json.JSONDecodeError:
                        logger.error(f"Raw error response: {await response.text()}")
                success = False
                break
    
    return success

async def reply_to_comment(comment_id, message):
    reply_url = f"https://graph.facebook.com/v12.0/{comment_id}/replies"
    
    message_chunks = split_message(message)
    success = True

    async with aiohttp.ClientSession() as session:
        for chunk in message_chunks:
            data = {
                'message': chunk,
                'access_token': INSTAGRAM_TOKEN
            }
            
            try:
                async with session.post(reply_url, data=data) as response:
                    await response.text()
                    response.raise_for_status()
                logger.info(f"Successfully replied to comment {comment_id} with chunk")
            except aiohttp.ClientError as e:
                logger.error(f"Failed to reply to comment. Error: {e}")
                if response.text:
                    try:
                        error_data = json.loads(await response.text())
                        logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
                    except json.JSONDecodeError:
                        logger.error(f"Raw error response: {await response.text()}")
                success = False
                break
    
    return success

async def fetch_comment_text(comment_id):
    comment_url = f"https://graph.facebook.com/v12.0/{comment_id}?fields=text&access_token={INSTAGRAM_TOKEN}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(comment_url) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('text', '')
        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch comment. Error: {e}")
            if response.text:
                try:
                    error_data = json.loads(await response.text())
                    logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
                except json.JSONDecodeError:
                    logger.error(f"Raw error response: {await response.text()}")
            return None

async def verify_instagram_token():
    url = f"https://graph.facebook.com/v12.0/me?access_token={INSTAGRAM_TOKEN}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                await response.text()
                response.raise_for_status()
            logger.info("Instagram token is valid")
            return True
        except aiohttp.ClientError as e:
            logger.error(f"Instagram token verification failed. Error: {e}")
            if response.text:
                try:
                    error_data = json.loads(await response.text())
                    logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
                except json.JSONDecodeError:
                    logger.error(f"Raw error response: {await response.text()}")
            return False

# Debug function to print all environment variables
def print_env_vars():
    logger.info("Debug: All environment variables:")
    for key, value in os.environ.items():
        logger.info(f"{key}: {value}")

# Call the debug function
print_env_vars()