from __future__ import annotations

from copy import deepcopy
from typing import Any


COMMON: dict[str, dict[str, Any]] = {
    "full_name": {"type": "text", "label": "Full name", "required": True},
    "mobile": {"type": "tel", "label": "Mobile number", "required": True, "pattern": "^[6-9][0-9]{9}$"},
    "aadhaar_last4": {"type": "text", "label": "Aadhaar last 4 digits", "required": True, "pattern": "^[0-9]{4}$", "max_length": 4},
    "email": {"type": "email", "label": "Email", "required": False},
}

IDENTITY_EXTRAS: dict[str, dict[str, Any]] = {
    "date_of_birth": {"type": "date", "label": "Date of birth", "required": True},
    "gender": {"type": "select", "label": "Gender", "required": True, "options": ["Female", "Male", "Other"]},
}

LOCATION_FIELDS: dict[str, dict[str, Any]] = {
    "address": {"type": "text", "label": "Address", "required": True},
    "district": {"type": "text", "label": "District", "required": True},
    "taluka": {"type": "text", "label": "Sub-district", "help_text": "Also called Taluka.", "required": True},
    "village_city": {"type": "text", "label": "Village / City", "required": True},
    "state": {"type": "text", "label": "State", "required": True, "default": "Maharashtra"},
    "pin_code": {"type": "text", "label": "PIN code", "required": True, "pattern": "^[0-9]{6}$", "max_length": 6},
}

BANK = [
    {"id": "account_holder_name", "type": "text", "label": "Account holder name", "required": True},
    {"id": "bank_account", "type": "text", "label": "Bank account number", "required": True, "pattern": "^[0-9]{6,18}$"},
    {"id": "ifsc", "type": "text", "label": "IFSC", "required": True, "pattern": "^[A-Z]{4}0[A-Z0-9]{6}$", "max_length": 11},
    {"id": "aadhaar_seeding_status", "type": "select", "label": "Aadhaar / bank seeding status", "required": False, "options": ["Seeded", "Not seeded", "Not applicable"]},
]

CONSENTS = [
    {"id": "consent_identity", "type": "checkbox", "label": "Consent for identity verification", "required": True},
    {"id": "consent_eligibility", "type": "checkbox", "label": "Consent for eligibility verification", "required": True},
]

SCHOLARSHIP_FIELDS = [
    {"id": "institution", "type": "text", "label": "School / Institution name", "required": True},
    {"id": "institution_location", "type": "text", "label": "School / Institution location", "required": True},
    {"id": "class_standard", "type": "text", "label": "Class / Standard", "required": True},
    {"id": "academic_year", "type": "text", "label": "Academic year", "required": True},
    {"id": "previous_marks", "type": "number", "label": "Previous examination percentage / marks", "required": True},
    {"id": "student_category", "type": "select", "label": "Student category", "required": False, "options": ["General", "SC", "ST", "OBC", "Other"]},
    {"id": "disability_status", "type": "select", "label": "Disability status", "required": False, "options": ["No", "Yes"]},
    {"id": "guardian_name", "type": "text", "label": "Parent / Guardian name", "required": True},
    {"id": "guardian_relationship", "type": "text", "label": "Guardian relationship", "required": True},
    {"id": "family_income", "type": "number", "label": "Family annual income", "required": True},
    {"id": "occupation", "type": "text", "label": "Family occupation", "required": False},
    {"id": "family_members", "type": "number", "label": "Number of family members", "required": False},
    {"id": "account_holder_type", "type": "select", "label": "Account holder type", "required": True, "options": ["Student", "Parent / Guardian"]},
    {"id": "account_holder_relationship", "type": "text", "label": "Account holder relationship", "required": False, "visible_if": {"field": "account_holder_type", "equals": "Parent / Guardian"}},
]

