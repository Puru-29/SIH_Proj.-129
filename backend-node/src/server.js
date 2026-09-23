import "dotenv/config";
import express from "express";
import cors from "cors";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import mongoose from "mongoose";
import { AuditLog, Application, Consent, DataMapping, Exception, Integration, Service, User, Workflow } from "./models.js";
import { runScholarshipWorkflow } from "./workflow.js";

const app = express();
const port = Number(process.env.PORT || 8001);
const secret = process.env.JWT_SECRET || "govflow-development-secret";
const memory = new Map();
let memoryMode = false;
app.use(cors({ origin: true, credentials: true }));
app.use(express.json());

const nextId = (name) => (memory.get(`counter:${name}`) || Date.now()) + 1;
const setCounter = (name, id) => memory.set(`counter:${name}`, id);
async function all(model, query = {}) { return memoryMode ? [...(memory.get(model.modelName) || [])].filter((item) => Object.entries(query).every(([k, v]) => item[k] === v)) : model.find(query).sort({ createdAt: -1 }).lean(); }
async function create(model, data) { const id = nextId(model.modelName); setCounter(model.modelName, id); const item = { ...data, id, createdAt: new Date(), updatedAt: new Date() }; if (memoryMode) { memory.set(model.modelName, [...(memory.get(model.modelName) || []), item]); return item; } return model.create(item); }
async function findOne(model, query) { return memoryMode ? (await all(model, query))[0] : model.findOne(query).lean(); }
async function save(model, query, patch) { const item = await findOne(model, query); if (!item) return null; Object.assign(item, patch, { updatedAt: new Date() }); if (memoryMode) { memory.set(model.modelName, (memory.get(model.modelName) || []).map((row) => row.id === item.id ? item : row)); return item; } return model.findOneAndUpdate(query, patch, { new: true }).lean(); }
const publicUser = (user) => ({ id: user.id, full_name: user.full_name, email: user.email, phone: user.phone || null, role: user.role, is_active: true, created_at: user.createdAt || new Date().toISOString() });
const tokenFor = (user) => jwt.sign({ id: user.id, role: user.role, email: user.email }, secret, { expiresIn: "8h" });
function auth(req, res, next) { const value = req.headers.authorization || ""; try { req.user = jwt.verify(value.replace("Bearer ", ""), secret); next(); } catch { res.status(401).json({ detail: "Authentication required" }); } }
const audit = (action, entity_type, entity_id, details, actor_id) => create(AuditLog, { action, entity_type, entity_id: String(entity_id), details, actor_id });

