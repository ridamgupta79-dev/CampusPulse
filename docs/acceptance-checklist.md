# CampusPulse — PS6 Acceptance Checklist

## 1. Student Data and Student 360
- [ ] Use clearly labelled synthetic student records.
- [ ] Represent attendance, academics, participation, fees, skills, and faculty feedback.
- [ ] Display a consolidated Student 360 view.
- [ ] Show missing, stale, and uncertain data honestly.
- [ ] Represent consent status and purpose limitations.

## 2. Explainable Risk Indicators
- [ ] Calculate transparent, configurable prototype indicators.
- [ ] Show contributing factors, observed values, thresholds, and rationale.
- [ ] Do not treat missing data as negative evidence.
- [ ] Record assessment history and rule version.
- [ ] Allow human review; never use scores for automatic punishment or diagnosis.

## 3. Recommendations and Human Review
- [ ] Recommend relevant support based on observed signals.
- [ ] Support remedial help, mentor check-ins, parent meetings, counselling referrals, fee-support follow-up, and placement-readiness support where appropriate.
- [ ] Route recommendations to the appropriate stakeholder.
- [ ] Allow authorized users to approve, edit, override, or decline recommendations.
- [ ] Record the decision, reason, and timestamp.

## 4. Intervention Orchestration
- [ ] Assign an owner or responsible team.
- [ ] Set priority and deadline.
- [ ] Track intervention status and valid status transitions.
- [ ] Show due, overdue, and escalated work.
- [ ] Record timestamped intervention events.
- [ ] Record follow-up proof.

## 5. Outcomes and Cohort Analytics
- [ ] Record baseline and follow-up measurements where appropriate.
- [ ] Record outcome notes, classifications, and evidence quality.
- [ ] Summarize cohort-level workload, overdue actions, follow-up completion, and outcomes.
- [ ] Display denominators, missing outcomes, and time windows.
- [ ] Describe observed changes without claiming unsupported causation.

## 6. Privacy and Responsible Design
- [ ] Enforce role- and purpose-aware access in the backend.
- [ ] Restrict fee details and sensitive counselling information.
- [ ] Represent consent and required review.
- [ ] Keep manual override and contextual review available.
- [ ] Clearly label the role switcher as a demo mechanism, not production authentication.
- [ ] Avoid psychological diagnosis, automatic punishment, and misleading claims.

## 7. Technical and Demo Acceptance
- [ ] Persist core workflow data in SQLite.
- [ ] Use backend APIs for core application workflows.
- [ ] Test API validation, permissions, and error handling.
- [ ] Verify that important data survives server restarts.
- [ ] Ensure visible frontend controls perform real actions.
- [ ] Complete the full demo: risk signal → recommendation → human decision → assignment → follow-up proof → outcome dashboard.

## Final acceptance rule

CampusPulse is not complete merely because it predicts risk or displays a dashboard. The primary acceptance test is one complete, persistent, human-reviewed intervention workflow with role-aware privacy and a recorded outcome.
