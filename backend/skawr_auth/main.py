"""Main FastAPI application for skawr-auth backend."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from skawr_auth.endpoints.auth import router as auth_router
from skawr_auth.endpoints.projects import router as projects_router

# Create FastAPI app
app = FastAPI(
    title="Skawr Auth API",
    description="Shared authentication service for Skawr projects",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("ENVIRONMENT") == "development" else [
        "https://admin.ziyad.one",
        "https://ziyad.one",
        "https://auth-ui.ziyad.one",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "skawr-auth"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Skawr Auth API", "version": "1.0.0"}