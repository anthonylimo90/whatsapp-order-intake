"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from src.db import init_db
from src.api import router, websocket_endpoint

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Initialize database
    await init_db()

    # Check if we should seed data
    if os.getenv("SEED_DATABASE", "false").lower() == "true":
        from src.db.seed import seed_database
        from src.db import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            await seed_database(session)

    yield

    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="WhatsApp Order Intake Demo",
    description="AI-powered order extraction from WhatsApp messages",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/api")

# WebSocket endpoint
app.websocket("/ws/chat")(websocket_endpoint)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "whatsapp-order-intake"}


# Serve frontend static files if they exist
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        """Serve the frontend application."""
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        """Serve frontend for all other routes (SPA routing)."""
        # Check if it's an API route
        if path.startswith("api/") or path.startswith("ws/"):
            return {"error": "Not found"}

        # Check if file exists in dist
        file_path = os.path.join(frontend_dist, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Return index.html for SPA routing
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
