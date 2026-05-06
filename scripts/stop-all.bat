@echo off
docker rm -f todo_frontend todo_backend todo_db todo_mail >nul 2>nul
docker network rm todo_net >nul 2>nul
echo Containers and network removed.
pause
