import json
import jwt
import datetime
import os
import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import urllib.request # This is still used by the /create-bill endpoint
import base64 # This is still used by the /create-bill endpoint

# --- NEW: Import our new utils toolbox ---
import utils

# The logging is configured in utils.py, but it's safe to have it here too.
logging.basicConfig(level=logging.INFO)


# --- REMOVED ---
# The following functions and variables have been removed from this file
# because they now exist in our central `utils.py` toolbox.
# - db_pool = None
# - MAX_HISTORY_LENGTH_FOR_FULL_CONTEXT
# - NUM_RECENT_MESSAGES_TO_KEEP
# - init_connection_pool()
# - get_db_connection()
# - release_db_connection()
# - summarize_chat_history()


def handler(request):
    # This preflight check could also be moved to utils, but we leave it for now.
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Password',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # This header function could also be moved to utils.
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    # --- REMOVED: Hardcoded MASTER_PROMPT and other constants ---
    # These are now either fetched from the database by utils.py or defined within utils.py
    JWT_SECRET = os.environ.get('JWT_SECRET', 'd528502f7a76853766814ffd7bdad0d3577ef4c1273995402a2239493a5d19cd')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'PFcreative@2025')
    
    path = request.path
    method = request.method

    conn = None
    try:
        # --- CHANGED: Now using the get_db_connection function from utils ---
        conn = utils.get_db_connection()
        cursor = conn.cursor()

        # All endpoints like /register, /login, /admin/*, /create-bill etc. remain unchanged for now
        # We are only focusing on refactoring the /generate-script endpoint's prompt logic

        # --- REGISTER ENDPOINT ---
        if path == '/register' and method == 'POST':
            # This part of the code remains unchanged.
            request_json = request.get_json(silent=True) or {}
            username = request_json.get('username')
            password = request_json.get('password')
            if not username or not password:
                return (json.dumps({'error': 'Username and password are required'}), 400, headers)
            cursor.execute('SELECT username FROM users WHERE username = %s', (username,))
            if cursor.fetchone():
                return (json.dumps({'error': 'Username already exists.'}), 409, headers)
            cursor.execute('INSERT INTO users (username, password, created_at) VALUES (%s, %s, %s)',
                         (username, password, datetime.datetime.now(datetime.timezone.utc)))
            conn.commit()
            logging.info(f"New user registered: {username}")
            return (json.dumps({'success': True, 'message': 'User registered successfully.'}), 201, headers)

        # --- GET USER STATUS ENDPOINT ---
        elif path == '/get-user-status' and method == 'GET':
            # This part of the code remains unchanged.
            try:
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    return (json.dumps({'error': 'Authorization token is missing or invalid.'}), 401, headers)
                token = auth_header.split(' ')[1]
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                username = payload.get('username')
                if not username:
                    return (json.dumps({'error': 'Invalid token payload.'}), 401, headers)
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
        
        # Other endpoints like /create-bill, /webhook-billplz, /login, /admin/* would go here
        # They are omitted for brevity as they are not the focus of our refactoring.
        # Let's jump to the /generate-script endpoint logic.

        # --- GENERATE SCRIPT ENDPOINT ---
        elif path == '/generate-script' and method == 'POST':
            try:
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    return (json.dumps({'error': 'Authorization token required'}), 401, headers)
                
                token = auth_header.split(' ')[1]
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                username = payload.get('username')
                if not username:
                    return (json.dumps({'error': 'Invalid token: username missing'}), 401, headers)

                cursor.execute('SELECT subscription_expires_at, active_token FROM users WHERE username = %s', (username,))
                user_record = cursor.fetchone()

                if not user_record:
                    return (json.dumps({'error': 'User not found'}), 404, headers)

                subscription_expires_at = user_record[0]
                active_token_from_db = user_record[1]

                if active_token_from_db != token:
                    return (json.dumps({'error': 'This account has been logged in on another device. Please log in again.'}), 409, headers)

                now = datetime.datetime.now(datetime.timezone.utc)
                if not subscription_expires_at or subscription_expires_at < now:
                    return (json.dumps({'error': 'Your subscription has expired. Please renew to continue.'}), 403, headers)

            except jwt.ExpiredSignatureError:
                return (json.dumps({'error': 'Token has expired, please log in again'}), 401, headers)
            except jwt.InvalidTokenError:
                return (json.dumps({'error': 'Invalid token, please log in again'}), 401, headers)
            except Exception as e:
                logging.error(f"Auth/Subscription check error for user {username}: {e}")
                return (json.dumps({'error': f'An internal server error occurred during authentication: {e}'}), 500, headers)

            request_json = request.get_json(silent=True) or {}
            user_project_info = request_json.get('project_info')
            chat_history_from_frontend = request_json.get('history', [])
            
            file_data = request_json.get('file_data')
            file_mime_type = request_json.get('file_mime_type')

            if not user_project_info and not file_data:
                if not chat_history_from_frontend:
                    pass
                else:
                    return (json.dumps({'error': 'Project information or file is required.'}), 400, headers)

            try:
                # --- MAJOR CHANGE HERE ---
                # 1. We fetch the master prompt dynamically from our utils function
                master_prompt = utils.get_active_master_prompt(conn)
                
                # 2. We configure GenAI (API key is now fetched inside utils.py)
                genai.configure(api_key=utils.GEMINI_API_KEY)
                
                # 3. We create the model with the dynamic system instruction
                model = genai.GenerativeModel(
                    'gemini-1.5-pro',
                    system_instruction=master_prompt
                )

                full_conversation_for_gemini = []
                
                # Using the constants from utils.py now would be ideal, but for now we hardcode them to avoid breaking things.
                # In a future step we can clean this up.
                MAX_HISTORY_LENGTH_FOR_FULL_CONTEXT = 12
                NUM_RECENT_MESSAGES_TO_KEEP = 8

                if len(chat_history_from_frontend) > MAX_HISTORY_LENGTH_FOR_FULL_CONTEXT:
                    history_to_summarize = chat_history_from_frontend[:-NUM_RECENT_MESSAGES_TO_KEEP]
                    recent_history = chat_history_from_frontend[-NUM_RECENT_MESSAGES_TO_KEEP:]
                    
                    # --- CHANGED: Call the summarize function from utils ---
                    # Note the arguments might be different. The utils one doesn't need the API key passed.
                    summary = utils.summarize_chat_history(history_to_summarize)
                    
                    full_conversation_for_gemini.append({
                        'role': 'user', 
                        'parts': [{'text': "CONTEXT SUMMARY OF EARLIER PARTS OF THE CONVERSATION:\n" + summary}]
                    })
                    full_conversation_for_gemini.extend(recent_history)
                    logging.info(f"Chat history summarized. Kept last {NUM_RECENT_MESSAGES_TO_KEEP} messages.")
                else:
                    full_conversation_for_gemini.extend(chat_history_from_frontend)

                current_user_input_parts = []
                if user_project_info:
                    current_user_input_parts.append({'text': user_project_info})
                if file_data and file_mime_type:
                    current_user_input_parts.append({
                        'inlineData': {
                            'mimeType': file_mime_type,
                            'data': file_data
                        }
                    })
                
                if current_user_input_parts:
                    full_conversation_for_gemini.append({'role': 'user', 'parts': current_user_input_parts})
                
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]

                response = model.generate_content(
                    full_conversation_for_gemini,
                    safety_settings=safety_settings
                )
                
                script_content = ""
                if hasattr(response, 'text'):
                    script_content = response.text
                elif response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text'):
                            script_content += part.text
                
                if script_content:
                    return (json.dumps({'success': True, 'script': script_content}), 200, headers)
                else:
                    logging.error(f"Gemini API returned no usable content or an error: {response}")
                    return (json.dumps({'error': 'Failed to generate script. No valid content returned from AI.'}), 500, headers)

            except Exception as e:
                logging.error(f"Error calling Gemini API: {e}", exc_info=True)
                return (json.dumps({'error': f'An AI service error occurred: {str(e)}'}), 500, headers)

        else:
            return (json.dumps({'error': 'Endpoint not found'}), 404, headers)

    except Exception as e:
        logging.error(f"An unexpected error occurred in handler: {e}", exc_info=True)
        return (json.dumps({'error': f'An internal server error occurred: {str(e)}'}), 500, headers)
    
    finally:
        if conn:
            try:
                # --- CHANGED: Now using the release_db_connection function from utils ---
                utils.release_db_connection(conn)
            except Exception as e:
                logging.error(f"Error closing cursor or connection: {e}")
