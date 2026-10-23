"""Internal gateway authentication, shared by the API and isolated tests."""
import os
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse


async def private_gateway(request: Request, call_next):
    """Production denies direct callers even when CORS permits their origin."""
    token = os.getenv("PIPELINE_INTERNAL_TOKEN", "")
    production = os.getenv("APP_ENV", "development").lower() == "production"
    if production or token:
        supplied = request.headers.get("x-internal-token", "")
        if len(token) < 32 or not secrets.compare_digest(supplied, token):
            return JSONResponse(status_code=403, content={"error": {"code": "PRIVATE_SERVICE", "message": "Access denied."}})
    return await call_next(request)
