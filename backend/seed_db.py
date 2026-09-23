"""
Database Seeding Script for SIH 26129 Inter-Governmental Mesh.
Populates SQLite database (sih26129.db) with realistic Indian e-Governance mesh data:
- Users (Admin, Officers, Citizens across Maharashtra)
- Departments (Revenue, Transport, Higher Education, Food & Civil Supplies, Health, Municipal)
- Digital Platform Mesh Nodes (DigiLocker, UIDAI, SAMARTH, PFMS, GSTN, Mahabhulekh)
- Government Services
- Live Applications across all statuses (Approved, Under Review, Submitted, Rejected)
- DPDP Data Share Consents
- Immutable Audit Trails
- Verified Documents
"""

import sys
from datetime import datetime, timedelta, timezone
from app.database import SessionLocal, Base, engine
from app.models.user import User, UserRole
from app.models.department import Department
from app.models.platform import DigitalPlatform, PlatformStatus
from app.models.service import Service
from app.models.application import ServiceApplication, ApplicationStatus
from app.models.consent import DataShareConsent, ConsentStatus
from app.models.audit import AuditLog
from app.models.document import Document
from app.core.security import hash_password


def seed_database(force: bool = False):
    print("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if force:
            print("Force flag set: clearing existing data...")
            db.query(AuditLog).delete()
            db.query(Document).delete()
            db.query(DataShareConsent).delete()
            db.query(ServiceApplication).delete()
            db.query(Service).delete()
            db.query(DigitalPlatform).delete()
            db.query(Department).delete()
            db.query(User).delete()
            db.commit()
        elif db.query(ServiceApplication).count() >= 15:
            print(f"Database already contains {db.query(ServiceApplication).count()} applications. Skipping.")
            return

        print("Seeding Users...")
        admin = User(
            full_name="GovFlow System Administrator",
            email="admin@govflow.in",
            phone="+919800000001",
            aadhaar_last4="9901",
            role=UserRole.ADMIN,
            hashed_password=hash_password("Admin@123"),
            is_active=True,
        )
        officer1 = User(
            full_name="Rajesh Sharma (Tahsildar)",
            email="officer@revenue.gov.in",
            phone="+919822011234",
            aadhaar_last4="4421",
            role=UserRole.OFFICER,
            hashed_password=hash_password("Officer@123"),
            is_active=True,
        )
        officer2 = User(
            full_name="Pooja Deshmukh (RTO Inspector)",
            email="transport.officer@maha.gov.in",
            phone="+919822011235",
            aadhaar_last4="5532",
            role=UserRole.OFFICER,
            hashed_password=hash_password("Officer@123"),
            is_active=True,
        )

        citizens_data = [
            ("Ramesh Patil", "ramesh.patil@gov.in", "+919823019801", "8492"),
            ("Aarav Patel", "aarav.patel@gmail.com", "+919823019802", "1948"),
            ("Priya Kulkarni", "priya.kulkarni@gmail.com", "+919823019803", "3029"),
            ("Suresh Verma", "suresh.verma@gmail.com", "+919823019804", "7145"),
            ("Sunita Sharma", "sunita.sharma@gmail.com", "+919823019805", "2918"),
            ("Arjun Nair", "arjun.nair@gmail.com", "+919823019806", "6621"),
            ("Fatima Sheikh", "fatima.sheikh@gmail.com", "+919823019807", "4419"),
            ("Vikram Reddy", "vikram.reddy@gmail.com", "+919823019808", "8823"),
            ("Ananya Iyer", "ananya.iyer@gmail.com", "+919823019809", "1290"),
            ("Manoj Kulkarni", "manoj.kulkarni@gmail.com", "+919823019810", "5512"),
            ("Pooja Deshpande", "pooja.deshpande@gmail.com", "+919823019811", "9034"),
            ("Imran Qureshi", "imran.qureshi@gmail.com", "+919823019812", "7718"),
            ("Kavita Joshi", "kavita.joshi@gmail.com", "+919823019813", "3321"),
            ("Rahul Verma", "rahul.verma@gmail.com", "+919823019814", "8841"),
            ("Sneha Gaikwad", "sneha.gaikwad@gmail.com", "+919823019815", "6612"),
        ]

        citizen_users = []
        for name, email, phone, last4 in citizens_data:
            c = User(
                full_name=name,
                email=email,
                phone=phone,
                aadhaar_last4=last4,
                role=UserRole.CITIZEN,
                hashed_password=hash_password("Citizen@123"),
                is_active=True,
            )
            citizen_users.append(c)

        db.add_all([admin, officer1, officer2] + citizen_users)
        db.flush()

        print("Seeding Departments...")
        dept_rev = Department(
            name="Revenue & Land Records",
            code="REV",
            description="Land ownership titles, 7/12 extract mutation, caste and income certification",
            state="Maharashtra",
        )
        dept_rto = Department(
            name="Transport & Motor Vehicles",
            code="RTO",
            description="Vehicle registration, driving licenses, and pollution/fitness certification",
            state="Maharashtra",
        )
        dept_edu = Department(
            name="Higher & Technical Education",
            code="EDU",
            description="Scholarship disbursement, college enrollment verification, and DigiLocker degrees",
            state="Maharashtra",
        )
        dept_fcs = Department(
            name="Food, Civil Supplies & Consumer Protection",
            code="FCS",
            description="National Food Security Scheme (NFSA), Ration Card transfers, PDS grain quota",
            state="Maharashtra",
        )
        dept_hlt = Department(
            name="Public Health & Family Welfare",
            code="HLT",
            description="Ayushman Bharat PM-JAY hospital empanelment and health insurance registry",
            state="Maharashtra",
        )
        db.add_all([dept_rev, dept_rto, dept_edu, dept_fcs, dept_hlt])
        db.flush()

        print("Seeding Digital Platforms / Mesh Nodes...")
        plat_digilocker = DigitalPlatform(
            name="DigiLocker Indian Document Mesh",
            slug="digilocker-mesh",
            base_url="https://api.digilocker.gov.in/v1",
            api_version="v2",
            status=PlatformStatus.ACTIVE,
            description="National citizen document repository with cryptographic signature verification",
            department_id=dept_rev.id,
        )
        plat_uidai = DigitalPlatform(
            name="UIDAI e-KYC Identity Gateway",
            slug="uidai-ekyc",
            base_url="https://api.uidai.gov.in/ekyc/v2",
            api_version="v2.5",
            status=PlatformStatus.ACTIVE,
            description="Aadhaar demographic and biometric OTP verification mesh service",
            department_id=dept_rev.id,
        )
        plat_samarth = DigitalPlatform(
            name="SAMARTH Higher Education Registry",
            slug="samarth-edu",
            base_url="https://samarth.edu.gov.in/api/v1",
            api_version="v1",
            status=PlatformStatus.ACTIVE,
            description="Unified student academic lifecycle, enrollment, and scholarship registry",
            department_id=dept_edu.id,
        )
        plat_pfms = DigitalPlatform(
            name="PFMS Public Financial Management System",
            slug="pfms-banking",
            base_url="https://pfms.nic.in/api/v3",
            api_version="v3",
            status=PlatformStatus.ACTIVE,
            description="Direct Benefit Transfer (DBT) and Aadhaar Payment Bridge (APB) clearinghouse",
            department_id=dept_rev.id,
        )
        plat_gstn = DigitalPlatform(
            name="GSTN Taxpayer Network",
            slug="gstn-tax",
            base_url="https://api.gstn.org.in/taxpayer/v2",
            api_version="v2",
            status=PlatformStatus.ACTIVE,
            description="Goods & Services Tax Network taxpayer identification and turnover verification API",
            department_id=dept_rev.id,
        )
        plat_mahabhulekh = DigitalPlatform(
            name="Mahabhulekh Land Records Gateway",
            slug="mahabhulekh-land",
            base_url="https://mahabhumi.gov.in/api/v1",
            api_version="v1.2",
            status=PlatformStatus.ACTIVE,
            description="Digital Land Records, 7/12 extracts, and Title Mutation register",
            department_id=dept_rev.id,
        )
        db.add_all([plat_digilocker, plat_uidai, plat_samarth, plat_pfms, plat_gstn, plat_mahabhulekh])
        db.flush()

        print("Seeding Government Services...")
        svc_sch = Service(
            name="Post-Matric Scholarship Scheme",
            code="SCH-POST-MATRIC",
            description="Direct scholarship disbursement for technical and higher education students",
            is_active=True,
            department_id=dept_edu.id,
            platform_id=plat_samarth.id,
        )
        svc_dbt = Service(
            name="Farmer Input Subsidy (DBT)",
            code="AGRI-DBT-SUB",
            description="Direct benefit transfer for agricultural equipment and crop input subsidy",
            is_active=True,
            department_id=dept_rev.id,
            platform_id=plat_pfms.id,
        )
        svc_rc = Service(
            name="Ration Card Family Transfer",
            code="PDS-RC-XFER",
            description="Inter-district transfer of NFSA/BPL ration quota entitlement",
            is_active=True,
            department_id=dept_fcs.id,
            platform_id=plat_digilocker.id,
        )
        svc_dl = Service(
            name="Driving License Smart Card Renewal",
            code="RTO-DL-RENEW",
            description="Renewal of non-transport and transport category driving licenses",
            is_active=True,
            department_id=dept_rto.id,
            platform_id=plat_digilocker.id,
        )
        svc_inc = Service(
            name="Income & Assets Certificate",
            code="REV-INC-CERT",
            description="Tehsildar issued annual income certificate for quota reservations",
            is_active=True,
            department_id=dept_rev.id,
            platform_id=plat_mahabhulekh.id,
        )
        db.add_all([svc_sch, svc_dbt, svc_rc, svc_dl, svc_inc])
        db.flush()

        print("Seeding Rich Real-World Service Applications...")
        apps_data = [
            ("SCH-10291", citizen_users[0].id, svc_sch.id, ApplicationStatus.APPROVED, "Verified via DigiLocker marksheet and PFMS bank validation."),
            ("SCH-10304", citizen_users[1].id, svc_sch.id, ApplicationStatus.UNDER_REVIEW, "Aadhaar e-KYC matched. SAMARTH college admission verification pending."),
            ("SCH-10318", citizen_users[4].id, svc_sch.id, ApplicationStatus.SUBMITTED, "Submitted with bonafide certificate and income affidavit."),
            ("FRM-20140", citizen_users[2].id, svc_dbt.id, ApplicationStatus.UNDER_REVIEW, "Land holding 2.4 acres 7/12 extract cross-verified with Mahabhulekh."),
            ("FRM-20155", citizen_users[9].id, svc_dbt.id, ApplicationStatus.APPROVED, "DBT payment of Rs 6,000 cleared to Bank of Maharashtra A/C."),
            ("FRM-20162", citizen_users[7].id, svc_dbt.id, ApplicationStatus.REJECTED, "Land registry area mismatch (claimed 5.0 acres, registry shows 1.2 acres)."),
            ("REV-30411", citizen_users[3].id, svc_inc.id, ApplicationStatus.APPROVED, "Digital Income Certificate issued with QR-code cryptographic signature."),
            ("REV-30422", citizen_users[5].id, svc_inc.id, ApplicationStatus.SUBMITTED, "Application under preliminary Tahsil clerk scrutiny."),
            ("REV-30435", citizen_users[6].id, svc_inc.id, ApplicationStatus.UNDER_REVIEW, "ITR Form 16 verification request dispatched to Income Tax mesh gateway."),
            ("RTO-40912", citizen_users[1].id, svc_dl.id, ApplicationStatus.APPROVED, "Smart driving license renewed. Speed Post tracking #EM9928172IN."),
            ("RTO-40925", citizen_users[8].id, svc_dl.id, ApplicationStatus.UNDER_REVIEW, "Biometric signature validated. Awaiting RTO officer approval."),
            ("PDS-50110", citizen_users[6].id, svc_rc.id, ApplicationStatus.APPROVED, "Ration family quota successfully mapped from Pune to Nashik district."),
            ("PDS-50122", citizen_users[11].id, svc_rc.id, ApplicationStatus.SUBMITTED, "Inter-district migration certificate attached via DigiLocker."),
            ("PDS-50134", citizen_users[12].id, svc_rc.id, ApplicationStatus.UNDER_REVIEW, "Verification with FPS Fair Price Shop biometrics in progress."),
            ("SCH-10340", citizen_users[13].id, svc_sch.id, ApplicationStatus.APPROVED, "Approved under Scheduled Caste Technical Education scholarship fund."),
            ("FRM-20188", citizen_users[14].id, svc_dbt.id, ApplicationStatus.SUBMITTED, "Crop damage input subsidy application for kharif season."),
            ("REV-30450", citizen_users[10].id, svc_inc.id, ApplicationStatus.APPROVED, "Annual income under Rs 1,50,000 certified by Tehsildar Rajesh Sharma."),
            ("RTO-40938", citizen_users[3].id, svc_dl.id, ApplicationStatus.APPROVED, "Commercial heavy vehicle badge renewed."),
        ]

        app_objects = []
        for ref_id, cit_id, s_id, st, rem in apps_data:
            app_objects.append(
                ServiceApplication(
                    reference_id=ref_id,
                    citizen_id=cit_id,
                    service_id=s_id,
                    status=st,
                    remarks=rem,
                )
            )

        db.add_all(app_objects)
        db.flush()

        print("Seeding Data Share Consents...")
        consents_data = [
            ("Aadhaar e-KYC Verification for Post-Matric Scholarship", ConsentStatus.GRANTED, plat_uidai.id, plat_samarth.id, citizen_users[0].id, 365),
            ("Academic Marks & Enrolment Data Exchange", ConsentStatus.GRANTED, plat_samarth.id, plat_pfms.id, citizen_users[0].id, 180),
            ("Land Title & 7/12 Extract Access for Farmer Subsidy DBT", ConsentStatus.GRANTED, plat_mahabhulekh.id, plat_pfms.id, citizen_users[2].id, 180),
            ("Tax Return Verification for Income Certificate", ConsentStatus.GRANTED, plat_gstn.id, plat_mahabhulekh.id, citizen_users[3].id, 90),
            ("Ration Quota Linkage to Aadhaar Identity", ConsentStatus.GRANTED, plat_uidai.id, plat_digilocker.id, citizen_users[6].id, 365),
            ("Old Driving License Data Retrieval from Sarathi", ConsentStatus.REVOKED, plat_digilocker.id, plat_uidai.id, citizen_users[1].id, 60),
        ]

        c_objects = []
        for purp, c_st, src_id, tgt_id, cit_id, days in consents_data:
            c_objects.append(
                DataShareConsent(
                    purpose=purp,
                    status=c_st,
                    source_platform_id=src_id,
                    target_platform_id=tgt_id,
                    citizen_id=cit_id,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=days),
                )
            )

        db.add_all(c_objects)
        db.flush()

        print("Seeding Documents...")
        d1 = Document(
            title="Aadhaar Card - Ramesh Patil",
            doc_type="Aadhaar Card",
            file_path="virtual://docs/aadhaar_ramesh.pdf",
            mime_type="application/pdf",
            owner_id=citizen_users[0].id,
            application_id=app_objects[0].id,
            is_verified=True,
            verification_score=0.98,
            fraud_risk_level="LOW",
            extracted_text="GOVERNMENT OF INDIA - UNIQUE IDENTIFICATION AUTHORITY OF INDIA - Ramesh Patil - 8492",
            extracted_entities='{"name": "Ramesh Patil", "id": "XXXX XXXX 8492"}',
        )
        d2 = Document(
            title="7/12 Land Record Extract - Priya Kulkarni",
            doc_type="Land Record (7/12 Extract)",
            file_path="virtual://docs/7_12_pune_priya.pdf",
            mime_type="application/pdf",
            owner_id=citizen_users[2].id,
            application_id=app_objects[3].id,
            is_verified=True,
            verification_score=0.94,
            fraud_risk_level="LOW",
            extracted_text="MAHARASHTRA STATE LAND RECORDS - VILLAGE: HAVELI - GAT NO: 142/2 - ACRES: 2.4",
            extracted_entities='{"owner": "Priya Kulkarni", "gat_no": "142/2", "acres": "2.4"}',
        )
        db.add_all([d1, d2])
        db.flush()

        print("Seeding Audit Logs...")
        logs = [
            AuditLog(
                action="SYSTEM_INIT",
                entity_type="mesh_kernel",
                entity_id="0",
                details="SIH26129 Inter-Governmental Mesh API initialized with 6 interconnected nodes.",
                actor_id=admin.id,
            ),
            AuditLog(
                action="CONSENT_GRANTED",
                entity_type="data_share_consent",
                entity_id=str(c_objects[0].id),
                details=f"Consent granted for Aadhaar eKYC -> SAMARTH by {citizen_users[0].full_name}",
                actor_id=citizen_users[0].id,
            ),
            AuditLog(
                action="APPLICATION_CREATED",
                entity_type="service_application",
                entity_id=str(app_objects[0].id),
                details=f"Application {app_objects[0].reference_id} created for {svc_sch.name}",
                actor_id=citizen_users[0].id,
            ),
            AuditLog(
                action="DOCUMENT_VERIFIED",
                entity_type="document",
                entity_id=str(d1.id),
                details="Aadhaar Card verified with EasyOCR + LayoutLMv3 composite score 0.98",
                actor_id=officer1.id,
            ),
            AuditLog(
                action="APPLICATION_APPROVED",
                entity_type="service_application",
                entity_id=str(app_objects[0].id),
                details="Post-Matric Scholarship approved by Tehsildar Rajesh Sharma",
                actor_id=officer1.id,
            ),
        ]
        db.add_all(logs)

        db.commit()
        print(f"Database seeded successfully with {len(app_objects)} applications, {len(c_objects)} consents, and {len(citizen_users)} citizens!")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    force_seed = "--force" in sys.argv
    seed_database(force=force_seed)
