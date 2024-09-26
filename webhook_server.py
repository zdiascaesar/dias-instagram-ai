from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import requests
import os
from dotenv import load_dotenv
from collections import deque
import time

# Load environment variables
load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
INSTAGRAM_TOKEN = os.getenv("INSTAGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Deduplication queue
message_queue = deque(maxlen=100)

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/webhook":
            params = parse_qs(parsed_path.query)
            mode = params.get("hub.mode", [None])[0]
            token = params.get("hub.verify_token", [None])[0]
            challenge = params.get("hub.challenge", [None])[0]

            if mode == "subscribe" and token == VERIFY_TOKEN:
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(challenge.encode())
            else:
                self.send_response(403)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        try:
            body = json.loads(post_data.decode())
            print("Received webhook data:")
            print(json.dumps(body, indent=2))
            
            # Handle Instagram-specific events
            if 'object' in body and body['object'] == 'instagram':
                handle_instagram_event(body)
            
        except json.JSONDecodeError:
            print("Received invalid JSON data")

        self.wfile.write(json.dumps({"status": "ok"}).encode())

def handle_instagram_event(event_data):
    for entry in event_data.get('entry', []):
        if 'messaging' in entry:
            for messaging_event in entry['messaging']:
                handle_message(messaging_event)
        elif 'changes' in entry:
            for change in entry.get('changes', []):
                if change.get('field') == 'mentions':
                    handle_mention(change.get('value', {}))

def handle_message(message_data):
    sender_id = message_data.get('sender', {}).get('id')
    recipient_id = message_data.get('recipient', {}).get('id')
    message = message_data.get('message', {})
    message_text = message.get('text', '')
    timestamp = message_data.get('timestamp', time.time() * 1000)  # Convert to milliseconds if not provided
    
    print(f"Received message: {message_text}")
    
    # Check for duplicate messages
    if is_duplicate_message(sender_id, message_text, timestamp):
        print("Duplicate message detected. Skipping.")
        return

    if sender_id and message_text and not message.get('is_echo', False):
        # Generate AI response
        ai_response = generate_ai_response(message_text)
        
        # Send the response
        send_message(sender_id, ai_response)
    else:
        print("Skipping message (might be an echo or invalid data)")

def is_duplicate_message(sender_id, message_text, timestamp):
    message_id = f"{sender_id}:{message_text}:{timestamp}"
    if message_id in message_queue:
        return True
    message_queue.append(message_id)
    return False

def handle_mention(mention_data):
    # Extract relevant information
    media_id = mention_data.get('media_id')
    comment_id = mention_data.get('comment_id')
    
    if comment_id:
        # Fetch the comment text
        comment_url = f"https://graph.facebook.com/v12.0/{comment_id}?fields=text&access_token={INSTAGRAM_TOKEN}"
        response = requests.get(comment_url)
        if response.status_code == 200:
            comment_text = response.json().get('text', '')
            print(f"New mention: {comment_text}")
            
            # Generate AI response
            ai_response = generate_ai_response(comment_text)
            
            # Reply to the comment
            reply_to_comment(comment_id, ai_response)
        else:
            print(f"Failed to fetch comment. Status code: {response.status_code}")
            print(f"Response content: {response.text}")
    else:
        print("Error: Invalid mention data received")

def generate_ai_response(input_text):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    data = {
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": f"As an AI Instagram consultant speaking english and russian, provide a friendly and engaging response to the following message: '{input_text}'. The response should be concise (max 50 words) and appropriate for Instagram."}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        ai_response = response.json()['content'][0]['text']
        return ai_response.strip()
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "Thank you for your message! We appreciate your engagement."

def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v12.0/me/messages"
    payload = {
        'recipient': {'id': recipient_id},
        'message': {'text': message_text},
        'access_token': INSTAGRAM_TOKEN
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Successfully sent message")
    else:
        print(f"Failed to send message. Status code: {response.status_code}")
        print(f"Response content: {response.text}")

def reply_to_comment(comment_id, message):
    reply_url = f"https://graph.facebook.com/v12.0/{comment_id}/replies"
    data = {
        'message': message,
        'access_token': INSTAGRAM_TOKEN
    }
    response = requests.post(reply_url, data=data)
    if response.status_code == 200:
        print("Successfully replied to comment")
    else:
        print(f"Failed to reply to comment. Status code: {response.status_code}")
        print(f"Response content: {response.text}")

if __name__ == "__main__":
    if not all([VERIFY_TOKEN, INSTAGRAM_TOKEN, ANTHROPIC_API_KEY]):
        print("Error: One or more required environment variables are not set.")
        exit(1)
    
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, WebhookHandler)
    print("Server running on port 8080")
    httpd.serve_forever()