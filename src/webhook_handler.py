from aiohttp import web
import json
from message_handler import handle_instagram_event
import os
import logging
import traceback

logger = logging.getLogger(__name__)

async def handle_instagram_webhook(request):
    if request.method == 'GET':
        query = request.query
        mode = query.get("hub.mode")
        token = query.get("hub.verify_token")
        challenge = query.get("hub.challenge")

        if mode == "subscribe" and token == os.getenv("VERIFY_TOKEN"):
            logger.info("Webhook verified successfully")
            return web.Response(text=challenge)
        else:
            logger.warning("Webhook verification failed")
            return web.Response(status=403)

    elif request.method == 'POST':
        try:
            body = await request.json()
            logger.info("Received webhook data:")
            logger.info(json.dumps(body, indent=2))
            
            # Handle Instagram-specific events
            if 'object' in body and body['object'] == 'instagram':
                logger.debug(f"Full Instagram event data: {json.dumps(body, indent=2)}")
                for entry in body.get('entry', []):
                    if 'messaging' in entry:
                        for messaging_event in entry['messaging']:
                            logger.debug(f"Individual messaging event: {json.dumps(messaging_event, indent=2)}")
                    elif 'changes' in entry:
                        for change in entry.get('changes', []):
                            logger.debug(f"Individual change event: {json.dumps(change, indent=2)}")
                
                await handle_instagram_event(body)
            else:
                logger.warning(f"Received unknown webhook object: {body.get('object')}")
            
            return web.json_response({"status": "ok"})
        except json.JSONDecodeError:
            logger.error("Received invalid JSON data")
            return web.Response(status=400)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return web.Response(status=500)

    else:
        return web.Response(status=405)

def setup_routes(app):
    app.router.add_route('*', '/webhook', handle_instagram_webhook)
    app.router.add_route('*', '/instagram_webhook', handle_instagram_webhook)