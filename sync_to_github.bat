@echo off
cd /d C:\Users\DC\my-bot-project
git add .
git commit -m "🔁 Auto-sync by Ben"
git push origin main
echo.
echo ✅ Готово: зміни надіслані в GitHub!
pause