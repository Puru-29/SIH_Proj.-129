from connectors.education_connector import EducationConnector
from connectors.employment_connector import EmploymentConnector
from connectors.municipal_connector import MunicipalConnector
from connectors.revenue_connector import RevenueConnector
from connectors.transport_connector import TransportConnector
from connectors.welfare_connector import WelfareConnector


def test_connectors_return_their_native_source_system_schemas():
    expected_fields = {
        RevenueConnector: {
            "full_name",
            "dob",
            "income_certificate_no",
            "annual_income",
        },
        EducationConnector: {
            "student_name",
            "date_of_birth",
            "student_id",
            "institution",
        },
        WelfareConnector: {
            "applicant_name",
            "eligibility_id",
            "scheme_name",
            "eligibility_status",
        },
        TransportConnector: {
            "applicantName",
            "birthDate",
            "licenseNumber",
        },
        MunicipalConnector: {
            "owner_name",
            "property_id",
            "assessment_status",
        },
        EmploymentConnector: {
            "applicant_name",
            "date_of_birth",
            "employment_id",
            "employer_name",
            "employment_status",
            "occupation",
        },
    }

    for connector_type, fields in expected_fields.items():
        connector = connector_type()
        record = connector.get_record(17, "Sample record", "Eligibility verification")

        assert fields <= record.keys()
        assert "records" not in record
        assert "citizenId" not in record
        assert "dateOfBirth" not in record
        assert connector.health_check() == {
            "status": "healthy",
            "mode": "local",
            "system": connector.system_name,
        }
        assert connector.verify_record(17, record)
        assert not connector.verify_record(18, record)


def test_connectors_return_separate_records_in_their_native_formats():
    revenue_record = RevenueConnector().get_record(17, "Income Certificate")
    education_record = EducationConnector().get_record(17, "Education Record")
    transport_record = TransportConnector().get_record(17, "Driving Licence")

    assert "income_certificate_no" in revenue_record
    assert "student_id" in education_record
    assert "licenseNumber" in transport_record
    assert "licenseNumber" not in revenue_record
    assert "income_certificate_no" not in education_record
