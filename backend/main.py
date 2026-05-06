import os
import smtplib
import imaplib
import poplib
from email.message import EmailMessage
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, TIMESTAMP, func
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://todo_user:todo_password@todo_db:5432/todo_db")

SMTP_HOST = os.getenv("SMTP_HOST", "todo_mail")
SMTP_PORT = int(os.getenv("SMTP_PORT", "3025"))
IMAP_HOST = os.getenv("IMAP_HOST", "todo_mail")
IMAP_PORT = int(os.getenv("IMAP_PORT", "3143"))
POP3_HOST = os.getenv("POP3_HOST", "todo_mail")
POP3_PORT = int(os.getenv("POP3_PORT", "3110"))

MAIL_FROM = os.getenv("MAIL_FROM", "user@localhost")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "password")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="ToDo REST API with WebSocket")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None


class TaskUpdate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool

    class Config:
        from_attributes = True


class EmailRequest(BaseModel):
    to: str = "user@localhost"


class ConnectionManager:
    """Stores active WebSocket clients and broadcasts events to all of them."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established"
        })

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


def task_to_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "completed": task.completed,
    }


def login_from_email(email: str) -> str:
    """GreenMail creates user as user:password@localhost, so login is local part: user."""
    return email.split("@")[0] if "@" in email else email


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # The server mainly sends events, but receiving text keeps the connection alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks", response_model=List[TaskOut])
def get_tasks():
    db = SessionLocal()
    try:
        return db.query(Task).order_by(Task.id).all()
    finally:
        db.close()


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    finally:
        db.close()


@app.post("/tasks", response_model=TaskOut)
async def create_task(data: TaskCreate):
    db = SessionLocal()
    try:
        task = Task(title=data.title, description=data.description)
        db.add(task)
        db.commit()
        db.refresh(task)

        await manager.broadcast({
            "type": "task_created",
            "message": "Task created",
            "task": task_to_dict(task)
        })
        return task
    finally:
        db.close()


@app.put("/tasks/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, data: TaskUpdate):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task.title = data.title
        task.description = data.description
        task.completed = data.completed
        db.commit()
        db.refresh(task)

        await manager.broadcast({
            "type": "task_updated",
            "message": "Task updated",
            "task": task_to_dict(task)
        })
        return task
    finally:
        db.close()


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        deleted_task = task_to_dict(task)
        db.delete(task)
        db.commit()

        await manager.broadcast({
            "type": "task_deleted",
            "message": "Task deleted",
            "task": deleted_task
        })
        return {"message": "Task deleted"}
    finally:
        db.close()


@app.post("/tasks/{task_id}/email")
def send_task_email(task_id: int, data: EmailRequest):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        msg = EmailMessage()
        msg["From"] = MAIL_FROM
        msg["To"] = data.to
        msg["Subject"] = f"ToDo task #{task.id}: {task.title}"
        msg.set_content(
            f"Задача #{task.id}\n"
            f"Название: {task.title}\n"
            f"Описание: {task.description or '-'}\n"
            f"Статус: {'Выполнена' if task.completed else 'Не выполнена'}"
        )

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.send_message(msg)

        return {"protocol": "SMTP", "message": f"Письмо отправлено на {data.to}"}
    finally:
        db.close()


@app.get("/mail/imap/check")
def check_mail_imap(email: str = Query("user@localhost")):
    try:
        username = login_from_email(email)
        mail = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        mail.login(username, MAIL_PASSWORD)
        mail.select("INBOX")
        status, messages = mail.search(None, "ALL")
        count = len(messages[0].split()) if messages and messages[0] else 0
        mail.logout()
        return {"protocol": "IMAP", "email": email, "login": username, "inbox_messages": count}
    except Exception as e:
        return {"protocol": "IMAP", "email": email, "error": str(e)}


@app.get("/mail/pop3/check")
def check_mail_pop3(email: str = Query("user@localhost")):
    try:
        username = login_from_email(email)
        mailbox = poplib.POP3(POP3_HOST, POP3_PORT, timeout=10)
        mailbox.user(username)
        mailbox.pass_(MAIL_PASSWORD)
        count, size = mailbox.stat()
        mailbox.quit()
        return {"protocol": "POP3", "email": email, "login": username, "messages": count, "size_bytes": size}
    except Exception as e:
        return {"protocol": "POP3", "email": email, "error": str(e)}
