# CampusPulse — API Contract

## 1. Purpose and Conventions

This document defines the planned HTTP API for the CampusPulse PS6 prototype.

- Backend: FastAPI
- Database: SQLite through SQLAlchemy
- Request/response format: JSON, except where an endpoint explicitly requires another format
- Base URL: `http://127.0.0.1:8000`
- API prefix: `/api`
- Interactive API documentation: `/docs`
- Data: synthetic demonstration records

These contracts describe the intended API. They are not claims that all endpoints have already been implemented.

## 2. Demo Identity

For the prototype, protected requests may use:

- `X-Demo-Role`: simulated role
- `X-Demo-Actor`: synthetic actor label

Supported roles:
- `faculty`
- `mentor`
- `hod`
- `counsellor`
- `finance`
- `placement`
- `student`, if the student view is implemented

Example:

    X-Demo-Role: faculty
    X-Demo-Actor: Demo Faculty 01

These headers simulate a user for the hackathon demonstration. They are not secure authentication and must never be presented as production identity verification.

The backend must centrally validate the role, permitted student scope, requested purpose, and field-level restrictions. A client-supplied role header alone is not proof of identity.

## 3. Standard Response Conventions

Successful reads return JSON objects or arrays according to the endpoint.

Successful creation returns the created resource and its identifier.

Successful updates return the updated resource or a consistent success response with the updated representation.

Timestamps should use ISO 8601 format. Dates should use `YYYY-MM-DD`.

Unknown or unavailable values must be represented explicitly. Missing data must not be silently converted to zero.

Sensitive fields must be omitted or restricted before the response is returned. Frontend hiding is not an authorization mechanism.

## 4. System

### GET /api/health

Purpose: verify that the API is running.

Example response:

    {
      "status": "healthy",
      "app": "CampusPulse",
      "version": "0.1.0"
    }

This endpoint must not require access to student records.

### GET /

Purpose: return a basic service message.

Example response:

    {
      "message": "CampusPulse API is running.",
      "docs": "/docs"
    }

## 5. Dashboard

### GET /api/dashboard

Purpose: return permitted dashboard metrics.

Planned response fields:
- `student_count`
- `review_priority_counts`
- `open_interventions`
- `overdue_interventions`
- `escalated_interventions`
- `follow_up_completion`
- `measured_outcome_count`
- `missing_or_stale_signal_count`
- `generated_at`

The backend must calculate metrics from persisted records. Values must not be permanent hardcoded frontend statistics.

The response must respect the viewer's role and permitted scope. Leadership analytics should not expose sensitive counselling notes or unnecessary financial details.

## 6. Students and Student 360

### GET /api/students

Purpose: list students within the caller's permitted scope.

Optional query parameters:
- `search`: search permitted synthetic student identifiers or names
- `cohort`: filter by cohort
- `department`: filter by department
- `review_priority`: filter by review-priority band

The backend must apply authorization before returning results.

### GET /api/students/{student_id}

Purpose: retrieve a permitted student's basic profile.

Planned response fields:
- `id`
- `synthetic_student_code`
- `name`
- `program`
- `department`
- `year_of_study`
- `cohort`

Additional fields may be returned only when allowed for the caller's role and purpose.

### GET /api/students/{student_id}/360

Purpose: return the role-appropriate Student 360 view.

Planned sections:
- `profile`
- `consent_summary`
- `signals`
- `data_quality`
- `latest_assessment`
- `recommendations`
- `interventions`
- `recent_events`

Each signal should identify its domain, name, value where available, recorded timestamp, source label, and freshness or quality status.

The response must:
- Display missing or stale data honestly.
- Restrict detailed fee information.
- Restrict sensitive counselling notes.
- Include only information required for the caller's permitted work.
- Avoid exposing restricted fields through nested objects or event notes.

The exact response shape may vary by role. Unauthorized fields must not be returned.

## 7. Risk Assessments

### POST /api/assessments

Purpose: calculate and persist a review-priority assessment for a permitted student.

Example request:

    {
      "student_id": 42,
      "purpose": "academic_support"
    }

