from app.schemas.user import UserCreate, UserRead
from app.schemas.department import DepartmentCreate, DepartmentRead
from app.schemas.platform import PlatformCreate, PlatformRead
from app.schemas.service import ServiceCreate, ServiceRead
from app.schemas.application import ApplicationCreate, ApplicationRead, ApplicationUpdate
from app.schemas.consent import ConsentCreate, ConsentRead
from app.schemas.document import DocumentCreate, DocumentRead
from app.schemas.audit import AuditLogRead
from app.schemas.ml import (
    OCRRequest,
    OCRResponse,
    LayoutLMRequest,
    LayoutLMResponse,
    NERRequest,
    NERResponse,
    DistilBertClassifyRequest,
    DistilBertClassifyResponse,
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    FullVerificationRequest,
    FullVerificationResponse,
    MLSystemStatusResponse,
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
)
from app.schemas.common_data_model import (
    Application as CommonApplication,
    Citizen as CommonCitizen,
    Document as CommonDocument,
    GovernmentRecord as CommonGovernmentRecord,
    VerifiedRecord,
    VerificationStatus,
)

__all__ = [
    "UserCreate",
    "UserRead",
    "DepartmentCreate",
    "DepartmentRead",
    "PlatformCreate",
    "PlatformRead",
    "ServiceCreate",
    "ServiceRead",
    "ApplicationCreate",
    "ApplicationRead",
    "ApplicationUpdate",
    "ConsentCreate",
    "ConsentRead",
    "DocumentCreate",
    "DocumentRead",
    "AuditLogRead",
    "OCRRequest",
    "OCRResponse",
    "LayoutLMRequest",
    "LayoutLMResponse",
    "NERRequest",
    "NERResponse",
    "DistilBertClassifyRequest",
    "DistilBertClassifyResponse",
    "RiskAssessmentRequest",
    "RiskAssessmentResponse",
    "FullVerificationRequest",
    "FullVerificationResponse",
    "MLSystemStatusResponse",
    "AnomalyDetectionRequest",
    "AnomalyDetectionResponse",
    "CommonApplication",
    "CommonCitizen",
    "CommonDocument",
    "CommonGovernmentRecord",
    "VerifiedRecord",
    "VerificationStatus",
]
