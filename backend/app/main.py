from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_v1_router
from app.api.v1.system import router as system_health_router
from app.api.v1.interoperability import unversioned_health_router


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Inter-Governmental Mesh API with integrated AI/ML Stack: EasyOCR, LayoutLMv3, spaCy NER, DistilBERT, and XGBoost/LightGBM.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(system_health_router, prefix="/api")
app.include_router(unversioned_health_router, prefix="/api")


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
