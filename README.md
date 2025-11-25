# Personal Assistant Bot 🤖

A modular Telegram bot designed to help manage your daily life, currently featuring intelligent calendar scheduling and voice command support. Built with Python, Google Calendar API, and Gemini AI.

## 🚀 Features

### 📅 Smart Calendar Management
*   **Natural Language Scheduling:** Create events just by typing (e.g., "Meeting with John tomorrow at 2 PM").
*   **AI-Powered Categorization:** Uses a custom AI model to predict and assign the correct calendar (e.g., Work, Personal) based on your event title.
*   **Schedule Overview:** Use `/schedule` to see your upcoming events for the next few days.

### 🎙️ Voice Command Support
*   **Voice-to-Text:** Send voice messages directly to the bot.
*   **Seamless Integration:** Voice notes are transcribed and processed exactly like text commands, allowing you to schedule events hands-free.

## 🛠️ How It Works

1.  **Input:** You send a text or voice message on Telegram.
2.  **Processing:**
    *   **Voice:** Transcribed into text using Gemini 1.5 Flash.
    *   **Text:** Analyzed by Gemini to extract event details (Title, Date, Time).
3.  **Intelligence:** A custom-trained AI (TF-IDF + LinearSVC) predicts which calendar the event belongs to.
4.  **Action:** The bot asks for confirmation via interactive buttons before creating the event in your Google Calendar.

## 📦 Tech Stack
*   **Core:** Python, `python-telegram-bot`
*   **AI:** Google Gemini 1.5 Flash, Scikit-learn (for custom categorization)
*   **APIs:** Google Calendar API
*   **Database:** (Planned for future task management)