# CampusPulse

**A Student Success and Intervention Orchestration Engine**

CampusPulse is a hackathon prototype for PS6. It aims to turn fragmented student-success signals into explainable, consent-aware, human-reviewed support workflows with accountable follow-up and measured outcomes.

> The core differentiator is the intervention workflow, not a risk score or dashboard alone.

## Problem

Institutions may hold attendance, academic, participation, fee, skills, and faculty-feedback data but fail to coordinate timely support. CampusPulse is designed to connect those signals to an appropriate support action, a responsible stakeholder, a deadline, follow-up evidence, and an outcome record.

## Core Workflow

1. Review a synthetic student's permitted Student 360 view.
2. Inspect explainable review-priority indicators.
3. Review a context-aware support recommendation.
4. Approve, edit, override, or decline the recommendation.
5. Assign an intervention owner/team and deadline.
6. Record timestamped follow-up evidence.
7. Record outcome measurements when available.
8. Review the resulting cohort-level analytics.

## Planned Features

- Student 360 across six data domains
- Explainable early-warning indicators
- Purpose-specific consent representation
- Role-aware information access
- Context-aware support recommendations
- Human review and manual override
- Intervention assignments, deadlines, and escalation
- Follow-up event history
- Outcome measurement
- Cohort-level analytics
- Synthetic demonstration data

## Technology Stack

**Frontend:** React, Vite, TypeScript, Tailwind CSS, Recharts

**Backend:** Python 3.11, FastAPI, Pydantic, SQLAlchemy, Uvicorn

**Database:** SQLite

**Testing:** Pytest and HTTPX

**Design source:** Google Stitch design to be supplied by the project owner.

Optional AI integrations and additional infrastructure will be considered only after the core workflow works reliably.

## Repository Layout

    CampusPulse-Fresh/
    ├── backend/
    │   ├── app/
    │   │   ├── api/
    │   │   │   └── routes/
    │   │   ├── core/
    │   │   ├── db/
    │   │   ├── models/
    │   │   ├── schemas/
    │   │   └── services/
    │   ├── tests/
    │   └── requirements.txt
    ├── frontend/
    ├── datasets/
    │   ├── raw/
    │   ├── processed/
    │   └── synthetic/
    ├── docs/
    └── notebooks/

The structure describes the intended project layout. Some components will be populated during subsequent implementation chapters.

## Documentation

- `docs/acceptance-checklist.md` — PS6 acceptance requirements
- `docs/demo-scenario.md` — synthetic hero-student workflow
- `docs/role-permission-matrix.md` — intended role permissions
- `docs/data-model.md` — initial database entities and relationships
- `docs/privacy-and-consent-rules.md` — privacy and consent behavior
- `docs/api-contract.md` — planned endpoint contracts
- `docs/architecture.md` — architecture and implementation principles

## Development Environment

The project is being developed on Windows using VS Code, PowerShell, and a dedicated Conda environment named `campuspulse-fresh` with Python 3.11.

### Backend

From the project root, activate the environment:

    conda activate campuspulse-fresh

Install the backend dependencies:

    python -m pip install -r backend/requirements.txt

Run the API:

    python -m uvicorn app.main:app --app-dir backend --reload

Open the interactive API documentation:

    http://127.0.0.1:8000/docs

The exact health endpoint will be aligned with the documented `/api/health` contract during API implementation.

### Frontend

The frontend directory will be scaffolded with Vite when frontend setup begins. Once it exists, frontend installation and startup commands will be documented here.

## Responsible Design

- Use synthetic data in the prototype.
- Treat risk indicators as decision support, not diagnosis.
- Never automatically punish or discipline students based on a score.
- Do not treat missing data as negative evidence.
- Restrict financial and sensitive counselling information.
- Require human review for consequential support decisions.
- Distinguish illustrative examples from recorded outcomes.
- Avoid unsupported causal claims about intervention effectiveness.

## Project Status

The project is being built incrementally from a clean directory. The initial FastAPI and SQLite connection setup exists; the complete data model, intervention workflow, API implementation, and frontend are still planned implementation work.

## License

No license has been selected yet.


## Synthetic cohort generator

The repository includes an additive, reproducible synthetic-data generator. With the
`campuspulse-fresh` environment active:

```powershell
cd backend
python -m app.seed.seed_large_dataset --count 2000
```

The count is the target number of `CP-SYN-*` generated students (the three curated
`CP-DEMO-*` students are kept separately). The generator adds varied fictional
students with six domain signals and purpose-specific demo consent states. It does
not overwrite the curated hero scenario. Generated records are not real institutional
data or evidence of real-world outcomes.

The student directory displays ten rows per page to keep the browser responsive
when the synthetic cohort is expanded.


## Database-backed demo login

The login form verifies credentials against the SQLite `auth_users` table. On first backend startup, six local demo accounts are created automatically.

Password for all demo accounts: `CampusPulse@123`

- `hod@campuspulse.demo`
- `faculty@campuspulse.demo`
- `mentor@campuspulse.demo`
- `counsellor@campuspulse.demo`
- `finance@campuspulse.demo`
- `placement@campuspulse.demo`

Choose the matching role in the sign-in selector. These are shared local prototype credentials, not production accounts. Do not expose the demo-account endpoint or these credentials in a deployed environment. The login endpoint verifies database credentials, but the existing data APIs still use the prototype `X-Demo-Role` header and must be upgraded to enforce authenticated sessions before production use.

## Open registration and database-backed login

The login screen now supports both **Sign in** and **Create an account**. New accounts are stored in `backend/data/campuspulse.db` (`auth_users` table). Registration accepts a full name, unique email, password (8–256 characters), and one of the six supported demo roles: `hod`, `faculty`, `mentor`, `counsellor`, `finance`, or `placement`. Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes, not plaintext. Duplicate emails are rejected. After registration, the new user is signed in and routed to the workspace for the selected role.

### API endpoints
- `POST /api/auth/register` — create an account.
- `POST /api/auth/login` — verify registered credentials and selected role.

### Important prototype security limitations
- This is open registration: anyone who can reach the app can create an account and select a role, including HOD. Do not expose this prototype to the public internet.
- The API currently returns a random demo access token, but the token is not persisted/validated as a server-side session and does not yet secure every data endpoint. Existing data APIs still rely on `X-Demo-Role` headers. Do not use real student data or treat role selection as authorization.
- Before deployment, implement verified identity, server-side session/token validation, role assignment policies (especially privileged roles), rate limiting, HTTPS, CSRF/session protections as appropriate, account recovery, and audit logging.
- Demo accounts are seeded at startup for the original walkthrough. You can use registration to create your own separate accounts; keep demo credentials private and remove them before any real deployment.

Run backend from the project root:
```powershell
conda activate campuspulse
python -m uvicorn app.main:app --app-dir backend --reload
```
Run frontend in another terminal:
```powershell
cd frontend
npm ci
npm run dev
```
