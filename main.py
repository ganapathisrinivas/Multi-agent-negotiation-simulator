import os
import sys

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from dataset_manager import load_dataset
from routers.negotiation_router import router, set_dataset


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


app = FastAPI(
    title="Real Estate Negotiation Platform",
    description=(
        "AI-Driven Multi-Agent Negotiation Training & "
        "Simulation Platform with Interactive Human Practice Mode"
    ),
    version="1.3.0",
)


try:
    dataset = load_dataset("dataset_real.csv")
    if dataset is None:
        dataset = []
    print(f"Dataset loaded successfully: {len(dataset)} properties")
except Exception as error:
    print("Dataset loading error:", error)
    dataset = []

set_dataset(dataset)


@app.get("/")
def home():
    return {
        "message": "Real Estate Negotiation Platform API is running",
        "docs": "/docs",
        "practice_ui": "/practice",
        "features": [
            "AI vs AI Multi-Agent Simulation",
            "Human vs AI Interactive Practice Mode",
            "Deadlock Detection",
        ],
    }


@app.get("/practice", response_class=HTMLResponse, include_in_schema=True)
@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def practice_ui():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "practice.html")
    if not os.path.exists(template_path):
        return HTMLResponse("<h1>Practice UI template not found</h1>", status_code=404)
    with open(template_path, "r", encoding="utf-8") as template_file:
        return HTMLResponse(template_file.read())


@app.get("/health")
def health():
    if hasattr(dataset, "empty"):
        loaded = not dataset.empty
        count = len(dataset)
    else:
        loaded = bool(dataset)
        count = len(dataset)
    return {"status": "running", "dataset_loaded": loaded, "property_count": count}


app.include_router(router)
