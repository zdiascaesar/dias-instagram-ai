import asyncio
from ai_handler import generate_ai_response, extract_client_info
from database_handler import save_or_update_client_data, get_client_data
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def simulate_conversation():
    user_id = "test_user_12"
    conversation = [
        "Hi, I'm interested in your programming course.",
        "You can call me John Doe.",
        "I'm living in New York City, USA.",
        "My email is john.doe@example.com and you can find me on Telegram @johndoe.",
        "You can reach me at +1 (234) 567-8900 if needed.",
        "I have a passion for AI and machine learning. Can you tell me more about the course?",
        "That sounds great! I'd like to sign up for the course. What's the next step?",
        "Awesome, I've completed the payment for the course.",
        "Is there anything else you need from me?"
    ]

    for message in conversation:
        # User message
        logger.info(f"User: {message}")
        
        # AI response
        ai_response = await generate_ai_response(user_id, message)
        logger.info(f"AI: {ai_response}")

        # Extract and update client info
        new_info = extract_client_info(message)
        if new_info:
            try:
                await save_or_update_client_data(user_id, new_info)
                logger.info(f"Updated client info: {new_info}")
            except Exception as e:
                logger.error(f"Error updating client info: {str(e)}")

        # Check if AI provides a summary when all information is collected
        if "summary" in ai_response.lower():
            logger.info("AI provided a summary of collected information.")

    # Verify saved data
    try:
        saved_data = await get_client_data(user_id)
        if saved_data:
            logger.info("Final saved client data:")
            logger.info(saved_data)
            
            # Verify all required fields are present
            required_fields = ['name', 'email', 'telegram_username', 'phone_number', 'city_country', 'interests', 'final_decision', 'paid']
            missing_fields = [field for field in required_fields if field not in saved_data]
            if missing_fields:
                logger.warning(f"Missing fields in saved data: {', '.join(missing_fields)}")
            else:
                logger.info("All required fields are present in saved data.")
        else:
            logger.error("Failed to retrieve client data from database.")
    except Exception as e:
        logger.error(f"Error retrieving client data: {str(e)}")

async def main():
    await simulate_conversation()

if __name__ == "__main__":
    asyncio.run(main())