SERVICE_CONFIGS: dict[str, dict[str, Any]] = {
    "PRE_MATRIC": {"name": "Pre-Matric Scholarship", "sections": [{"id": "personal", "label": "Personal details", "fields": list(COMMON.keys())}, {"id": "education", "label": "Education", "fields": [f["id"] for f in SCHOLARSHIP_FIELDS[:7]]}, {"id": "family", "label": "Family and eligibility", "fields": [f["id"] for f in SCHOLARSHIP_FIELDS[7:12]]}, {"id": "bank", "label": "Bank / DBT", "fields": [f["id"] for f in SCHOLARSHIP_FIELDS[12:]] + [f["id"] for f in BANK]}, {"id": "consent", "label": "Consent", "fields": ["consent_identity", "consent_eligibility", "consent_income", "consent_education", "consent_bank"]}], "workflow": ["Application Submitted", "Authentication", "Consent", "Income Verification", "Education Verification", "Bank Verification", "Eligibility Check", "Department Approval", "Completed"]},
    "POST_MATRIC": {"name": "Post-Matric Scholarship", "sections": [{"id": "personal", "label": "Personal details", "fields": list(COMMON.keys())}, {"id": "education", "label": "Education", "fields": ["institution", "institution_location", "course_name", "course_level", "course_year", "academic_year", "previous_qualification", "previous_marks", "admission_type", "student_category", "disability_status"]}, {"id": "family", "label": "Family and eligibility", "fields": ["guardian_name", "guardian_relationship", "family_income", "occupation", "family_members"]}, {"id": "bank", "label": "Bank / DBT", "fields": [f["id"] for f in BANK]}, {"id": "consent", "label": "Consent", "fields": [f["id"] for f in CONSENTS] + ["consent_income", "consent_education", "consent_bank"]}], "workflow": ["Application Submitted", "Authentication", "Consent", "Education Verification", "Income Verification", "Bank Verification", "Eligibility Check", "Department Approval", "Completed"]},
    "FARMER": {"name": "Farmer Assistance", "sections": [{"id": "personal", "label": "Personal details", "fields": list(COMMON.keys())}, {"id": "farmer", "label": "Farmer details", "fields": ["farmer_type", "land_ownership", "survey_gat_number", "land_area", "land_unit", "irrigation_status", "land_location"]}, {"id": "crop", "label": "Crop details", "fields": ["current_crop", "crop_season", "cultivated_area", "irrigation_type", "crop_category"]}, {"id": "eligibility", "label": "Eligibility", "fields": ["family_income", "farmer_category", "scheme_eligibility"]}, {"id": "bank", "label": "Bank / DBT", "fields": [f["id"] for f in BANK]}, {"id": "consent", "label": "Consent", "fields": ["consent_identity", "consent_land", "consent_bank", "consent_eligibility"]}], "workflow": ["Application Submitted", "Authentication", "Consent", "Land Record Verification", "Farmer Eligibility", "Bank Verification", "Department Approval", "Completed"]},
    "DBT": {"name": "Direct Benefit Subsidy", "sections": [{"id": "personal", "label": "Personal details", "fields": list(COMMON.keys())}, {"id": "subsidy", "label": "Subsidy details", "fields": ["subsidy_type", "beneficiary_category", "subsidy_purpose", "asset_details", "quantity_value", "existing_reference"]}, {"id": "eligibility", "label": "Family and eligibility", "fields": ["family_income", "family_details", "eligibility_category"]}, {"id": "bank", "label": "Bank / DBT", "fields": [f["id"] for f in BANK]}, {"id": "consent", "label": "Consent", "fields": ["consent_identity", "consent_eligibility", "consent_bank", "consent_dbt"]}], "workflow": ["Application Submitted", "Authentication", "Consent", "Eligibility Verification", "Beneficiary Verification", "Bank / DBT Verification", "Department Approval", "Completed"]},
    "PENSION": {"name": "Senior Citizen Pension", "sections": [{"id": "personal", "label": "Personal details", "fields": list(COMMON.keys()) + ["age"]}, {"id": "senior", "label": "Senior citizen details", "fields": ["marital_status", "occupation", "living_arrangement", "dependents"]}, {"id": "eligibility", "label": "Financial and eligibility", "fields": ["family_income", "applicant_income", "pension_status", "existing_benefit", "eligibility_category"]}, {"id": "bank", "label": "Bank / DBT", "fields": [f["id"] for f in BANK]}, {"id": "declaration", "label": "Declaration", "fields": ["self_declaration"]}, {"id": "consent", "label": "Consent", "fields": ["consent_identity", "consent_eligibility", "consent_bank", "consent_dbt"]}], "workflow": ["Application Submitted", "Authentication", "Consent", "Age Verification", "Income / Eligibility Verification", "Bank Verification", "Department Approval", "Completed"]},
    "RESIDENCE": {"name": "Residence Certificate", "sections": [{"id": "personal", "label": "Personal details", "fields": ["full_name", "date_of_birth", "gender", "mobile", "email", "aadhaar_last4"]}, {"id": "current", "label": "Current residence", "fields": ["address", "district", "taluka", "village_city", "pin_code"]}, {"id": "permanent", "label": "Permanent residence", "fields": ["permanent_address", "permanent_district", "permanent_taluka", "permanent_village_city", "permanent_pin_code"]}, {"id": "residency", "label": "Residency", "fields": ["residing_since", "residence_duration", "previous_address", "certificate_reason"]}, {"id": "consent", "label": "Consent", "fields": ["consent_identity", "consent_address"]}], "workflow": ["Application Submitted", "Authentication", "Consent", "Address Verification", "Document Verification", "Officer Review", "Certificate Generation", "Completed"]},
    "INCOME": {"name": "Income Certificate", "sections": [{"id": "personal", "label": "Personal details", "fields": list(COMMON.keys())}, {"id": "family", "label": "Family", "fields": ["family_head_name", "family_head_relationship", "family_members", "dependents"]}, {"id": "income", "label": "Income details", "fields": ["family_income", "financial_year", "income_source", "occupation", "other_income", "salary_income", "agricultural_income", "business_income", "other_income_amount"]}, {"id": "purpose", "label": "Certificate purpose", "fields": ["certificate_purpose", "scheme_service", "existing_reference"]}, {"id": "consent", "label": "Consent", "fields": ["consent_identity", "consent_income"]}], "workflow": ["Application Submitted", "Authentication", "Consent", "Income Verification", "Document Verification", "Officer Review", "Certificate Generation", "Completed"]},
    "DRIVING": {"name": "Driving Licence", "sections": [{"id": "personal", "label": "Citizen details", "fields": list(COMMON.keys())}, {"id": "licence", "label": "Licence details", "fields": ["licence_application_type", "driving_category", "existing_licence_number", "appointment_preference"]}, {"id": "address", "label": "Address details", "fields": list(LOCATION_FIELDS)}], "workflow": ["Application Submitted", "Identity Verification", "Address Verification", "Document Review", "Appointment Scheduling", "Transport Department Review", "Licence Decision"]},
    "PROPERTY": {"name": "Property Verification", "sections": [{"id": "personal", "label": "Applicant details", "fields": list(COMMON.keys())}, {"id": "property", "label": "Property details", "fields": ["property_id", "survey_number", "property_address", "verification_purpose"]}], "workflow": ["Application Submitted", "Municipal Record Lookup", "Land Record Verification", "Ownership Validation", "Property Verification Issued"]},
}

