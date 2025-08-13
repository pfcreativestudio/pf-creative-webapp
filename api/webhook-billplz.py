import json
import datetime
import logging
from api.utils import get_db_connection, release_db_connection, get_cors_headers, cors_preflight, BILLPLZ_X_SIGNATURE

def handler(request):
    """
    Handles Billplz webhook callbacks to update user subscriptions.
    """
    preflight_response = cors_preflight(request)
    if preflight_response:
        return preflight_response

    headers = get_cors_headers()
    conn = None
    try:
        # Verify signature
        incoming_signature = request.headers.get('X-Signature')
        if incoming_signature != BILLPLZ_X_SIGNATURE:
            logging.warning("Invalid signature in webhook")
            return (json.dumps({'error': 'Invalid signature'}), 403, headers)
        
        data = request.get_json()
        paid = data.get('paid')
        username = data.get('reference_1', '')
        plan_id = data.get('reference_2', '')
        
        if paid and username:
            # Determine subscription duration based on plan_id
            if plan_id == 'pro_3m':
                subscription_days = 365
            elif plan_id == 'competent_2m':
                subscription_days = 180
            else:  # beginner_1m
                subscription_days = 30
            
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.datetime.utcnow()
            
            # Check current expiry
            cursor.execute('SELECT subscription_expires_at FROM users WHERE username = %s', (username,))
            current_expiry = cursor.fetchone()
            
            if current_expiry and current_expiry[0] and current_expiry[0] > now:
                new_expiry = current_expiry[0] + datetime.timedelta(days=subscription_days)
            else:
                new_expiry = now + datetime.timedelta(days=subscription_days)
            
            # Update database
            cursor.execute('''
                UPDATE users 
                SET subscription_expires_at = %s 
                WHERE username = %s
            ''', (new_expiry, username))
            conn.commit()
            logging.info(f"Subscription updated for {username}: {new_expiry}")
            return (json.dumps({'success': True}), 200, headers)
        
        return (json.dumps({'error': 'Payment not processed'}), 400, headers)
    except Exception as e:
        logging.error(f"Webhook processing error: {str(e)}", exc_info=True)
        return (json.dumps({'error': 'Internal server error'}), 500, headers)
    finally:
        if conn:
            try:
                cursor.close()
            except Exception as e:
                logging.error(f"Error closing cursor: {e}")
            release_db_connection(conn)