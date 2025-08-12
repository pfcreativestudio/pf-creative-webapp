import json
import jwt
import base64
import urllib.request
import urllib.error
import logging
import os
import psycopg2
import psycopg2.pool

# --- START: Added self-contained functions and constants ---
# This logic is copied from your utils.py to make this file independent.

logging.basicConfig(level=logging.INFO)

db_pool = None

# Vercel Environment variables will be automatically loaded
BILLPLZ_API_KEY = os.environ.get('BILLPLZ_API_KEY', "f9478c0c-a6fc-444b-9132-69b144a7af47")
BILLPLZ_COLLECTION_ID = os.environ.get('BILLPLZ_COLLECTION_ID', "ek0rvdud")
BASE_URL = os.environ.get('BASE_URL', "https://pfcreativestudio.vercel.app")
JWT_SECRET = os.environ.get('JWT_SECRET', 'd528502f7a76853766814ffd7bdad0d3577ef4c1273995402a2239493a5d19cd')

def init_connection_pool():
    global db_pool
    if db_pool:
        return
    try:
        db_user = os.environ.get('DB_USER')
        db_password = os.environ.get('DB_PASSWORD')
        db_name = os.environ.get('DB_NAME')
        instance_connection_name = os.environ.get('INSTANCE_CONNECTION_NAME')
        db_socket_dir = '/cloudsql'
        conn_string = f'user={db_user} password={db_password} dbname={db_name} host={db_socket_dir}/{instance_connection_name}'
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, dsn=conn_string)
        logging.info("Database connection pool initialized successfully for create-bill.")
    except Exception as e:
        logging.error(f"Error initializing connection pool for create-bill: {e}")
        db_pool = None

init_connection_pool()

def get_db_connection():
    if not db_pool:
        raise Exception("Database connection pool is not available.")
    return db_pool.getconn()

def release_db_connection(conn):
    if db_pool:
        db_pool.putconn(conn)

def cors_preflight(request):
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Password',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    return None

def get_cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }

# --- END: Added self-contained functions and constants ---


def handler(request):
    """
    Handles the creation of a payment bill with Billplz.
    """
    preflight_response = cors_preflight(request)
    if preflight_response:
        return preflight_response

    headers = get_cors_headers()
    conn = None
    cursor = None # Define cursor here
    try:
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
        
        req_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {base64.b64encode(f"{BILLPLZ_API_KEY}:".encode()).decode()}'
        }
        
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
            return (json.dumps({'error': 'Failed to create payment link from provider'}), 502, headers)

    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        logging.error(f"Billplz HTTP Error: {e.code} - {error_body}")
        return (json.dumps({'error': 'Payment service provider error'}), 502, headers)
    except urllib.error.URLError as e:
        logging.error(f"Billplz connection error: {str(e)}")
        return (json.dumps({'error': 'Cannot connect to payment service'}), 503, headers)
    except Exception as e:
        logging.error(f"Create Bill Error: {str(e)}", exc_info=True)
        return (json.dumps({'error': 'Internal server error'}), 500, headers)
    finally:
        if conn:
            if cursor:
                try:
                    cursor.close()
                except Exception as e:
                    logging.error(f"Error closing cursor: {e}")
            release_db_connection(conn)
