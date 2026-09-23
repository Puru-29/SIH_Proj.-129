from app.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    User,
    Department,
    DigitalPlatform,
    Service,
    ServiceApplication,
    DataShareConsent,
    Document,
    AuditLog,
)
from app.models.user import UserRole
from app.models.platform import PlatformStatus
from app.models.application import ApplicationStatus
from app.models.consent import ConsentStatus


def seed_database():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if users already exist
        if db.query(User).first():
            print("Database already has data. Skipping seeding.")
            return

        print("Seeding initial users...")
        admin = User(
            full_name="Admin Officer",
            email="admin@gov.in",
            phone="9000000001",
            role=UserRole.ADMIN,
            hashed_password=hash_password("Admin@123"),
            is_active=True,
        )
        officer = User(
            full_name="Rajesh Sharma",
            email="officer.sharma@revenue.gov.in",
            phone="9000000002",
            role=UserRole.OFFICER,
            hashed_password=hash_password("Officer@123"),
            is_active=True,
        )
        citizen = User(
            full_name="Aarav Patil",
            email="aarav.patil@gmail.com",
            phone="9876543210",
            aadhaar_last4="4321",
            role=UserRole.CITIZEN,
            hashed_password=hash_password("Citizen@123"),
            is_active=True,
        )
        db.add_all([admin, officer, citizen])
        db.commit()
        db.refresh(admin)
        db.refresh(officer)
        db.refresh(citizen)

        print("Seeding departments...")
        dept_rev = Department(
            name="Revenue & Land Records",
            code="REV_MH",
            description="Department of Revenue and Land Administration, Maharashtra",
            state="Maharashtra",
        )
        dept_trans = Department(
            name="Transport Department",
            code="TRANS_MH",
            description="Motor Vehicles Department / Regional Transport Office (RTO)",
            state="Maharashtra",
        )
        dept_fcs = Department(
            name="Food & Civil Supplies",
            code="FCS_MH",
            description="Public Distribution System & Essential Commodities",
            state="Maharashtra",
        )
        dept_health = Department(
            name="Public Health Department",
            code="HEALTH_MH",
            description="Public Health Services and Hospital Management",
            state="Maharashtra",
        )
        db.add_all([dept_rev, dept_trans, dept_fcs, dept_health])
        db.commit()
        db.refresh(dept_rev)
        db.refresh(dept_trans)

        print("Seeding digital platforms...")
        plat_aaple = DigitalPlatform(
            name="Aaple Sarkar Portal",
            slug="aaple-sarkar",
            base_url="https://aaplesarkar.mahaonline.gov.in",
            api_version="v1",
            status=PlatformStatus.ACTIVE,
            description="Maharashtra Citizen Services Single Window Portal",
            department_id=dept_rev.id,
        )
        plat_sarathi = DigitalPlatform(
            name="Sarathi RTO Services",
            slug="sarathi-rto",
            base_url="https://parivahan.gov.in/sarathiservice",
            api_version="v1",
            status=PlatformStatus.ACTIVE,
            description="National and State Transport Licensing Service",
            department_id=dept_trans.id,
        )
        plat_digilocker = DigitalPlatform(
            name="DigiLocker Maharashtra Gateway",
            slug="digilocker-mh",
            base_url="https://digilocker.gov.in",
            api_version="v2",
            status=PlatformStatus.ACTIVE,
            description="Digital Document Repository and Verification",
            department_id=dept_rev.id,
        )
        db.add_all([plat_aaple, plat_sarathi, plat_digilocker])
        db.commit()
        db.refresh(plat_aaple)
        db.refresh(plat_sarathi)

        print("Seeding services...")
        svc_income = Service(
            name="Income Certificate",
            code="INC_CERT_01",
            description="Issuance of official annual income certificate",
            is_active=True,
            department_id=dept_rev.id,
            platform_id=plat_aaple.id,
        )
        svc_domicile = Service(
            name="Domicile Certificate",
            code="DOM_CERT_01",
            description="Proof of permanent residence in Maharashtra",
            is_active=True,
            department_id=dept_rev.id,
            platform_id=plat_aaple.id,
        )
        svc_dl = Service(
            name="Driving License Verification",
            code="DL_VERIFY_01",
            description="Cross-platform instant verification of driving license",
            is_active=True,
            department_id=dept_trans.id,
            platform_id=plat_sarathi.id,
        )
        db.add_all([svc_income, svc_domicile, svc_dl])
        db.commit()
        db.refresh(svc_income)
        db.refresh(svc_dl)

        print("Seeding applications...")
        app1 = ServiceApplication(
            reference_id="MH-REV-2026-0001",
            status=ApplicationStatus.SUBMITTED,
            remarks="Application submitted with income proofs",
            citizen_id=citizen.id,
            service_id=svc_income.id,
        )
        app2 = ServiceApplication(
            reference_id="MH-TRANS-2026-0002",
            status=ApplicationStatus.APPROVED,
            remarks="DL verification completed successfully via interoperability gateway",
            citizen_id=citizen.id,
            service_id=svc_dl.id,
        )
        db.add_all([app1, app2])
        db.commit()
        db.refresh(app1)

        print("Seeding data-share consent...")
        consent = DataShareConsent(
            purpose="Income verification using Ration and Land records",
            status=ConsentStatus.GRANTED,
            source_platform_id=plat_aaple.id,
            target_platform_id=plat_sarathi.id,
            citizen_id=citizen.id,
        )
        db.add(consent)

        print("Seeding documents...")
        doc1 = Document(
            title="Aadhaar Card",
            doc_type="identity_proof",
            file_path="/documents/aadhaar_aarav.pdf",
            mime_type="application/pdf",
            owner_id=citizen.id,
            application_id=app1.id,
        )
        doc2 = Document(
            title="Salary Slip 2026",
            doc_type="income_proof",
            file_path="/documents/salary_aarav.pdf",
            mime_type="application/pdf",
            owner_id=citizen.id,
            application_id=app1.id,
        )
        db.add_all([doc1, doc2])

        print("Seeding audit log...")
        audit = AuditLog(
            action="INITIAL_SEED",
            entity_type="System",
            entity_id="INIT_01",
            details="Seeded initial demo departments, platforms, services, and users for SIH26129",
            actor_id=admin.id,
        )
        db.add(audit)
        db.commit()

        print("Database seeded successfully with all models and initial data!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
