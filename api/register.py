import json
import datetime
import logging

from api.utils import get_db_connection, release_db_connection, get_cors_headers, cors_preflight

def handler(request):
    """
    Handles user registration.
    """
    preflight_response = cors_preflight(request)
    if preflight_response:
        return preflight_response

    headers = get_cors_headers()
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        request_json = request.get_json(silent=True) or {}
        username = request_json.get('username')
        password = request_json.get('password')
        
        if not username or not password:
            return (json.dumps({'error': 'Username and password are required'}), 400, headers)
        
        cursor.execute('SELECT username FROM users WHERE username = %s', (username,))
        if cursor.fetchone():
            return (json.dumps({'error': 'Username already exists.'}), 409, headers)
            
        cursor.execute('INSERT INTO users (username, password, created_at) VALUES (%s, %s, %s)',
                     (username, password, datetime.datetime.utcnow()))
        conn.commit()
        logging.info(f"New user registered: {username}")
        
        return (json.dumps({'success': True, 'message': 'User registered successfully.'}), 201, headers)

    except Exception as e:
        logging.error(f"Registration error: {str(e)}", exc_info=True) 
        return (json.dumps({'error': 'Internal server error'}), 500, headers)
    finally:
        if conn:
            try:
                cursor.close()
            except Exception as e:
                logging.error(f"Error closing cursor: {e}")
            release_db_connection(conn)
