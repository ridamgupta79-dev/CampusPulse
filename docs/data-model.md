# CampusPulse — Initial Data Model

## 1. Design Principles

- Use SQLite and SQLAlchemy for persistent prototype data.
- Use synthetic student records only.
- Preserve assessment, intervention, event, and outcome history.
- Represent missing or stale signals explicitly.
- Store only the minimum information required for each workflow.
- Keep fee information and sensitive counselling details restricted.
- Treat risk indicators as human-reviewed decision support, not diagnosis or punishment.

## 2. Core Entities

### Student
Purpose: central synthetic student record.

Planned fields:
- id
- synthetic_student_code
- fictional_name
- program
- department
- year_of_study
- cohort
- advisor/mentor assignment where appropriate
- created_at

### StudentConsent
Purpose: represent consent or preference by purpose.

Planned fields:
- id
- student_id
- purpose_category
- status
- recorded_at
- source_or_note

Possible statuses: granted, declined, unknown, withdrawn.

### StudentSignal
Purpose: store observations from student-success data domains.

Planned fields:
- id
- student_id
- domain
- signal_name
- numeric_value and/or text_value
- recorded_at
- source_label
- freshness_or_quality_status
- visibility_or_purpose_category where needed

Required domains:
- attendance
- academics
- participation
- fees
- skills
- faculty feedback

Missing information must not be fabricated as zero.

### RiskAssessment
Purpose: preserve an explainable review-priority assessment.

Planned fields:
- id
- student_id
- score or indicator summary
- review_priority_band
- factor_breakdown
- missing_or_stale_signal_notes
- rule_version
- assessed_at

Assessment history must be retained. The score is a prototype heuristic, not a validated prediction.

### Recommendation
Purpose: explain a proposed support action.

Planned fields:
- id
- student_id
- assessment_id, optional
- intervention_type
- rationale
- contributing_signal references or evidence summary
- intended_role_or_team
- suggested_next_step
- priority
- decision_status
- decision_reason where applicable
- created_at
- reviewed_at where applicable

Possible decisions include proposed, approved, edited, overridden, and declined. The final implementation will define valid transitions.

### Intervention
Purpose: track the assigned support workflow.

Planned fields:
- id
- student_id
- recommendation_id, optional
- intervention_type
- description
- assigned_role_or_team
- assigned_owner
- due_date
- status
- priority
- override_reason where applicable
- created_at
- updated_at

The backend will validate lifecycle transitions and derive overdue status consistently.

### InterventionEvent
Purpose: maintain an auditable event history.

Planned fields:
- id
- intervention_id
- event_type
- actor_role_or_label
- timestamp
- concise_note_or_follow_up_proof
- optional_metadata

Important decisions, assignment changes, status transitions, follow-up evidence, and escalation actions should create appropriate events.

Sensitive counselling notes must not be placed in broadly visible event text.

### InterventionOutcome
Purpose: record what was measured after an intervention.

Planned fields:
- id
- intervention_id
- metric_name
- baseline_value
- baseline_date
- follow_up_value
- follow_up_date
- outcome_classification
- outcome_note
- evidence_quality

Possible classifications:
- improved
- mixed
- no measured improvement
- worsened
- insufficient evidence

The implementation must account for metric direction, missing measurements, and evidence quality. Observed changes do not establish causation.

## 3. Relationships

- Student has many StudentConsent records.
- Student has many StudentSignal records.
- Student has many RiskAssessment records.
- Student has many Recommendation records.
- A RiskAssessment can inform multiple Recommendations.
- Student has many Intervention records.
- A Recommendation can lead to multiple Interventions if the workflow requires it.
- Intervention has many InterventionEvent records.
- Intervention has many InterventionOutcome records.

The database will use primary keys and foreign keys to maintain these relationships.

## 4. Privacy and Authorization

- Backend services enforce role and purpose restrictions.
- Financial details are available only to authorized workflows.
- Sensitive counselling notes are restricted.
- Consent for one purpose does not automatically authorize another.
- The prototype's demo-role mechanism is not production authentication.
- Risk scores never trigger automatic punishment or irreversible decisions.

## 5. Implementation Scope

This document defines the initial conceptual schema. Exact SQLAlchemy field types, constraints, indexes, deletion behavior, and response schemas will be finalized during implementation and testing.

No production-grade identity provider, external queue, or additional database service is required for the initial prototype.