Planned response fields:
- `id`
- `student_id`
- `score`, if applicable
- `review_priority_band`
- `factors`
- `missing_or_stale_signals`
- `rule_version`
- `assessed_at`

Each factor should explain:
- The contributing signal.
- The observed value.
- The applicable threshold or rationale.
- The contribution to the result, where applicable.

The assessment must not treat missing data as negative evidence. Scores and thresholds are prototype heuristics, not validated predictions or diagnoses.

### GET /api/students/{student_id}/assessments

Purpose: retrieve permitted assessment history for a student.

The backend must apply role and student-scope restrictions.

## 8. Recommendations

### POST /api/recommendations

Purpose: create a proposed support recommendation.

Example request:

    {
      "student_id": 42,
      "assessment_id": 1,
      "intervention_type": "academic_support",
      "rationale": "Recent attendance and assessment trends suggest that an academic check-in may be useful.",
      "intended_role": "faculty",
      "suggested_next_step": "Review pending assignments with the student.",
      "priority": "medium"
    }

`assessment_id` is optional when the recommendation is supported by another permitted workflow.

Planned response fields:
- `id`
- `student_id`
- `assessment_id`
- `intervention_type`
- `rationale`
- `intended_role`
- `suggested_next_step`
- `priority`
- `decision_status`
- `created_at`

New recommendations begin as proposed. Creation does not mean the recommendation has been approved or assigned.

### GET /api/recommendations

Purpose: list recommendations within the caller's permitted scope.

Optional filters:
- `decision_status`
- `intended_role`
- `priority`
- `student_id`

### GET /api/recommendations/{recommendation_id}

Purpose: retrieve one recommendation and its permitted evidence.

### PATCH /api/recommendations/{recommendation_id}

Purpose: record a human decision or edit a recommendation.

Example approval request:

    {
      "action": "approve",
      "reason": "Reviewed the available academic evidence."
    }

Supported actions:
- `approve`
- `edit`
- `override`
- `decline`

An edit may include revised rationale, intended role, suggested next step, or priority.

An override must record its reason. A decline must record a reason. The backend must validate the requested action, current state, permissions, and any applicable consent requirements.

A recommendation decision alone does not imply that an intervention has been assigned.

## 9. Interventions

### POST /api/interventions

Purpose: create an intervention after the appropriate human decision.

Example request:

    {
      "student_id": 42,
      "recommendation_id": 1,
      "intervention_type": "academic_support",
      "description": "Arrange an academic check-in and review pending assignments.",
      "assigned_role": "faculty",
      "assigned_owner": "Demo Faculty 01",
      "due_date": "2026-10-14",
      "priority": "medium"
    }

Planned response fields:
- `id`
- `student_id`
- `recommendation_id`
- `intervention_type`
- `description`
- `assigned_role`
- `assigned_owner`
- `due_date`
- `status`
- `priority`
- `created_at`
- `updated_at`

The backend must validate permissions, owner/team assignment, date fields, and the source recommendation when one is supplied.

### GET /api/interventions

Purpose: retrieve a permitted intervention worklist.

Optional filters:
- `status`
- `assigned_role`
- `assigned_owner`
- `student_id`
- `overdue`

Overdue status should be derived consistently from the due date and the current non-terminal status, rather than maintained as an unrelated manual flag.

### GET /api/interventions/{intervention_id}

Purpose: retrieve a permitted intervention and its current state.

### PATCH /api/interventions/{intervention_id}

Purpose: update permitted intervention fields.

Potential updates:
- Status
- Assigned owner
- Assigned role/team
- Due date
- Priority
- Description

The backend must validate lifecycle transitions and authorization. Important changes must create timestamped intervention events.

### POST /api/interventions/{intervention_id}/events

Purpose: record a workflow event or follow-up proof.

Example request:

    {
      "event_type": "follow_up_completed",
      "note": "Academic check-in completed; pending assignments and support plan reviewed."
    }

Planned response fields:
- `id`
- `intervention_id`
- `event_type`
- `actor_role`
- `actor_label`
- `timestamp`
- `note`

