@echo off
echo 🔧 Створюємо чисту копію репозиторію...
mkdir clean_repo
cd clean_repo

echo 🔄 Клонуємо репозиторій...
git clone https://github.com/kermach11/my-bot-project.git .
if errorlevel 1 (
    echo ❌ Помилка при клонуванні. Перевір URL або доступ.
    pause
    exit /b
)

echo 🧹 Очищуємо історію комітів від файлу 'env'...
git filter-repo --path env --invert-paths
if errorlevel 1 (
    echo ❌ Помилка при запуску filter-repo. Перевір, чи він встановлений.
    pause
    exit /b
)

echo 🚀 Форсований пуш очищеного репозиторію...
git push --force
if errorlevel 1 (
    echo ❌ Push заблоковано або сталася помилка.
    pause
    exit /b
)

echo ✅ Готово! Репозиторій очищено та оновлено на GitHub.
pause
