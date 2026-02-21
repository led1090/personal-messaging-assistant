@echo off
cd /d "C:\Users\rahmh\Documents\AIAgentsPlatform\personal-messaging-assistant"
echo [%date% %time%] Starting personal-messaging-assistant bot... >> bot_startup.log
python app.py >> bot_startup.log 2>&1
echo [%date% %time%] Bot exited with code %ERRORLEVEL% >> bot_startup.log
