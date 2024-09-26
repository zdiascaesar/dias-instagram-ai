import asyncio
import time
from collections import defaultdict
from instagram_api import send_message
from ai_handler import generate_ai_response
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

    async def add_user_message(self, user_id):
        self.user_timestamps[user_id] = time.time()
        self.sent_reminders[user_id] = set()

    async def check_and_send_reminders(self):
        current_time = time.time()
        for user_id, timestamp in self.user_timestamps.items():
            for interval, interval_name in self.reminder_intervals:
                if current_time - timestamp > interval and interval_name not in self.sent_reminders[user_id]:
                    await self.send_reminder(user_id, interval_name)
                    self.sent_reminders[user_id].add(interval_name)

    async def send_reminder(self, user_id, interval):
        context = f"""You are an AI assistant for a programming course. Your task is to generate a reminder message for a user who hasn't interacted with the course in {interval}. The message should be engaging, encouraging, and aim to bring the user back to the course. Keep the message concise, friendly, and tailored to the time that has passed."""

        input_text = f"Generate a reminder message for a user who hasn't interacted with the course in {interval}."
        
        try:
            reminder_message = await generate_ai_response(user_id, input_text, context)
        except Exception as e:
            logger.error(f"Error generating AI reminder: {e}")
            reminder_message = f"Hey there! It's been {interval} since we last connected. How about we continue your programming journey?"

        success = await send_message(user_id, reminder_message)
        if success:
            logger.info(f"Sent {interval} reminder to user {user_id}")
        else:
            logger.error(f"Failed to send {interval} reminder to user {user_id}")

    async def run(self):
        while True:
            await self.check_and_send_reminders()
            await asyncio.sleep(3600)  # Check every hour

reminder_bot = ReminderBot()

async def start_reminder_bot():
    asyncio.create_task(reminder_bot.run())

def get_reminder_bot():
    return reminder_bot