# Personal Assistant Telegram Bot

This project implements a Telegram bot that acts as a personal assistant, focusing on Toggl time tracking, with advanced features like voice message transcription and natural language understanding (NLU) powered by Google Gemini. The bot is designed to run as a webhook-based Flask application, compatible with serverless platforms like Google Cloud Run.

## Features

-   **Telegram Bot Integration:** Responds to commands and messages via webhooks.
-   **Toggl Time Tracking:**
    -   Fetch and display Toggl clients and projects using inline keyboard buttons.
    -   Start new time entries.
    -   Add past time entries with specified durations.
    -   Stop active time entries.
-   **Voice Message Transcription:** Uses Google Gemini to convert spoken messages into text.
-   **Natural Language Understanding (NLU):** Leverages Google Gemini to understand user intent from text (both typed and transcribed voice messages) for Toggl actions.
-   **Google Cloud Run Compatibility:** Structured for easy deployment to Google Cloud Run.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd Personal Assistant Telegram Bot
```

### 2. Create and Activate a Virtual Environment

It's recommended to use a virtual environment to manage project dependencies.

```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a file named `.env` in the root directory of the project and populate it with your API keys and webhook URL:

```dotenv
# Telegram Bot Token - Get this from BotFather (https://t.me/BotFather)
TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"

# Toggl API Key - Get this from your Toggl Profile settings (https://track.toggl.com/profile)
TOGGL_API_KEY="YOUR_TOGGL_API_KEY"

# Gemini API Key - Get this from Google AI Studio (https://aistudio.google.com/app/apikey)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Webhook URL for Telegram. This should be the public URL where your Flask app is accessible.
# For local testing with ngrok: https://<your-ngrok-id>.ngrok.io/webhook
WEBHOOK_URL="YOUR_WEBHOOK_URL"

# Optional: Set FLASK_ENV to "development" for local development without auto-setting webhook
# FLASK_ENV="development"
```

**Important:** Replace the placeholder values with your actual tokens and URL.

### 5. Set the Telegram Webhook

For the bot to receive updates, you need to tell Telegram where to send them.

#### Local Development (using `ngrok` for public URL)

1.  **Install `ngrok`:** Download from [ngrok.com](https://ngrok.com/) and set it up.
2.  **Start `ngrok`:** Run `ngrok http 5000` (assuming your Flask app runs on port 5000). Copy the `https` forwarding URL.
3.  **Update `.env`:** Set `WEBHOOK_URL` in your `.env` file to `YOUR_NGROK_URL/webhook` (e.g., `https://abcdef123456.ngrok.io/webhook`).
4.  **Run Flask app locally:**
    ```bash
    python app.py
    ```
5.  **Manually set webhook:** Open your browser or use `curl` to visit `YOUR_FLASK_APP_URL/set_webhook` (e.g., `http://127.0.0.1:5000/set_webhook` if running locally, or `YOUR_NGROK_URL/set_webhook`).

#### Google Cloud Run Deployment

When deploying to Google Cloud Run, the `WEBHOOK_URL` will be the URL assigned to your Cloud Run service, followed by `/webhook`. The bot will attempt to set the webhook automatically on startup if `FLASK_ENV` is not set to `development`.

### 6. Run the Flask Application

Once configured, you can run the Flask application:

```bash
python app.py
```

For production deployment (e.g., on Cloud Run), `gunicorn` will be used as specified in the `Procfile`:

```bash
gunicorn app:app --workers 1 --bind :$PORT
```

## Usage

After setting up the bot and webhook:

-   Send `/start` to your bot to get a welcome message.
-   Send `/toggl_clients` to view your Toggl clients and select a project using inline buttons.
-   Type messages like:
    -   "Start a timer for coding on a new feature"
    -   "Add 45 minutes for project planning"
    -   "Stop current task"
-   Send **voice messages**. The bot will transcribe them using Gemini and then process their intent for Toggl actions.

## Extensibility

The project is designed with modularity in mind. New features can be added by creating new modules under the `features/` directory and integrating them into `app.py`'s dispatcher.