ADDITIONAL_SERVICE_CONFIGS: dict[str, tuple[str, list[str], list[str]]] = {
    "CASTE": ("Caste Certificate", ["family_category", "sub_caste", "family_head_name", "family_head_relationship", "certificate_purpose"], ["Application Submitted", "Identity Verification", "Family Record Check", "Revenue Review", "Caste Certificate Issued"]),
    "LAND_RECORD": ("Land Record Verification", ["survey_number", "land_record_type", "property_id", "mutation_reference"], ["Application Submitted", "Survey Record Lookup", "Ownership Verification", "Mutation History Check", "Land Record Report Issued"]),
    "STUDENT": ("Student Verification", ["student_id", "institution", "institution_location", "course_name", "course_level", "academic_year", "previous_marks"], ["Application Submitted", "Student Identity Check", "Institution Record Lookup", "Enrollment Verification", "Student Verification Issued"]),
    "EDUCATION_CERT": ("Education Certificate", ["institution", "course_name", "course_level", "course_year", "academic_year", "certificate_type"], ["Application Submitted", "Academic Record Lookup", "Institution Review", "Certificate Validation", "Education Certificate Issued"]),
    "VEHICLE_REGISTRATION": ("Vehicle Registration", ["vehicle_type", "vehicle_make", "vehicle_model", "chassis_number", "engine_number", "invoice_number", "insurance_policy_number", "registration_category"], ["Application Submitted", "Vehicle Identity Check", "Insurance Verification", "Ownership Review", "Vehicle Registration Issued"]),
    "LICENCE_VERIFICATION": ("Licence Verification", ["licence_number", "driving_category", "date_of_birth"], ["Application Submitted", "Identity Verification", "Transport Record Lookup", "Licence Status Validation", "Verification Result Issued"]),
    "BIRTH_CERTIFICATE": ("Birth Certificate", ["child_name", "date_of_birth", "place_of_birth", "mother_name", "father_name", "hospital_name", "registration_number"], ["Application Submitted", "Birth Record Lookup", "Hospital Record Check", "Municipal Review", "Birth Certificate Issued"]),
    "DEATH_CERTIFICATE": ("Death Certificate", ["deceased_name", "date_of_death", "place_of_death", "informant_name", "informant_relationship", "hospital_name", "registration_number"], ["Application Submitted", "Death Record Lookup", "Hospital Record Check", "Municipal Review", "Death Certificate Issued"]),
    "SCHOLARSHIP_ASSISTANCE": ("Scholarship Assistance", [field["id"] for field in SCHOLARSHIP_FIELDS], ["Application Submitted", "Student Verification", "Income Eligibility Check", "Document Review", "Scholarship Assistance Decision"]),
    "EMPLOYMENT_REGISTRATION": ("Employment Registration", ["highest_qualification", "skills", "experience_years", "employment_category", "preferred_location"], ["Application Submitted", "Identity Verification", "Qualification Review", "Employment Registry Check", "Registration Approved"]),
    "SKILL_VERIFICATION": ("Skill Verification", ["skill_name", "training_provider", "training_certificate_number", "completion_date", "assessment_reference"], ["Application Submitted", "Training Record Lookup", "Skill Assessment Validation", "Employment Review", "Skill Verification Issued"]),
    "EMPLOYMENT_CERTIFICATE": ("Employment Certificate", ["employment_status", "employer_name", "occupation", "employment_start_date", "employment_end_date", "certificate_purpose"], ["Application Submitted", "Employment Record Lookup", "Employer Verification", "Department Review", "Employment Certificate Issued"]),
}

