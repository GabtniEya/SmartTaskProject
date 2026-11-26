
import os
import time
import logging
from typing import Optional

import psycopg2
import requests

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import RealDictCursor
from psycopg2 import Error as PostgreSQLError
from pydantic import BaseModel, Field


# ==========================================
# 1. CONFIGURATION
# ==========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SmartTask AI API",
    description="API de gestion intelligente des tâches",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# PostgreSQL configuration
DB = {
    "host": os.getenv("DB_HOST", "db"),
    "dbname": os.getenv("DB_NAME", "smarttask"),
    "user": os.getenv("DB_USER", "smarttask"),
    "password": os.getenv("DB_PASSWORD", "smarttask")
}

# AI Service configuration
AI_URL = os.getenv("AI_URL", "http://ai-service:8001")


# ==========================================
# 2. PYDANTIC MODELS
# ==========================================

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    priority: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


# ==========================================
# 3. POSTGRESQL CONNECTION
# ==========================================

def connect():
    """
    Establish a PostgreSQL connection.
    Retry up to 20 times if the database is unavailable.
    """

    for attempt in range(20):
        try:
            return psycopg2.connect(
                **DB,
                cursor_factory=RealDictCursor,
                connect_timeout=5
            )

        except psycopg2.OperationalError as e:
            logger.warning(
                "Database connection attempt %s/20 failed: %s",
                attempt + 1,
                e
            )
            time.sleep(2)

    raise HTTPException(
        status_code=503,
        detail="Base de données PostgreSQL indisponible"
    )


# ==========================================
# 4. DATABASE QUERY FUNCTION
# ==========================================

def query(sql, params=(), fetch="all"):
    """
    Execute an SQL query.

    fetch='all'  : return all rows
    fetch='one'  : return one row
    fetch=None   : execute without returning rows
    """

    connection = connect()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)

                if fetch == "all":
                    return cursor.fetchall()

                elif fetch == "one":
                    return cursor.fetchone()

                return None

    except PostgreSQLError as e:
        logger.exception("Database query failed")

        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'exécution de la requête SQL"
        )

    finally:
        connection.close()


# ==========================================
# 5. AI SERVICE INTEGRATION
# ==========================================

def ai_priority(title: str, description: str):
    """
    Send task information to Eya's AI service
    and retrieve the predicted priority.
    """

    try:
        response = requests.post(
            f"{AI_URL}/classify",
            json={
                "title": title,
                "description": description
            },
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        return data.get("priority", "medium")

    except requests.RequestException as e:
        logger.warning("AI service unavailable: %s", e)
        return "medium"

    except (ValueError, AttributeError):
        logger.warning("Invalid AI service response")
        return "medium"


# ==========================================
# 6. HOME
# ==========================================

@app.get("/")
def home():
    return {
        "message": "Bienvenue dans SmartTask AI !",
        "status": "success"
    }


# ==========================================
# 7. HEALTH CHECK
# ==========================================

@app.get("/health")
def health():
    """
    Check backend and PostgreSQL availability.
    """

    try:
        query("SELECT 1", fetch="one")

        return {
            "status": "healthy",
            "backend": "running",
            "database": "connected"
        }

    except HTTPException:
        raise


# ==========================================
# 8. GET ALL TASKS
# ==========================================

@app.get("/tasks")
def list_tasks():
    """
    Retrieve all tasks from PostgreSQL.
    """

    return query(
        """
        SELECT *
        FROM tasks
        ORDER BY id DESC
        """
    )


# ==========================================
# 9. CREATE TASK
# ==========================================

@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    """
    Create a new task.

    If priority is not provided,
    ask the AI service to predict it.
    """

    priority = task.priority

    if not priority:
        priority = ai_priority(
            task.title,
            task.description
        )

    return query(
        """
        INSERT INTO tasks (title, description, priority)
        VALUES (%s, %s, %s)
        RETURNING *
        """,
        (
            task.title,
            task.description,
            priority
        ),
        fetch="one"
    )


# ==========================================
# 10. UPDATE TASK
# ==========================================

@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    """
    Update an existing task.
    """

    row = query(
        """
        UPDATE tasks
        SET
            title = COALESCE(%s, title),
            description = COALESCE(%s, description),
            priority = COALESCE(%s, priority),
            status = COALESCE(%s, status)
        WHERE id = %s
        RETURNING *
        """,
        (
            task.title,
            task.description,
            task.priority,
            task.status,
            task_id
        ),
        fetch="one"
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Tâche introuvable"
        )

    return row


# ==========================================
# 11. DELETE TASK
# ==========================================

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    """
    Delete an existing task.
    """

    row = query(
        """
        DELETE FROM tasks
        WHERE id = %s
        RETURNING id
        """,
        (task_id,),
        fetch="one"
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Tâche introuvable"
        )

    return {
        "message": "Tâche supprimée avec succès",
        "id": task_id
    }


# ==========================================
# 12. AI SUGGESTIONS
# ==========================================

@app.get("/suggestions")
def suggestions():
    """
    Retrieve tasks from PostgreSQL
    and send them to the AI service
    to generate suggestions.
    """

    tasks = query(
        """
        SELECT title, priority, status
        FROM tasks
        """
    )

    try:
        response = requests.post(
            f"{AI_URL}/suggest",
            json={
                "tasks": tasks
            },
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:
        logger.error("AI suggestions error: %s", e)

        raise HTTPException(
            status_code=503,
            detail="Service IA indisponible"
        )
