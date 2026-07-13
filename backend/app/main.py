from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import Base, engine
from .routers import ai, auth, competences, dashboard, entities, knowledge, notifications, search

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CAOS API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