for service_key, (service_name, fields, workflow) in ADDITIONAL_SERVICE_CONFIGS.items():
    sections = [{"id": "personal", "label": "Personal details", "fields": list(COMMON.keys())}]
    if service_key in {"STUDENT", "EDUCATION_CERT", "SCHOLARSHIP_ASSISTANCE"}:
        sections.append({"id": "education", "label": "Education details", "fields": fields})
    elif service_key in {"VEHICLE_REGISTRATION", "LICENCE_VERIFICATION"}:
        sections.append({"id": "transport", "label": "Transport details", "fields": fields})
    elif service_key in {"BIRTH_CERTIFICATE", "DEATH_CERTIFICATE"}:
        sections.append({"id": "civil_record", "label": "Civil registration details", "fields": fields})
    elif service_key.startswith("EMPLOYMENT") or service_key == "SKILL_VERIFICATION":
        sections.append({"id": "employment", "label": "Employment and skills details", "fields": fields})
    elif service_key == "CASTE":
        sections.append({"id": "family", "label": "Family and certificate details", "fields": fields})
    else:
        sections.append({"id": "record", "label": "Record details", "fields": fields})
    SERVICE_CONFIGS[service_key] = {"name": service_name, "sections": sections, "workflow": workflow}

SERVICE_CATALOG: dict[str, tuple[str, str]] = {
    "Caste Certificate": ("CASTE-CERT", "Revenue"),
    "Land Record Verification": ("LAND-RECORD-VERIFY", "Revenue"),
    "Student Verification": ("STUDENT-VERIFY", "Education"),
    "Education Certificate": ("EDUCATION-CERT", "Education"),
    "Vehicle Registration": ("VEHICLE-REG", "Transport"),
    "Licence Verification": ("LICENCE-VERIFY", "Transport"),
    "Birth Certificate": ("BIRTH-CERT", "Municipal"),
    "Death Certificate": ("DEATH-CERT", "Municipal"),
    "Scholarship Assistance": ("SCHOLARSHIP-AID", "Social Welfare"),
    "Employment Registration": ("EMPLOYMENT-REG", "Employment"),
    "Skill Verification": ("SKILL-VERIFY", "Employment"),
    "Employment Certificate": ("EMPLOYMENT-CERT", "Employment"),
}

SERVICE_NAMES = [config["name"] for config in SERVICE_CONFIGS.values()]

VERIFIED_RECORD_FIELDS: dict[str, dict[str, set[str]]] = {
    "INCOME": {"income": {"family_income", "family_members", "address"}},
    "POST_MATRIC": {
        "student": {"institution", "institution_location", "course_name", "course_level", "course_year", "academic_year", "previous_qualification", "previous_marks", "admission_type", "student_category", "disability_status"},
        "income": {"family_income"},
    },
    "DRIVING": {"licence": {"existing_licence_number"}, "address": {"address", "district", "taluka", "village_city", "state", "pin_code"}},
    "PROPERTY": {"property": {"property_id", "property_address"}, "land": {"survey_number"}},
}


