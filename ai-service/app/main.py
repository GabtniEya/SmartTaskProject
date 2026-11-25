from typing import List
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="SmartTask AI - Service IA", version="1.0.0")

HIGH = ["urgent", "asap", "demain", "aujourd", "deadline", "examen", "rendu",
        "critique", "bug", "important", "livraison", "démo", "demo"]
LOW = ["idée", "idee", "plus tard", "optionnel", "ranger", "lire", "un jour"]
ORDER = {"high": 0, "medium": 1, "low": 2}


class TaskIn(BaseModel):
    title: str
    description: str = ""


class TaskItem(BaseModel):
    title: str
    priority: str = "medium"
    status: str = "todo"


class SuggestIn(BaseModel):
    tasks: List[TaskItem]


@app.get("/")
def home():
    return {"service": "ai-service", "status": "success"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/classify")
def classify(t: TaskIn):
    text = f"{t.title} {t.description}".lower()
    score = sum(2 for w in HIGH if w in text) - sum(2 for w in LOW if w in text)
    priority = "high" if score >= 2 else "low" if score <= -2 else "medium"
    return {"priority": priority, "score": score}


@app.post("/suggest")
def suggest(data: SuggestIn):
    todo = [t for t in data.tasks if t.status != "done"]
    if not todo:
        return {"suggestions": ["🎉 Tout est terminé, bravo ! Prenez une pause."]}
    todo.sort(key=lambda t: ORDER.get(t.priority, 1))
    high = [t for t in todo if t.priority == "high"]
    tips = [f"🎯 Commencez par : « {todo[0].title} »."]
    if len(high) > 2:
        tips.append(f"⚠️ {len(high)} tâches urgentes : répartissez-les dans l'équipe.")
    if len(todo) > 5:
        tips.append("🧩 Beaucoup de tâches ouvertes : regroupez-les en 2-3 blocs de travail.")
    tips.append("⏱️ Conseil : travaillez par sessions de 25 min (Pomodoro).")
    return {"suggestions": tips}
