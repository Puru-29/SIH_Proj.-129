from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.departments import router as departments_router
from app.api.v1.platforms import router as platforms_router
from app.api.v1.services import router as services_router
from app.api.v1.applications import router as applications_router
from app.api.v1.consents import router as consents_router
from app.api.v1.audit import router as audit_router
from app.api.v1.stats import router as stats_router
from app.api.v1.documents import router as documents_router
from app.api.v1.ml import router as ml_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(departments_router)
api_v1_router.include_router(platforms_router)
api_v1_router.include_router(services_router)
api_v1_router.include_router(applications_router)
api_v1_router.include_router(consents_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(stats_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(ml_router)


@api_v1_router.get("/system/health", tags=["System"])
def get_system_health():
    return {"status": "ok", "app": "SIH26129 Inter-Governmental Mesh API"}


@api_v1_router.get("/info", tags=["System"])
def get_v1_info():
    return {
        "version": "1.0.0",
        "system": "SIH26129 Inter-Governmental Mesh API",
        "modules": [
            "EasyOCR",
            "LayoutLMv3",
            "spaCy NER",
            "DistilBERT",
            "XGBoost",
            "LightGBM",
            "One-Class SVM & LOF",
            "Document Verification Pipeline",
        ],
    }

