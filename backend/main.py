from fastapi import FastAPI

app = FastAPI()


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