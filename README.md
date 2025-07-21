# PF Creative AI Studio - Video Script Generator

This project is a web application that generates video scripts using AI. Users can input product information, and the AI will generate a professional video script based on a master prompt.

## Project Structure

- `index.html`: The main user interface.
- `script.js`: Handles frontend logic, form submission, and communication with the backend.
- `multilingual.js`: Manages language switching functionality.
- `backend/main.py`: The Google Cloud Function that processes requests and interacts with the Gemini API.
- `backend/requirements.txt`: Python dependencies for the backend.

## Setup and Deployment

### Backend Deployment (Google Cloud Function)

1. Obtain a Gemini API key from Google AI Studio.
2. Deploy the `backend/main.py` as a Google Cloud Function (Python 3.9+ runtime) with an HTTP trigger.
3. Configure the `API_KEY` and `MASTER_PROMPT_V12_4` variables in `main.py`.
4. Note down the trigger URL of the deployed function.

### Frontend Setup

1. Update `script.js` with the Google Cloud Function trigger URL.
2. Open `index.html` in your browser to use the application locally, or deploy it to a static hosting service like Vercel.

## Usage

1. Enter the brand name, product name, and target audience in the provided fields.
2. Click 'Generate My Script' to get an AI-generated video script.
3. Use the 'Copy Script' button to copy the generated script to your clipboard.


