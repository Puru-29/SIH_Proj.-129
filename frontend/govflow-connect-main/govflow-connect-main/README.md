# GovFlow Connect

Build a complete frontend web application from scratch for SIH 26129 — GovFlow.

GovFlow is a Government Interoperability + Workflow Orchestration Platform.

The goal is NOT to make another UMANG/API marketplace/government portal. 

Build GovFlow as a ONE-STEP-AHEAD solution that demonstrates capabilities existing platforms do not provide together.

Use React + Tailwind CSS. Frontend only for now. I will connect my MERN backend later. Use realistic mock data + localStorage for functionality.

DESIGN:

Use a premium GovTech/enterprise theme:

- Dark navy sidebar

- Light background

- Blue + teal accents

- Rounded cards

- Subtle borders/shadows

- Clean modern typography

- Professional charts and workflow visualizations

- Responsive desktop/tablet/mobile

- Do NOT make it look like a traditional government portal or generic admin dashboard.

BUILD THE COMPLETE APP, NOT ONLY A DASHBOARD.

PAGES:

Landing, Login, Signup, Forgot Password, OTP, Dashboard, Services, Workflows, Workflow Builder, Applications, Departments, Integrations, Data Mapping, Consent, Monitoring, Exceptions, Audit Logs, Reports, Users, Notifications, Profile and Settings.

CORE DIFFERENTIATORS — MAKE THESE THE HEART OF THE PRODUCT:

1. VISUAL WORKFLOW ORCHESTRATOR

Show complete cross-department workflows visually.

Allow users to create/edit/connect workflow nodes.

Example:

Citizen → Authentication → Consent → Income → Education → Bank → Eligibility → Approval → Completed

Add a working “Run Demo Workflow” that animates each stage.

2. UNIVERSAL DATA/SCHEMA MAPPER

Show different systems using different formats:

REST/JSON, SOAP/XML, Legacy Systems

→ GovFlow Normalization Layer

→ Destination System

Example:

citizen_name → fullName

mobile_no → phone

dob → dateOfBirth

Include Auto Map, Validate and Save Mapping interactions.

3. AUTOMATIC EXCEPTION RECOVERY

Do more than display API errors.

Create:

Failed → Detect → Retry → Recover → Continue Workflow

Allow Retry to actually change the frontend state.

4. UNIFIED CITIZEN JOURNEY

One application ID should show the complete journey across every department, system, consent request, workflow stage and exception.

5. CONSENT-CENTRIC DATA SHARING

Show:

Who requested the data

What data

Why it is needed

Which department receives it

Consent status

Expiry

Revocation

6. REAL-TIME-STYLE INTEROPERABILITY MONITORING

Show connected systems with:

Healthy / Degraded / Down

API success rate

Latency

Uptime

Failures

Active workflows

7. LOCATION-AWARE GOVERNANCE

Global location selector:

Country → State → District → City

Use mock locations such as Nashik, Pune, Mumbai, Delhi, Bengaluru and Hyderabad.

Changing location should update relevant mock:

- Departments

- Services

- Applications

- Workflows

- Integrations

- Monitoring

- Reports

8. DEVELOPER INTEGRATION WORKSPACE

Provide a professional interface to view:

- Connected systems

- API status

- Endpoints

- Request/response preview

- Schemas

- Authentication

- Logs

- Integration health

MAIN DEMO:

Create a Scholarship Application workflow.

When “Run Demo” is clicked:

Citizen Request

↓

Authentication ✓

↓

Consent ✓

↓

Income Verification ✓

↓

Education Verification ⚠

↓

Automatic Retry

↓

Education Verification ✓

↓

Bank Verification ✓

↓

Eligibility ✓

↓

Approval ✓

↓

Completed ✓

While running, show:

- Current workflow stage

- Department involved

- System contacted

- Data exchanged

- API status

- Processing time

- Audit event

This should be the main SIH judging demonstration.

AUTHENTICATION:

Create a polished login/signup/OTP experience with:

Email, Mobile/OTP, Forgot Password, Role Selection, Validation, Loading/Error/Success states and Logout.

Roles:

Admin, Department Officer, Developer, Operator, Auditor.

Add frontend route protection.

DASHBOARD:

Show:

Active Services

Running Workflows

Connected Systems

Applications

API Success Rate

Processing Time

System Health

Exceptions

Recent Activity

Department Performance

Workflow Analytics

SERVICES:

Create service catalog + detail pages for:

Scholarship, Income Certificate, Residence Certificate, Pension, Subsidy, Business Registration and Farmer Assistance.

APPLICATIONS:

List + detail page with:

Citizen, Service, Location, Status, Current Stage, Workflow, Departments, Consent, Exceptions and Audit Timeline.

DEPARTMENTS:

Show department locations, services, connected systems, health, applications and response time.

INTEGRATIONS:

Support mock REST/JSON, SOAP/XML and Legacy systems with detailed health/log/schema views.

MONITORING:

Charts for uptime, latency, API success/failure, workflow health and system activity.

EXCEPTIONS:

Show failures and provide working Retry / Escalate / View Error actions.

AUDIT LOGS:

Show complete traceability of every workflow, data access, consent action, API call and status change.

REPORTS:

Professional analytics for applications, workflows, department performance, API reliability, processing time and exceptions.

GLOBAL SEARCH:

Search Applications, Services, Departments, Workflows, Integrations and Users.

NOTIFICATIONS:

Workflow completion, API failure, consent updates, new applications and system alerts.

Use reusable components and realistic Indian government mock data.

FINAL PRODUCT PRINCIPLE:

Do NOT try to compete by having more basic pages.

Compete through:

Interoperability

+ Workflow Orchestration

+ Intelligent Data Mapping

+ Exception Recovery

+ Unified Citizen Journey

+ Consent

+ Monitoring

+ Location Intelligence

+ Developer Integration Workspace

The final application should make a judge immediately understand:

“Existing platforms provide access to government services. GovFlow connects the systems behind those services and intelligently orchestrates the complete cross-department journey.”

Make every route, button, CTA, filter, form, modal and major interaction functional with frontend state.

Do not leave dead pages or placeholder screens.

Build everything from scratch, test all routes, fix errors, ensure responsive design, and make the final frontend hackathon-ready and visually impressive.

make this in 10credits please

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/3a447174-976b-42dd-931c-1133779ee1e4).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
