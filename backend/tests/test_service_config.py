from types import SimpleNamespace

from app.services.service_config import get_service_config


def test_caste_certificate_form_includes_gender_and_sub_caste_guidance():
    service = SimpleNamespace(
        code="CASTE-CERT",
        name="Caste Certificate",
        id=1,
        department_id=1,
    )

    config = get_service_config(service)
    fields = {field["id"]: field for field in config["fields"]}

    assert fields["gender"]["type"] == "select"
    assert fields["gender"]["options"] == ["Female", "Male", "Other"]
    assert fields["sub_caste"]["help_text"] == (
        "Enter the specific caste or community name shown on your supporting "
        "documents; this is more specific than the family category above."
    )
