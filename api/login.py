
import json
import jwt
import datetime
import logging

from api.utils import get_db_connection, release_db_connection, get_cors_headers, cors_preflight, JWT_SECRET

def handler(request):
    """
    Handles user login and generates a JWT token.
    """
    preflight_response = cors_preflight(request)
    if preflight_response:
        return preflight_response

    headers = get_cors_headers()
    conn = None
    try:
        request_json = request.get_json(silent=True) or {}
        username = request_json.get('username')
        password = request_json.get('password')
        if not username or not password: 
            return (json.dumps({'success': False, 'message': 'Username and password required'}), 400, headers)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE username = %s', (username,))
        user_record = cursor.fetchone()
        
        if not user_record or user_record[0] != password: 
            return (json.dumps({'success': False, 'message': 'Invalid username or password'}), 401, headers)
        
        token = jwt.encode({'username': username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, JWT_SECRET, algorithm='HS256')
        
        try:
            cursor.execute('UPDATE users SET active_token = %s WHERE username = %s', (token, username))
            conn.commit()
            logging.info(f"New active token stored for user '{username}'.")
        except Exception as e:
            conn.rollback()
            logging.error(f"Failed to store active token for user '{username}': {e}")
            return (json.dumps({'error': 'Failed to create a valid session.'}), 500, headers)

        return (json.dumps({'success': True, 'token': token}), 200, headers)

    except Exception as e:
        logging.error(f"Login error: {str(e)}", exc_info=True) 
        return (json.dumps({'error': 'Internal server error'}), 500, headers)
    finally:
        if conn:
            try:
                cursor.close()
            except Exception as e:
                logging.error(f"Error closing cursor: {e}")
            release_db_connection(conn)
