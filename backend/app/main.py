import os
import time
from typing import Optional

import psycopg2
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

app = FastAPI(
    title="SmartTask AI API",
    description="API de gestion intelligente des tâches",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB = dict(
    host=os.getenv("DB_HOST", "db"),
    dbname=os.getenv("DB_NAME", "smarttask"),
    user=os.getenv("DB_USER", "smarttask"),
    password=os.getenv("DB_PASSWORD", "smarttask"),
)
AI_URL = os.getenv("AI_URL", "http://ai-service:8001")


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


def connect():
    for _ in range(20):
        try:
            return psycopg2.connect(**DB, cursor_factory=RealDictCursor)
        except psycopg2.OperationalError:
            time.sleep(2)
    raise HTTPException(503, "Base de données indisponible")


def query(sql, params=(), fetch="all"):
    c = connect()
    try:
        with c, c.cursor() as cur:
            cur.execute(sql, params)
            if fetch == "all":
                return cur.fetchall()
            if fetch == "one":
                return cur.fetchone()
    finally:
        c.close()


def ai_priority(title, description):
    try:
        r = requests.post(f"{AI_URL}/classify",
                          json={"title": title, "description": description}, timeout=5)
        return r.json()["priority"]
    except Exception:
        return "medium"


@app.get("/")
def home():
    return {"message": "Bienvenue dans SmartTask AI !", "status": "success"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/tasks")
def list_tasks():
    return query("SELECT * FROM tasks ORDER BY status DESC, id DESC")


@app.post("/tasks", status_code=201)
def create_task(t: TaskCreate):
    priority = t.priority or ai_priority(t.title, t.description)
    return query(
        "INSERT INTO tasks (title, description, priority) VALUES (%s,%s,%s) RETURNING *",
        (t.title, t.description, priority), fetch="one")


@app.put("/tasks/{task_id}")
def update_task(task_id: int, t: TaskUpdate):
    row = query(
        """UPDATE tasks SET title=COALESCE(%s,title), description=COALESCE(%s,description),
           priority=COALESCE(%s,priority), status=COALESCE(%s,status)
           WHERE id=%s RETURNING *""",
        (t.title, t.description, t.priority, t.status, task_id), fetch="one")
    if not row:
        raise HTTPException(404, "Tâche introuvable")
    return row


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    query("DELETE FROM tasks WHERE id=%s", (task_id,), fetch=None)
    return {"deleted": task_id}


@app.get("/suggestions")
def suggestions():
    tasks = query("SELECT title, priority, status FROM tasks")
    try:
        r = requests.post(f"{AI_URL}/suggest", json={"tasks": tasks}, timeout=5)
        return r.json()
    except Exception:
        raise HTTPException(503, "Service IA indisponible")