def ensure_service_catalog(db: Any) -> None:
    from app.models.department import Department
    from app.models.platform import DigitalPlatform, PlatformStatus
    from app.models.service import Service

    def get_or_create_department_platform(
        department_name: str,
        department_code: str,
        platform_name: str,
        platform_slug: str,
        description: str,
    ) -> tuple[Any, Any]:
        department = db.query(Department).filter(Department.name == department_name).first()
        if department is None:
            department = Department(
                name=department_name,
                code=department_code,
                description=description,
                state="Maharashtra",
            )
            db.add(department)
            db.flush()

        platform = db.query(DigitalPlatform).filter(
            DigitalPlatform.department_id == department.id
        ).first()
        if platform is None:
            platform = DigitalPlatform(
                name=platform_name,
                slug=platform_slug,
                api_version="v1",
                status=PlatformStatus.ACTIVE,
                description=description,
                department_id=department.id,
            )
            db.add(platform)
            db.flush()
        return department, platform

    education, education_service_platform = get_or_create_department_platform(
        "Education Department",
        "EDUCATION_MH",
        "Education Records Gateway",
        "education-records-mh",
        "Education enrolment and certificate verification services.",
    )
    revenue = db.query(Department).filter(Department.name.ilike("%Revenue%"),).first()
    social_welfare, social_welfare_platform = get_or_create_department_platform(
        "Social Welfare Department",
        "SOCIAL_WELFARE_MH",
        "Social Welfare Services Gateway",
        "social-welfare-mh",
        "Social Welfare service applications and eligibility verification.",
    )
    employment, employment_platform = get_or_create_department_platform(
        "Employment Department",
        "EMPLOYMENT_MH",
        "Employment and Skills Gateway",
        "employment-skills-mh",
        "Employment registration, skills verification, and certificate services.",
    )
    platform = db.query(DigitalPlatform).first()
    education_platform = db.query(DigitalPlatform).filter(DigitalPlatform.department_id == education.id).first() if education else education_service_platform
    ownership = {
        "Pre-Matric Scholarship": (education, education_platform),
        "Post-Matric Scholarship": (social_welfare, social_welfare_platform),
        "Farmer Assistance": (revenue, platform),
        "Direct Benefit Subsidy": (revenue, platform),
        "Senior Citizen Pension": (revenue, platform),
        "Residence Certificate": (revenue, platform),
        "Income Certificate": (revenue, platform),
    }
    transport = db.query(Department).filter(Department.name.ilike("%Transport%")).first()
    municipal, municipal_platform = get_or_create_department_platform(
        "Municipal Department",
        "MUNICIPAL_MH",
        "Municipal Property Services Gateway",
        "municipal-property-mh",
        "Municipal property assessment and verification services.",
    )
    transport_platform = db.query(DigitalPlatform).filter(DigitalPlatform.department_id == transport.id).first() if transport else platform
    if transport and not transport_platform:
        transport_platform = DigitalPlatform(
            name="Transport Licensing Gateway",
            slug="transport-licensing-mh",
            api_version="v1",
            status=PlatformStatus.ACTIVE,
            description="Transport licensing and appointment services.",
            department_id=transport.id,
        )
        db.add(transport_platform)
        db.flush()
    ownership.update({
        "Driving Licence": (transport, transport_platform),
        "Property Verification": (municipal, municipal_platform),
    })
    department_platforms = {
        "Revenue": (revenue, platform),
        "Education": (education, education_platform),
        "Social Welfare": (social_welfare, social_welfare_platform),
        "Transport": (transport, transport_platform),
        "Municipal": (municipal, municipal_platform),
        "Employment": (employment, employment_platform),
    }
    for service_name, (_service_code, department_key) in SERVICE_CATALOG.items():
        ownership[service_name] = department_platforms[department_key]
    for name, (department, service_platform) in ownership.items():
        if not department or not service_platform:
            continue
        service = db.query(Service).filter(Service.name == name).first()
        if service:
            service.department_id = department.id
            service.platform_id = service_platform.id
            continue
        code = SERVICE_CATALOG.get(name, (None, ""))[0] or {
            "Pre-Matric Scholarship": "SCH-PRE",
            "Farmer Assistance": "FARMER-AID",
            "Direct Benefit Subsidy": "DBT-GENERAL",
            "Senior Citizen Pension": "PENSION-SC",
            "Residence Certificate": "RES-CERT",
            "Income Certificate": "INC-CERT",
            "Driving Licence": "DRIVING-LICENCE",
            "Property Verification": "PROPERTY-VERIFY",
        }.get(name, "SCH-POST")
        db.add(Service(name=name, code=code, description=f"Configurable GovFlow service: {name}", is_active=True, department_id=department.id, platform_id=service_platform.id))
    db.commit()