Actor information and timestamps must be generated or validated by the backend, not trusted blindly from the client.

Event notes must not contain unnecessary financial details or broadly visible sensitive counselling information.

### POST /api/interventions/{intervention_id}/outcomes

Purpose: record an outcome measurement.

Example request:

    {
      "metric_name": "assessment_average",
      "baseline_value": 52,
      "baseline_date": "2026-10-10",
      "follow_up_value": 60,
      "follow_up_date": "2026-10-17",
      "outcome_classification": "improved",
      "outcome_note": "The recorded assessment average increased after the support period.",
      "evidence_quality": "demonstration"
    }

The example is illustrative; actual records must be based on data entered or seeded for the demo.

The backend must validate measurement dates, supported classification values, and metric-aware interpretation. An observed change does not establish that an intervention caused the change.

### POST /api/interventions/{intervention_id}/escalate

Optional endpoint.

Purpose: request an authorized escalation according to configured policy.

Escalation must record an event and follow a controlled routing rule. The application must not generate an uncontrolled cascade of assignments.

An in-app overdue indicator may be sufficient for the initial prototype.

## 10. Cohort Analytics

### GET /api/analytics/cohort

Purpose: retrieve permitted cohort-level summaries.

Planned metrics:
- Student counts by review-priority band.
- Open interventions by status and responsible team.
- Due, overdue, and escalated counts.
- Follow-up completion.
- Missing or stale signal counts.
- Outcome categories with their denominators.
- Cohort and program breakdowns.
- Reporting time window.

### GET /api/analytics/effectiveness

Purpose: summarize recorded intervention outcomes.

Planned breakdowns:
- Intervention type.
- Outcome classification.
- Number of interventions with measured outcomes.
- Number without sufficient evidence.
- Baseline/follow-up availability.
- Relevant reporting period.

Analytics must not claim causation from simple before-and-after values. Sensitive counselling details must not appear in broad leadership analytics.

## 11. Consent Endpoints

### GET /api/students/{student_id}/consents

Purpose: return consent information permitted for the caller's role and purpose.

### PATCH /api/students/{student_id}/consents

Purpose: update a consent record under explicitly authorized demo rules.

A consent update must identify the relevant purpose and status. The backend should preserve the consent history rather than silently overwriting the only record.

Consent for one purpose must not automatically authorize another.

These endpoints may be implemented only if required by the final UI and demo workflow. The underlying consent and authorization rules remain mandatory.

## 12. Error Response Contract

Use a consistent JSON error shape:

    {
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "The request could not be processed.",
        "details": []
      }
    }

Expected categories:

- `400 Bad Request`: invalid action or workflow transition.
- `401 Unauthorized`: missing or invalid identity when required by the implemented identity mechanism.
- `403 Forbidden`: the caller lacks permission or the action is blocked by an applicable policy.
- `404 Not Found`: the requested resource does not exist or is not available to the caller under the chosen disclosure policy.
- `422 Unprocessable Entity`: request fields fail validation.
- `500 Internal Server Error`: unexpected server-side failure.

Error responses must not disclose restricted data, internal secrets, stack traces, or private notes.

FastAPI's default validation error format may need a consistent exception handler to match this contract.

## 13. Workflow and Persistence Rules

- Core workflows must read and write database records.
- Important decisions and changes must create event records.
- The backend must validate recommendation decisions and intervention status transitions.
- Follow-up evidence must be persisted.
- Outcome records must be persisted.
- Dashboard metrics must reflect persisted records.
- Authorization checks must be enforced server-side.
- Missing data must remain distinguishable from zero.
- Synthetic and illustrative data must be clearly labelled.
- The complete risk-to-outcome scenario must remain testable through the API.

## 14. Implementation Order

1. Health and dashboard.
2. Student list, detail, and Student 360.
3. Consent and role-aware access.
4. Risk assessments.
5. Recommendations and human decisions.
6. Intervention assignment, deadlines, and events.
7. Outcomes and cohort analytics.
8. API tests and end-to-end verification.

The API should be implemented incrementally. Do not create placeholder endpoints that appear functional but return permanent hardcoded results.
