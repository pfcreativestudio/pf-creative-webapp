import json
import jwt
import logging

from api.utils import get_db_connection, release_db_connection, get_cors_headers, cors_preflight, JWT_SECRET

def handler(request):
    """
    Retrieves the user's subscription status.
    """
    preflight_response = cors_preflight(request)
    if preflight_response:
        return preflight_response

    headers = get_cors_headers()
    conn = None
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return (json.dumps({'error': 'Authorization token is missing or invalid.'}), 401, headers)
            
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        username = payload.get('username')
        
        if not username:
            return (json.dumps({'error': 'Invalid token payload.'}), 401, headers)
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, subscription_expires_at FROM users WHERE username = %s', (username,))
        user_record = cursor.fetchone()
        
        if not user_record:
            return (json.dumps({'error': 'User not found.'}), 404, headers)
            
        user_data = {
            'username': user_record[0],
            'subscription_expires_at': user_record[1].isoformat() if user_record[1] else None
        }
        
        return (json.dumps(user_data), 200, headers)
        
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return (json.dumps({'error': 'Token is expired or invalid.'}), 401, headers)
    except Exception as e:
        logging.error(f"Get user status error: {e}")
        return (json.dumps({'error': 'Internal server error'}), 500, headers)
    finally:
        if conn:
            try:
                cursor.close()
            except Exception as e:
                logging.error(f"Error closing cursor: {e}")
            release_db_connection(conn)