FIELD_OVERRIDES: dict[str, dict[str, Any]] = {
    "licence_application_type": {"type": "select", "label": "Application type", "required": True, "options": ["New licence", "Renewal"]},
    "driving_category": {"type": "select", "label": "Vehicle category", "required": True, "options": ["Two-wheeler", "Four-wheeler", "Commercial"]},
    "existing_licence_number": {"type": "text", "label": "Existing licence number", "required": False, "visible_if": {"field": "licence_application_type", "equals": "Renewal"}},
    "appointment_preference": {"type": "date", "label": "Preferred appointment date", "required": True},
    "property_id": {"type": "text", "label": "Property ID", "required": True},
    "survey_number": {"type": "text", "label": "Survey number", "required": True},
    "property_address": {"type": "text", "label": "Property address", "required": True},
    "verification_purpose": {"type": "text", "label": "Reason for verification", "required": True},
    "family_category": {"type": "select", "label": "Family category", "required": True, "options": ["SC", "ST", "OBC", "VJNT", "SBC", "Other"]},
    "sub_caste": {"type": "text", "label": "Sub-caste", "required": True},
    "land_record_type": {"type": "select", "label": "Land record type", "required": True, "options": ["Ownership extract", "Mutation record", "Survey record", "Other"]},
    "mutation_reference": {"type": "text", "label": "Mutation reference (if known)", "required": False},
    "student_id": {"type": "text", "label": "Student ID / enrollment number", "required": True},
    "certificate_type": {"type": "text", "label": "Certificate requested", "required": True},
    "vehicle_type": {"type": "select", "label": "Vehicle type", "required": True, "options": ["Two-wheeler", "Car", "Commercial vehicle", "Other"]},
    "vehicle_make": {"type": "text", "label": "Vehicle make", "required": True},
    "vehicle_model": {"type": "text", "label": "Vehicle model", "required": True},
    "chassis_number": {"type": "text", "label": "Chassis number", "required": True},
    "engine_number": {"type": "text", "label": "Engine number", "required": True},
    "invoice_number": {"type": "text", "label": "Purchase invoice number", "required": True},
    "insurance_policy_number": {"type": "text", "label": "Insurance policy number", "required": True},
    "registration_category": {"type": "select", "label": "Registration category", "required": True, "options": ["Private", "Commercial", "Other"]},
    "licence_number": {"type": "text", "label": "Driving licence number", "required": True},
    "child_name": {"type": "text", "label": "Child's full name", "required": True},
    "date_of_birth": {"type": "date", "label": "Date of birth", "required": True},
    "place_of_birth": {"type": "text", "label": "Place of birth", "required": True},
    "mother_name": {"type": "text", "label": "Mother's full name", "required": True},
    "father_name": {"type": "text", "label": "Father's full name", "required": True},
    "hospital_name": {"type": "text", "label": "Hospital / facility", "required": False},
    "registration_number": {"type": "text", "label": "Existing registration number (if known)", "required": False},
    "deceased_name": {"type": "text", "label": "Deceased person's full name", "required": True},
    "date_of_death": {"type": "date", "label": "Date of death", "required": True},
    "informant_name": {"type": "text", "label": "Informant's full name", "required": True},
    "informant_relationship": {"type": "text", "label": "Relationship to deceased", "required": True},
    "highest_qualification": {"type": "text", "label": "Highest qualification", "required": True},
    "skills": {"type": "text", "label": "Skills / occupation", "required": True},
    "experience_years": {"type": "number", "label": "Years of experience", "required": True},
    "employment_category": {"type": "select", "label": "Employment category", "required": True, "options": ["Seeking work", "Currently employed", "Self-employed", "Other"]},
    "preferred_location": {"type": "text", "label": "Preferred work location", "required": True},
    "skill_name": {"type": "text", "label": "Skill to verify", "required": True},
    "training_provider": {"type": "text", "label": "Training provider", "required": True},
    "training_certificate_number": {"type": "text", "label": "Training certificate number", "required": True},
    "completion_date": {"type": "date", "label": "Training completion date", "required": True},
    "assessment_reference": {"type": "text", "label": "Assessment reference (if available)", "required": False},
    "employment_status": {"type": "select", "label": "Employment status", "required": True, "options": ["Employed", "Self-employed", "Not currently employed"]},
    "employer_name": {"type": "text", "label": "Employer / organization", "required": True},
    "occupation": {"type": "text", "label": "Occupation / role", "required": True},
    "employment_start_date": {"type": "date", "label": "Employment start date", "required": True},
    "employment_end_date": {"type": "date", "label": "Employment end date (if applicable)", "required": False},
    "institution": {"type": "text", "label": "Institution / College name", "required": True},
    "institution_location": {"type": "text", "label": "Institution location", "required": True},
    "course_name": {"type": "text", "label": "Course name", "required": True},
    "course_level": {"type": "select", "label": "Course level", "required": True, "options": ["School", "Undergraduate", "Postgraduate", "Diploma", "Other"]},
    "course_year": {"type": "text", "label": "Course year", "required": True},
    "previous_qualification": {"type": "text", "label": "Previous examination qualification", "required": True},
    "admission_type": {"type": "select", "label": "Admission type", "required": False, "options": ["Regular", "Management", "Other"]},
    "farmer_type": {"type": "select", "label": "Farmer type", "required": True, "options": ["Individual", "Tenant farmer", "Sharecropper"]},
    "land_ownership": {"type": "select", "label": "Land ownership status", "required": True, "options": ["Owned", "Leased", "Shared"]},
    "survey_gat_number": {"type": "text", "label": "Survey / Gat number", "required": True},
    "land_area": {"type": "number", "label": "Land area", "required": True},
    "land_unit": {"type": "select", "label": "Land unit", "required": True, "options": ["Acre", "Hectare", "Guntha"]},
    "irrigation_status": {"type": "select", "label": "Irrigation status", "required": True, "options": ["Irrigated", "Non-irrigated"]},
    "land_location": {"type": "text", "label": "Land location", "required": True},
    "current_crop": {"type": "text", "label": "Current crop", "required": True},
    "crop_season": {"type": "select", "label": "Crop season", "required": True, "options": ["Kharif", "Rabi", "Zaid"]},
    "cultivated_area": {"type": "number", "label": "Cultivated area", "required": True},
    "irrigation_type": {"type": "text", "label": "Irrigation type", "required": False},
    "crop_category": {"type": "text", "label": "Crop category", "required": False},
    "farmer_category": {"type": "text", "label": "Farmer category", "required": False},
    "scheme_eligibility": {"type": "text", "label": "Scheme eligibility details", "required": False},
    "subsidy_type": {"type": "select", "label": "Subsidy / scheme type", "required": True, "options": ["Agriculture", "Housing", "Equipment", "Other"]},
    "beneficiary_category": {"type": "text", "label": "Beneficiary category", "required": True},
    "subsidy_purpose": {"type": "text", "label": "Purpose of subsidy", "required": True},
    "asset_details": {"type": "text", "label": "Asset, product, or service details", "required": True},
    "quantity_value": {"type": "text", "label": "Quantity / value", "required": False},
    "existing_reference": {"type": "text", "label": "Existing beneficiary / certificate number", "required": False},
    "family_details": {"type": "text", "label": "Family details", "required": False},
    "eligibility_category": {"type": "text", "label": "Eligibility category", "required": True},
    "age": {"type": "number", "label": "Age", "required": True},
    "marital_status": {"type": "select", "label": "Marital status", "required": True, "options": ["Single", "Married", "Widowed", "Divorced", "Other"]},
    "living_arrangement": {"type": "text", "label": "Current living arrangement", "required": True},
    "dependents": {"type": "number", "label": "Number of dependents", "required": True},
    "applicant_income": {"type": "number", "label": "Applicant income", "required": True},
    "pension_status": {"type": "select", "label": "Current pension status", "required": True, "options": ["Not receiving pension", "Receiving pension"]},
    "existing_benefit": {"type": "text", "label": "Existing government pension / benefit", "required": False},
    "self_declaration": {"type": "checkbox", "label": "I confirm that the information provided is correct", "required": True},
    "permanent_address": {"type": "text", "label": "Permanent address", "required": True},
    "permanent_district": {"type": "text", "label": "Permanent district", "required": True},
    "permanent_taluka": {"type": "text", "label": "Permanent sub-district", "help_text": "Also called Taluka.", "required": True},
    "permanent_village_city": {"type": "text", "label": "Permanent village / city", "required": True},
    "permanent_pin_code": {"type": "text", "label": "Permanent PIN code", "required": True, "pattern": "^[0-9]{6}$", "max_length": 6},
    "residing_since": {"type": "date", "label": "Residing at this address since", "required": True},
    "residence_duration": {"type": "text", "label": "Duration of residence", "required": True},
    "certificate_reason": {"type": "text", "label": "Reason for requesting certificate", "required": True},
    "consent_address": {"type": "checkbox", "label": "Allow address verification", "required": True},
    "family_head_name": {"type": "text", "label": "Family head name", "required": True},
    "family_head_relationship": {"type": "text", "label": "Relationship to family head", "required": True},
    "financial_year": {"type": "text", "label": "Income period / financial year", "required": True},
    "income_source": {"type": "text", "label": "Main income source", "required": True},
    "other_income": {"type": "text", "label": "Other income sources", "required": False},
    "salary_income": {"type": "number", "label": "Salary income", "required": False},
    "agricultural_income": {"type": "number", "label": "Agricultural income", "required": False},
    "business_income": {"type": "number", "label": "Business income", "required": False},
    "other_income_amount": {"type": "number", "label": "Other income amount", "required": False},
    "certificate_purpose": {"type": "text", "label": "Purpose for requesting income certificate", "required": True},
    "scheme_service": {"type": "text", "label": "Scheme / service requiring certificate", "required": True},
}

