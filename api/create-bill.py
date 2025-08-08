import json
import jwt
import base64
import urllib.request
import urllib.error
import logging

from api.utils import get_db_connection, release_db_connection, get_cors_headers, cors_preflight, JWT_SECRET, BILLPLZ_COLLECTION_ID, BILLPLZ_API_KEY, BASE_URL

def handler(request):
    """
    Handles the creation of a payment bill with Billplz.
    """
    # Handle CORS preflight requests
    preflight_response = cors_preflight(request)
    if preflight_response:
        return preflight_response

    headers = get_cors_headers()
    conn = None
    try:
        # User authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return (json.dumps({'error': 'Authorization token required'}), 401, headers)
        
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        username = payload.get('username')
        if not username:
            return (json.dumps({'error': 'Invalid token: username missing'}), 401, headers)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM users WHERE username = %s', (username,))
        user_record = cursor.fetchone()
        if not user_record:
            return (json.dumps({'error': 'User not found'}), 404, headers)

        request_json = request.get_json(silent=True) or {}
        plan_name = request_json.get('planName')
        amount = request_json.get('amount')
        plan_id = request_json.get('planId', '')
        
        if not plan_name or not amount:
            return (json.dumps({'error': 'Plan information is missing'}), 400, headers)

        # Build Billplz payload
        billplz_payload = {
            'collection_id': BILLPLZ_COLLECTION_ID,
            'email': f"{username}@pfcreative.system", 
            'name': username,
            'amount': str(int(amount)),
            'description': plan_name[:200],
            'callback_url': f"{BASE_URL}/api/webhook-billplz",
            'redirect_url': f"{BASE_URL}/payment-success.html",
            'reference_1_label': 'Username',
            'reference_1': username,
            'reference_2_label': 'PlanID',
            'reference_2': plan_id
        }
        
        # Build API request headers
        req_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {base64.b64encode(f"{BILLPLZ_API_KEY}:".encode()).decode()}'
        }
        
        # Create and send the request to Billplz
        req = urllib.request.Request(
            'https://www.billplz.com/api/v3/bills',
            method='POST',
            data=json.dumps(billplz_payload).encode('utf-8'),
            headers=req_headers
        )

        with urllib.request.urlopen(req) as response:
            if response.getcode() == 200:
                billplz_result = json.loads(response.read().decode())
                if 'url' in billplz_result:
                    logging.info(f"Payment link created for {username}: {billplz_result['url']}")
                    return (json.dumps({
                        'url': billplz_result['url'],
                        'bill_id': billplz_result.get('id', '')
                    }), 200, headers)
            
            error_body = response.read().decode()
            logging.error(f"Billplz API error: {response.getcode()} - {error_body}")
            return (json.dumps({'error': 'Failed to create payment link'}), 502, headers)

    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        logging.error(f"Billplz HTTP Error: {e.code} - {error_body}")
        return (json.dumps({'error': 'Payment service error'}), 502, headers)
    except urllib.error.URLError as e:
        logging.error(f"Billplz connection error: {str(e)}")
        return (json.dumps({'error': 'Cannot connect to payment service'}), 503, headers)
    except Exception as e:
        logging.error(f"Create Bill Error: {str(e)}", exc_info=True)
        return (json.dumps({'error': 'Internal server error'}), 500, headers)
    finally:
        if conn:
            try:
                cursor.close()
            except Exception as e:
                logging.error(f"Error closing cursor: {e}")
            release_db_connection(conn)
