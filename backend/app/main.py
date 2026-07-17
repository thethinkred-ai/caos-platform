from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import get_settings
from .db import Base, engine
from .routers import ai, auth, competences, dashboard, entities, google, knowledge, notifications, profile, search, stepik

settings = get_settings()
Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="CAOS API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=()"
    if "https" in settings.frontend_url:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "caos-api"}


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(entities.router, prefix="/api/v1", tags=["entities"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(knowledge.router, prefix="/api/v1", tags=["knowledge"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(ai.router, prefix="/api/v1", tags=["ai"])
app.include_router(notifications.router, prefix="/api/v1", tags=["notifications"])
app.include_router(competences.router, prefix="/api/v1", tags=["competences"])
app.include_router(stepik.router, prefix="/api/v1", tags=["stepik"])
app.include_router(google.router, prefix="/api/v1", tags=["google"])
app.include_router(profile.router, prefix="/api/v1", tags=["profile"])