CONSENT_FIELDS: dict[str, tuple[str, str]] = {
    "consent_identity": ("Allow identity verification", "Used to verify your identity for this application."),
    "consent_income": ("Allow income verification", "Used to check the income details required for this service."),
    "consent_education": ("Allow education verification", "Used to verify school, college, course, or marks details."),
    "consent_bank": ("Allow bank account verification", "Used to verify the account before any eligible payment."),
    "consent_dbt": ("Allow subsidy payment verification", "Used to process an approved benefit through Direct Benefit Transfer (DBT)."),
    "consent_land": ("Allow land-record verification", "Used to verify land ownership and cultivation details."),
    "consent_eligibility": ("Allow eligibility verification", "Used to check whether you meet this service's configured requirements."),
    "consent_address": ("Allow address verification", "Used to verify your current or permanent residence."),
}

DEFAULT_FIELD = {"type": "text", "label": "Details", "required": False}


def _field(field_id: str) -> dict[str, Any]:
    value = deepcopy(COMMON.get(field_id) or IDENTITY_EXTRAS.get(field_id) or LOCATION_FIELDS.get(field_id) or FIELD_OVERRIDES.get(field_id) or DEFAULT_FIELD)
    value["id"] = field_id
    if field_id.startswith("consent_"):
        label, help_text = CONSENT_FIELDS.get(field_id, ("Allow verification for this service", "This permission is used only to process this application."))
        value = {"id": field_id, "type": "checkbox", "label": label, "help_text": help_text, "required": True}
    return value


