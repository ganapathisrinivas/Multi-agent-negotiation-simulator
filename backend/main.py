from fastapi import FastAPI

from backend.config.settings import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)


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