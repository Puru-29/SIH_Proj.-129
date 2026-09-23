import urllib.request
import urllib.error
import json
import sys

BASE = "http://127.0.0.1:8000"
results = []


def test(name, url, method="GET", data=None, token=None):
    try:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(f"{BASE}{url}", data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=10) as res:
            res_data = json.loads(res.read().decode())
            results.append((name, True, f"Status {res.status}", res_data))
            return res_data
    except Exception as e:
        results.append((name, False, str(e), None))
        return None


print("=== TESTING BACKEND ON http://127.0.0.1:8000 ===\n")

# 1. Health
test("1. Health Check", "/health")

# 2. System Info
test("2. System Info", "/api/v1/info")

# 3. ML Status
test("3. ML Engines Status", "/api/v1/ml/status")

# 4. Auth Login
login_res = test(
    "4. Auth Login (Admin)",
    "/api/v1/auth/login",
    method="POST",
    data={"email": "admin@govflow.in", "password": "Admin@123"},
)
token = login_res.get("access_token") if login_res else None

# 5. Get Current User (/me)
test("5. Current User Profile (/me)", "/api/v1/auth/me", token=token)

# 6. Departments
test("6. List Departments", "/api/v1/departments")

# 7. Platforms (Mesh Nodes)
test("7. List Mesh Platforms", "/api/v1/platforms")

# 8. Services
test("8. List Services", "/api/v1/services")

# 9. Applications
test("9. List Applications", "/api/v1/applications")

# 10. Consents
test("10. List Consents", "/api/v1/consents")

# 11. Dashboard Stats
test("11. Dashboard Stats", "/api/v1/stats/dashboard")

# 12. AI Document Verification
test(
    "12. AI Document Verification",
    "/api/v1/documents/upload-and-verify",
    method="POST",
    data={
        "title": "Test Aadhaar Verification",
        "doc_type": "Aadhaar Card",
        "owner_id": 1,
        "document_text": "GOVERNMENT OF INDIA - UNIQUE IDENTIFICATION AUTHORITY OF INDIA - Aarav Patel - 4892 1948 8492",
        "citizen_full_name": "Aarav Patel",
        "citizen_aadhaar_last4": "8492",
        "claimed_income": 120000.0,
        "mesh_income": 120000.0,
        "claimed_land_acres": 2.4,
        "mesh_land_acres": 2.4,
    },
)

print("\n" + "=" * 65)
all_pass = True
for name, ok, msg, data in results:
    status_icon = "[PASS]" if ok else "[FAIL]"
    if not ok:
        all_pass = False
    print(f"{status_icon} {name}: {msg}")
    if ok and name == "3. ML Engines Status" and data:
        print(f"       -> {data.get('ready_count', 6)}/{data.get('total_engines', 6)} AI Engines Ready")
    elif ok and name == "11. Dashboard Stats" and data:
        print(
            f"       -> Total Applications: {data.get('total_applications')}, Active Nodes: {data.get('active_mesh_nodes')}, Success Rate: {data.get('api_success_rate')}%"
        )
    elif ok and name == "12. AI Document Verification" and data:
        pipeline = data.get("ai_pipeline_result", {})
        print(
            f"       -> Verdict: {pipeline.get('overall_verdict')}, Trust: {pipeline.get('confidence_score')}, Risk: {pipeline.get('risk_level')}"
        )

print("=" * 65)
if all_pass:
    print(">>> ALL 12 BACKEND TESTS PASSED SUCCESSFULLY! <<<")
else:
    print(">>> SOME TESTS FAILED - Check details above. <<<")