def _service_config_key(service: Any) -> str:
    code = (service.code or "").upper()
    name = (service.name or "").lower()
    key = next((key for key, config in SERVICE_CONFIGS.items() if key in code or config["name"].lower() == name), None)
    if key is None:
        key = "INCOME" if "income" in name else "RESIDENCE" if "residence" in name or "domicile" in name else "POST_MATRIC" if "scholarship" in name else "DBT"
    return key


def get_service_config(service: Any) -> dict[str, Any]:
    key = _service_config_key(service)
    config = deepcopy(SERVICE_CONFIGS[key])
    config.pop("workflow", None)
    personal_extras = {
        "PRE_MATRIC": ["date_of_birth", "gender"],
        "POST_MATRIC": ["date_of_birth", "gender"],
        "FARMER": ["date_of_birth", "gender"],
        "DBT": ["date_of_birth", "gender"],
        "PENSION": ["date_of_birth", "gender"],
        "INCOME": ["date_of_birth", "gender"],
    }.get(key, [])
    for section in config["sections"]:
        if section["id"] == "personal":
            section["fields"] = list(dict.fromkeys(section["fields"] + personal_extras))
            break
    if key != "RESIDENCE":
        personal_index = next((index for index, section in enumerate(config["sections"]) if section["id"] == "personal"), 0)
        config["sections"].insert(personal_index + 1, {"id": "location", "label": "Address details", "fields": list(LOCATION_FIELDS)})
    fields = {field_id: _field(field_id) if isinstance(field_id, str) else field_id for section in config["sections"] for field_id in section["fields"]}
    config["service_id"] = service.id
    config["service_name"] = service.name
    config["department_id"] = service.department_id
    config["fields"] = list(fields.values())
    section_help = {
        "consent": "Choose the permissions needed to verify and process this application. These permissions do not change your application details.",
        "bank": "Enter the account that should receive an approved payment or benefit.",
    }
    config["sections"] = [{**section, "description": section_help.get(section["id"]), "fields": [fields[field_id] for field_id in section["fields"]]} for section in config["sections"]]
    return config


def validate_form_data(
    service: Any,
    form_data: dict[str, Any],
    verified_records: dict[str, str] | None = None,
) -> list[str]:
    config = get_service_config(service)
    record_fields = VERIFIED_RECORD_FIELDS.get(_service_config_key(service), {})
    satisfied_fields = {
        field_id
        for record_key, record_id in (verified_records or {}).items()
        if record_id and record_key in record_fields
        for field_id in record_fields[record_key]
    }
    errors: list[str] = []
    fields = {field["id"]: field for field in config["fields"]}
    for field_id, field in fields.items():
        condition = field.get("visible_if")
        visible = not condition or form_data.get(condition["field"]) == condition["equals"]
        value = form_data.get(field_id)
        if visible and field.get("required") and field_id not in satisfied_fields and (value is None or value is False or str(value).strip() == ""):
            errors.append(f"{field['label']} is required.")
        if visible and value not in (None, "") and field.get("pattern"):
            import re
            if not re.fullmatch(field["pattern"], str(value)):
                errors.append(f"{field['label']} has an invalid format.")
        if visible and field.get("type") == "date" and value not in (None, ""):
            from datetime import date
            try:
                selected_date = date.fromisoformat(str(value))
                if selected_date > date.today() or selected_date.year < 1900:
                    errors.append(f"{field['label']} must be a valid past date.")
            except ValueError:
                errors.append(f"{field['label']} has an invalid date.")
        if visible and value not in (None, "") and field.get("options") and value not in field["options"]:
            errors.append(f"{field['label']} has an invalid option.")
    if config["sections"]:
        allowed = set(fields)
        form_data_keys = set(form_data)
        extra = form_data_keys - allowed
        if extra:
            errors.append("Submitted form contains fields not supported by this service.")
    return errors
