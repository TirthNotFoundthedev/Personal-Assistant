@echo off
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting Personal Assistant...
python "D:\000Programming Life\Projects\Telegram\Personal Assistant\main.py"

echo Personal Assistant has finished or encountered an error.
PAUSE
