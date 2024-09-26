import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
from typing import Dict, Any, Optional, List

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Supabase client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

async def save_or_update_client_data(instagram_id: str, client_data: Dict[str, Any]) -> bool:
    """
    Save or update client data in Supabase database.
    
    :param instagram_id: Instagram ID of the client
    :param client_data: Dictionary containing client information
    :return: True if successful, False otherwise
    """
    try:
        # Ensure instagram_id is in the client_data
        client_data['instagram_id'] = instagram_id

        # Check if the client already exists
        existing_data = await get_client_data(instagram_id)
        
        if existing_data:
            # Update existing record
            response = supabase.table("clients").update(client_data).eq("instagram_id", instagram_id).execute()
        else:
            # Insert new record
            response = supabase.table("clients").insert(client_data).execute()
        
        if response.data:
            logger.info(f"Successfully saved/updated client data for Instagram ID: {instagram_id}")
            return True
        else:
            logger.error(f"Failed to save/update client data: {response.error}")
            return False
    except Exception as e:
        logger.error(f"Error saving/updating client data: {str(e)}")
        return False

async def get_client_data(instagram_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve client data from Supabase database.
    
    :param instagram_id: Instagram ID of the client
    :return: Client data if found, None otherwise
    """
    try:
        response = supabase.table("clients").select("*").eq("instagram_id", instagram_id).execute()
        data = response.data
        if data:
            return data[0]
        else:
            logger.info(f"No client data found for Instagram ID: {instagram_id}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving client data: {str(e)}")
        return None

async def get_clients_for_reminders() -> List[Dict[str, Any]]:
    """
    Retrieve clients who need reminders (final decision is uncertain or haven't paid).
    
    :return: List of client data for those who need reminders
    """
    try:
        response = supabase.table("clients").select("*").or_(
            "final_decision.eq.not sure,final_decision.eq.I will think about it,payment_status.eq.false"
        ).execute()
        data = response.data
        if data:
            logger.info(f"Retrieved {len(data)} clients for reminders")
            return data
        else:
            logger.info("No clients found for reminders")
            return []
    except Exception as e:
        logger.error(f"Error retrieving clients for reminders: {str(e)}")
        return []

async def verify_supabase_connection() -> bool:
    """
    Verify the Supabase connection by performing a simple query.
    
    :return: True if connection is successful, False otherwise
    """
    try:
        response = supabase.table('clients').select('instagram_id').limit(1).execute()
        if response.data is not None:
            logger.info("Supabase connection verified successfully")
            return True
        else:
            logger.error("Supabase connection failed: No data returned")
            return False
    except Exception as e:
        logger.error(f"Supabase connection failed: {str(e)}")
        return False