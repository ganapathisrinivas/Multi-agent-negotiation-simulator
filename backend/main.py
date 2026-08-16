from fastapi import FastAPI

from backend.api.tasks import router as tasks_router
from backend.api.scenarios import router as scenarios_router
from backend.api.agents import router as agents_router
from backend.api.negotiations import router as negotiations_router
from backend.config.settings import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)


app.include_router(tasks_router)
app.include_router(scenarios_router)
app.include_router(agents_router)
app.include_router(negotiations_router)


@app.get("/")
def home():
    return {
        "message": "Multi-Agent System API is running!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }