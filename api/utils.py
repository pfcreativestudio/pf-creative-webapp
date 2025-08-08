import json
import jwt
import datetime
import os
import logging
import psycopg2
import psycopg2.pool
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import urllib.request
import base64

# Set up logging
logging.basicConfig(level=logging.INFO)

# Global variables and constants
db_pool = None
MAX_HISTORY_LENGTH_FOR_FULL_CONTEXT = 8

# Vercel Environment variables will be automatically loaded
# Billplz configuration - these should be set as Vercel environment variables
BILLPLZ_API_KEY = os.environ.get('BILLPLZ_API_KEY', "f9478c0c-a6fc-444b-9132-69b144a7af47")
BILLPLZ_COLLECTION_ID = os.environ.get('BILLPLZ_COLLECTION_ID', "ek0rvdud")
BILLPLZ_X_SIGNATURE = os.environ.get('BILLPLZ_X_SIGNATURE', "02012c5e2e15131188ea0c34447e4b4aa65511e88ed48180347205ee74d5aff6537f91d64188af7c9c4059e5cc924395ae909d265ef26c010b9e16ed1fa920f2")
BASE_URL = os.environ.get('BASE_URL', "https://pfcreativestudio.vercel.app")
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
JWT_SECRET = os.environ.get('JWT_SECRET', 'd528502f7a76853766814ffd7bdad0d3577ef4c1273995402a2239493a5d19cd')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'PFcreative@2025') 


def init_connection_pool():
    """Initializes the PostgreSQL connection pool."""
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
        logging.info("Database connection pool initialized successfully.")
        
        conn = db_pool.getconn()
        cursor = conn.cursor()

        # Check and add columns if they don't exist
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='subscription_expires_at'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_expires_at TIMESTAMPTZ;")
            logging.info("Column 'subscription_expires_at' added to 'users' table.")

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='active_token'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE users ADD COLUMN active_token TEXT;")
            logging.info("Column 'active_token' added to 'users' table.")

        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                created_at TIMESTAMPTZ,
                subscription_expires_at TIMESTAMPTZ,
                active_token TEXT
            )
        ''')
        
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        logging.info("Users table initialized or updated successfully.")

    except Exception as e:
        logging.error(f"Error initializing connection pool: {e}")
        db_pool = None

init_connection_pool()

def get_db_connection():
    """Retrieves a connection from the pool."""
    if not db_pool:
        raise Exception("Database connection pool is not available.")
    return db_pool.getconn()

def release_db_connection(conn):
    """Releases a connection back to the pool."""
    if db_pool:
        db_pool.putconn(conn)

def cors_preflight(request):
    """Handles CORS preflight requests."""
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
    """Returns standard CORS headers."""
    return {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }

def summarize_chat_history(history_to_summarize_raw):
    """Summarizes chat history for context preservation."""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        summarization_model = genai.GenerativeModel('gemini-1.0-pro') 

        summarize_prompt_parts = [
            "Please summarize the following chat conversation for context preservation. ",
            "The summary should concisely capture key details, decisions, and progress points related to video script generation (e.g., product info, chosen styles, strategy, approved scenes). ",
            "Exclude greetings and minor conversational filler. Aim for brevity (max 200 words). ",
            "Ensure the summary is purely factual and does not introduce new information.",
            "\n\nChat Log:\n"
        ]
        
        for entry in history_to_summarize_raw:
            role = entry.get('role', 'unknown')
            parts = entry.get('parts', [])
            text_content = ""
            for part in parts:
                if isinstance(part, dict) and 'text' in part:
                    text_content += part['text']
                elif isinstance(part, dict) and 'inlineData' in part:
                    text_content += f" (File: {part.get('inlineData', {}).get('mimeType', 'unknown')}) " 
                elif isinstance(part, str): 
                    text_content += part
            summarize_prompt_parts.append(f"{role.capitalize()}: {text_content}\n")

        summarize_prompt_parts.append("\n\nSummary:")

        response = summarization_model.generate_content(summarize_prompt_parts, generation_config={"temperature": 0.2})

        if response.candidates and hasattr(response.candidates[0], 'text'):
            summary = response.candidates[0].text
            logging.info(f"Chat history summarized successfully: {summary[:100]}...")
            return summary
        else:
            logging.warning(f"Summarization model returned no usable content: {response}")
            return "Previous conversation context has been summarized." 
    except Exception as e:
        logging.error(f"Error during chat summarization: {e}", exc_info=True)
        return "Previous conversation context has been summarized (error occurred)."

