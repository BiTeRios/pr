@echo off
cd /d "%~dp0.."

echo Removing old containers...
docker rm -f todo_frontend todo_backend todo_db todo_mail >nul 2>nul

echo Creating Docker network...
docker network create todo_net >nul 2>nul

echo Starting PostgreSQL...
docker run -d --name todo_db --network todo_net ^
 -e POSTGRES_USER=todo_user ^
 -e POSTGRES_PASSWORD=todo_password ^
 -e POSTGRES_DB=todo_db ^
 -v "%cd%\db\init.sql:/docker-entrypoint-initdb.d/init.sql" ^
 -p 5432:5432 postgres:16

echo Starting GreenMail SMTP/IMAP/POP3...
docker run -d --name todo_mail --network todo_net ^
 -e GREENMAIL_OPTS="-Dgreenmail.setup.test.all -Dgreenmail.hostname=0.0.0.0 -Dgreenmail.users=user:password@localhost" ^
 -p 3025:3025 -p 3143:3143 -p 3110:3110 greenmail/standalone:2.1.3

echo Building backend...
docker build -t todo_backend ./backend

echo Starting backend...
docker run -d --name todo_backend --network todo_net ^
 -e DATABASE_URL=postgresql+psycopg2://todo_user:todo_password@todo_db:5432/todo_db ^
 -e SMTP_HOST=todo_mail -e SMTP_PORT=3025 ^
 -e IMAP_HOST=todo_mail -e IMAP_PORT=3143 ^
 -e POP3_HOST=todo_mail -e POP3_PORT=3110 ^
 -e MAIL_FROM=user@localhost ^
 -e MAIL_PASSWORD=password ^
 -p 8000:8000 todo_backend

echo Building frontend...
docker build -t todo_frontend ./frontend

echo Starting frontend...
docker run -d --name todo_frontend --network todo_net ^
 -e VITE_API_URL=http://localhost:8000 ^
 -p 5173:5173 todo_frontend

echo.
docker ps

echo.
echo Open frontend: http://localhost:5173
echo Open backend:  http://localhost:8000/docs
echo Mail account:  user@localhost / password
echo.
pause
