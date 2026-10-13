# CampusPulse — System Architecture

## 1. Overview

CampusPulse is a consent-aware student-success and intervention orchestration platform.

It converts fragmented student-success signals into explainable, human-reviewed support workflows. The platform records who owns an intervention, when it is due, what follow-up occurred, and what outcome was measured.

**Core promise:** Don't stop at identifying a student who may need help. Coordinate the right people, track the support delivered, and record what happened next.

All demonstration student records are synthetic.

## 2. Architectural Principles

- Build a complete intervention workflow before adding optional features.
- Keep the backend monolithic for hackathon reliability.
- Persist core records in SQLite.
- Separate HTTP endpoints, business logic, database models, and API schemas.
- Enforce permissions in the backend.
- Preserve important decisions and workflow events.
- Explain risk indicators and show data-quality limitations.
- Keep financial and sensitive counselling information restricted.
- Never automatically punish or diagnose a student from a risk score.
- Treat outcome measurements as observations, not proof of causation.

## 3. Technology Stack

### Frontend
- React
- Vite
- TypeScript
- Tailwind CSS
- Recharts where useful
- Google Stitch as the intended visual design source, supplied by the user

### Backend
- Python 3.11
- FastAPI
- Pydantic
- SQLAlchemy
- Uvicorn

### Database
- SQLite for local persistent storage

### Testing and data
- Pytest
- HTTPX
- Synthetic, reproducible demonstration records
- NumPy, Pandas, and scikit-learn when required for data preparation or model evaluation

External AI services, Redis, Celery, Temporal, n8n, production authentication, and PostgreSQL are optional future enhancements, not prerequisites for the core workflow.

## 4. High-Level Architecture

Browser application
→ HTTP/JSON API
→ FastAPI routes
→ Backend services and authorization policies
→ SQLAlchemy models and sessions
→ SQLite database

The browser presents information and collects user actions. The backend validates requests, checks permissions, executes business rules, and persists changes.

The database is the source of truth for core student records, assessments, recommendations, interventions, events, and outcomes.

## 5. Backend Modules

### core/
Application configuration and shared policies.

### db/
SQLAlchemy base, database engine, session creation, and database dependencies.

### models/
Persistent entities and their relationships.

### schemas/
Validated request and response structures.

### api/routes/
HTTP endpoints for the dashboard, students, assessments, recommendations, interventions, consent, and analytics.

### services/
Business logic for:
- Student 360 aggregation
- Role and purpose authorization
- Explainable risk assessment
- Recommendation generation and review
- Intervention assignment and lifecycle transitions
- Deadlines and escalation
- Follow-up events and outcomes
- Cohort analytics

### tests/
Automated tests for data validation, permissions, risk explanations, workflow transitions, persistence, and API behavior.

## 6. Core Data Model

The initial model consists of eight core entities:

1. Student
2. StudentConsent
3. StudentSignal
4. RiskAssessment
5. Recommendation
6. Intervention
7. InterventionEvent
8. InterventionOutcome

A student can have multiple signals and assessments. Assessments can inform recommendations. Approved recommendations can lead to interventions. Interventions can accumulate timestamped events and outcome measurements.

The conceptual model is documented in `data-model.md`.

## 7. Main Application Workflow

### Stage 1 — Student signals
Collect synthetic attendance, academic, participation, fee, skills, and faculty-feedback observations.

### Stage 2 — Student 360
Aggregate the permitted profile, signals, consent information, data freshness, assessments, and active interventions.

### Stage 3 — Explainable assessment
Calculate transparent prototype review indicators. Show observed values, relevant thresholds, contributing factors, and missing-data caveats.

### Stage 4 — Recommendation
Suggest context-appropriate support and its intended stakeholder.

### Stage 5 — Human review
An authorized user approves, edits, overrides, or declines the recommendation. Relevant decisions and reasons are recorded.

### Stage 6 — Assignment and deadline
Create an intervention with a responsible owner/team, priority, and due date.

### Stage 7 — Follow-up evidence
Record a timestamped event describing the action actually performed.

### Stage 8 — Outcome
Record baseline and follow-up measurements when available, along with classification and evidence quality.

### Stage 9 — Cohort analytics
Aggregate persisted records to show workload, overdue actions, follow-up completion, and recorded outcomes.

## 8. Consent, Privacy, and Authorization

The prototype uses simulated demo roles, not production authentication.

The backend must check the caller's permitted scope, requested purpose, sensitive-field access, and relevant consent requirements.

Detailed fee information is restricted to finance-authorized workflows. Sensitive counselling notes are restricted to the counsellor. Other roles receive only the minimum coordination information required for permitted work.

Missing or stale signals are not negative evidence. Consent for one purpose does not automatically grant permission for another.

The policy documents are:
- `role-permission-matrix.md`
- `privacy-and-consent-rules.md`

## 9. API Design

The planned API uses the `/api` prefix.

Key resource groups:
- Health
- Dashboard
- Students and Student 360
- Risk assessments
- Recommendations
- Interventions and events
- Outcomes
- Consent
- Cohort analytics

The complete planned request/response contract is in `api-contract.md`.

Endpoint implementation status must be verified against the code; a documented endpoint is not necessarily an implemented endpoint.

## 10. Persistence and Event History

Core workflows must use database records rather than permanent frontend arrays.

Important actions—such as human decisions, assignments, status transitions, follow-up events, and escalations—must be persisted.

Intervention events provide a history of what happened, who recorded it, and when. Outcome records preserve measurements rather than replacing the entire history with one latest status.

## 11. Frontend Strategy

The user will supply the Google Stitch design during the frontend chapter.

The frontend must follow that design rather than introduce an unrelated visual direction. Core screens will be mapped to typed API calls and real backend data.

Planned screens include:
- Command Center
- Student 360
- Recommendation review
- Intervention workbench
- Follow-up and outcome entry
- Leadership analytics
- Optional restricted student view

Every visible control must perform its advertised action and provide appropriate loading, error, empty, and success states.

## 12. Testing Strategy

Tests will cover:
- Student 360 and required signal domains
- Missing and stale data
- Consent and role restrictions
- Explainable assessment rules
- Recommendation routing and human decisions
- Intervention status transitions
- Owner assignment, deadlines, and escalation
- Event history and follow-up proof
- Outcome calculations and evidence quality
- Cohort aggregation and denominators
- Persistence across application restarts

## 13. Limitations

The prototype uses synthetic data and configurable heuristic rules. It does not establish real-world predictive validity or causal intervention effectiveness.

Demo-role headers are not production authentication. The prototype does not provide a complete legal consent-management system, psychological diagnosis, automatic disciplinary decisions, or full institutional integration.

## 14. Definition of Success

The primary acceptance test is a complete, persisted demonstration:

Risk signal
→ explainable recommendation
→ human decision
→ assigned intervention and deadline
→ timestamped follow-up proof
→ measured outcome
→ updated cohort analytics
