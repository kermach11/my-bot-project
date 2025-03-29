@echo off
setlocal
set SNAPSHOT_DIR=%~dp0snapshots
set SNAPSHOT_NAME=ben_snapshot_%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set SNAPSHOT_NAME=%SNAPSHOT_NAME: =0%
mkdir "%SNAPSHOT_DIR%" 2>nul
powershell -Command "Compress-Archive -Path '%~dp0*' -CompressionLevel Optimal -DestinationPath '%SNAPSHOT_DIR%\\%SNAPSHOT_NAME%.zip' -Force -Exclude 'env', 'env/*', '*.sqlite', '*.pyc', '__pycache__'"
echo 📦 Snapshot created at: %SNAPSHOT_DIR%\%SNAPSHOT_NAME%.zip
pause