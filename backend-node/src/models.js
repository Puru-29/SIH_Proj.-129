import mongoose from "mongoose";

const options = { timestamps: true, versionKey: false };
const userSchema = new mongoose.Schema({ id: Number, full_name: String, email: { type: String, unique: true }, phone: String, password_hash: String, role: { type: String, enum: ["citizen", "officer", "admin", "developer", "operator", "auditor"], default: "citizen" }, department: String }, options);
const applicationSchema = new mongoose.Schema({ id: Number, reference_id: { type: String, unique: true }, citizen_id: Number, service_id: Number, service_name: String, location: String, status: { type: String, default: "submitted" }, form_data: mongoose.Schema.Types.Mixed, remarks: String, workflow: [{ key: String, label: String, status: String, detail: String, attempts: Number, updated_at: Date }] }, options);
const serviceSchema = new mongoose.Schema({ id: Number, name: String, code: String, description: String, department_id: Number, workflow_id: Number, is_active: { type: Boolean, default: true } }, options);
const workflowSchema = new mongoose.Schema({ id: Number, name: String, service_code: String, stages: [{ key: String, label: String, connector: String }] }, options);
const integrationSchema = new mongoose.Schema({ id: Number, name: String, connector: String, status: String, base_url: String }, options);
const consentSchema = new mongoose.Schema({ id: Number, application_id: Number, citizen_id: Number, purpose: String, status: { type: String, default: "granted" }, source_platform_name: String, target_platform_name: String, expires_at: Date }, options);
const dataMappingSchema = new mongoose.Schema({ id: Number, integration_id: Number, source: String, target: String, status: String }, options);
const exceptionSchema = new mongoose.Schema({ id: Number, application_id: Number, stage: String, system: String, code: String, message: String, status: String, recovery: String, attempts: Number }, options);
const auditLogSchema = new mongoose.Schema({ id: Number, action: String, entity_type: String, entity_id: String, details: String, actor_id: Number }, options);

export const User = mongoose.model("User", userSchema);
export const Application = mongoose.model("Application", applicationSchema);
export const Service = mongoose.model("Service", serviceSchema);
export const Workflow = mongoose.model("Workflow", workflowSchema);
export const Integration = mongoose.model("Integration", integrationSchema);
export const Consent = mongoose.model("Consent", consentSchema);
export const DataMapping = mongoose.model("DataMapping", dataMappingSchema);
export const Exception = mongoose.model("Exception", exceptionSchema);
export const AuditLog = mongoose.model("AuditLog", auditLogSchema);