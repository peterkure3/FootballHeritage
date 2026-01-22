"""
FastAPI application for football betting predictions.
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.append(str(Path(__file__).parent.parent))

from config import API_HOST, API_PORT, API_TITLE, API_VERSION, API_DESCRIPTION
from config import API_ALLOWED_ORIGINS
from api.routes import router

# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
)

# Add CORS middleware
# For production, replace ["*"] with specific domains:
# allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=API_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1", tags=["predictions"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Football Betting Predictions API",
        "version": API_VERSION,
        "docs": "/docs",
    }


def main():
    """Run the API server."""
    uvicorn.run(
        "api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
