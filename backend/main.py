import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.auth import router as auth_router
from contextlib import asynccontextmanager
from backend.database.mongodb import Database
from backend.api.drive import router as drive_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to Database
    await Database.connect_db()
    yield
    # Shutdown: Clean up connections
    await Database.close_db()

app = FastAPI(
    title="Telegram Drive API",
    description="A secure virtual drive cloud implementation using Telegram storage.",
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(auth_router)
app.include_router(drive_router)

# Enable loose cross-origin access for local frontend development interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """
    Verifies backend server life status.
    """
    return {
        "status": "healthy",
        "service": "telegram-drive-backend",
        "engine": "FastAPI"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)