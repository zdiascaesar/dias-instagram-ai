import asyncio
import time
from collections import defaultdict
from instagram_api import send_message
from ai_handler import generate_ai_response
from database_handler import get_clients_for_reminders, get_client_data
import logging

logger = logging.getLogger(__name__)

class ReminderBot:
    def __init__(self):
        self.user_timestamps = defaultdict(float)
        self.sent_reminders = defaultdict(set)
        self.reminder_intervals = [
            (12 * 3600, "12 hours"),
            (7 * 24 * 3600, "1 week"),
            (14 * 24 * 3600, "2 weeks"),
            (30 * 24 * 3600, "1 month")
        ]
        self.running = False
        self.task = None

    async def add_user_message(self, user_id):
        self.user_timestamps[user_id] = time.time()
        self.sent_reminders[user_id] = set()

    async def check_and_send_reminders(self):
        clients_for_reminders = await get_clients_for_reminders()
        for client in clients_for_reminders:
            await self.send_targeted_reminder(client)

    async def send_targeted_reminder(self, client):
        user_id = client['instagram_id']
        final_decision = client.get('final_decision', '')
        payment_status = client.get('payment_status', False)

        context = f"""You are an AI assistant for an Instagram consultant service. Your task is to generate a reminder message for a potential client. 
        The client's final decision was "{final_decision}" and their payment status is {"completed" if payment_status else "pending"}. 
        If the client hasn't made a decision, encourage them to make one. If they haven't paid, remind them about the payment.
        The message should be engaging, encouraging, and aim to convert the lead or complete the payment. 
        Keep the message concise, friendly, and tailored to the client's current status."""

        input_text = f"Generate a targeted reminder message for a client with final decision: {final_decision} and payment status: {'completed' if payment_status else 'pending'}."
        
        try:
            reminder_message = await generate_ai_response(user_id, input_text, context)
        except Exception as e:
            logger.error(f"Error generating AI reminder: {e}")
            reminder_message = f"Hey there! We noticed you haven't made a final decision about our Instagram consultant service. We'd love to help you grow your Instagram presence. Let's chat about your needs!"

        success = await send_message(user_id, reminder_message)
        if success:
            logger.info(f"Sent targeted reminder to user {user_id}")
        else:
            logger.error(f"Failed to send targeted reminder to user {user_id}")

    async def run(self):
        self.running = True
        while self.running:
            await self.check_and_send_reminders()
            await asyncio.sleep(3600 * 12)  # Check every 12 hours

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("ReminderBot stopped")

reminder_bot = ReminderBot()

async def start_reminder_bot():
    reminder_bot.task = asyncio.create_task(reminder_bot.run())

def get_reminder_bot():
    return reminder_bot