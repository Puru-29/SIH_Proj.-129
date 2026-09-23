from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, ensure_application_columns, ensure_user_columns, SessionLocal
from app.services.service_config import ensure_service_catalog
from app import models  # noqa: F401 — register SQLAlchemy models
from app.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_application_columns()
    ensure_user_columns()
    catalog_db = SessionLocal()
    try:
        ensure_service_catalog(catalog_db)
    finally:
        catalog_db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Inter-Governmental Mesh API with integrated AI/ML Stack: EasyOCR, LayoutLMv3, spaCy NER, DistilBERT, and XGBoost/LightGBM.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/", tags=["System"])
def root():
    return {
        "status": "ok",
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/favicon.ico", include_in_schema=False, status_code=204)
def favicon():
    return Response(status_code=204)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "app": settings.app_name}