app.get("/health", (_req, res) => res.json({ status: "ok", app: "GovFlow Node API", database: memoryMode ? "memory-fallback" : "mongodb" }));
app.post("/api/v1/auth/signup", async (req, res) => { const { full_name, email, password, phone, role = "citizen", department } = req.body; if (!full_name || !email || !password) return res.status(400).json({ detail: "full_name, email and password are required" }); if (await findOne(User, { email: email.toLowerCase() })) return res.status(409).json({ detail: "Email is already registered" }); const roles = ["citizen", "officer", "admin", "developer", "operator", "auditor"]; const user = await create(User, { full_name, email: email.toLowerCase(), phone, password_hash: await bcrypt.hash(password, 12), role: roles.includes(role) ? role : "citizen", department }); await audit("user.registered", "User", user.id, "Account created", user.id); res.status(201).json({ access_token: tokenFor(user), token_type: "bearer", user: publicUser(user) }); });
app.post("/api/v1/auth/login", async (req, res) => { const user = await findOne(User, { email: String(req.body.email || "").toLowerCase() }); if (!user || !(await bcrypt.compare(req.body.password || "", user.password_hash))) return res.status(401).json({ detail: "Invalid email or password" }); await audit("user.login", "User", user.id, "Authenticated", user.id); res.json({ access_token: tokenFor(user), token_type: "bearer", user: publicUser(user) }); });
app.get("/api/v1/auth/me", auth, async (req, res) => { const user = await findOne(User, { id: req.user.id }); user ? res.json(publicUser(user)) : res.status(404).json({ detail: "User not found" }); });
app.get("/api/v1/services", async (_req, res) => res.json(await all(Service, { is_active: true })));
app.post("/api/v1/services", auth, async (req, res) => res.status(201).json(await create(Service, req.body)));
app.get("/api/v1/workflows", async (_req, res) => res.json(await all(Workflow)));
app.post("/api/v1/workflows", auth, async (req, res) => res.status(201).json(await create(Workflow, req.body)));
app.get("/api/v1/integrations", async (_req, res) => res.json(await all(Integration)));
app.post("/api/v1/integrations", auth, async (req, res) => res.status(201).json(await create(Integration, req.body)));
app.get("/api/v1/platforms", async (_req, res) => res.json((await all(Integration)).map((item) => ({ ...item, slug: item.connector, api_version: "v1", description: "GovFlow sandbox connector", department_id: 1 }))));
app.get("/api/v1/applications", auth, async (req, res) => { const query = req.user.role === "citizen" ? { citizen_id: req.user.id } : {}; res.json(await all(Application, query)); });
const applicationQuery = (value) => /^\d+$/.test(value) ? { id: Number(value) } : { reference_id: value };
async function nextApplicationReference(prefix) {
	for (let attempt = 0; attempt < 10; attempt += 1) {
		const candidate = `${prefix}-${Math.floor(100000 + Math.random() * 900000)}`;
		if (!(await findOne(Application, { reference_id: candidate }))) return candidate;
	}
	throw new Error("Unable to allocate a unique application ID");
}
app.post("/api/v1/applications", auth, async (req, res) => { const citizenId = req.user.role === "citizen" ? req.user.id : req.body.citizen_id; const service = await findOne(Service, { id: Number(req.body.service_id) }); if (!service) return res.status(404).json({ detail: "Service not found" }); const prefix = service.code || "APP"; const application = await create(Application, { reference_id: await nextApplicationReference(prefix), citizen_id: citizenId, service_id: service.id, service_name: service.name, location: req.body.location || "Nashik, Maharashtra", status: "submitted", form_data: req.body.form_data || {}, remarks: req.body.remarks || "" }); const consent = await create(Consent, { application_id: application.id, citizen_id: citizenId, purpose: `Eligibility verification for ${service.name}`, source_platform_name: "Citizen Portal", target_platform_name: "GovFlow Government Mesh", status: req.body.consent ? "granted" : "revoked" }); if (req.body.consent) { const workflow = await runScholarshipWorkflow(application); const updated = await save(Application, { id: application.id }, { workflow, status: "under_review", remarks: "Application submitted to Government Staff workflow" }); await audit("application.submitted", "Application", application.reference_id, "Citizen application submitted", citizenId); return res.status(201).json({ ...updated, consent_id: consent.id }); } res.status(400).json({ detail: "Consent is required before submission" }); });
app.get("/api/v1/applications/track/:reference", async (req, res) => { const item = await findOne(Application, { reference_id: req.params.reference }); item ? res.json(item) : res.status(404).json({ detail: "Application not found" }); });
app.get("/api/v1/applications/:id", auth, async (req, res) => { const item = await findOne(Application, applicationQuery(req.params.id)); item ? res.json(item) : res.status(404).json({ detail: "Application not found" }); });
app.patch("/api/v1/applications/:id/status", auth, async (req, res) => { const item = await save(Application, { id: Number(req.params.id) }, { status: req.body.status, remarks: req.body.remarks }); item ? res.json(item) : res.status(404).json({ detail: "Application not found" }); });
app.get("/api/v1/applications/:id/workflow", auth, async (req, res) => { const item = await findOne(Application, applicationQuery(req.params.id)); item ? res.json(item.workflow || []) : res.status(404).json({ detail: "Application not found" }); });
app.get("/api/v1/consents", auth, async (req, res) => res.json(await all(Consent, req.user.role === "citizen" ? { citizen_id: req.user.id } : {})));
app.post("/api/v1/consents", auth, async (req, res) => res.status(201).json(await create(Consent, { ...req.body, citizen_id: req.user.role === "citizen" ? req.user.id : req.body.citizen_id })));
app.post("/api/v1/consents/:id/revoke", auth, async (req, res) => { const item = await save(Consent, { id: Number(req.params.id) }, { status: "revoked" }); item ? res.json(item) : res.status(404).json({ detail: "Consent not found" }); });
app.get("/api/v1/audit-logs", auth, async (req, res) => { const logs = await all(AuditLog, req.query.entity_id ? { entity_id: String(req.query.entity_id) } : {}); res.json(logs.slice(0, Number(req.query.limit || 50))); });
app.get("/api/v1/exceptions", auth, async (_req, res) => res.json(await all(Exception)));
app.get("/api/v1/data-mapping", auth, async (_req, res) => res.json(await all(DataMapping)));
app.post("/api/v1/data-mapping", auth, async (req, res) => res.status(201).json(await create(DataMapping, req.body)));
app.get("/api/v1/stats/dashboard", auth, async (_req, res) => { const applications = await all(Application); const consents = await all(Consent, { status: "granted" }); const auditLogs = await all(AuditLog); const services = await all(Service); return res.json({ total_applications: applications.length, applications_by_status: Object.fromEntries(["submitted", "under_review", "approved", "rejected"].map((status) => [status, applications.filter((item) => item.status === status).length])), total_mesh_nodes: (await all(Integration)).length, active_mesh_nodes: (await all(Integration)).filter((item) => item.status === "active").length, total_departments: 1, total_services: services.length, total_consents_granted: consents.length, total_audit_events: auditLogs.length, total_documents_verified: applications.length, api_success_rate: 99.2, avg_latency_ms: 42, fraud_anomalies_detected: 0, system_status: "operational", timestamp: Date.now() }); });
app.get("/api/v1/monitoring", auth, async (_req, res) => res.json({ status: "operational", api_success_rate: 99.2, avg_latency_ms: 42, connectors: (await all(Integration)).map((item) => ({ name: item.name, status: item.status })) }));
async function seed() {
	if (!(await findOne(Service, { code: "SCH" }))) {
		await create(Service, { name: "Post-Matric Scholarship", code: "SCH", description: "Merit-cum-means scholarship", department_id: 1, workflow_id: 1, is_active: true });
		await create(Workflow, { name: "Scholarship Eligibility", service_code: "SCH", stages: [{ key: "authentication", label: "Authentication", connector: "Aadhaar" }, { key: "consent", label: "Consent", connector: "GovFlow" }, { key: "income", label: "Income verification", connector: "Revenue" }, { key: "education", label: "Education verification", connector: "Education" }, { key: "bank", label: "Bank verification", connector: "PFMS" }] });
		for (const [name, connector] of [["Aadhaar", "aadhaar"], ["Education", "education"], ["Revenue", "revenue"], ["Land Records", "landRecords"], ["PFMS", "pfms"]]) await create(Integration, { name, connector, status: "active", base_url: "sandbox://govflow" });
	}
	const additionalServices = [
		["PMS", "Pre-Matric Scholarship", "Scholarship support for students in classes 1 to 10"],
		["INC", "Income Certificate", "Revenue certificate issuance and verification"],
		["RES", "Residence Certificate", "State residence certificate application"],
		["PEN", "Senior Citizen Pension", "Pension eligibility and life certificate workflow"],
		["SUB", "Direct Benefit Subsidy", "Consent-bound subsidy enrolment"],
		["FRM", "Farmer Assistance", "Agriculture assistance and land record verification"],
	];
	for (const [code, name, description] of additionalServices) {
		if (!(await findOne(Service, { code }))) await create(Service, { name, code, description, department_id: 1, workflow_id: 1, is_active: true });
	}
	if (!(await findOne(User, { email: "admin@govflow.in" }))) await create(User, { full_name: "GovFlow System Administrator", email: "admin@govflow.in", password_hash: await bcrypt.hash("Admin@123", 12), role: "admin", department: "Inter-Governmental Mesh" });
	const admin = await findOne(User, { email: "admin@govflow.in" });
	if (!(await findOne(Application, { reference_id: "SCH-10291" })) && admin) {
		const application = await create(Application, { reference_id: "SCH-10291", citizen_id: admin.id, service_id: 1, service_name: "Post-Matric Scholarship", location: "Nashik, Maharashtra", status: "under_review", form_data: { name: "Ramesh Patil", institution: "KTHM College, Nashik", income: "180000", citizen_id: "CIT-900100" }, remarks: "Education verification is in progress", workflow: [
			{ key: "submitted", label: "Application Submitted", status: "completed", detail: "Application received by GovFlow Citizen Gateway", attempts: 1, updated_at: new Date("2026-09-12T08:30:00Z") },
			{ key: "authentication", label: "Authentication", status: "completed", detail: "Aadhaar identity matched", attempts: 1, updated_at: new Date("2026-09-12T08:31:00Z") },
			{ key: "consent", label: "Consent check", status: "completed", detail: "Consent granted for eligibility verification", attempts: 1, updated_at: new Date("2026-09-12T08:32:00Z") },
			{ key: "income", label: "Income verification", status: "completed", detail: "Family income verified by Revenue Department", attempts: 1, updated_at: new Date("2026-09-12T08:35:00Z") },
			{ key: "education", label: "Education verification", status: "recovered", detail: "Timeout, retry and fallback connector recovery completed", attempts: 2, updated_at: new Date("2026-09-12T10:44:00Z") },
			{ key: "bank", label: "Bank verification", status: "pending", detail: "Waiting for PFMS account validation", attempts: 0, updated_at: new Date("2026-09-12T10:45:00Z") },
		] });
		await create(Consent, { application_id: application.id, citizen_id: admin.id, purpose: "Verify academic eligibility for post-matric scholarship", source_platform_name: "Education Department", target_platform_name: "SAMARTH Education API", status: "granted", expires_at: new Date("2026-12-12T00:00:00Z") });
		await create(Consent, { application_id: application.id, citizen_id: admin.id, purpose: "Means test for scholarship income ceiling", source_platform_name: "Revenue Department", target_platform_name: "Income Tax Verification", status: "granted", expires_at: new Date("2026-12-12T00:00:00Z") });
		await create(Exception, { application_id: application.id, stage: "Education Verification", system: "SAMARTH Education API", code: "HTTP 504", message: "Upstream gateway timeout while fetching enrolment record", status: "recovered", recovery: "Retry followed by state education mirror fallback", attempts: 2 });
		await audit("application.submitted", "Application", application.reference_id, "Scholarship application submitted", admin.id);
		await audit("workflow.recovered", "Application", application.reference_id, "Education verification recovered through fallback connector", admin.id);
	}
}
try { await mongoose.connect(process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/govflow", { serverSelectionTimeoutMS: 1200 }); console.log("Connected to MongoDB"); } catch (error) { if (process.env.ALLOW_MEMORY_FALLBACK === "false") throw error; memoryMode = true; console.warn("MongoDB unavailable; using development memory fallback. Set MONGODB_URI for persistence."); }
await seed();
app.listen(port, "127.0.0.1", () => console.log(`GovFlow Node API listening on http://127.0.0.1:${port}`));