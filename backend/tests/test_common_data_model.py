from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import DataMapping, Department, DigitalPlatform
from app.schemas.common_data_model import (
    Application,
    Citizen,
    Document,
    GovernmentRecord,
    VerificationStatus,
    VerifiedRecord,
)
from app.services.interoperability.mapping_service import MappingService
from app.services.interoperability.normalization_service import NormalizationService


def test_mapping_configuration_is_persisted_and_maps_source_fields_to_cdm():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        department = Department(name="Revenue & Land Records", code="REV")
        destination_department = Department(name="Social Welfare", code="WEL")
        db.add_all([department, destination_department])
        db.flush()
        source = DigitalPlatform(
            name="Local Revenue Records Adapter",
            slug="local-revenue-test",
            department_id=department.id,
        )
        target = DigitalPlatform(
            name="Local Welfare Adapter",
            slug="local-welfare-test",
            department_id=destination_department.id,
        )
        db.add_all([source, target])
        db.flush()

        mapped = MappingService().map_to_common_model(
            db,
            raw={
                "full_name": "Example Citizen",
                "dob": "10/05/2003",
                "income_certificate_no": "inc-17",
                "annual_income": 500000,
            },
            citizen_id=17,
            source_system=source,
            target_system_id=target.id,
            requested_type="Income Certificate",
            connector_key="revenue",
        )
        db.commit()

        mapping = db.query(DataMapping).one()
        assert mapping.status == "active"
        assert {
            (rule.source_field, rule.target_field)
            for rule in mapping.rules
        } >= {
            ("full_name", "name"),
            ("dob", "date_of_birth"),
            ("income_certificate_no", "identifier"),
            ("income_certificate_no", "certificate_number"),
            ("annual_income", "annual_income"),
        }
        assert mapped["name"] == "Example Citizen"
        assert mapped["date_of_birth"] == "10/05/2003"
        assert mapped["identifier"] == "inc-17"
        assert mapped["annual_income"] == 500000
        assert mapped["source_system"] == source.name


def test_normalization_validates_and_canonicalizes_citizen_fields():
    normalized = NormalizationService().normalize(
        {
            "citizen_id": "17",
            "name": "  Example Citizen ",
            "date_of_birth": "10/05/2003",
            "identifier": " inc 17 ",
            "source_system": "Local Revenue Records Adapter",
            "verification_status": "VERIFIED",
            "record_type": "Income Certificate",
            "details": {"annual_income": 500000},
        }
    )

    assert normalized["name"] == "Example Citizen"
    assert normalized["date_of_birth"] == "2003-05-10"
    assert normalized["identifier"] == "INC17"
    assert normalized["verification_status"] == "VERIFIED"
    assert normalized["details"]["annual_income"] == 500000


def test_common_data_model_schemas_cover_portal_domain_records():
    citizen = Citizen(
        name="Example Citizen",
        date_of_birth=date(2003, 5, 10),
        identifier="INC-17",
        source_system="Local Revenue Records Adapter",
        verification_status=VerificationStatus.VERIFIED,
    )
    government_record = GovernmentRecord(
        record_id="INC-17",
        record_type="Income Certificate",
        citizen=citizen,
        source_system="Local Revenue Records Adapter",
        verification_status=VerificationStatus.VERIFIED,
        values={"annual_income": 500000},
    )
    document = Document(
        document_id="DOC-17",
        document_type="Income Certificate",
        issuer="Revenue Department",
        verification_status=VerificationStatus.VERIFIED,
        source_system="Local Revenue Records Adapter",
    )
    application = Application(
        application_id="APP-17",
        service_id=4,
        citizen_identifier=citizen.identifier,
        status="under_review",
    )
    verified_record = VerifiedRecord(
        citizen=citizen,
        government_record=government_record,
        verification_status=VerificationStatus.VERIFIED,
    )

    assert verified_record.citizen.date_of_birth.isoformat() == "2003-05-10"
    assert government_record.values["annual_income"] == 500000
    assert document.document_type == "Income Certificate"
    assert application.citizen_identifier == citizen.identifier
